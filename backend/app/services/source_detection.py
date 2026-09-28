"""
Source detection service for SPHEREx science images.

Uses Photutils for background estimation and source detection
with DAOStarFinder, followed by Astropy WCS conversion of
pixel centroids to sky coordinates (RA, DEC).

Designed for 29×29 pixel SPHEREx cutouts (~0.05° at 6.2 arcsec/pixel).
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from photutils.detection import DAOStarFinder

from app.models.motion import DetectedSource

logger = logging.getLogger(__name__)


class SourceDetectionError(Exception):
    """Raised when source detection fails."""
    pass


# SPHEREx pixel scale: ~6.2 arcsec/pixel
# Typical PSF FWHM is ~6.2 arcsec = ~1 pixel in cutout images
SPHEREX_PIXEL_SCALE_ARCSEC = 6.2
DEFAULT_FWHM_PIXELS = 1.5  # Conservative initial estimate for DAOStarFinder


def load_science_image(
    fits_path: Path,
    center_ra: float,
    center_dec: float
) -> Tuple[np.ndarray, WCS, Dict[str, Any]]:
    """
    Opens a SPHEREx MEF FITS file and extracts the science IMAGE data,
    WCS, and VARIANCE (if available).

    Reuses the same HDU identification logic as fits_service.inspect_fits_cutout:
    1. Look for extension named 'IMAGE' with 2D data
    2. Fallback to first 2D HDU with celestial WCS keywords

    Returns:
        (data, wcs, metadata_dict)

    Raises:
        SourceDetectionError: if no suitable science image or WCS is found.
    """
    if not fits_path.exists():
        raise SourceDetectionError(f"FITS file not found: {fits_path}")

    try:
        hdul = fits.open(fits_path)
    except Exception as e:
        raise SourceDetectionError(f"Cannot open FITS file {fits_path.name}: {e}") from e

    # Locate science IMAGE HDU (identical logic to fits_service.py)
    science_hdu = None
    science_idx = -1
    for idx, hdu in enumerate(hdul):
        if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 2:
            if hdu.name.upper() == "IMAGE":
                science_hdu = hdu
                science_idx = idx
                break

    if science_hdu is None:
        for idx, hdu in enumerate(hdul):
            if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 2:
                if hdu.header and "CTYPE1" in hdu.header and "CRVAL1" in hdu.header:
                    science_hdu = hdu
                    science_idx = idx
                    break

    if science_hdu is None:
        hdul.close()
        raise SourceDetectionError(
            f"No valid 2D science IMAGE extension found in {fits_path.name}"
        )

    data = np.array(science_hdu.data, dtype=np.float64, copy=True)
    header = science_hdu.header

    # Construct and validate WCS
    try:
        wcs = WCS(header)
        if not wcs.is_celestial:
            hdul.close()
            raise SourceDetectionError(
                f"WCS in {fits_path.name} HDU {science_idx} is not celestial "
                f"(CTYPE1={header.get('CTYPE1', 'N/A')})"
            )
    except SourceDetectionError:
        raise
    except Exception as e:
        hdul.close()
        raise SourceDetectionError(
            f"Failed to construct celestial WCS from {fits_path.name} HDU {science_idx}: {e}"
        ) from e

    # Extract variance data if available (HDU 3 = VARIANCE in SPHEREx MEF)
    variance = None
    for hdu in hdul:
        if hdu.name.upper() == "VARIANCE" and hdu.data is not None:
            if hdu.data.shape == data.shape:
                variance = np.array(hdu.data, dtype=np.float64, copy=True)
                break

    # Extract metadata from headers
    primary_hdr = hdul[0].header if len(hdul) > 0 else {}
    date_obs = header.get("DATE-OBS", primary_hdr.get("DATE-OBS", None))
    mjd_obs = header.get("MJD-OBS", primary_hdr.get("MJD-OBS", None))
    bandpass = header.get("BANDPASS", primary_hdr.get("BANDPASS", None))
    exposure = header.get("XPOSURE", header.get("EXPTIME", primary_hdr.get("EXPTIME", None)))

    hdul.close()

    metadata = {
        "science_index": science_idx,
        "image_shape": list(data.shape),
        "date_obs": str(date_obs) if date_obs else None,
        "mjd_obs": float(mjd_obs) if mjd_obs is not None else None,
        "bandpass": str(bandpass) if bandpass else None,
        "exposure_time": float(exposure) if exposure is not None else None,
        "variance": variance,
        "wcs_projection": f"{header.get('CTYPE1', 'N/A')}/{header.get('CTYPE2', 'N/A')}",
    }

    return data, wcs, metadata


def preprocess_image(
    data: np.ndarray,
    variance: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, float, float, float]:
    """
    Preprocesses a science image for source detection:
    1. Replaces non-finite values (NaN, Inf) with local median
    2. Computes sigma-clipped background statistics

    Returns:
        (cleaned_data, background_mean, background_median, background_std)
    """
    cleaned = data.copy()

    # Replace non-finite pixels with 0 (will be masked during detection)
    non_finite_mask = ~np.isfinite(cleaned)
    n_bad = int(np.count_nonzero(non_finite_mask))
    if n_bad > 0:
        logger.info("Replacing %d non-finite pixels in %s image", n_bad, cleaned.shape)
        cleaned[non_finite_mask] = 0.0

    # Sigma-clipped statistics for background estimation
    # For small 29×29 SPHEREx cutouts, use the whole image
    mean, median, std = sigma_clipped_stats(cleaned, sigma=3.0, maxiters=10)

    logger.info(
        "Background statistics: mean=%.4f, median=%.4f, std=%.4f",
        mean, median, std
    )

    return cleaned, float(mean), float(median), float(std)


def detect_sources(
    data: np.ndarray,
    wcs: WCS,
    detection_sigma: float = 3.0,
    fwhm_pixels: float = DEFAULT_FWHM_PIXELS,
    variance: Optional[np.ndarray] = None,
    edge_margin_pixels: int = 1
) -> List[DetectedSource]:
    """
    Detects point sources in a preprocessed science image using DAOStarFinder.

    Algorithm:
    1. Estimate background via sigma-clipped statistics
    2. Subtract background median
    3. Run DAOStarFinder with threshold = detection_sigma × background_std
    4. Filter edge sources
    5. Convert pixel centroids to sky coordinates via WCS
    6. Estimate SNR from peak value and background noise (or variance if available)

    Parameters:
        data: 2D science image array (float64)
        wcs: Astropy celestial WCS object
        detection_sigma: Detection threshold in multiples of background sigma
        fwhm_pixels: Expected source FWHM in pixels
        variance: Optional variance map (same shape as data)
        edge_margin_pixels: Reject sources within this many pixels of image edge

    Returns:
        List of DetectedSource objects with pixel + sky coordinates
    """
    if data.size == 0:
        raise SourceDetectionError("Science image has zero pixels")

    # Preprocess
    cleaned, bg_mean, bg_median, bg_std = preprocess_image(data, variance)

    if bg_std <= 0.0:
        logger.warning("Background std is zero or negative (%.4f). Image may be uniform.", bg_std)
        return []

    # Background-subtracted image
    bgsub = cleaned - bg_median

    # Detection threshold
    threshold = detection_sigma * bg_std
    logger.info(
        "DAOStarFinder: sigma=%.1f, threshold=%.4f, FWHM=%.2f px",
        detection_sigma, threshold, fwhm_pixels
    )

    # Run DAOStarFinder
    finder = DAOStarFinder(fwhm=fwhm_pixels, threshold=threshold)
    try:
        sources_table = finder(bgsub)
    except Exception as e:
        raise SourceDetectionError(f"DAOStarFinder failed: {e}") from e

    if sources_table is None or len(sources_table) == 0:
        logger.info("No sources detected above %.1f-sigma threshold", detection_sigma)
        return []

    logger.info("DAOStarFinder detected %d raw sources", len(sources_table))

    # Filter edge sources
    height, width = data.shape
    detected_sources: List[DetectedSource] = []
    source_counter = 0

    # Column names changed in photutils ≥2.0: xcentroid → x_centroid
    colnames = sources_table.colnames
    x_col = "x_centroid" if "x_centroid" in colnames else "xcentroid"
    y_col = "y_centroid" if "y_centroid" in colnames else "ycentroid"

    for row in sources_table:
        x_centroid = float(row[x_col])
        y_centroid = float(row[y_col])
        peak = float(row["peak"])
        flux = float(row["flux"])

        # Quality flags
        flags: List[str] = []

        # Edge check
        if (x_centroid < edge_margin_pixels or
            x_centroid > width - 1 - edge_margin_pixels or
            y_centroid < edge_margin_pixels or
            y_centroid > height - 1 - edge_margin_pixels):
            flags.append("edge_source")

        # Convert pixel to sky coordinates via WCS
        try:
            sky_coords = wcs.pixel_to_world_values(x_centroid, y_centroid)
            ra = float(sky_coords[0])
            dec = float(sky_coords[1])
        except Exception as e:
            logger.warning(
                "WCS conversion failed for source at (%.2f, %.2f): %s",
                x_centroid, y_centroid, e
            )
            flags.append("wcs_conversion_failed")
            continue

        # Check for NaN sky coordinates
        if not np.isfinite(ra) or not np.isfinite(dec):
            logger.warning(
                "WCS produced non-finite coordinates for pixel (%.2f, %.2f): RA=%.4f, DEC=%.4f",
                x_centroid, y_centroid, ra, dec
            )
            flags.append("invalid_sky_coordinates")
            continue

        flags.append("valid_wcs")

        # Estimate SNR
        # Method 1: Use variance map if available
        snr = None
        centroid_uncertainty_arcsec = None
        ix, iy = int(round(x_centroid)), int(round(y_centroid))

        if variance is not None and 0 <= iy < height and 0 <= ix < width:
            var_at_source = variance[iy, ix]
            if np.isfinite(var_at_source) and var_at_source > 0:
                noise = np.sqrt(var_at_source)
                snr = peak / noise
                # Centroid uncertainty: ~FWHM / (2 * SNR) in pixels, convert to arcsec
                if snr > 0:
                    centroid_unc_px = fwhm_pixels / (2.0 * snr)
                    centroid_uncertainty_arcsec = centroid_unc_px * SPHEREX_PIXEL_SCALE_ARCSEC
        else:
            # Fallback: estimate SNR from peak / background_std
            if bg_std > 0:
                snr = peak / bg_std
                if snr > 0:
                    centroid_unc_px = fwhm_pixels / (2.0 * snr)
                    centroid_uncertainty_arcsec = centroid_unc_px * SPHEREX_PIXEL_SCALE_ARCSEC

        if snr is not None:
            if snr >= 10.0:
                flags.append("high_snr")
            elif snr >= 3.0:
                flags.append("medium_snr")
            else:
                flags.append("low_snr")

        source_counter += 1
        detected_sources.append(DetectedSource(
            source_id=source_counter,
            x=round(x_centroid, 4),
            y=round(y_centroid, 4),
            ra=round(ra, 8),
            dec=round(dec, 8),
            flux=round(flux, 6) if np.isfinite(flux) else None,
            peak_value=round(peak, 6) if np.isfinite(peak) else None,
            snr=round(snr, 2) if snr is not None and np.isfinite(snr) else None,
            fwhm_pixels=round(fwhm_pixels, 2),
            quality_flags=flags
        ))

    logger.info(
        "Source detection complete: %d valid sources from %d raw detections",
        len(detected_sources), len(sources_table)
    )

    return detected_sources
