"""
Hypothesis Evaluation Engine for SPHEREx Moving Object Explorer.

Provides deterministic, rule-based scientific evaluation when a new observation
(Epoch 3) is added to an existing two-epoch moving object candidate.

Calculates:
1. Trajectory extrapolation on celestial sphere using Astropy SkyCoord
2. Positional and kinematic residuals (angular separation, PA divergence, speed consistency)
3. Classification of updated hypothesis: STRENGTHENED, WEAKENED, CHANGED, INCONCLUSIVE
4. Transparent, evidence-grounded scientific explanation of the decision
"""
import logging
import math
import uuid
from typing import List, Optional, Tuple

import astropy.units as u
from astropy.coordinates import Angle, SkyCoord
from astropy.time import Time

from app.models.hypothesis import (
    ChallengeScenarioInfo,
    EvidenceComparison,
    EvidenceSnapshot,
    Hypothesis,
    HypothesisClassification,
    HypothesisUpdateRequest,
    HypothesisUpdateResult,
    NewObservationInput,
    TrajectoryPrediction,
)
from app.services.cross_matching import position_angle_to_direction

logger = logging.getLogger(__name__)

# Standard SPHEREx calibrated pixel scale
SPHEREX_PIXEL_SCALE_ARCSEC = 6.16


def compute_elapsed_days(
    t1_utc: Optional[str],
    t2_utc: Optional[str],
    t1_mjd: Optional[float] = None,
    t2_mjd: Optional[float] = None,
) -> float:
    """
    Computes elapsed time in days between two timestamps using Astropy Time.
    """
    time1: Optional[Time] = None
    time2: Optional[Time] = None

    if t1_utc:
        try:
            time1 = Time(t1_utc, format="iso", scale="utc")
        except Exception:
            pass
    if time1 is None and t1_mjd is not None:
        try:
            time1 = Time(t1_mjd, format="mjd")
        except Exception:
            pass

    if t2_utc:
        try:
            time2 = Time(t2_utc, format="iso", scale="utc")
        except Exception:
            pass
    if time2 is None and t2_mjd is not None:
        try:
            time2 = Time(t2_mjd, format="mjd")
        except Exception:
            pass

    if time1 is None or time2 is None:
        return 0.0

    dt_days = (time2 - time1).jd
    return float(dt_days)


def predict_trajectory(
    baseline: EvidenceSnapshot,
    new_obs_time_utc: str,
    new_obs_time_mjd: Optional[float] = None,
) -> TrajectoryPrediction:
    """
    Predicts expected position at new observation epoch based on baseline trajectory.

    Uses Astropy SkyCoord.directional_offset_by to compute spherical offset,
    preventing naive Euclidean RA/DEC subtraction errors and correctly handling
    declination convergence and RA wraparound.
    """
    elapsed_days = compute_elapsed_days(
        t1_utc=baseline.timestamp_utc_2,
        t2_utc=new_obs_time_utc,
        t1_mjd=baseline.timestamp_mjd_2,
        t2_mjd=new_obs_time_mjd,
    )

    # Safe fallback if timestamps identical or inverted
    effective_days = max(elapsed_days, 0.0)

    # Expected displacement along sky trajectory
    expected_disp_arcsec = baseline.angular_speed_arcsec_day * effective_days

    # Spherical extrapolation from Epoch 2 position along position angle
    c2 = SkyCoord(ra=baseline.ra_2 * u.deg, dec=baseline.dec_2 * u.deg, frame="icrs")
    pa_angle = Angle(baseline.position_angle_deg * u.deg)
    dist_angle = Angle(expected_disp_arcsec * u.arcsec)

    predicted_coord = c2.directional_offset_by(pa_angle, dist_angle)

    return TrajectoryPrediction(
        predicted_ra=round(float(predicted_coord.ra.deg), 6),
        predicted_dec=round(float(predicted_coord.dec.deg), 6),
        baseline_displacement_arcsec=round(baseline.displacement_arcsec, 2),
        baseline_angular_speed_arcsec_day=round(baseline.angular_speed_arcsec_day, 4),
        baseline_position_angle_deg=round(baseline.position_angle_deg, 1),
        baseline_direction=baseline.direction,
        elapsed_days_e2_to_e3=round(effective_days, 2),
        expected_displacement_from_e2_arcsec=round(expected_disp_arcsec, 2),
    )


def compare_evidence(
    baseline: EvidenceSnapshot,
    new_obs: NewObservationInput,
    prediction: TrajectoryPrediction,
) -> EvidenceComparison:
    """
    Compares the predicted trajectory position against the measured position in the new observation.
    """
    is_detected = (
        new_obs.detection_status == "DETECTED"
        and new_obs.measured_ra is not None
        and new_obs.measured_dec is not None
    )

    if not is_detected:
        return EvidenceComparison(
            expected_ra=prediction.predicted_ra,
            expected_dec=prediction.predicted_dec,
            measured_ra=None,
            measured_dec=None,
            angular_residual_arcsec=None,
            angular_residual_pixels=None,
            observed_displacement_from_e2_arcsec=None,
            observed_speed_arcsec_day=None,
            observed_position_angle_deg=None,
            position_angle_residual_deg=None,
            stationary_separation_from_e1_arcsec=None,
            stationary_separation_from_e2_arcsec=None,
            detection_reliable=False,
            snr=new_obs.snr,
        )

    # Measured coordinate
    c_meas = SkyCoord(ra=new_obs.measured_ra * u.deg, dec=new_obs.measured_dec * u.deg, frame="icrs")
    c_pred = SkyCoord(ra=prediction.predicted_ra * u.deg, dec=prediction.predicted_dec * u.deg, frame="icrs")
    c_e1 = SkyCoord(ra=baseline.ra_1 * u.deg, dec=baseline.dec_1 * u.deg, frame="icrs")
    c_e2 = SkyCoord(ra=baseline.ra_2 * u.deg, dec=baseline.dec_2 * u.deg, frame="icrs")

    # Angular residual between predicted and measured position
    residual_arcsec = float(c_pred.separation(c_meas).arcsec)
    residual_pixels = residual_arcsec / SPHEREX_PIXEL_SCALE_ARCSEC

    # Observed displacement from Epoch 2
    obs_disp_arcsec = float(c_e2.separation(c_meas).arcsec)

    # Observed apparent speed
    obs_speed = obs_disp_arcsec / max(prediction.elapsed_days_e2_to_e3, 0.001)

    # Observed position angle from Epoch 2 to Epoch 3
    if obs_disp_arcsec > 0.1:
        obs_pa = float(c_e2.position_angle(c_meas).deg) % 360.0
        # Position angle difference (shortest arc on circle)
        pa_diff = abs(obs_pa - baseline.position_angle_deg)
        pa_residual = min(pa_diff, 360.0 - pa_diff)
    else:
        obs_pa = baseline.position_angle_deg
        pa_residual = 0.0

    # Tests against stationarity with respect to E1 and E2
    sep_e1 = float(c_e1.separation(c_meas).arcsec)
    sep_e2 = float(c_e2.separation(c_meas).arcsec)

    is_reliable = (new_obs.snr is None or new_obs.snr >= 3.0)

    return EvidenceComparison(
        expected_ra=prediction.predicted_ra,
        expected_dec=prediction.predicted_dec,
        measured_ra=round(float(new_obs.measured_ra), 6),
        measured_dec=round(float(new_obs.measured_dec), 6),
        angular_residual_arcsec=round(residual_arcsec, 2),
        angular_residual_pixels=round(residual_pixels, 2),
        observed_displacement_from_e2_arcsec=round(obs_disp_arcsec, 2),
        observed_speed_arcsec_day=round(obs_speed, 4),
        observed_position_angle_deg=round(obs_pa, 1),
        position_angle_residual_deg=round(pa_residual, 1),
        stationary_separation_from_e1_arcsec=round(sep_e1, 2),
        stationary_separation_from_e2_arcsec=round(sep_e2, 2),
        detection_reliable=is_reliable,
        snr=new_obs.snr,
    )


def evaluate_hypothesis_update(request: HypothesisUpdateRequest) -> HypothesisUpdateResult:
    """
    Applies deterministic, rule-based scientific criteria to evaluate how the new
    observation updates the working hypothesis.
    """
    baseline = request.baseline_evidence
    new_obs = request.new_observation
    hypo = request.hypothesis

    # 1. Compute trajectory prediction
    prediction = predict_trajectory(
        baseline=baseline,
        new_obs_time_utc=new_obs.observation_time_utc,
        new_obs_time_mjd=new_obs.observation_time_mjd,
    )

    # 2. Compare predicted and measured evidence
    comp = compare_evidence(baseline, new_obs, prediction)

    detailed_reasons: List[str] = []
    warnings: List[str] = []

    # Check for observation time interval validity
    if prediction.elapsed_days_e2_to_e3 <= 0.0:
        warnings.append(
            "Observation interval between Epoch 2 and new observation is zero or negative. "
            "Motion calculations require forward time evolution."
        )

    # RULE 1: INCONCLUSIVE
    # Target not detected, ambiguous, SNR below threshold, or missing coordinates
    if (
        new_obs.detection_status != "DETECTED"
        or not comp.detection_reliable
        or comp.measured_ra is None
        or comp.measured_dec is None
    ):
        classification = HypothesisClassification.INCONCLUSIVE
        confidence = "uncertain"
        summary_verdict = "INCONCLUSIVE — Candidate not reliably detected in new observation."
        
        status_label = new_obs.detection_status
        snr_label = f"{new_obs.snr:.1f}" if new_obs.snr is not None else "N/A"

        explanation = (
            f"The new observation does not provide sufficient evidence to update the hypothesis because "
            f"the candidate was not reliably detected (status: {status_label}, SNR: {snr_label}). "
            f"Without an independent astrometric position at Epoch 3, the trajectory cannot be constrained."
        )

        detailed_reasons.append(
            f"Candidate detection status in new observation is '{status_label}'."
        )
        if new_obs.snr is not None and new_obs.snr < request.min_snr_threshold:
            detailed_reasons.append(
                f"Measured SNR ({new_obs.snr:.1f}) is below the required detection threshold "
                f"of {request.min_snr_threshold:.1f} sigma."
            )
        detailed_reasons.append(
            "Astrometric trajectory cannot be evaluated without a confirmed centroid measurement."
        )

        updated_hypo = Hypothesis(
            hypothesis_id=hypo.hypothesis_id,
            title=hypo.title,
            description="Hypothesis unconstrained: new observation lacked reliable detection.",
            candidate_id=hypo.candidate_id,
            initial_observations=hypo.initial_observations,
            current_status="insufficient-evidence",
            confidence="low",
        )

        return HypothesisUpdateResult(
            update_id=str(uuid.uuid4())[:8],
            hypothesis_id=hypo.hypothesis_id,
            previous_classification=hypo.current_status,
            new_classification=classification,
            confidence=confidence,
            summary_verdict=summary_verdict,
            explanation=explanation,
            detailed_reasons=detailed_reasons,
            trajectory_prediction=prediction,
            evidence_comparison=comp,
            updated_hypothesis=updated_hypo,
            warnings=warnings,
        )

    # RULE 2: CHANGED
    # Target is detected, but its measured position is essentially stationary with respect to
    # Epoch 1 or Epoch 2 (separation <= stationary_threshold_arcsec, ~1/3 SPHEREx pixel),
    # demonstrating that the previous interpretation of continuous motion was flawed.
    is_stationary_to_e1 = (
        comp.stationary_separation_from_e1_arcsec is not None
        and comp.stationary_separation_from_e1_arcsec <= request.stationary_threshold_arcsec
    )
    is_stationary_to_e2 = (
        comp.stationary_separation_from_e2_arcsec is not None
        and comp.stationary_separation_from_e2_arcsec <= request.stationary_threshold_arcsec
    )

    if is_stationary_to_e1 or is_stationary_to_e2:
        classification = HypothesisClassification.CHANGED
        confidence = "high" if (new_obs.snr and new_obs.snr >= 5.0) else "medium"
        summary_verdict = "CHANGED — New observation indicates source is stationary."

        ref_epoch = "Epoch 1" if is_stationary_to_e1 else "Epoch 2"
        sep_val = comp.stationary_separation_from_e1_arcsec if is_stationary_to_e1 else comp.stationary_separation_from_e2_arcsec

        explanation = (
            f"The new observation changes the hypothesis because the candidate's newly measured position "
            f"is stationary relative to {ref_epoch} (separation: {sep_val:.2f}″ <= {request.stationary_threshold_arcsec:.1f}″). "
            f"This indicates that the earlier two-epoch detection likely involved an ambiguous cross-match or transient "
            f"rather than genuine continuous physical motion."
        )

        detailed_reasons.append(
            f"Separation from {ref_epoch} position is {sep_val:.2f}″, which is within the stationary threshold "
            f"of {request.stationary_threshold_arcsec:.1f}″ (~1/3 SPHEREx pixel)."
        )
        detailed_reasons.append(
            f"Source shows zero significant displacement after {prediction.elapsed_days_e2_to_e3:.1f} elapsed days."
        )
        detailed_reasons.append(
            "Working hypothesis updated from 'moving-object candidate' to 'stationary source / cross-match ambiguity'."
        )

        updated_hypo = Hypothesis(
            hypothesis_id=hypo.hypothesis_id,
            title="Source represents a stationary astronomical object with prior cross-match ambiguity",
            description="Re-evaluation reveals source is stationary; apparent motion was an artifact of cross-matching.",
            candidate_id=hypo.candidate_id,
            initial_observations=hypo.initial_observations + [new_obs.observation_id],
            current_status="stationary",
            confidence=confidence,
        )

        return HypothesisUpdateResult(
            update_id=str(uuid.uuid4())[:8],
            hypothesis_id=hypo.hypothesis_id,
            previous_classification=hypo.current_status,
            new_classification=classification,
            confidence=confidence,
            summary_verdict=summary_verdict,
            explanation=explanation,
            detailed_reasons=detailed_reasons,
            trajectory_prediction=prediction,
            evidence_comparison=comp,
            updated_hypothesis=updated_hypo,
            warnings=warnings,
        )

    # RULE 3: STRENGTHENED
    # Target detected, residual within tolerance, and motion direction consistent
    is_residual_consistent = (
        comp.angular_residual_arcsec is not None
        and comp.angular_residual_arcsec <= request.residual_tolerance_arcsec
    )
    is_direction_consistent = (
        comp.position_angle_residual_deg is not None
        and comp.position_angle_residual_deg <= request.direction_tolerance_deg
    )

    if is_residual_consistent and is_direction_consistent:
        classification = HypothesisClassification.STRENGTHENED
        confidence = "high" if (new_obs.snr and new_obs.snr >= 5.0) else "medium"
        summary_verdict = "STRENGTHENED — Trajectory confirmed across three independent epochs."

        explanation = (
            f"The new observation strengthens the moving-object hypothesis because the candidate was "
            f"independently detected with SNR {new_obs.snr:.1f} and its measured position "
            f"(RA {comp.measured_ra:.5f}°, DEC {comp.measured_dec:.5f}°) lies within {comp.angular_residual_arcsec:.2f}″ "
            f"({comp.angular_residual_pixels:.2f} pixels) of the predicted trajectory, with consistent direction "
            f"(ΔPA = {comp.position_angle_residual_deg:.1f}° <= {request.direction_tolerance_deg}°)."
        )

        detailed_reasons.append(
            f"Independent detection across 3 distinct visits confirms physical persistence of the candidate."
        )
        detailed_reasons.append(
            f"Astrometric residual of {comp.angular_residual_arcsec:.2f}″ is within the 1.5-pixel tolerance "
            f"of {request.residual_tolerance_arcsec:.2f}″."
        )
        detailed_reasons.append(
            f"Observed motion direction (PA {comp.observed_position_angle_deg:.1f}°) aligns with baseline "
            f"trajectory (PA {baseline.position_angle_deg:.1f}°) within {comp.position_angle_residual_deg:.1f}°."
        )
        detailed_reasons.append(
            f"Observed speed ({comp.observed_speed_arcsec_day:.2f}″/day) remains consistent with baseline "
            f"apparent speed ({baseline.angular_speed_arcsec_day:.2f}″/day)."
        )

        updated_hypo = Hypothesis(
            hypothesis_id=hypo.hypothesis_id,
            title="Candidate represents a confirmed three-epoch moving astronomical source",
            description="Trajectory confirmed by three independent observations with consistent direction and speed.",
            candidate_id=hypo.candidate_id,
            initial_observations=hypo.initial_observations + [new_obs.observation_id],
            current_status="high-confidence-candidate",
            confidence="high",
        )

        return HypothesisUpdateResult(
            update_id=str(uuid.uuid4())[:8],
            hypothesis_id=hypo.hypothesis_id,
            previous_classification=hypo.current_status,
            new_classification=classification,
            confidence=confidence,
            summary_verdict=summary_verdict,
            explanation=explanation,
            detailed_reasons=detailed_reasons,
            trajectory_prediction=prediction,
            evidence_comparison=comp,
            updated_hypothesis=updated_hypo,
            warnings=warnings,
        )

    # RULE 4: WEAKENED
    # Target was reliably detected, but position deviates significantly from expected trajectory
    classification = HypothesisClassification.WEAKENED
    confidence = "medium"
    summary_verdict = "WEAKENED — New observation contradicts predicted trajectory."

    residual_val = comp.angular_residual_arcsec or 0.0
    residual_px = comp.angular_residual_pixels or 0.0
    pa_res = comp.position_angle_residual_deg or 0.0

    explanation = (
        f"The new observation weakens the moving-object hypothesis because although a source was "
        f"detected with SNR {new_obs.snr:.1f}, its measured position deviates by {residual_val:.2f}″ "
        f"({residual_px:.2f} pixels) from the expected trajectory, which significantly exceeds the "
        f"allowable tolerance ({request.residual_tolerance_arcsec:.2f}″). This contradiction challenges "
        f"simple ballistic or Keplerian motion."
    )

    detailed_reasons.append(
        f"Astrometric residual of {residual_val:.2f}″ exceeds the 1.5-pixel threshold ({request.residual_tolerance_arcsec:.2f}″)."
    )
    if comp.position_angle_residual_deg and comp.position_angle_residual_deg > request.direction_tolerance_deg:
        detailed_reasons.append(
            f"Observed motion direction deviated by {pa_res:.1f}° from baseline trajectory "
            f"(tolerance: {request.direction_tolerance_deg}°)."
        )
    detailed_reasons.append(
        "Trajectory discontinuity suggests either an unrelated field source or an unmodeled non-linear acceleration."
    )

    updated_hypo = Hypothesis(
        hypothesis_id=hypo.hypothesis_id,
        title="Candidate trajectory contradicted by third-epoch observation",
        description="Astrometric deviation in Epoch 3 contradicts linear extrapolation of baseline motion.",
        candidate_id=hypo.candidate_id,
        initial_observations=hypo.initial_observations + [new_obs.observation_id],
        current_status="weakened-candidate",
        confidence="low",
    )

    return HypothesisUpdateResult(
        update_id=str(uuid.uuid4())[:8],
        hypothesis_id=hypo.hypothesis_id,
        previous_classification=hypo.current_status,
        new_classification=classification,
        confidence=confidence,
        summary_verdict=summary_verdict,
        explanation=explanation,
        detailed_reasons=detailed_reasons,
        trajectory_prediction=prediction,
        evidence_comparison=comp,
        updated_hypothesis=updated_hypo,
        warnings=warnings,
    )


def get_challenge_scenarios() -> List[ChallengeScenarioInfo]:
    """
    Returns 4 controlled, deterministic challenge demonstration scenarios
    illustrating all four scientific evaluation outcomes:
    1. Consistent continuation -> STRENGTHENED
    2. Trajectory deviation -> WEAKENED
    3. Stationary coincident source -> CHANGED
    4. Non-detection / low SNR -> INCONCLUSIVE
    """
    baseline_standard = EvidenceSnapshot(
        candidate_id="SPH-CAND-2025-01",
        observation_id_1="2025W18_1B_0001_1",
        observation_id_2="2025W43_1A_0142_1",
        timestamp_utc_1="2025-04-28 13:00:15",
        timestamp_utc_2="2025-10-28 13:00:15",
        ra_1=276.2413,
        dec_1=64.8427,
        ra_2=276.2632,
        dec_2=64.8225,
        displacement_arcsec=80.08,
        angular_speed_arcsec_day=0.4376,
        position_angle_deg=155.2,
        direction="Southeast",
        snr_1=14.2,
        snr_2=13.8,
        confidence="high",
        status="moving-object-candidate",
    )

    # 1. STRENGTHENED: Continuation to 2026-04-28 (182 days later)
    # Expected: RA ~276.2851, DEC ~64.8023. Measured within 0.8 arcsec
    obs_strengthened = NewObservationInput(
        observation_id="2026W18_1A_0317_1",
        observation_time_utc="2026-04-28 13:00:15",
        ra_center=276.28,
        dec_center=64.80,
        bandpass="SPHEREx-D4",
        is_scenario=True,
        scenario_name="Scenario A: Orbital Trajectory Continuation",
        detection_status="DETECTED",
        measured_ra=276.2853,
        measured_dec=64.8021,
        measured_x=120.4,
        measured_y=118.2,
        snr=12.4,
        flux=450.2,
    )

    # 2. WEAKENED: Severe trajectory deviation (residual ~42 arcsec)
    obs_weakened = NewObservationInput(
        observation_id="2026W18_SCENARIO_DEV",
        observation_time_utc="2026-04-28 13:00:15",
        ra_center=276.28,
        dec_center=64.80,
        bandpass="SPHEREx-D4",
        is_scenario=True,
        scenario_name="Scenario B: Trajectory Deviation",
        detection_status="DETECTED",
        measured_ra=276.2500,
        measured_dec=64.8400,
        measured_x=45.2,
        measured_y=210.6,
        snr=10.2,
        flux=380.0,
    )

    # 3. CHANGED: Measured position coincident with Epoch 1 (separation 0.3″)
    obs_changed = NewObservationInput(
        observation_id="2026W18_SCENARIO_STAT",
        observation_time_utc="2026-04-28 13:00:15",
        ra_center=276.24,
        dec_center=64.84,
        bandpass="SPHEREx-D4",
        is_scenario=True,
        scenario_name="Scenario C: Stationary Coincident Source",
        detection_status="DETECTED",
        measured_ra=276.2414,
        measured_dec=64.8426,
        measured_x=100.1,
        measured_y=100.2,
        snr=14.1,
        flux=520.0,
    )

    # 4. INCONCLUSIVE: Target not detected / low SNR
    obs_inconclusive = NewObservationInput(
        observation_id="2026W18_SCENARIO_NODET",
        observation_time_utc="2026-04-28 13:00:15",
        ra_center=276.28,
        dec_center=64.80,
        bandpass="SPHEREx-D4",
        is_scenario=True,
        scenario_name="Scenario D: Non-Detection / Low SNR",
        detection_status="NOT_DETECTED",
        measured_ra=None,
        measured_dec=None,
        snr=1.4,
    )

    return [
        ChallengeScenarioInfo(
            scenario_id="scenario-strengthened",
            title="Consistent Trajectory Continuation",
            expected_outcome=HypothesisClassification.STRENGTHENED,
            description="The candidate is detected within 0.8″ of the predicted trajectory with consistent velocity and direction.",
            baseline_evidence=baseline_standard,
            new_observation=obs_strengthened,
        ),
        ChallengeScenarioInfo(
            scenario_id="scenario-weakened",
            title="Contradictory Trajectory Deviation",
            expected_outcome=HypothesisClassification.WEAKENED,
            description="A reliable source is detected, but deviates by 42.5″ from the ballistic trajectory.",
            baseline_evidence=baseline_standard,
            new_observation=obs_weakened,
        ),
        ChallengeScenarioInfo(
            scenario_id="scenario-changed",
            title="Stationary Source Recovery",
            expected_outcome=HypothesisClassification.CHANGED,
            description="The measured position is coincident with Epoch 1 (<0.4″), indicating a stationary source with prior cross-matching ambiguity.",
            baseline_evidence=baseline_standard,
            new_observation=obs_changed,
        ),
        ChallengeScenarioInfo(
            scenario_id="scenario-inconclusive",
            title="Non-Detection / Low SNR",
            expected_outcome=HypothesisClassification.INCONCLUSIVE,
            description="The candidate is not detected above 3 sigma at the predicted epoch.",
            baseline_evidence=baseline_standard,
            new_observation=obs_inconclusive,
        ),
    ]
