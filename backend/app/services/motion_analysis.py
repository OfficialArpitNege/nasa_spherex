"""
Motion analysis orchestrator service.

Coordinates the full two-epoch pipeline:
1. Load and validate both FITS files
2. Detect sources in each epoch
3. Compute time difference
4. Cross-match source catalogs in sky coordinates
5. Classify matches (stationary / possible-motion / moving-object-candidate)
6. Generate motion trail visualizations
7. Assemble structured MotionAnalysisResult
"""
import logging
import uuid
from pathlib import Path
from typing import Optional

from astropy.time import Time

from app.config import settings
from app.models.motion import (
    EpochInfo,
    MotionAnalysisRequest,
    MotionAnalysisResult,
    SourceStatistics,
    TimeDifference,
)
from app.services.source_detection import (
    SourceDetectionError,
    detect_sources,
    load_science_image,
)
from app.services.cross_matching import (
    CrossMatchError,
    cross_match_catalogs,
)
from app.services.visualization import generate_motion_trail

logger = logging.getLogger(__name__)


class MotionAnalysisError(Exception):
    """Raised when the motion analysis pipeline encounters an unrecoverable error."""
    pass


def compute_time_difference(
    timestamp_utc_1: Optional[str],
    timestamp_utc_2: Optional[str],
    timestamp_mjd_1: Optional[float],
    timestamp_mjd_2: Optional[float],
) -> TimeDifference:
    """
    Computes the elapsed time between two observation epochs.

    Tries UTC ISO strings first, falls back to MJD values.
    Uses Astropy Time for precise conversion.

    Returns:
        TimeDifference with seconds, hours, and days.

    Raises:
        MotionAnalysisError: if neither UTC nor MJD timestamps are available.
    """
    t1: Optional[Time] = None
    t2: Optional[Time] = None

    # Try UTC strings first
    if timestamp_utc_1:
        try:
            t1 = Time(timestamp_utc_1, format="iso", scale="utc")
        except Exception:
            pass
    if timestamp_utc_2:
        try:
            t2 = Time(timestamp_utc_2, format="iso", scale="utc")
        except Exception:
            pass

    # Fallback to MJD
    if t1 is None and timestamp_mjd_1 is not None:
        try:
            t1 = Time(timestamp_mjd_1, format="mjd")
        except Exception:
            pass
    if t2 is None and timestamp_mjd_2 is not None:
        try:
            t2 = Time(timestamp_mjd_2, format="mjd")
        except Exception:
            pass

    if t1 is None or t2 is None:
        raise MotionAnalysisError(
            "Cannot compute time difference: at least one epoch is missing "
            "both UTC and MJD timestamps."
        )

    # Compute difference (absolute value; order doesn't matter for displacement)
    dt = abs((t2 - t1).sec)  # in seconds

    return TimeDifference(
        seconds=round(dt, 3),
        hours=round(dt / 3600.0, 6),
        days=round(dt / 86400.0, 6),
    )


def run_motion_analysis(request: MotionAnalysisRequest) -> MotionAnalysisResult:
    """
    Execute the full two-epoch motion analysis pipeline.

    This is the main orchestrator that:
    1. Validates inputs and FITS files
    2. Loads science images and WCS from both epochs
    3. Detects sources in each epoch using DAOStarFinder
    4. Computes time difference between epochs
    5. Cross-matches source catalogs using sky coordinates
    6. Classifies each match as stationary/possible-motion/candidate
    7. Generates motion trail visualizations for candidates
    8. Assembles and returns the complete MotionAnalysisResult

    Parameters:
        request: MotionAnalysisRequest with FITS paths, timestamps, and configuration

    Returns:
        MotionAnalysisResult with full pipeline output

    Raises:
        MotionAnalysisError: for pipeline-level failures
    """
    analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"
    warnings_list = []

    logger.info("Starting motion analysis %s", analysis_id)
    logger.info("  Epoch 1: %s (%s)", request.observation_id_1, request.fits_path_1)
    logger.info("  Epoch 2: %s (%s)", request.observation_id_2, request.fits_path_2)

    # Validate FITS paths
    fits_path_1 = Path(request.fits_path_1)
    fits_path_2 = Path(request.fits_path_2)

    if not fits_path_1.exists():
        raise MotionAnalysisError(f"FITS file for epoch 1 not found: {fits_path_1}")
    if not fits_path_2.exists():
        raise MotionAnalysisError(f"FITS file for epoch 2 not found: {fits_path_2}")

    epoch_1_ra = request.ra
    epoch_1_dec = request.dec
    epoch_2_ra = request.ra_2 if request.ra_2 is not None else request.ra
    epoch_2_dec = request.dec_2 if request.dec_2 is not None else request.dec

    # === Step 1: Load science images and WCS ===
    try:
        data_1, wcs_1, meta_1 = load_science_image(fits_path_1, epoch_1_ra, epoch_1_dec)
    except SourceDetectionError as e:
        raise MotionAnalysisError(f"Failed to load epoch 1 science image: {e}") from e

    try:
        data_2, wcs_2, meta_2 = load_science_image(fits_path_2, epoch_2_ra, epoch_2_dec)
    except SourceDetectionError as e:
        raise MotionAnalysisError(f"Failed to load epoch 2 science image: {e}") from e

    # Determine bandpass from request or FITS header
    bandpass_1 = request.bandpass_1 or meta_1.get("bandpass")
    bandpass_2 = request.bandpass_2 or meta_2.get("bandpass")

    # Bandpass compatibility check
    if bandpass_1 and bandpass_2 and bandpass_1 != bandpass_2:
        warnings_list.append(
            f"BANDPASS MISMATCH: Epoch 1 uses {bandpass_1}, Epoch 2 uses {bandpass_2}. "
            f"Different SPHEREx detector channels observe different infrared wavelengths. "
            f"Brightness/flux differences between epochs should NOT be interpreted as motion evidence. "
            f"Only positional information (RA/DEC centroids) is used for motion analysis."
        )
        logger.warning("Cross-band comparison: %s vs %s", bandpass_1, bandpass_2)

    # Build epoch info
    epoch_1_info = EpochInfo(
        observation_id=request.observation_id_1,
        timestamp_utc=request.timestamp_utc_1,
        timestamp_mjd=request.timestamp_mjd_1,
        ra_center=epoch_1_ra,
        dec_center=epoch_1_dec,
        bandpass=bandpass_1,
        fits_path=str(fits_path_1),
        image_shape=list(data_1.shape),
        wcs_available=True,
        wcs_projection=meta_1.get("wcs_projection"),
        sources_detected=0,
    )

    epoch_2_info = EpochInfo(
        observation_id=request.observation_id_2,
        timestamp_utc=request.timestamp_utc_2,
        timestamp_mjd=request.timestamp_mjd_2,
        ra_center=epoch_2_ra,
        dec_center=epoch_2_dec,
        bandpass=bandpass_2,
        fits_path=str(fits_path_2),
        image_shape=list(data_2.shape),
        wcs_available=True,
        wcs_projection=meta_2.get("wcs_projection"),
        sources_detected=0,
    )

    # === Step 2: Compute time difference ===
    try:
        time_diff = compute_time_difference(
            request.timestamp_utc_1, request.timestamp_utc_2,
            request.timestamp_mjd_1, request.timestamp_mjd_2
        )
    except MotionAnalysisError as e:
        raise

    if time_diff.days < 0.001:
        raise MotionAnalysisError(
            f"Insufficient time difference between epochs: {time_diff.seconds:.1f} seconds. "
            "Meaningful motion analysis requires observations separated by at least minutes."
        )

    logger.info(
        "Time difference: %.3f days (%.1f hours, %.0f seconds)",
        time_diff.days, time_diff.hours, time_diff.seconds
    )

    # === Step 3: Detect sources in each epoch ===
    variance_1 = meta_1.get("variance")
    variance_2 = meta_2.get("variance")

    try:
        sources_1 = detect_sources(
            data=data_1,
            wcs=wcs_1,
            detection_sigma=request.detection_sigma,
            variance=variance_1,
        )
    except SourceDetectionError as e:
        raise MotionAnalysisError(f"Source detection failed for epoch 1: {e}") from e

    try:
        sources_2 = detect_sources(
            data=data_2,
            wcs=wcs_2,
            detection_sigma=request.detection_sigma,
            variance=variance_2,
        )
    except SourceDetectionError as e:
        raise MotionAnalysisError(f"Source detection failed for epoch 2: {e}") from e

    epoch_1_info.sources_detected = len(sources_1)
    epoch_2_info.sources_detected = len(sources_2)

    logger.info("Sources detected: epoch 1 = %d, epoch 2 = %d", len(sources_1), len(sources_2))

    if len(sources_1) == 0:
        warnings_list.append(
            f"No sources detected in epoch 1 ({request.observation_id_1}) above "
            f"{request.detection_sigma}-sigma threshold."
        )
    if len(sources_2) == 0:
        warnings_list.append(
            f"No sources detected in epoch 2 ({request.observation_id_2}) above "
            f"{request.detection_sigma}-sigma threshold."
        )

    # === Step 4: Cross-match catalogs ===
    try:
        (
            candidates, matched_count, stationary_count,
            possible_motion_count, candidate_count, unmatched_1
        ) = cross_match_catalogs(
            sources_1=sources_1,
            sources_2=sources_2,
            match_tolerance_arcsec=request.match_tolerance_arcsec,
            elapsed_time_days=time_diff.days,
            motion_threshold_arcsec=request.motion_threshold_arcsec,
            candidate_threshold_arcsec=request.candidate_threshold_arcsec,
        )
    except CrossMatchError as e:
        raise MotionAnalysisError(f"Cross-matching failed: {e}") from e

    unmatched_2 = len(sources_2) - (matched_count)
    # Correct for sources in epoch 2 that didn't get matched due to many-to-one prevention
    if unmatched_2 < 0:
        unmatched_2 = 0

    stats = SourceStatistics(
        sources_detected_epoch_1=len(sources_1),
        sources_detected_epoch_2=len(sources_2),
        matched_sources=matched_count,
        stationary_count=stationary_count,
        possible_motion_count=possible_motion_count,
        candidate_count=candidate_count,
        unmatched_epoch_1=unmatched_1,
        unmatched_epoch_2=unmatched_2,
    )

    if matched_count == 0 and len(sources_1) > 0 and len(sources_2) > 0:
        warnings_list.append(
            f"No cross-matches found between {len(sources_1)} sources in epoch 1 and "
            f"{len(sources_2)} sources in epoch 2 within {request.match_tolerance_arcsec}\" tolerance. "
            "This could indicate a WCS offset, pointing difference, or insufficient overlap."
        )

    # === Step 5: Generate motion trail visualizations ===
    motion_dir = Path(settings.CACHE_DIR) / "motion"
    motion_dir.mkdir(parents=True, exist_ok=True)

    try:
        trail_paths = generate_motion_trail(
            candidates=candidates,
            wcs_1=wcs_1,
            wcs_2=wcs_2,
            data_1=data_1,
            data_2=data_2,
            observation_id_1=request.observation_id_1,
            observation_id_2=request.observation_id_2,
            timestamp_utc_1=request.timestamp_utc_1,
            timestamp_utc_2=request.timestamp_utc_2,
            bandpass_1=bandpass_1,
            bandpass_2=bandpass_2,
            output_dir=motion_dir,
            analysis_id=analysis_id,
        )

        # Assign motion trail paths to candidates
        # The overview plot is at index 0; per-candidate panels follow
        motion_candidates = [
            c for c in candidates
            if c.status in ("moving-object-candidate", "possible-motion")
        ]
        for i, c in enumerate(motion_candidates):
            # Panel paths start at index 1 (after overview)
            panel_idx = 1 + i
            if panel_idx < len(trail_paths):
                c.motion_trail_path = trail_paths[panel_idx]

    except Exception as e:
        logger.warning("Visualization generation encountered an error: %s", e)
        warnings_list.append(f"Motion trail visualization partially failed: {e}")

    # === Step 6: Assemble result ===
    detection_params = {
        "detection_sigma": request.detection_sigma,
        "match_tolerance_arcsec": request.match_tolerance_arcsec,
        "motion_threshold_arcsec": request.motion_threshold_arcsec,
        "candidate_threshold_arcsec": request.candidate_threshold_arcsec,
        "source_detection_method": "photutils.DAOStarFinder",
        "cross_match_method": "astropy.coordinates.SkyCoord.match_to_catalog_sky",
        "wcs_method": "astropy.wcs.WCS (celestial TAN-SIP)",
        "angular_separation_method": "astropy.coordinates.SkyCoord.separation (Vincenty spherical)",
        "position_angle_method": "astropy.coordinates.SkyCoord.position_angle",
        "spherex_pixel_scale_arcsec": 6.2,
    }

    # Add scientific limitation warnings
    warnings_list.append(
        "SPHEREx cutout images are 29×29 pixels (~3 arcmin). Source detection and "
        "cross-matching is limited to this small field of view."
    )
    warnings_list.append(
        "Centroid uncertainty estimates are approximate, based on FWHM/SNR. "
        "Sub-pixel accuracy depends on actual PSF shape and background structure."
    )
    if candidate_count == 0 and matched_count > 0:
        warnings_list.append(
            "No moving-object candidates identified. All matched sources are consistent "
            "with stationary positions or have insufficient quality for candidate classification."
        )

    result = MotionAnalysisResult(
        analysis_id=analysis_id,
        observation_1=epoch_1_info,
        observation_2=epoch_2_info,
        time_difference=time_diff,
        source_statistics=stats,
        candidates=candidates,
        detection_parameters=detection_params,
        warnings=warnings_list,
    )

    logger.info(
        "Motion analysis %s complete: %d sources matched, %d candidates identified",
        analysis_id, matched_count, candidate_count
    )

    return result
