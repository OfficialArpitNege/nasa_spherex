"""
Pydantic models for the Hypothesis Update & New Observation analysis pipeline.

Defines structured schemas for:
- Evidence snapshot of baseline two-epoch observations
- New observation metadata and measurements (Epoch 3)
- Trajectory extrapolation (using spherical astronomy)
- Deterministic hypothesis classification (STRENGTHENED, WEAKENED, CHANGED, INCONCLUSIVE)
- Detailed evidence-based scientific comparisons
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HypothesisClassification(str, Enum):
    """Deterministic scientific classification of hypothesis update."""
    STRENGTHENED = "STRENGTHENED"
    WEAKENED = "WEAKENED"
    CHANGED = "CHANGED"
    INCONCLUSIVE = "INCONCLUSIVE"


class TrajectoryPrediction(BaseModel):
    """
    Astrometric prediction of candidate position at the epoch of the new observation,
    calculated via spherical coordinate extrapolation along the baseline velocity vector.
    """
    predicted_ra: float = Field(..., description="Expected Right Ascension in degrees (ICRS)")
    predicted_dec: float = Field(..., description="Expected Declination in degrees (ICRS)")
    baseline_displacement_arcsec: float = Field(..., description="Angular separation between Epoch 1 and Epoch 2 (arcsec)")
    baseline_angular_speed_arcsec_day: float = Field(..., description="Baseline apparent speed on sky (arcsec/day)")
    baseline_position_angle_deg: float = Field(..., description="Baseline motion direction angle (0°=N, 90°=E)")
    baseline_direction: str = Field(..., description="Human-readable cardinal direction (e.g. Southeast)")
    elapsed_days_e2_to_e3: float = Field(..., description="Elapsed interval from Epoch 2 to Epoch 3 (days)")
    expected_displacement_from_e2_arcsec: float = Field(
        ..., description="Expected angular distance from Epoch 2 position (arcsec)"
    )


class EvidenceSnapshot(BaseModel):
    """
    Structured snapshot of evidence established by the initial two-epoch analysis.
    """
    candidate_id: str = Field(..., description="Unique candidate identifier")
    observation_id_1: str = Field(..., description="SPHEREx observation ID for Epoch 1")
    observation_id_2: str = Field(..., description="SPHEREx observation ID for Epoch 2")
    timestamp_utc_1: Optional[str] = Field(None, description="Epoch 1 observation timestamp (ISO UTC)")
    timestamp_utc_2: Optional[str] = Field(None, description="Epoch 2 observation timestamp (ISO UTC)")
    timestamp_mjd_1: Optional[float] = Field(None, description="Epoch 1 MJD")
    timestamp_mjd_2: Optional[float] = Field(None, description="Epoch 2 MJD")
    ra_1: float = Field(..., ge=0.0, le=360.0, description="Epoch 1 RA in degrees")
    dec_1: float = Field(..., ge=-90.0, le=90.0, description="Epoch 1 DEC in degrees")
    ra_2: float = Field(..., ge=0.0, le=360.0, description="Epoch 2 RA in degrees")
    dec_2: float = Field(..., ge=-90.0, le=90.0, description="Epoch 2 DEC in degrees")
    displacement_arcsec: float = Field(..., description="Observed displacement between E1 and E2 in arcsec")
    angular_speed_arcsec_day: float = Field(..., description="Observed apparent angular speed in arcsec/day")
    position_angle_deg: float = Field(..., description="Observed motion direction angle (0°=N, 90°=E)")
    direction: str = Field(..., description="Cardinal/intercardinal direction of motion")
    snr_1: Optional[float] = Field(None, description="SNR in Epoch 1")
    snr_2: Optional[float] = Field(None, description="SNR in Epoch 2")
    confidence: str = Field("medium", description="Confidence classification of baseline candidate")
    status: str = Field("moving-object-candidate", description="Baseline classification status")


class NewObservationInput(BaseModel):
    """
    Metadata and measurement data for the new observation (Epoch 3).
    Can represent another real SPHEREx observation or a controlled scenario observation.
    """
    observation_id: str = Field(..., description="SPHEREx or scenario observation identifier")
    observation_time_utc: str = Field(..., description="Observation start time in UTC ISO format")
    observation_time_mjd: Optional[float] = Field(None, description="Observation time in MJD")
    ra_center: float = Field(..., ge=0.0, le=360.0, description="Field center RA in degrees")
    dec_center: float = Field(..., ge=-90.0, le=90.0, description="Field center DEC in degrees")
    bandpass: Optional[str] = Field(None, description="SPHEREx bandpass (e.g. SPHEREx-D4)")
    is_scenario: bool = Field(False, description="Whether this is a controlled scenario/demo observation")
    scenario_name: Optional[str] = Field(None, description="Label of scenario if simulated")
    detection_status: str = Field("DETECTED", description="Status: 'DETECTED', 'NOT_DETECTED', or 'AMBIGUOUS'")
    measured_ra: Optional[float] = Field(None, ge=0.0, le=360.0, description="Measured source centroid RA in degrees")
    measured_dec: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Measured source centroid DEC in degrees")
    measured_x: Optional[float] = Field(None, description="Pixel centroid x coordinate")
    measured_y: Optional[float] = Field(None, description="Pixel centroid y coordinate")
    snr: Optional[float] = Field(None, description="Signal-to-noise ratio in new observation")
    flux: Optional[float] = Field(None, description="Aperture flux measurement")
    fits_path: Optional[str] = Field(None, description="Path to FITS file if available")
    preview_url: Optional[str] = Field(None, description="Preview image URL if available")


class EvidenceComparison(BaseModel):
    """
    Detailed scientific comparison between predicted trajectory and new observation.
    """
    expected_ra: float = Field(..., description="Predicted RA on the sky")
    expected_dec: float = Field(..., description="Predicted DEC on the sky")
    measured_ra: Optional[float] = Field(None, description="Measured RA on the sky")
    measured_dec: Optional[float] = Field(None, description="Measured DEC on the sky")
    angular_residual_arcsec: Optional[float] = Field(
        None, description="Angular separation between predicted and measured coordinates (arcsec)"
    )
    angular_residual_pixels: Optional[float] = Field(
        None, description="Residual in SPHEREx pixel scale units (~6.16″/pixel)"
    )
    observed_displacement_from_e2_arcsec: Optional[float] = Field(
        None, description="Angular displacement from Epoch 2 position to measured Epoch 3 (arcsec)"
    )
    observed_speed_arcsec_day: Optional[float] = Field(
        None, description="Apparent angular speed between Epoch 2 and Epoch 3 (arcsec/day)"
    )
    observed_position_angle_deg: Optional[float] = Field(
        None, description="Position angle from Epoch 2 to Epoch 3 (degrees)"
    )
    position_angle_residual_deg: Optional[float] = Field(
        None, description="Angular deviation in direction of motion (degrees)"
    )
    stationary_separation_from_e1_arcsec: Optional[float] = Field(
        None, description="Separation from Epoch 1 position (tests whether source was stationary)"
    )
    stationary_separation_from_e2_arcsec: Optional[float] = Field(
        None, description="Separation from Epoch 2 position (tests whether source was stationary)"
    )
    detection_reliable: bool = Field(..., description="Whether source was reliably detected")
    snr: Optional[float] = Field(None, description="Measured SNR in new observation")


class Hypothesis(BaseModel):
    """
    The working scientific hypothesis regarding a candidate moving object.
    """
    hypothesis_id: str = Field(..., description="Hypothesis identifier")
    title: str = Field(
        "Candidate represents a genuine moving astronomical source",
        description="Concise scientific hypothesis statement"
    )
    description: str = Field(..., description="Full scientific description of hypothesis")
    candidate_id: str = Field(..., description="Target candidate reference ID")
    initial_observations: List[str] = Field(default_factory=list, description="IDs of initial supporting observations")
    current_status: str = Field("moving-object-candidate", description="Current status")
    confidence: str = Field("medium", description="Current confidence level")


class HypothesisUpdateRequest(BaseModel):
    """
    Request model for evaluating a new observation against the current hypothesis.
    """
    hypothesis: Hypothesis
    baseline_evidence: EvidenceSnapshot
    new_observation: NewObservationInput
    # Configurable evaluation thresholds
    residual_tolerance_arcsec: float = Field(
        9.24, gt=0.0,
        description="Maximum residual tolerance for STRENGTHENED (~1.5 SPHEREx pixels = 9.24″)"
    )
    direction_tolerance_deg: float = Field(
        40.0, gt=0.0,
        description="Maximum position angle deviation for trajectory consistency (degrees)"
    )
    stationary_threshold_arcsec: float = Field(
        2.5, gt=0.0,
        description="Displacement threshold below which source is considered stationary (~1/3 SPHEREx pixel)"
    )
    min_snr_threshold: float = Field(
        3.0, gt=0.0,
        description="Minimum SNR for reliable detection in new observation"
    )


class HypothesisUpdateResult(BaseModel):
    """
    Structured outcome of the hypothesis update evaluation.
    """
    update_id: str = Field(..., description="Unique update evaluation ID")
    hypothesis_id: str = Field(..., description="Target hypothesis ID")
    previous_classification: str = Field(..., description="Previous hypothesis status")
    new_classification: HypothesisClassification = Field(
        ..., description="Updated hypothesis classification (STRENGTHENED, WEAKENED, CHANGED, INCONCLUSIVE)"
    )
    confidence: str = Field(..., description="Updated confidence level (high, medium, low, uncertain)")
    summary_verdict: str = Field(..., description="One-line scientific verdict")
    explanation: str = Field(..., description="Evidence-based explanation of the update decision")
    detailed_reasons: List[str] = Field(default_factory=list, description="List of specific quantitative findings")
    trajectory_prediction: TrajectoryPrediction = Field(..., description="Expected trajectory calculation")
    evidence_comparison: EvidenceComparison = Field(..., description="Detailed quantitative comparison")
    updated_hypothesis: Hypothesis = Field(..., description="Updated hypothesis object")
    warnings: List[str] = Field(default_factory=list, description="Scientific warnings and caveats")
    scientific_disclaimer: str = Field(
        default=(
            "SCIENTIFIC INTEGRITY NOTICE: Hypothesis evaluations are deterministic "
            "comparisons of kinematic residuals and detection quality against explicit astrometric "
            "rules. This analysis does not claim confirmation of Planet X, Planet Nine, or any specific body."
        ),
        description="Mandatory scientific disclaimer"
    )


class ChallengeScenarioInfo(BaseModel):
    """
    Metadata and payload for a pre-configured challenge demonstration scenario.
    """
    scenario_id: str
    title: str
    expected_outcome: HypothesisClassification
    description: str
    baseline_evidence: EvidenceSnapshot
    new_observation: NewObservationInput
