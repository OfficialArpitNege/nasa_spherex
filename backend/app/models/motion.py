"""
Pydantic models for the Step 3 motion-analysis pipeline.

Defines structured schemas for the two-epoch source detection,
cross-matching, and moving-object candidate classification output.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PixelSkyPosition(BaseModel):
    """Position of a detected source in both pixel and sky coordinates."""
    x: float = Field(..., description="Source centroid x pixel coordinate")
    y: float = Field(..., description="Source centroid y pixel coordinate")
    ra: float = Field(..., description="Right Ascension in degrees (ICRS)")
    dec: float = Field(..., description="Declination in degrees (ICRS)")


class DetectedSource(BaseModel):
    """A single source detected in one epoch's science image."""
    source_id: int = Field(..., description="Sequential source ID within this epoch")
    x: float = Field(..., description="Centroid x pixel coordinate")
    y: float = Field(..., description="Centroid y pixel coordinate")
    ra: float = Field(..., description="Right Ascension in degrees (ICRS)")
    dec: float = Field(..., description="Declination in degrees (ICRS)")
    flux: Optional[float] = Field(None, description="Aperture flux measurement (image units)")
    peak_value: Optional[float] = Field(None, description="Peak pixel value at centroid")
    snr: Optional[float] = Field(None, description="Signal-to-noise ratio estimate")
    fwhm_pixels: Optional[float] = Field(None, description="Estimated FWHM in pixels")
    quality_flags: List[str] = Field(
        default_factory=list,
        description="Quality flags: valid_wcs, high_snr, low_snr, edge_source, etc."
    )


class EpochInfo(BaseModel):
    """Metadata for one observation epoch used in the analysis."""
    observation_id: str = Field(..., description="NASA/IRSA SPHEREx observation ID")
    timestamp_utc: Optional[str] = Field(None, description="Observation time in UTC ISO string")
    timestamp_mjd: Optional[float] = Field(None, description="Observation time in MJD")
    ra_center: float = Field(..., description="Cutout center RA in degrees")
    dec_center: float = Field(..., description="Cutout center DEC in degrees")
    bandpass: Optional[str] = Field(None, description="SPHEREx bandpass/detector channel (e.g. SPHEREx-D4)")
    fits_path: str = Field(..., description="Path to local cached FITS cutout file")
    image_shape: List[int] = Field(..., description="Science image dimensions [height, width]")
    wcs_available: bool = Field(..., description="Whether valid celestial WCS was constructed")
    wcs_projection: Optional[str] = Field(None, description="WCS projection type (e.g. RA---TAN-SIP/DEC--TAN-SIP)")
    sources_detected: int = Field(0, description="Number of sources detected in this epoch")


class TimeDifference(BaseModel):
    """Elapsed time between two observation epochs."""
    seconds: float = Field(..., description="Elapsed time in seconds")
    hours: float = Field(..., description="Elapsed time in hours")
    days: float = Field(..., description="Elapsed time in days")


class AngularDisplacement(BaseModel):
    """Angular distance travelled on the sky."""
    arcsec: float = Field(..., description="Angular displacement in arcseconds")
    arcmin: float = Field(..., description="Angular displacement in arcminutes")
    degrees: float = Field(..., description="Angular displacement in degrees")


class AngularSpeed(BaseModel):
    """Average apparent angular speed on the sky."""
    arcsec_per_day: float = Field(..., description="Average angular speed in arcsec/day")
    arcsec_per_hour: float = Field(..., description="Average angular speed in arcsec/hour")


class CandidateQuality(BaseModel):
    """Quality and confidence metrics for a moving-object candidate."""
    snr_epoch_1: Optional[float] = Field(None, description="Source SNR in epoch 1")
    snr_epoch_2: Optional[float] = Field(None, description="Source SNR in epoch 2")
    centroid_uncertainty_arcsec: Optional[float] = Field(
        None, description="Estimated centroid positional uncertainty in arcsec"
    )
    cross_match_separation_arcsec: float = Field(
        ..., description="Cross-match angular separation in arcsec"
    )
    displacement_to_uncertainty_ratio: Optional[float] = Field(
        None, description="Ratio of displacement to positional uncertainty (significance)"
    )
    confidence: str = Field(
        ..., description="Confidence level: high, medium, low, uncertain"
    )


class MovingObjectCandidate(BaseModel):
    """A single moving-object candidate identified by the two-epoch analysis."""
    candidate_id: str = Field(..., description="Unique candidate identifier (e.g. candidate_001)")
    status: str = Field(
        ...,
        description=(
            "Classification status: 'moving-object-candidate', "
            "'possible-motion', 'stationary', 'uncertain'"
        )
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="List of evidence supporting or refuting motion"
    )
    position_epoch_1: PixelSkyPosition = Field(..., description="Source position in epoch 1")
    position_epoch_2: PixelSkyPosition = Field(..., description="Source position in epoch 2")
    angular_displacement: AngularDisplacement = Field(
        ..., description="Angular distance on the sky between the two positions"
    )
    average_angular_speed: AngularSpeed = Field(
        ..., description="Average apparent angular motion"
    )
    position_angle_deg: float = Field(
        ..., description="Position angle of motion (0°=North, 90°=East)"
    )
    direction_label: str = Field(
        ..., description="Human-readable cardinal/intercardinal direction"
    )
    quality: CandidateQuality = Field(..., description="Quality and confidence metrics")
    motion_trail_path: Optional[str] = Field(
        None, description="Path to motion trail visualization image"
    )


class SourceStatistics(BaseModel):
    """Summary statistics for the two-epoch source detection and matching."""
    sources_detected_epoch_1: int = Field(0, description="Sources detected in epoch 1")
    sources_detected_epoch_2: int = Field(0, description="Sources detected in epoch 2")
    matched_sources: int = Field(0, description="Sources successfully cross-matched between epochs")
    stationary_count: int = Field(0, description="Sources classified as stationary")
    possible_motion_count: int = Field(0, description="Sources classified as possible motion")
    candidate_count: int = Field(0, description="Sources classified as moving-object candidates")
    unmatched_epoch_1: int = Field(0, description="Sources in epoch 1 with no match in epoch 2")
    unmatched_epoch_2: int = Field(0, description="Sources in epoch 2 with no match in epoch 1")


class MotionAnalysisRequest(BaseModel):
    """Request body for the POST /api/analyze-motion endpoint."""
    fits_path_1: str = Field(..., description="Path to cached FITS cutout for epoch 1")
    fits_path_2: str = Field(..., description="Path to cached FITS cutout for epoch 2")
    observation_id_1: str = Field(..., description="Observation ID for epoch 1")
    observation_id_2: str = Field(..., description="Observation ID for epoch 2")
    ra: float = Field(..., ge=0.0, le=360.0, description="Target center RA in degrees (epoch 1)")
    dec: float = Field(..., ge=-90.0, le=90.0, description="Target center DEC in degrees (epoch 1)")
    ra_2: Optional[float] = Field(None, ge=0.0, le=360.0, description="Target center RA in degrees for epoch 2")
    dec_2: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Target center DEC in degrees for epoch 2")
    timestamp_utc_1: Optional[str] = Field(None, description="Observation 1 UTC timestamp")
    timestamp_utc_2: Optional[str] = Field(None, description="Observation 2 UTC timestamp")
    timestamp_mjd_1: Optional[float] = Field(None, description="Observation 1 MJD timestamp")
    timestamp_mjd_2: Optional[float] = Field(None, description="Observation 2 MJD timestamp")
    bandpass_1: Optional[str] = Field(None, description="Bandpass of epoch 1")
    bandpass_2: Optional[str] = Field(None, description="Bandpass of epoch 2")
    # Configurable detection/matching parameters
    detection_sigma: float = Field(
        3.0, gt=0.0,
        description="Source detection threshold in sigma above background (default: 3.0)"
    )
    match_tolerance_arcsec: float = Field(
        30.0, gt=0.0,
        description="Cross-match angular tolerance in arcseconds (default: 30.0)"
    )
    motion_threshold_arcsec: float = Field(
        2.0, gt=0.0,
        description=(
            "Minimum angular displacement in arcsec to classify as possible motion. "
            "Below this, source is considered stationary. (default: 2.0, ~1/3 SPHEREx pixel)"
        )
    )
    candidate_threshold_arcsec: float = Field(
        6.2, gt=0.0,
        description=(
            "Minimum angular displacement in arcsec to classify as moving-object candidate. "
            "Default is 6.2 arcsec (~1 SPHEREx pixel). Sources must exceed this AND have "
            "sufficient quality to be classified as candidates."
        )
    )


class MotionAnalysisResult(BaseModel):
    """Complete structured result from the two-epoch motion analysis pipeline."""
    analysis_id: str = Field(..., description="Unique analysis run identifier")
    observation_1: EpochInfo = Field(..., description="Metadata for epoch 1")
    observation_2: EpochInfo = Field(..., description="Metadata for epoch 2")
    time_difference: TimeDifference = Field(..., description="Elapsed time between epochs")
    source_statistics: SourceStatistics = Field(..., description="Detection and matching summary")
    candidates: List[MovingObjectCandidate] = Field(
        default_factory=list, description="List of identified moving-object candidates"
    )
    detection_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Detection and matching configuration used"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Scientific warnings, limitations, and caveats"
    )
    scientific_disclaimer: str = Field(
        default=(
            "SCIENTIFIC DISCLAIMER: This analysis identifies moving-object candidates only. "
            "Results require independent scientific validation. This system does NOT claim to "
            "detect or identify Planet X, Planet Nine, or any specific solar system body. "
            "All candidates are classified as 'moving-object candidates requiring further investigation'."
        ),
        description="Mandatory scientific disclaimer"
    )
