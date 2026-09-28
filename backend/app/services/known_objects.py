"""
Known moving object service for SPHEREx validation.

Supports testing the SPHEREx moving-object analysis pipeline against official
NASA/IPAC IRSA observation tables of confirmed moving objects, specifically
the interstellar comet 3I/ATLAS.

Uses the official IRSA 3I/ATLAS table:
https://irsa.ipac.caltech.edu/data/SPHEREx/docs/comet3iatlas/obscore_3I_Atlas.vot
"""
from enum import Enum
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io.votable import parse_single_table
from astropy.time import Time
import numpy as np
from pydantic import BaseModel, Field
import requests

from app.config import settings
from app.models.motion import DetectedSource
from app.models.search import SPHERExObservationModel
from app.services.cross_matching import compute_angular_separation

logger = logging.getLogger(__name__)

IRSA_3I_ATLAS_VOTABLE_URL = (
    "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/comet3iatlas/obscore_3I_Atlas.vot"
)


class KnownObjectError(Exception):
    """Raised when fetching or parsing known-object observation data fails."""
    pass


class KnownObjectObservation(BaseModel):
    """
    Normalized metadata for a single observation of a known moving object
    from an official IRSA observation table.
    """
    obs_id: str = Field(..., description="SPHEREx observation ID")
    observation_time_utc: str = Field(..., description="UTC timestamp in ISO format")
    observation_time_mjd: float = Field(..., description="Observation start time in MJD")
    spherex_detector: str = Field(..., description="SPHEREx detector channel (e.g. D3)")
    bandpass: str = Field(..., description="Formatted bandpass string (e.g. SPHEREx-D3)")
    comet_ra: float = Field(..., description="Predicted comet RA from IRSA ephemeris in degrees")
    comet_dec: float = Field(..., description="Predicted comet DEC from IRSA ephemeris in degrees")
    pointing_ra: float = Field(..., description="Observation telescope pointing center RA in degrees")
    pointing_dec: float = Field(..., description="Observation telescope pointing center DEC in degrees")
    exposure_time_sec: float = Field(..., description="Exposure duration in seconds")
    data_access_url: str = Field(..., description="Datalink URL for data access")
    dataproduct_type: str = Field("image", description="Data product type")


def fetch_known_object_table(
    cache_dir: Optional[Path] = None,
    url: str = IRSA_3I_ATLAS_VOTABLE_URL,
    refresh: bool = False,
    timeout: int = 45,
) -> Path:
    """
    Downloads and caches the official IRSA 3I/ATLAS VOTable.
    Returns the path to the cached local VOTable file.
    """
    if cache_dir is None:
        cache_dir = Path(settings.CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)

    votable_path = cache_dir / "obscore_3I_Atlas.vot"

    if votable_path.exists() and votable_path.stat().st_size > 1000 and not refresh:
        logger.info("Using cached 3I/ATLAS VOTable: %s", votable_path)
        return votable_path

    logger.info("Downloading official IRSA 3I/ATLAS VOTable from %s...", url)
    headers = {
        "User-Agent": "SPHEREx-Moving-Object-Explorer/0.1.0 (NASA Space Apps 2026)",
        "Accept": "application/x-votable+xml, text/xml, */*",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        if votable_path.exists() and votable_path.stat().st_size > 1000:
            logger.warning("Network request failed (%s); falling back to cached VOTable.", e)
            return votable_path
        raise KnownObjectError(
            f"Failed to download official IRSA 3I/ATLAS observation table: {e}"
        ) from e

    try:
        votable_path.write_bytes(response.content)
        logger.info("Saved 3I/ATLAS VOTable to %s (%d bytes)", votable_path, len(response.content))
    except Exception as e:
        raise KnownObjectError(f"Failed to write VOTable to local cache: {e}") from e

    return votable_path


def parse_known_object_table(votable_path: Path) -> List[KnownObjectObservation]:
    """
    Parses the official IRSA 3I/ATLAS VOTable and returns normalized observations.
    """
    if not votable_path.exists():
        raise KnownObjectError(f"VOTable file does not exist: {votable_path}")

    try:
        votable = parse_single_table(str(votable_path))
        table_data = votable.array
    except Exception as e:
        raise KnownObjectError(f"Failed to parse IRSA VOTable: {e}") from e

    observations: List[KnownObjectObservation] = []

    def _str_val(v: Any) -> str:
        if isinstance(v, bytes):
            return v.decode("utf-8", errors="replace").strip()
        return str(v).strip()

    for row in table_data:
        try:
            obs_id = _str_val(row["obs_id"])
            detector = _str_val(row["spherex_detector"])
            t_min = float(row["t_min"])
            t_exptime = float(row["t_exptime"])
            comet_ra = float(row["comet_ra"])
            comet_dec = float(row["comet_dec"])
            pointing_ra = float(row["s_ra"])
            pointing_dec = float(row["s_dec"])
            access_url = _str_val(row["access_url"])

            # Compute UTC ISO string from MJD
            utc_str = Time(t_min, format="mjd", scale="utc").iso

            bandpass = f"SPHEREx-{detector}" if not detector.startswith("SPHEREx-") else detector

            observations.append(
                KnownObjectObservation(
                    obs_id=obs_id,
                    observation_time_utc=utc_str,
                    observation_time_mjd=t_min,
                    spherex_detector=detector,
                    bandpass=bandpass,
                    comet_ra=comet_ra,
                    comet_dec=comet_dec,
                    pointing_ra=pointing_ra,
                    pointing_dec=pointing_dec,
                    exposure_time_sec=t_exptime,
                    data_access_url=access_url,
                    dataproduct_type="image",
                )
            )
        except Exception as e:
            logger.debug("Skipping unparseable row in VOTable: %s", e)
            continue

    if not observations:
        raise KnownObjectError("No valid observations could be extracted from IRSA VOTable.")

    return observations


def get_known_object_pair(
    obs_id_1: str = "2025W32_2D_0017_2",
    obs_id_2: str = "2025W32_2D_0017_4",
    detector: str = "D3",
    cache_dir: Optional[Path] = None,
    votable_path: Optional[Path] = None,
) -> Tuple[KnownObjectObservation, KnownObjectObservation]:
    """
    Finds and returns the validation observation pair from the official 3I/ATLAS table.
    Defaults to the confirmed validation pair on 2025-08-07 using detector channel D3.
    """
    if votable_path is None:
        votable_path = fetch_known_object_table(cache_dir=cache_dir)

    all_obs = parse_known_object_table(votable_path)

    obs1: Optional[KnownObjectObservation] = None
    obs2: Optional[KnownObjectObservation] = None

    for obs in all_obs:
        if obs.obs_id == obs_id_1 and obs.spherex_detector == detector:
            obs1 = obs
        elif obs.obs_id == obs_id_2 and obs.spherex_detector == detector:
            obs2 = obs

    if obs1 is None:
        raise KnownObjectError(
            f"Observation {obs_id_1} with detector {detector} not found in 3I/ATLAS table."
        )
    if obs2 is None:
        raise KnownObjectError(
            f"Observation {obs_id_2} with detector {detector} not found in 3I/ATLAS table."
        )

    return obs1, obs2


def to_spherex_observation(known_obs: KnownObjectObservation) -> SPHERExObservationModel:
    """
    Converts a KnownObjectObservation into a SPHERExObservationModel for compatibility
    with existing cutout retrieval and WCS services.
    """
    return SPHERExObservationModel(
        observation_id=known_obs.obs_id,
        ra=known_obs.pointing_ra,
        dec=known_obs.pointing_dec,
        bandpass=known_obs.bandpass,
        observation_time_mjd=known_obs.observation_time_mjd,
        observation_time_utc=known_obs.observation_time_utc,
        exposure_time_sec=known_obs.exposure_time_sec,
        dataproduct_type=known_obs.dataproduct_type,
        obs_collection="spherex_qr2",
        data_access_url=known_obs.data_access_url,
    )


class DetectionStatus(str, Enum):
    """
    Standardized detection status for known-object target association.
    """
    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    AMBIGUOUS = "AMBIGUOUS"


class TargetAssociationResult(BaseModel):
    """
    Structured result model for associating detected sources with a predicted known-object position.
    Replaces loosely structured dictionaries and guarantees scientific rigor.
    """
    target_name: str = Field("3I/ATLAS", description="Name of the target object")
    predicted_ra: float = Field(..., description="Externally supplied predicted RA in degrees")
    predicted_dec: float = Field(..., description="Externally supplied predicted DEC in degrees")
    predicted_x: Optional[float] = Field(None, description="Predicted pixel X coordinate if WCS provided")
    predicted_y: Optional[float] = Field(None, description="Predicted pixel Y coordinate if WCS provided")

    status: DetectionStatus = Field(..., description="Detection status: DETECTED, NOT_DETECTED, or AMBIGUOUS")

    measured_ra: Optional[float] = Field(None, description="Independently measured centroid RA in degrees")
    measured_dec: Optional[float] = Field(None, description="Independently measured centroid DEC in degrees")
    measured_x: Optional[float] = Field(None, description="Measured centroid pixel X coordinate")
    measured_y: Optional[float] = Field(None, description="Measured centroid pixel Y coordinate")

    separation_arcsec: Optional[float] = Field(
        None,
        description="Spherical angular separation between predicted and measured positions in arcseconds",
    )
    pixel_separation: Optional[float] = Field(
        None,
        description="Pixel distance between predicted and measured positions",
    )
    snr: Optional[float] = Field(
        None,
        description="Signal-to-noise ratio of matched detected source",
    )

    matched_source: Optional[DetectedSource] = Field(None, description="Matched DetectedSource object")
    candidate_sources_in_tolerance: int = Field(0, description="Count of detected sources falling within max_separation_arcsec")
    min_separation_arcsec: Optional[float] = Field(None, description="Angular separation to closest detected source, even if outside tolerance")
    max_separation_arcsec: float = Field(15.0, description="Configured maximum separation tolerance in arcseconds")
    evaluation_note: str = Field(..., description="Human-readable evaluation note explaining detection status")


# Type alias for known-object detection result model
KnownObjectDetectionResult = TargetAssociationResult


def associate_target_source(
    detected_sources: List[DetectedSource],
    predicted_ra: float,
    predicted_dec: float,
    max_separation_arcsec: float = 15.0,
    target_name: str = "3I/ATLAS",
    wcs: Optional[Any] = None,
    predicted_x: Optional[float] = None,
    predicted_y: Optional[float] = None,
) -> TargetAssociationResult:
    """
    Reusable target-association service for known moving objects.

    Accepts:
      - detected_sources: List[DetectedSource]
      - predicted_ra: float (degrees)
      - predicted_dec: float (degrees)
      - max_separation_arcsec: float (default: 15.0 arcsec)
      - target_name: str (default: "3I/ATLAS")
      - wcs: optional Astropy WCS for pixel conversion
      - predicted_x, predicted_y: optional predicted pixel coordinates

    Computes spherical angular separation to all detected sources using Astropy SkyCoord.
    Selects the nearest valid detected source within tolerance.

    Returns:
      TargetAssociationResult with status:
        - DETECTED: exactly one detected source within max_separation_arcsec.
        - NOT_DETECTED: zero detected sources within max_separation_arcsec. Does not invent a measured position.
        - AMBIGUOUS: multiple detected sources within max_separation_arcsec.
    """
    # Convert predicted sky position to pixel position if WCS provided
    if wcs is not None and (predicted_x is None or predicted_y is None):
        try:
            px, py = wcs.world_to_pixel_values(predicted_ra, predicted_dec)
            if not (np.isnan(px) or np.isnan(py)):
                predicted_x = float(px)
                predicted_y = float(py)
        except Exception as e:
            logger.debug("Could not calculate predicted pixel coordinates from WCS: %s", e)

    # If no detected sources at all
    if not detected_sources:
        return TargetAssociationResult(
            target_name=target_name,
            predicted_ra=predicted_ra,
            predicted_dec=predicted_dec,
            predicted_x=predicted_x,
            predicted_y=predicted_y,
            status=DetectionStatus.NOT_DETECTED,
            measured_ra=None,
            measured_dec=None,
            measured_x=None,
            measured_y=None,
            separation_arcsec=None,
            pixel_separation=None,
            snr=None,
            matched_source=None,
            candidate_sources_in_tolerance=0,
            min_separation_arcsec=None,
            max_separation_arcsec=max_separation_arcsec,
            evaluation_note="Target not detected: no sources detected in image",
        )

    # Compute spherical angular separation using Astropy SkyCoord
    pred_coord = SkyCoord(ra=predicted_ra * u.deg, dec=predicted_dec * u.deg, frame="icrs")
    source_coords = SkyCoord(
        ra=[s.ra for s in detected_sources] * u.deg,
        dec=[s.dec for s in detected_sources] * u.deg,
        frame="icrs",
    )
    separations = pred_coord.separation(source_coords).arcsec
    sep_array = np.atleast_1d(separations)

    paired: List[Tuple[DetectedSource, float]] = []
    for s, sep_val in zip(detected_sources, sep_array):
        paired.append((s, float(sep_val)))
    paired.sort(key=lambda item: item[1])

    closest_source, min_sep = paired[0]
    sources_in_tol = [item for item in paired if item[1] <= max_separation_arcsec]
    n_in_tol = len(sources_in_tol)

    if n_in_tol == 0:
        return TargetAssociationResult(
            target_name=target_name,
            predicted_ra=predicted_ra,
            predicted_dec=predicted_dec,
            predicted_x=predicted_x,
            predicted_y=predicted_y,
            status=DetectionStatus.NOT_DETECTED,
            measured_ra=None,
            measured_dec=None,
            measured_x=None,
            measured_y=None,
            separation_arcsec=None,
            pixel_separation=None,
            snr=None,
            matched_source=None,
            candidate_sources_in_tolerance=0,
            min_separation_arcsec=min_sep,
            max_separation_arcsec=max_separation_arcsec,
            evaluation_note=(
                f"Target not detected within {max_separation_arcsec:.1f} arcsec tolerance "
                f"(nearest detected source is {min_sep:.2f} arcsec away)"
            ),
        )

    # Nearest valid detected source within tolerance
    matched_s, sep_val = sources_in_tol[0]

    # Calculate pixel separation if predicted pixel coords available
    pix_sep = None
    if predicted_x is not None and predicted_y is not None:
        pix_sep = float(np.hypot(matched_s.x - predicted_x, matched_s.y - predicted_y))

    if n_in_tol == 1:
        status = DetectionStatus.DETECTED
        note = (
            f"Single source detected within {max_separation_arcsec:.1f} arcsec tolerance "
            f"(separation: {sep_val:.2f} arcsec, SNR: {matched_s.snr:.1f})"
        )
    else:
        status = DetectionStatus.AMBIGUOUS
        note = (
            f"Ambiguous association: {n_in_tol} detected sources fall within {max_separation_arcsec:.1f} arcsec tolerance. "
            f"Nearest source is at {sep_val:.2f} arcsec (SNR: {matched_s.snr:.1f})."
        )

    return TargetAssociationResult(
        target_name=target_name,
        predicted_ra=predicted_ra,
        predicted_dec=predicted_dec,
        predicted_x=predicted_x,
        predicted_y=predicted_y,
        status=status,
        measured_ra=matched_s.ra,
        measured_dec=matched_s.dec,
        measured_x=matched_s.x,
        measured_y=matched_s.y,
        separation_arcsec=sep_val,
        pixel_separation=pix_sep,
        snr=matched_s.snr,
        matched_source=matched_s,
        candidate_sources_in_tolerance=n_in_tol,
        min_separation_arcsec=min_sep,
        max_separation_arcsec=max_separation_arcsec,
        evaluation_note=note,
    )


def evaluate_known_object_detection(
    predicted_ra: float,
    predicted_dec: float,
    detected_sources: List[DetectedSource],
    tolerance_arcsec: float = 15.0,
) -> Tuple[Optional[DetectedSource], Optional[float]]:
    """
    Evaluates detected sources against an externally supplied ephemeris position.
    Maintained for backward compatibility; calls associate_target_source internally.

    Returns:
        (closest_source, separation_arcsec) if closest_source is within tolerance_arcsec,
        (None, min_separation_arcsec) if no source is within tolerance.
    """
    res = associate_target_source(
        detected_sources=detected_sources,
        predicted_ra=predicted_ra,
        predicted_dec=predicted_dec,
        max_separation_arcsec=tolerance_arcsec,
    )
    if res.status in (DetectionStatus.DETECTED, DetectionStatus.AMBIGUOUS):
        return res.matched_source, res.separation_arcsec
    return None, res.min_separation_arcsec


def generate_known_object_visualization(
    fits_path_1: Path,
    fits_path_2: Path,
    pred_ra_1: float,
    pred_dec_1: float,
    pred_ra_2: float,
    pred_dec_2: float,
    detected_1: Optional[DetectedSource],
    detected_2: Optional[DetectedSource],
    output_png_path: Path,
    title: str = "3I/ATLAS SPHEREx Validation",
) -> Path:
    """
    Generates a side-by-side visualization comparing Epoch 1 and Epoch 2 images,
    annotating predicted positions and measured centroids with distinct labels.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from astropy.visualization import ZScaleInterval
    from app.services.fits_service import inspect_fits_cutout

    output_png_path.parent.mkdir(parents=True, exist_ok=True)

    info1 = inspect_fits_cutout(fits_path_1, pred_ra_1, pred_dec_1)
    info2 = inspect_fits_cutout(fits_path_2, pred_ra_2, pred_dec_2)

    wcs1 = info1.get("wcs")
    wcs2 = info2.get("wcs")
    data1 = info1.get("data")
    data2 = info2.get("data")

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), facecolor="#0B0F19")
    interval = ZScaleInterval()

    for idx, (ax, data, wcs, pred_ra, pred_dec, detected, epoch_lbl) in enumerate([
        (axes[0], data1, wcs1, pred_ra_1, pred_dec_1, detected_1, "Epoch 1 (14:01 UTC)"),
        (axes[1], data2, wcs2, pred_ra_2, pred_dec_2, detected_2, "Epoch 2 (14:05 UTC)"),
    ], start=1):
        ax.set_facecolor("#0F172A")
        if data is not None:
            clean_data = np.nan_to_num(data, nan=np.nanmedian(data))
            vmin, vmax = interval.get_limits(clean_data)
            ax.imshow(clean_data, origin="lower", cmap="magma", vmin=vmin, vmax=vmax)

        # Plot predicted position
        if wcs is not None:
            px, py = wcs.world_to_pixel_values(pred_ra, pred_dec)
            ax.scatter([px], [py], s=120, facecolors="none", edgecolors="#38BDF8", linewidths=2, label="Predicted (IRSA)")

        # Plot detected centroid if available
        if detected is not None:
            ax.scatter([detected.x], [detected.y], s=100, marker="+", color="#F43F5E", linewidths=2, label="Measured (Centroid)")

        ax.set_title(epoch_lbl, color="#E2E8F0", fontsize=12, pad=10)
        ax.tick_params(colors="#94A3B8")
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.legend(loc="upper right", facecolor="#1E293B", edgecolor="#475569", labelcolor="#F1F5F9", fontsize=9)

    fig.suptitle(title, color="#F8FAFC", fontsize=14, weight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_png_path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    return output_png_path
