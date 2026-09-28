"""
Cross-matching service for two-epoch source catalogs.

Performs positional cross-matching in sky coordinates (RA/DEC) using
Astropy SkyCoord and proper spherical angular separation rather than
naive Euclidean RA/DEC subtraction.

Classifies matched pairs as stationary, possible-motion, or
moving-object-candidate based on configurable angular displacement thresholds.
"""
import logging
import math
from typing import List, Optional, Tuple

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

from app.models.motion import (
    AngularDisplacement,
    AngularSpeed,
    CandidateQuality,
    DetectedSource,
    MovingObjectCandidate,
    PixelSkyPosition,
)

logger = logging.getLogger(__name__)


class CrossMatchError(Exception):
    """Raised when cross-matching encounters an unrecoverable error."""
    pass


def compute_angular_separation(
    ra1: float, dec1: float,
    ra2: float, dec2: float
) -> float:
    """
    Compute angular separation between two sky positions using Astropy SkyCoord.

    Uses proper spherical geometry (Vincenty formula internally)
    rather than simple Euclidean distance in RA/DEC space.

    Returns:
        Angular separation in arcseconds.
    """
    coord1 = SkyCoord(ra=ra1 * u.deg, dec=dec1 * u.deg, frame="icrs")
    coord2 = SkyCoord(ra=ra2 * u.deg, dec=dec2 * u.deg, frame="icrs")
    sep = coord1.separation(coord2)
    return sep.arcsec


def compute_position_angle(
    ra1: float, dec1: float,
    ra2: float, dec2: float
) -> float:
    """
    Compute the astronomical position angle of motion from position 1 to position 2.

    Convention:
      0° = North
      90° = East
      180° = South
      270° = West

    Uses Astropy SkyCoord.position_angle() which implements the proper
    spherical formula.

    Returns:
        Position angle in degrees [0, 360).
    """
    coord1 = SkyCoord(ra=ra1 * u.deg, dec=dec1 * u.deg, frame="icrs")
    coord2 = SkyCoord(ra=ra2 * u.deg, dec=dec2 * u.deg, frame="icrs")
    pa = coord1.position_angle(coord2)
    pa_deg = pa.deg % 360.0
    return pa_deg


def position_angle_to_direction(pa_deg: float) -> str:
    """
    Convert a position angle to a human-readable cardinal/intercardinal direction.

    PA convention: 0°=N, 90°=E, 180°=S, 270°=W
    """
    # Normalize to [0, 360)
    pa = pa_deg % 360.0

    if pa < 22.5 or pa >= 337.5:
        return "North"
    elif pa < 67.5:
        return "Northeast"
    elif pa < 112.5:
        return "East"
    elif pa < 157.5:
        return "Southeast"
    elif pa < 202.5:
        return "South"
    elif pa < 247.5:
        return "Southwest"
    elif pa < 292.5:
        return "West"
    else:
        return "Northwest"


def cross_match_catalogs(
    sources_1: List[DetectedSource],
    sources_2: List[DetectedSource],
    match_tolerance_arcsec: float = 30.0,
    elapsed_time_days: float = 1.0,
    motion_threshold_arcsec: float = 2.0,
    candidate_threshold_arcsec: float = 6.2,
) -> Tuple[List[MovingObjectCandidate], int, int, int, int, int]:
    """
    Cross-match two source catalogs using sky coordinates.

    Algorithm:
    1. Build SkyCoord arrays from both catalogs
    2. For each source in catalog 1, find the nearest source in catalog 2
       within the match tolerance
    3. Compute angular displacement, position angle, and angular speed
    4. Classify each match as stationary, possible-motion, or moving-object-candidate
    5. Return candidates and match statistics

    Classification thresholds:
    - displacement < motion_threshold_arcsec → 'stationary'
    - motion_threshold ≤ displacement < candidate_threshold → 'possible-motion'
    - displacement ≥ candidate_threshold AND quality checks pass → 'moving-object-candidate'

    Parameters:
        sources_1: Detected sources from epoch 1
        sources_2: Detected sources from epoch 2
        match_tolerance_arcsec: Maximum angular separation for cross-matching
        elapsed_time_days: Time difference between epochs in days
        motion_threshold_arcsec: Minimum displacement for 'possible-motion'
        candidate_threshold_arcsec: Minimum displacement for 'moving-object-candidate'

    Returns:
        (candidates_list, matched_count, stationary_count,
         possible_motion_count, candidate_count, unmatched_1_count)
    """
    if not sources_1:
        logger.warning("No sources in epoch 1 catalog; cannot cross-match")
        return [], 0, 0, 0, 0, 0

    if not sources_2:
        logger.warning("No sources in epoch 2 catalog; cannot cross-match")
        return [], 0, 0, 0, 0, len(sources_1)

    # Build SkyCoord arrays
    coords_1 = SkyCoord(
        ra=[s.ra for s in sources_1] * u.deg,
        dec=[s.dec for s in sources_1] * u.deg,
        frame="icrs"
    )
    coords_2 = SkyCoord(
        ra=[s.ra for s in sources_2] * u.deg,
        dec=[s.dec for s in sources_2] * u.deg,
        frame="icrs"
    )

    # Match catalog 1 against catalog 2 (nearest-neighbor)
    # Returns: idx (index into coords_2), sep2d (angular separation), dist3d
    idx_matches, sep2d, _ = coords_1.match_to_catalog_sky(coords_2)

    candidates: List[MovingObjectCandidate] = []
    matched_count = 0
    stationary_count = 0
    possible_motion_count = 0
    candidate_count = 0
    # Sort candidate matches by separation so closest pairs match first
    candidate_pairs = [
        (float(sep.arcsec), i, int(j))
        for i, (j, sep) in enumerate(zip(idx_matches, sep2d))
        if float(sep.arcsec) <= match_tolerance_arcsec
    ]
    candidate_pairs.sort(key=lambda p: p[0])

    used_epoch1_indices = set()
    used_epoch2_indices = set()

    for sep_arcsec, i, j_int in candidate_pairs:
        # Skip if either source was already assigned (bijective 1-to-1 matching)
        if i in used_epoch1_indices or j_int in used_epoch2_indices:
            continue
        used_epoch1_indices.add(i)
        used_epoch2_indices.add(j_int)

        matched_count += 1
        s1 = sources_1[i]
        s2 = sources_2[j_int]

        # Compute precise angular displacement
        displacement_arcsec = compute_angular_separation(s1.ra, s1.dec, s2.ra, s2.dec)
        displacement_arcmin = displacement_arcsec / 60.0
        displacement_deg = displacement_arcsec / 3600.0

        # Compute position angle
        pa_deg = compute_position_angle(s1.ra, s1.dec, s2.ra, s2.dec)
        direction = position_angle_to_direction(pa_deg)

        # Compute angular speed
        if elapsed_time_days > 0:
            speed_arcsec_per_day = displacement_arcsec / elapsed_time_days
            speed_arcsec_per_hour = speed_arcsec_per_day / 24.0
        else:
            speed_arcsec_per_day = 0.0
            speed_arcsec_per_hour = 0.0

        # Build evidence list
        evidence: List[str] = []
        evidence.append("detected_in_both_epochs")

        if "valid_wcs" in s1.quality_flags:
            evidence.append("valid_wcs_epoch_1")
        if "valid_wcs" in s2.quality_flags:
            evidence.append("valid_wcs_epoch_2")

        # Estimate centroid uncertainty from source SNR
        # Conservative estimate: centroid uncertainty ≈ FWHM / (2 × SNR)
        centroid_unc_arcsec: Optional[float] = None
        fwhm_arcsec = (s1.fwhm_pixels or 1.5) * 6.2  # SPHEREx pixel scale
        if s1.snr is not None and s1.snr > 0 and s2.snr is not None and s2.snr > 0:
            # Combined uncertainty from both epochs (quadrature sum)
            unc1 = fwhm_arcsec / (2.0 * s1.snr)
            unc2 = fwhm_arcsec / (2.0 * s2.snr)
            centroid_unc_arcsec = math.sqrt(unc1**2 + unc2**2)

        # Classification
        status: str
        displacement_significance: Optional[float] = None

        if centroid_unc_arcsec is not None and centroid_unc_arcsec > 0:
            displacement_significance = displacement_arcsec / centroid_unc_arcsec

        if displacement_arcsec < motion_threshold_arcsec:
            status = "stationary"
            evidence.append("displacement_below_motion_threshold")
            stationary_count += 1
        elif displacement_arcsec < candidate_threshold_arcsec:
            status = "possible-motion"
            evidence.append("displacement_above_motion_threshold")
            evidence.append("displacement_below_candidate_threshold")
            possible_motion_count += 1
        else:
            # Check additional quality criteria for candidate status
            quality_ok = True

            # Check edge sources
            if "edge_source" in s1.quality_flags or "edge_source" in s2.quality_flags:
                evidence.append("edge_source_warning")

            # Check SNR
            if s1.snr is not None and s1.snr >= 3.0:
                evidence.append("sufficient_snr_epoch_1")
            elif s1.snr is not None:
                evidence.append("low_snr_epoch_1")
                quality_ok = False
            else:
                evidence.append("unknown_snr_epoch_1")

            if s2.snr is not None and s2.snr >= 3.0:
                evidence.append("sufficient_snr_epoch_2")
            elif s2.snr is not None:
                evidence.append("low_snr_epoch_2")
                quality_ok = False
            else:
                evidence.append("unknown_snr_epoch_2")

            # Check if displacement exceeds uncertainty significantly
            if displacement_significance is not None:
                if displacement_significance >= 3.0:
                    evidence.append("displacement_exceeds_uncertainty_3sigma")
                elif displacement_significance >= 2.0:
                    evidence.append("displacement_exceeds_uncertainty_2sigma")
                else:
                    evidence.append("displacement_within_uncertainty")
                    quality_ok = False

            evidence.append("displacement_exceeds_candidate_threshold")

            if quality_ok:
                status = "moving-object-candidate"
                evidence.append("quality_checks_passed")
                candidate_count += 1
            else:
                status = "possible-motion"
                evidence.append("quality_checks_failed_downgraded")
                possible_motion_count += 1

        # Determine confidence level
        if status == "stationary":
            confidence = "high"
        elif status == "moving-object-candidate":
            if displacement_significance is not None and displacement_significance >= 5.0:
                confidence = "high"
            elif displacement_significance is not None and displacement_significance >= 3.0:
                confidence = "medium"
            else:
                confidence = "low"
        else:
            confidence = "low"

        candidate_id = f"candidate_{matched_count:03d}"

        candidates.append(MovingObjectCandidate(
            candidate_id=candidate_id,
            status=status,
            evidence=evidence,
            position_epoch_1=PixelSkyPosition(
                x=s1.x, y=s1.y, ra=s1.ra, dec=s1.dec
            ),
            position_epoch_2=PixelSkyPosition(
                x=s2.x, y=s2.y, ra=s2.ra, dec=s2.dec
            ),
            angular_displacement=AngularDisplacement(
                arcsec=round(displacement_arcsec, 4),
                arcmin=round(displacement_arcmin, 6),
                degrees=round(displacement_deg, 8)
            ),
            average_angular_speed=AngularSpeed(
                arcsec_per_day=round(speed_arcsec_per_day, 4),
                arcsec_per_hour=round(speed_arcsec_per_hour, 6)
            ),
            position_angle_deg=round(pa_deg, 2),
            direction_label=direction,
            quality=CandidateQuality(
                snr_epoch_1=s1.snr,
                snr_epoch_2=s2.snr,
                centroid_uncertainty_arcsec=(
                    round(centroid_unc_arcsec, 4) if centroid_unc_arcsec is not None else None
                ),
                cross_match_separation_arcsec=round(sep_arcsec, 4),
                displacement_to_uncertainty_ratio=(
                    round(displacement_significance, 2)
                    if displacement_significance is not None else None
                ),
                confidence=confidence
            ),
            motion_trail_path=None  # Set later by visualization service
        ))

    unmatched_1 = len(sources_1) - matched_count

    logger.info(
        "Cross-match complete: %d matched, %d stationary, %d possible-motion, "
        "%d candidates, %d unmatched from epoch 1",
        matched_count, stationary_count, possible_motion_count,
        candidate_count, unmatched_1
    )

    return (
        candidates, matched_count, stationary_count,
        possible_motion_count, candidate_count, unmatched_1
    )
