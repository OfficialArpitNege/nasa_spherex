"""
Unit tests for the Hypothesis Update & New Observation analysis pipeline.

Verifies:
1. Trajectory extrapolation accuracy with spherical geometry and RA wraparound
2. Deterministic rule evaluation for:
   - STRENGTHENED (consistent continuation)
   - WEAKENED (trajectory deviation)
   - CHANGED (stationary source recovery)
   - INCONCLUSIVE (non-detection or low SNR)
3. FastAPI endpoints POST /api/hypothesis/update and GET /api/hypothesis/scenarios
4. All challenge scenarios produce their designated expected outcome
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.hypothesis import (
    EvidenceSnapshot,
    Hypothesis,
    HypothesisClassification,
    HypothesisUpdateRequest,
    NewObservationInput,
)
from app.services.hypothesis_analysis import (
    evaluate_hypothesis_update,
    get_challenge_scenarios,
    predict_trajectory,
)

client = TestClient(app)


@pytest.fixture
def baseline_evidence():
    return EvidenceSnapshot(
        candidate_id="SPH-TEST-001",
        observation_id_1="OBS_EPOCH_1",
        observation_id_2="OBS_EPOCH_2",
        timestamp_utc_1="2025-04-28 12:00:00",
        timestamp_utc_2="2025-10-28 12:00:00",
        ra_1=276.2413,
        dec_1=64.8427,
        ra_2=276.2632,
        dec_2=64.8225,
        displacement_arcsec=80.08,
        angular_speed_arcsec_day=0.4376,
        position_angle_deg=155.2,
        direction="Southeast",
        snr_1=14.0,
        snr_2=13.5,
        confidence="high",
        status="moving-object-candidate",
    )


@pytest.fixture
def working_hypothesis():
    return Hypothesis(
        hypothesis_id="HYPO-001",
        title="Candidate represents a genuine moving astronomical source",
        description="Two-epoch baseline motion detected with 80.08 arcsec displacement over 183 days.",
        candidate_id="SPH-TEST-001",
        initial_observations=["OBS_EPOCH_1", "OBS_EPOCH_2"],
        current_status="moving-object-candidate",
        confidence="high",
    )


def test_trajectory_prediction_spherical(baseline_evidence):
    # Predict 182 days forward from Epoch 2 (to 2026-04-28)
    prediction = predict_trajectory(
        baseline=baseline_evidence,
        new_obs_time_utc="2026-04-28 12:00:00",
    )
    assert prediction.elapsed_days_e2_to_e3 > 180.0
    assert prediction.expected_displacement_from_e2_arcsec > 70.0
    # Expected RA and DEC should follow SE direction (RA increases, DEC decreases)
    assert prediction.predicted_ra > baseline_evidence.ra_2
    assert prediction.predicted_dec < baseline_evidence.dec_2


def test_trajectory_prediction_ra_wraparound():
    # Near RA = 359.95 moving East across 0°
    wraparound_baseline = EvidenceSnapshot(
        candidate_id="SPH-WRAP-001",
        observation_id_1="OBS_W1",
        observation_id_2="OBS_W2",
        timestamp_utc_1="2025-01-01 00:00:00",
        timestamp_utc_2="2025-01-11 00:00:00",
        ra_1=359.90,
        dec_1=0.0,
        ra_2=359.98,
        dec_2=0.0,
        displacement_arcsec=288.0,
        angular_speed_arcsec_day=28.8,
        position_angle_deg=90.0,  # Pure East
        direction="East",
        snr_1=15.0,
        snr_2=15.0,
        confidence="high",
        status="moving-object-candidate",
    )
    # 5 days later, it should cross 0° to ~0.02°
    prediction = predict_trajectory(wraparound_baseline, "2025-01-16 00:00:00")
    assert 0.0 <= prediction.predicted_ra < 1.0


def test_hypothesis_strengthened(working_hypothesis, baseline_evidence):
    # Prediction: ~276.2851, ~64.8023
    new_obs = NewObservationInput(
        observation_id="OBS_EPOCH_3",
        observation_time_utc="2026-04-28 12:00:00",
        ra_center=276.28,
        dec_center=64.80,
        detection_status="DETECTED",
        measured_ra=276.2853,
        measured_dec=64.8021,
        snr=12.0,
    )
    req = HypothesisUpdateRequest(
        hypothesis=working_hypothesis,
        baseline_evidence=baseline_evidence,
        new_observation=new_obs,
    )
    res = evaluate_hypothesis_update(req)
    assert res.new_classification == HypothesisClassification.STRENGTHENED
    assert res.evidence_comparison.angular_residual_arcsec < 5.0
    assert "strengthens" in res.explanation.lower()
    assert res.updated_hypothesis.confidence == "high"


def test_hypothesis_weakened(working_hypothesis, baseline_evidence):
    # Measured point deviates significantly (40+ arcsec off)
    new_obs = NewObservationInput(
        observation_id="OBS_EPOCH_3_DEV",
        observation_time_utc="2026-04-28 12:00:00",
        ra_center=276.28,
        dec_center=64.80,
        detection_status="DETECTED",
        measured_ra=276.2500,
        measured_dec=64.8400,
        snr=10.0,
    )
    req = HypothesisUpdateRequest(
        hypothesis=working_hypothesis,
        baseline_evidence=baseline_evidence,
        new_observation=new_obs,
    )
    res = evaluate_hypothesis_update(req)
    assert res.new_classification == HypothesisClassification.WEAKENED
    assert res.evidence_comparison.angular_residual_arcsec > 9.24
    assert "weakens" in res.explanation.lower()


def test_hypothesis_changed(working_hypothesis, baseline_evidence):
    # Measured point is coincident with Epoch 1 (<0.5 arcsec)
    new_obs = NewObservationInput(
        observation_id="OBS_EPOCH_3_STAT",
        observation_time_utc="2026-04-28 12:00:00",
        ra_center=276.24,
        dec_center=64.84,
        detection_status="DETECTED",
        measured_ra=276.2414,
        measured_dec=64.8426,
        snr=14.0,
    )
    req = HypothesisUpdateRequest(
        hypothesis=working_hypothesis,
        baseline_evidence=baseline_evidence,
        new_observation=new_obs,
    )
    res = evaluate_hypothesis_update(req)
    assert res.new_classification == HypothesisClassification.CHANGED
    assert res.evidence_comparison.stationary_separation_from_e1_arcsec < 2.5
    assert "stationary" in res.explanation.lower()


def test_hypothesis_inconclusive_not_detected(working_hypothesis, baseline_evidence):
    new_obs = NewObservationInput(
        observation_id="OBS_EPOCH_3_NODET",
        observation_time_utc="2026-04-28 12:00:00",
        ra_center=276.28,
        dec_center=64.80,
        detection_status="NOT_DETECTED",
        measured_ra=None,
        measured_dec=None,
        snr=1.2,
    )
    req = HypothesisUpdateRequest(
        hypothesis=working_hypothesis,
        baseline_evidence=baseline_evidence,
        new_observation=new_obs,
    )
    res = evaluate_hypothesis_update(req)
    assert res.new_classification == HypothesisClassification.INCONCLUSIVE
    assert "not reliably detected" in res.explanation.lower()


def test_hypothesis_inconclusive_low_snr(working_hypothesis, baseline_evidence):
    new_obs = NewObservationInput(
        observation_id="OBS_EPOCH_3_LOWSNR",
        observation_time_utc="2026-04-28 12:00:00",
        ra_center=276.28,
        dec_center=64.80,
        detection_status="DETECTED",
        measured_ra=276.2851,
        measured_dec=64.8023,
        snr=1.8,  # Below 3.0 threshold
    )
    req = HypothesisUpdateRequest(
        hypothesis=working_hypothesis,
        baseline_evidence=baseline_evidence,
        new_observation=new_obs,
        min_snr_threshold=3.0,
    )
    res = evaluate_hypothesis_update(req)
    assert res.new_classification == HypothesisClassification.INCONCLUSIVE


def test_challenge_scenarios_deterministic_outcomes():
    scenarios = get_challenge_scenarios()
    assert len(scenarios) == 4

    expected_map = {
        "scenario-strengthened": HypothesisClassification.STRENGTHENED,
        "scenario-weakened": HypothesisClassification.WEAKENED,
        "scenario-changed": HypothesisClassification.CHANGED,
        "scenario-inconclusive": HypothesisClassification.INCONCLUSIVE,
    }

    for sc in scenarios:
        assert sc.scenario_id in expected_map
        expected_outcome = expected_map[sc.scenario_id]
        assert sc.expected_outcome == expected_outcome

        # Run evaluation on the scenario
        hypo = Hypothesis(
            hypothesis_id="HYPO-SCENARIO",
            description="Testing challenge scenario",
            candidate_id=sc.baseline_evidence.candidate_id,
            initial_observations=[
                sc.baseline_evidence.observation_id_1,
                sc.baseline_evidence.observation_id_2,
            ],
            current_status="moving-object-candidate",
            confidence="high",
        )
        req = HypothesisUpdateRequest(
            hypothesis=hypo,
            baseline_evidence=sc.baseline_evidence,
            new_observation=sc.new_observation,
        )
        result = evaluate_hypothesis_update(req)
        assert result.new_classification == expected_outcome


def test_api_hypothesis_endpoints():
    # 1. GET /api/hypothesis/scenarios
    sc_resp = client.get("/api/hypothesis/scenarios")
    assert sc_resp.status_code == 200
    sc_data = sc_resp.json()
    assert len(sc_data) == 4

    # 2. POST /api/hypothesis/update with scenario 0
    sc0 = sc_data[0]
    hypo = {
        "hypothesis_id": "API-TEST-HYPO",
        "title": "Candidate represents a genuine moving astronomical source",
        "description": "Baseline two-epoch motion",
        "candidate_id": sc0["baseline_evidence"]["candidate_id"],
        "initial_observations": ["OBS1", "OBS2"],
        "current_status": "moving-object-candidate",
        "confidence": "high",
    }
    update_payload = {
        "hypothesis": hypo,
        "baseline_evidence": sc0["baseline_evidence"],
        "new_observation": sc0["new_observation"],
    }
    update_resp = client.post("/api/hypothesis/update", json=update_payload)
    assert update_resp.status_code == 200
    res_data = update_resp.json()
    assert res_data["new_classification"] == "STRENGTHENED"
    assert "explanation" in res_data
    assert "trajectory_prediction" in res_data
    assert "evidence_comparison" in res_data
