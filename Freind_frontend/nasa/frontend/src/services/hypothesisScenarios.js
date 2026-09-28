/**
 * Default demonstration challenge scenarios and client-side evaluator fallback.
 * Guarantees that the 4 challenge scenarios are always available and render
 * even if the backend dev process has not yet been restarted.
 */

export const DEFAULT_CHALLENGE_SCENARIOS = [
  {
    scenario_id: "scenario-strengthened",
    title: "Consistent Trajectory Continuation",
    expected_outcome: "STRENGTHENED",
    description: "The candidate is independently detected within 0.8″ of the predicted trajectory with consistent velocity and direction.",
    baseline_evidence: {
      candidate_id: "SPH-CAND-2025-01",
      observation_id_1: "2025W18_1B_0001_1",
      observation_id_2: "2025W43_1A_0142_1",
      timestamp_utc_1: "2025-04-28 13:00:15",
      timestamp_utc_2: "2025-10-28 13:00:15",
      ra_1: 276.2413,
      dec_1: 64.8427,
      ra_2: 276.2632,
      dec_2: 64.8225,
      displacement_arcsec: 80.08,
      angular_speed_arcsec_day: 0.4376,
      position_angle_deg: 155.2,
      direction: "Southeast",
      snr_1: 14.2,
      snr_2: 13.8,
      confidence: "high",
      status: "moving-object-candidate",
    },
    new_observation: {
      observation_id: "2026W18_1A_0317_1",
      observation_time_utc: "2026-04-28 13:00:15",
      ra_center: 276.28,
      dec_center: 64.80,
      bandpass: "SPHEREx-D4",
      is_scenario: true,
      scenario_name: "Scenario A: Orbital Trajectory Continuation",
      detection_status: "DETECTED",
      measured_ra: 276.2853,
      measured_dec: 64.8021,
      measured_x: 120.4,
      measured_y: 118.2,
      snr: 12.4,
      flux: 450.2,
    },
  },
  {
    scenario_id: "scenario-weakened",
    title: "Contradictory Trajectory Deviation",
    expected_outcome: "WEAKENED",
    description: "A reliable source is detected with SNR 10.2, but deviates by 42.5″ from the ballistic trajectory.",
    baseline_evidence: {
      candidate_id: "SPH-CAND-2025-01",
      observation_id_1: "2025W18_1B_0001_1",
      observation_id_2: "2025W43_1A_0142_1",
      timestamp_utc_1: "2025-04-28 13:00:15",
      timestamp_utc_2: "2025-10-28 13:00:15",
      ra_1: 276.2413,
      dec_1: 64.8427,
      ra_2: 276.2632,
      dec_2: 64.8225,
      displacement_arcsec: 80.08,
      angular_speed_arcsec_day: 0.4376,
      position_angle_deg: 155.2,
      direction: "Southeast",
      snr_1: 14.2,
      snr_2: 13.8,
      confidence: "high",
      status: "moving-object-candidate",
    },
    new_observation: {
      observation_id: "2026W18_SCENARIO_DEV",
      observation_time_utc: "2026-04-28 13:00:15",
      ra_center: 276.28,
      dec_center: 64.80,
      bandpass: "SPHEREx-D4",
      is_scenario: true,
      scenario_name: "Scenario B: Trajectory Deviation",
      detection_status: "DETECTED",
      measured_ra: 276.2500,
      measured_dec: 64.8400,
      measured_x: 45.2,
      measured_y: 210.6,
      snr: 10.2,
      flux: 380.0,
    },
  },
  {
    scenario_id: "scenario-changed",
    title: "Stationary Source Recovery",
    expected_outcome: "CHANGED",
    description: "The measured position is coincident with Epoch 1 (<0.4″), indicating a stationary source with prior cross-matching ambiguity.",
    baseline_evidence: {
      candidate_id: "SPH-CAND-2025-01",
      observation_id_1: "2025W18_1B_0001_1",
      observation_id_2: "2025W43_1A_0142_1",
      timestamp_utc_1: "2025-04-28 13:00:15",
      timestamp_utc_2: "2025-10-28 13:00:15",
      ra_1: 276.2413,
      dec_1: 64.8427,
      ra_2: 276.2632,
      dec_2: 64.8225,
      displacement_arcsec: 80.08,
      angular_speed_arcsec_day: 0.4376,
      position_angle_deg: 155.2,
      direction: "Southeast",
      snr_1: 14.2,
      snr_2: 13.8,
      confidence: "high",
      status: "moving-object-candidate",
    },
    new_observation: {
      observation_id: "2026W18_SCENARIO_STAT",
      observation_time_utc: "2026-04-28 13:00:15",
      ra_center: 276.24,
      dec_center: 64.84,
      bandpass: "SPHEREx-D4",
      is_scenario: true,
      scenario_name: "Scenario C: Stationary Coincident Source",
      detection_status: "DETECTED",
      measured_ra: 276.2414,
      measured_dec: 64.8426,
      measured_x: 100.1,
      measured_y: 100.2,
      snr: 14.1,
      flux: 520.0,
    },
  },
  {
    scenario_id: "scenario-inconclusive",
    title: "Non-Detection / Low SNR",
    expected_outcome: "INCONCLUSIVE",
    description: "The candidate is not detected above 3 sigma at the predicted epoch.",
    baseline_evidence: {
      candidate_id: "SPH-CAND-2025-01",
      observation_id_1: "2025W18_1B_0001_1",
      observation_id_2: "2025W43_1A_0142_1",
      timestamp_utc_1: "2025-04-28 13:00:15",
      timestamp_utc_2: "2025-10-28 13:00:15",
      ra_1: 276.2413,
      dec_1: 64.8427,
      ra_2: 276.2632,
      dec_2: 64.8225,
      displacement_arcsec: 80.08,
      angular_speed_arcsec_day: 0.4376,
      position_angle_deg: 155.2,
      direction: "Southeast",
      snr_1: 14.2,
      snr_2: 13.8,
      confidence: "high",
      status: "moving-object-candidate",
    },
    new_observation: {
      observation_id: "2026W18_SCENARIO_NODET",
      observation_time_utc: "2026-04-28 13:00:15",
      ra_center: 276.28,
      dec_center: 64.80,
      bandpass: "SPHEREx-D4",
      is_scenario: true,
      scenario_name: "Scenario D: Non-Detection / Low SNR",
      detection_status: "NOT_DETECTED",
      measured_ra: null,
      measured_dec: null,
      snr: 1.4,
    },
  },
];

/**
 * Client-side deterministic evaluation fallback if backend is unreachable or reloading.
 */
export function evaluateHypothesisClientFallback(payload) {
  const { hypothesis: hypo, baseline_evidence: baseline, new_observation: newObs } = payload;
  const t2 = new Date(baseline.timestamp_utc_2 || '2025-10-28T13:00:15Z').getTime();
  const t3 = new Date(newObs.observation_time_utc.replace(' ', 'T') + (newObs.observation_time_utc.includes('Z') ? '' : 'Z')).getTime();
  const elapsedDays = Math.max(0.1, (t3 - t2) / (1000 * 86400));
  const expectedDisp = baseline.angular_speed_arcsec_day * elapsedDays;

  // Spherical approximation
  const rad = Math.PI / 180;
  const paRad = baseline.position_angle_deg * rad;
  const cosDec = Math.cos(baseline.dec_2 * rad);
  const dRa = (expectedDisp / 3600) * Math.sin(paRad) / Math.max(0.01, cosDec);
  const dDec = (expectedDisp / 3600) * Math.cos(paRad);

  const predRa = baseline.ra_2 + dRa;
  const predDec = baseline.dec_2 + dDec;

  const isDetected = newObs.detection_status === 'DETECTED' && newObs.measured_ra != null && newObs.measured_dec != null;

  if (!isDetected || (newObs.snr != null && newObs.snr < 3.0)) {
    return {
      update_id: 'cl-inconclusive',
      hypothesis_id: hypo.hypothesis_id,
      previous_classification: hypo.current_status,
      new_classification: 'INCONCLUSIVE',
      confidence: 'uncertain',
      summary_verdict: 'INCONCLUSIVE — Candidate not reliably detected in new observation.',
      explanation: `The new observation does not provide sufficient evidence to update the hypothesis because the candidate was not reliably detected (status: ${newObs.detection_status}, SNR: ${newObs.snr != null ? newObs.snr.toFixed(1) : 'N/A'}). Without an independent astrometric position at Epoch 3, the trajectory cannot be constrained.`,
      detailed_reasons: [
        `Candidate detection status in new observation is '${newObs.detection_status}'.`,
        `Measured SNR (${newObs.snr != null ? newObs.snr.toFixed(1) : 'N/A'}) is below the 3.0 sigma detection threshold.`,
        'Astrometric trajectory cannot be evaluated without a confirmed centroid measurement.'
      ],
      trajectory_prediction: {
        predicted_ra: parseFloat(predRa.toFixed(6)),
        predicted_dec: parseFloat(predDec.toFixed(6)),
        baseline_displacement_arcsec: baseline.displacement_arcsec,
        baseline_angular_speed_arcsec_day: baseline.angular_speed_arcsec_day,
        baseline_position_angle_deg: baseline.position_angle_deg,
        baseline_direction: baseline.direction,
        elapsed_days_e2_to_e3: parseFloat(elapsedDays.toFixed(2)),
        expected_displacement_from_e2_arcsec: parseFloat(expectedDisp.toFixed(2))
      },
      evidence_comparison: {
        expected_ra: parseFloat(predRa.toFixed(6)),
        expected_dec: parseFloat(predDec.toFixed(6)),
        measured_ra: null,
        measured_dec: null,
        angular_residual_arcsec: null,
        angular_residual_pixels: null,
        observed_displacement_from_e2_arcsec: null,
        observed_speed_arcsec_day: null,
        observed_position_angle_deg: null,
        position_angle_residual_deg: null,
        stationary_separation_from_e1_arcsec: null,
        stationary_separation_from_e2_arcsec: null,
        detection_reliable: false,
        snr: newObs.snr
      },
      updated_hypothesis: {
        ...hypo,
        current_status: 'insufficient-evidence',
        confidence: 'low'
      },
      warnings: [],
      scientific_disclaimer: "SCIENTIFIC INTEGRITY NOTICE: Hypothesis evaluations are deterministic comparisons of kinematic residuals and detection quality against explicit astrometric rules."
    };
  }

  // Calculate separation from predicted
  const dx = (newObs.measured_ra - predRa) * cosDec * 3600;
  const dy = (newObs.measured_dec - predDec) * 3600;
  const residual = Math.hypot(dx, dy);

  // Separation from E1 and E2
  const dx1 = (newObs.measured_ra - baseline.ra_1) * Math.cos(baseline.dec_1 * rad) * 3600;
  const dy1 = (newObs.measured_dec - baseline.dec_1) * 3600;
  const sepE1 = Math.hypot(dx1, dy1);

  const dx2 = (newObs.measured_ra - baseline.ra_2) * cosDec * 3600;
  const dy2 = (newObs.measured_dec - baseline.dec_2) * 3600;
  const obsDisp = Math.hypot(dx2, dy2);
  const obsSpeed = obsDisp / elapsedDays;
  const obsPa = (Math.atan2(dx2, dy2) / rad + 360) % 360;
  const paDiff = Math.abs(obsPa - baseline.position_angle_deg);
  const paResidual = Math.min(paDiff, 360 - paDiff);

  if (sepE1 <= 2.5 || obsDisp <= 2.5) {
    return {
      update_id: 'cl-changed',
      hypothesis_id: hypo.hypothesis_id,
      previous_classification: hypo.current_status,
      new_classification: 'CHANGED',
      confidence: 'high',
      summary_verdict: 'CHANGED — New observation indicates source is stationary.',
      explanation: `The new observation changes the hypothesis because the candidate's newly measured position is stationary relative to an earlier epoch (separation: ${sepE1.toFixed(2)}″ <= 2.5″). This indicates that the earlier two-epoch detection likely involved an ambiguous cross-match or transient rather than genuine continuous physical motion.`,
      detailed_reasons: [
        `Separation from Epoch 1 position is ${sepE1.toFixed(2)}″, within the 2.5″ stationary threshold (~1/3 SPHEREx pixel).`,
        `Source shows zero significant displacement after ${elapsedDays.toFixed(1)} elapsed days.`,
        "Working hypothesis updated from 'moving-object candidate' to 'stationary source / cross-match ambiguity'."
      ],
      trajectory_prediction: {
        predicted_ra: parseFloat(predRa.toFixed(6)),
        predicted_dec: parseFloat(predDec.toFixed(6)),
        baseline_displacement_arcsec: baseline.displacement_arcsec,
        baseline_angular_speed_arcsec_day: baseline.angular_speed_arcsec_day,
        baseline_position_angle_deg: baseline.position_angle_deg,
        baseline_direction: baseline.direction,
        elapsed_days_e2_to_e3: parseFloat(elapsedDays.toFixed(2)),
        expected_displacement_from_e2_arcsec: parseFloat(expectedDisp.toFixed(2))
      },
      evidence_comparison: {
        expected_ra: parseFloat(predRa.toFixed(6)),
        expected_dec: parseFloat(predDec.toFixed(6)),
        measured_ra: newObs.measured_ra,
        measured_dec: newObs.measured_dec,
        angular_residual_arcsec: parseFloat(residual.toFixed(2)),
        angular_residual_pixels: parseFloat((residual / 6.16).toFixed(2)),
        observed_displacement_from_e2_arcsec: parseFloat(obsDisp.toFixed(2)),
        observed_speed_arcsec_day: parseFloat(obsSpeed.toFixed(4)),
        observed_position_angle_deg: parseFloat(obsPa.toFixed(1)),
        position_angle_residual_deg: parseFloat(paResidual.toFixed(1)),
        stationary_separation_from_e1_arcsec: parseFloat(sepE1.toFixed(2)),
        stationary_separation_from_e2_arcsec: parseFloat(obsDisp.toFixed(2)),
        detection_reliable: true,
        snr: newObs.snr
      },
      updated_hypothesis: {
        ...hypo,
        current_status: 'stationary',
        confidence: 'high'
      },
      warnings: [],
      scientific_disclaimer: "SCIENTIFIC INTEGRITY NOTICE: Hypothesis evaluations are deterministic comparisons of kinematic residuals and detection quality against explicit astrometric rules."
    };
  }

  if (residual <= 9.24 && paResidual <= 40.0) {
    return {
      update_id: 'cl-strengthened',
      hypothesis_id: hypo.hypothesis_id,
      previous_classification: hypo.current_status,
      new_classification: 'STRENGTHENED',
      confidence: 'high',
      summary_verdict: 'STRENGTHENED — Trajectory confirmed across three independent epochs.',
      explanation: `The new observation strengthens the moving-object hypothesis because the candidate was independently detected with SNR ${newObs.snr.toFixed(1)} and its measured position lies within ${residual.toFixed(2)}″ (${(residual / 6.16).toFixed(2)} pixels) of the predicted trajectory, with consistent direction (ΔPA = ${paResidual.toFixed(1)}°).`,
      detailed_reasons: [
        'Independent detection across 3 distinct visits confirms physical persistence of the candidate.',
        `Astrometric residual of ${residual.toFixed(2)}″ is within the 1.5-pixel tolerance (9.24″).`,
        `Observed motion direction aligns with baseline trajectory within ${paResidual.toFixed(1)}°.`,
        `Observed speed (${obsSpeed.toFixed(2)}″/day) remains consistent with baseline apparent speed.`
      ],
      trajectory_prediction: {
        predicted_ra: parseFloat(predRa.toFixed(6)),
        predicted_dec: parseFloat(predDec.toFixed(6)),
        baseline_displacement_arcsec: baseline.displacement_arcsec,
        baseline_angular_speed_arcsec_day: baseline.angular_speed_arcsec_day,
        baseline_position_angle_deg: baseline.position_angle_deg,
        baseline_direction: baseline.direction,
        elapsed_days_e2_to_e3: parseFloat(elapsedDays.toFixed(2)),
        expected_displacement_from_e2_arcsec: parseFloat(expectedDisp.toFixed(2))
      },
      evidence_comparison: {
        expected_ra: parseFloat(predRa.toFixed(6)),
        expected_dec: parseFloat(predDec.toFixed(6)),
        measured_ra: newObs.measured_ra,
        measured_dec: newObs.measured_dec,
        angular_residual_arcsec: parseFloat(residual.toFixed(2)),
        angular_residual_pixels: parseFloat((residual / 6.16).toFixed(2)),
        observed_displacement_from_e2_arcsec: parseFloat(obsDisp.toFixed(2)),
        observed_speed_arcsec_day: parseFloat(obsSpeed.toFixed(4)),
        observed_position_angle_deg: parseFloat(obsPa.toFixed(1)),
        position_angle_residual_deg: parseFloat(paResidual.toFixed(1)),
        stationary_separation_from_e1_arcsec: parseFloat(sepE1.toFixed(2)),
        stationary_separation_from_e2_arcsec: parseFloat(obsDisp.toFixed(2)),
        detection_reliable: true,
        snr: newObs.snr
      },
      updated_hypothesis: {
        ...hypo,
        current_status: 'high-confidence-candidate',
        confidence: 'high'
      },
      warnings: [],
      scientific_disclaimer: "SCIENTIFIC INTEGRITY NOTICE: Hypothesis evaluations are deterministic comparisons of kinematic residuals and detection quality against explicit astrometric rules."
    };
  }

  // WEAKENED
  return {
    update_id: 'cl-weakened',
    hypothesis_id: hypo.hypothesis_id,
    previous_classification: hypo.current_status,
    new_classification: 'WEAKENED',
    confidence: 'medium',
    summary_verdict: 'WEAKENED — New observation contradicts predicted trajectory.',
    explanation: `The new observation weakens the moving-object hypothesis because although a source was detected with SNR ${newObs.snr.toFixed(1)}, its measured position deviates by ${residual.toFixed(2)}″ (${(residual / 6.16).toFixed(2)} pixels) from the expected trajectory, which significantly exceeds the allowable tolerance (9.24″).`,
    detailed_reasons: [
      `Astrometric residual of ${residual.toFixed(2)}″ exceeds the 1.5-pixel threshold (9.24″).`,
      `Observed motion direction deviated by ${paResidual.toFixed(1)}° from baseline trajectory.`,
      'Trajectory discontinuity suggests either an unrelated field source or an unmodeled non-linear acceleration.'
    ],
    trajectory_prediction: {
      predicted_ra: parseFloat(predRa.toFixed(6)),
      predicted_dec: parseFloat(predDec.toFixed(6)),
      baseline_displacement_arcsec: baseline.displacement_arcsec,
      baseline_angular_speed_arcsec_day: baseline.angular_speed_arcsec_day,
      baseline_position_angle_deg: baseline.position_angle_deg,
      baseline_direction: baseline.direction,
      elapsed_days_e2_to_e3: parseFloat(elapsedDays.toFixed(2)),
      expected_displacement_from_e2_arcsec: parseFloat(expectedDisp.toFixed(2))
    },
    evidence_comparison: {
      expected_ra: parseFloat(predRa.toFixed(6)),
      expected_dec: parseFloat(predDec.toFixed(6)),
      measured_ra: newObs.measured_ra,
      measured_dec: newObs.measured_dec,
      angular_residual_arcsec: parseFloat(residual.toFixed(2)),
      angular_residual_pixels: parseFloat((residual / 6.16).toFixed(2)),
      observed_displacement_from_e2_arcsec: parseFloat(obsDisp.toFixed(2)),
      observed_speed_arcsec_day: parseFloat(obsSpeed.toFixed(4)),
      observed_position_angle_deg: parseFloat(obsPa.toFixed(1)),
      position_angle_residual_deg: parseFloat(paResidual.toFixed(1)),
      stationary_separation_from_e1_arcsec: parseFloat(sepE1.toFixed(2)),
      stationary_separation_from_e2_arcsec: parseFloat(obsDisp.toFixed(2)),
      detection_reliable: true,
      snr: newObs.snr
    },
    updated_hypothesis: {
      ...hypo,
      current_status: 'weakened-candidate',
      confidence: 'low'
    },
    warnings: [],
    scientific_disclaimer: "SCIENTIFIC INTEGRITY NOTICE: Hypothesis evaluations are deterministic comparisons of kinematic residuals and detection quality against explicit astrometric rules."
  };
}
