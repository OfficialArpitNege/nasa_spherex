import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { 
  checkBackendHealth, 
  searchObservations, 
  fetchCutout, 
  analyzeMotion, 
  validateKnownObject3IAtlas, 
  fetchChallengeScenarios,
  updateHypothesis,
  ApiError 
} from '../services/api';
import { 
  DEFAULT_CHALLENGE_SCENARIOS, 
  evaluateHypothesisClientFallback 
} from '../services/hypothesisScenarios';

const SkyContext = createContext();

export function SkyProvider({ children }) {
  // Navigation & View Mode
  const [mode, setMode] = useState('explore'); // 'explore' | 'compare' | 'validation' | 'hypothesis' | 'discover' | 'about'
  const [view, setView] = useState('blink'); // 'a' | 'b' | 'blink'
  const [blinkSpeed, setBlinkSpeed] = useState(5);
  
  // Real Sky Coordinates (Default: SPHEREx North Ecliptic Pole Deep Field)
  const [coords, setCoords] = useState({
    ra: "18h 25m 02s",
    dec: "+64° 49' 12\"",
    ra_deg: 276.26,
    dec_deg: 64.82,
    region: "SPHEREx DEEP FIELD (NEP)"
  });

  // Backend Health Connection Status
  const [backendStatus, setBackendStatus] = useState('connecting'); // 'connected' | 'connecting' | 'unavailable'
  const [backendError, setBackendError] = useState(null);

  // Search State
  const [searchParams, setSearchParams] = useState({
    ra: 276.26,
    dec: 64.82,
    radius_arcmin: 30.0,
    start_date: '',
    end_date: ''
  });
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [observations, setObservations] = useState([]);
  const [selectedObs1, setSelectedObs1] = useState(null);
  const [selectedObs2, setSelectedObs2] = useState(null);
  const [selectedObs3, setSelectedObs3] = useState(null); // Optional third observation

  // Cutouts & Analysis State
  const [cutout1, setCutout1] = useState(null);
  const [cutout2, setCutout2] = useState(null);
  const [cutout3, setCutout3] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStage, setAnalysisStage] = useState('');
  const [analysisError, setAnalysisError] = useState(null);
  const [motionResult, setMotionResult] = useState(null);

  // Hypothesis Update & Challenge State ("The New Observation")
  const [hypothesis, setHypothesis] = useState(null);
  const [hypothesisResult, setHypothesisResult] = useState(null);
  const [challengeScenarios, setChallengeScenarios] = useState(DEFAULT_CHALLENGE_SCENARIOS);
  const [isLoadingHypothesis, setIsLoadingHypothesis] = useState(false);
  const [hypothesisError, setHypothesisError] = useState(null);
  const [isNewObsModalOpen, setIsNewObsModalOpen] = useState(false);

  // 3I/ATLAS Known Object Validation State
  const [knownObjectResult, setKnownObjectResult] = useState(null);
  const [isLoadingKnownObject, setIsLoadingKnownObject] = useState(false);
  const [knownObjectError, setKnownObjectError] = useState(null);

  // Canvas & Interaction State (Friend's original state preserved)
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(-1);
  const [detected, setDetected] = useState(false);
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [statusText, setStatusText] = useState('');
  const [isFocusMode, setIsFocusMode] = useState(false);

  // Initial Backend Health Verification
  const verifyBackend = useCallback(async () => {
    try {
      setBackendStatus('connecting');
      await checkBackendHealth();
      setBackendStatus('connected');
      setBackendError(null);
    } catch (err) {
      setBackendStatus('unavailable');
      setBackendError(err.message || 'FastAPI backend is offline.');
    }
  }, []);

  // Load Challenge Scenarios on mount
  const loadScenarios = useCallback(async () => {
    try {
      const list = await fetchChallengeScenarios();
      if (list && list.length > 0) {
        setChallengeScenarios(list);
      }
    } catch (err) {
      console.warn('Could not load challenge scenarios from backend, keeping default scenarios:', err);
    }
  }, []);

  useEffect(() => {
    verifyBackend();
    loadScenarios();
    const interval = setInterval(verifyBackend, 30000);
    return () => clearInterval(interval);
  }, [verifyBackend, loadScenarios]);

  // Mode switching
  const switchMode = (newMode) => {
    setMode(newMode);
    setIsFocusMode(false);
    
    if (newMode === 'compare') {
      if (!motionResult && observations.length === 0) {
        setStatusText('Search SPHEREx archive and select two epochs to analyze.');
      } else if (motionResult) {
        setStatusText(`${candidates.length} moving-object candidate(s) identified.`);
      }
    } else if (newMode === 'hypothesis') {
      setStatusText('Hypothesis Update: Incorporating new observation evidence.');
    } else if (newMode === 'discover') {
      setStatusText('Inspect blinking epochs. Click any source you suspect shifted position.');
    } else if (newMode === 'validation') {
      setStatusText('Known Object Validation: Interstellar Comet 3I/ATLAS');
    } else {
      setStatusText('');
    }
  };

  /**
   * Execute real NASA/IRSA SPHEREx search
   */
  const executeSearch = async (customParams = null) => {
    const params = customParams || searchParams;
    setIsSearching(true);
    setSearchError(null);
    try {
      const res = await searchObservations(params);
      const obsList = res.observations || [];
      setObservations(obsList);

      // Auto-select first two distinct dates if available
      if (obsList.length >= 2) {
        setSelectedObs1(obsList[0]);
        const date1 = (obsList[0].observation_time_utc || '').split('T')[0];
        const differentDate = obsList.find(o => (o.observation_time_utc || '').split('T')[0] !== date1);
        setSelectedObs2(differentDate || obsList[1]);
        
        // Find third date if available
        const date2 = ((differentDate || obsList[1]).observation_time_utc || '').split('T')[0];
        const thirdDate = obsList.find(o => {
          const d = (o.observation_time_utc || '').split('T')[0];
          return d !== date1 && d !== date2;
        });
        setSelectedObs3(thirdDate || null);
      } else if (obsList.length === 1) {
        setSelectedObs1(obsList[0]);
        setSelectedObs2(null);
        setSelectedObs3(null);
      } else {
        setSelectedObs1(null);
        setSelectedObs2(null);
        setSelectedObs3(null);
      }

      setCoords(prev => ({
        ...prev,
        ra_deg: params.ra,
        dec_deg: params.dec,
        region: params.ra === 276.26 ? "SPHEREx DEEP FIELD (NEP)" : `FIELD (RA ${params.ra.toFixed(2)}, DEC ${params.dec.toFixed(2)})`
      }));

      setStatusText(`Found ${obsList.length} SPHEREx observations. Select epochs to analyze.`);
      return obsList;
    } catch (err) {
      const msg = err.message || 'Failed to search SPHEREx archive.';
      setSearchError(msg);
      setStatusText(`Search error: ${msg}`);
      return [];
    } finally {
      setIsSearching(false);
    }
  };

  /**
   * Execute two-epoch motion analysis pipeline
   */
  const executeMotionAnalysis = async (obsA = selectedObs1, obsB = selectedObs2) => {
    if (!obsA || !obsB) {
      setAnalysisError('Please select two observation epochs to run motion analysis.');
      return null;
    }
    if (obsA.observation_id === obsB.observation_id) {
      setAnalysisError('Please select two distinct observations for temporal comparison.');
      return null;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    setMotionResult(null);

    try {
      // Stage 1: Cutout retrieval for Epoch 1
      setAnalysisStage('Retrieving SPHEREx Epoch 1 FITS...');
      const c1 = await fetchCutout({
        observation_id: obsA.observation_id,
        ra: searchParams.ra,
        dec: searchParams.dec,
        cutout_size_deg: 0.05,
        datalink_url: obsA.data_access_url,
        bandpass: obsA.bandpass,
        observation_time_utc: obsA.observation_time_utc
      });
      setCutout1(c1);

      // Stage 2: Cutout retrieval for Epoch 2
      setAnalysisStage('Retrieving SPHEREx Epoch 2 FITS...');
      const c2 = await fetchCutout({
        observation_id: obsB.observation_id,
        ra: searchParams.ra,
        dec: searchParams.dec,
        cutout_size_deg: 0.05,
        datalink_url: obsB.data_access_url,
        bandpass: obsB.bandpass,
        observation_time_utc: obsB.observation_time_utc
      });
      setCutout2(c2);

      // Stage 3: Source detection and motion analysis
      setAnalysisStage('Detecting sources & calculating kinematics...');
      const analysisReq = {
        fits_path_1: c1.fits_relative_path || c1.fits_filename,
        fits_path_2: c2.fits_relative_path || c2.fits_filename,
        observation_id_1: obsA.observation_id,
        observation_id_2: obsB.observation_id,
        ra: searchParams.ra,
        dec: searchParams.dec,
        timestamp_utc_1: obsA.observation_time_utc,
        timestamp_utc_2: obsB.observation_time_utc,
        bandpass_1: obsA.bandpass,
        bandpass_2: obsB.bandpass,
        detection_sigma: 3.0,
        match_tolerance_arcsec: 30.0,
        motion_threshold_arcsec: 2.0,
        candidate_threshold_arcsec: 6.2
      };

      const result = await analyzeMotion(analysisReq);
      setMotionResult(result);

      // Map real candidates to frontend format
      const mappedCandidates = (result.candidates || []).map((cand, idx) => {
        return {
          ...cand,
          n: idx + 1,
          candidate_id: cand.candidate_id,
          label: cand.status === 'moving-object-candidate' ? 'Moving-object candidate' : 'Possible motion',
          title: cand.status === 'moving-object-candidate' ? 'MOVING-OBJECT CANDIDATE' : 'POSSIBLE MOTION',
          bx: cand.position_epoch_1.x,
          by: cand.position_epoch_1.y,
          vx: cand.position_epoch_2.x - cand.position_epoch_1.x,
          vy: cand.position_epoch_2.y - cand.position_epoch_1.y,
          flux: false,
          displacement_arcsec: cand.angular_displacement.arcsec,
          speed_arcsec_day: cand.average_angular_speed.arcsec_per_day,
          direction: cand.direction_label,
          position_angle: cand.position_angle_deg,
          snr_1: cand.quality.snr_epoch_1,
          snr_2: cand.quality.snr_epoch_2,
          confidence: cand.quality.confidence,
          trail_path: cand.motion_trail_path
        };
      });

      setCandidates(mappedCandidates);
      setDetected(mappedCandidates.length > 0);

      if (mappedCandidates.length > 0) {
        const topCand = mappedCandidates[0];
        setSelectedCandidate(topCand);
        setStatusText(`${mappedCandidates.length} moving-object candidate(s) identified.`);

        // Initialize baseline hypothesis
        setHypothesis({
          hypothesis_id: `HYP-${topCand.candidate_id}`,
          title: `Candidate ${topCand.candidate_id} represents a genuine moving astronomical source`,
          description: `Two-epoch baseline motion detected with ${topCand.displacement_arcsec.toFixed(2)}″ displacement in direction ${topCand.direction} (${topCand.position_angle.toFixed(1)}°).`,
          candidate_id: topCand.candidate_id,
          initial_observations: [obsA.observation_id, obsB.observation_id],
          current_status: 'moving-object-candidate',
          confidence: topCand.confidence || 'medium'
        });
      } else if (result.source_statistics && result.source_statistics.stationary_count > 0) {
        setStatusText(`Stationary / no significant motion detected (${result.source_statistics.stationary_count} sources matched).`);
      } else {
        setStatusText('Insufficient evidence for motion.');
      }

      return result;
    } catch (err) {
      const msg = err.message || 'Motion analysis pipeline failed.';
      setAnalysisError(msg);
      setStatusText(`Analysis error: ${msg}`);
      return null;
    } finally {
      setIsAnalyzing(false);
      setAnalysisStage('');
    }
  };

  /**
   * Evaluate New Observation against current hypothesis
   */
  const executeHypothesisUpdate = async (newObsData, customBaseline = null, customHypo = null) => {
    setIsLoadingHypothesis(true);
    setHypothesisError(null);
    try {
      let baseline = customBaseline;
      if (!baseline && selectedCandidate && motionResult && selectedObs1 && selectedObs2) {
        baseline = {
          candidate_id: selectedCandidate.candidate_id,
          observation_id_1: selectedObs1.observation_id,
          observation_id_2: selectedObs2.observation_id,
          timestamp_utc_1: selectedObs1.observation_time_utc,
          timestamp_utc_2: selectedObs2.observation_time_utc,
          ra_1: selectedCandidate.position_epoch_1.ra,
          dec_1: selectedCandidate.position_epoch_1.dec,
          ra_2: selectedCandidate.position_epoch_2.ra,
          dec_2: selectedCandidate.position_epoch_2.dec,
          displacement_arcsec: selectedCandidate.angular_displacement.arcsec,
          angular_speed_arcsec_day: selectedCandidate.average_angular_speed.arcsec_per_day,
          position_angle_deg: selectedCandidate.position_angle_deg,
          direction: selectedCandidate.direction_label,
          snr_1: selectedCandidate.quality?.snr_epoch_1,
          snr_2: selectedCandidate.quality?.snr_epoch_2,
          confidence: selectedCandidate.quality?.confidence || 'medium',
          status: selectedCandidate.status || 'moving-object-candidate'
        };
      }

      if (!baseline && challengeScenarios && challengeScenarios.length > 0) {
        baseline = challengeScenarios[0].baseline_evidence;
      }
      if (!baseline) {
        baseline = DEFAULT_CHALLENGE_SCENARIOS[0].baseline_evidence;
      }

      const activeHypo = customHypo || hypothesis || {
        hypothesis_id: `HYP-${baseline?.candidate_id || '001'}`,
        title: 'Candidate represents a genuine moving astronomical source',
        description: 'Baseline two-epoch apparent motion.',
        candidate_id: baseline?.candidate_id || 'SPH-001',
        initial_observations: [baseline?.observation_id_1 || 'E1', baseline?.observation_id_2 || 'E2'],
        current_status: baseline?.status || 'moving-object-candidate',
        confidence: baseline?.confidence || 'medium'
      };

      const payload = {
        hypothesis: activeHypo,
        baseline_evidence: baseline,
        new_observation: newObsData
      };

      let result;
      try {
        result = await updateHypothesis(payload);
      } catch (apiErr) {
        console.warn('Backend updateHypothesis unavailable, using deterministic evaluator fallback:', apiErr);
        result = evaluateHypothesisClientFallback(payload);
      }

      setHypothesisResult(result);
      setHypothesis(result.updated_hypothesis);
      setStatusText(`Hypothesis Update: ${result.new_classification} — ${result.summary_verdict}`);
      return result;
    } catch (err) {
      const msg = err.message || 'Failed to update hypothesis with new observation.';
      setHypothesisError(msg);
      return null;
    } finally {
      setIsLoadingHypothesis(false);
    }
  };

  /**
   * Execute official 3I/ATLAS Known Object Validation
   */
  const executeKnownObjectValidation = async () => {
    setIsLoadingKnownObject(true);
    setKnownObjectError(null);
    try {
      const result = await validateKnownObject3IAtlas();
      setKnownObjectResult(result);
      return result;
    } catch (err) {
      const msg = err.message || 'Failed to validate 3I/ATLAS known object.';
      setKnownObjectError(msg);
      return null;
    } finally {
      setIsLoadingKnownObject(false);
    }
  };

  return (
    <SkyContext.Provider value={{
      mode, switchMode,
      view, setView,
      blinkSpeed, setBlinkSpeed,
      coords, setCoords,
      backendStatus, backendError, verifyBackend,
      searchParams, setSearchParams,
      isSearching, searchError,
      observations, setObservations,
      selectedObs1, setSelectedObs1,
      selectedObs2, setSelectedObs2,
      selectedObs3, setSelectedObs3,
      executeSearch,
      cutout1, cutout2, cutout3,
      isAnalyzing, analysisStage, analysisError,
      motionResult, setMotionResult,
      executeMotionAnalysis,
      hypothesis, setHypothesis,
      hypothesisResult, setHypothesisResult,
      challengeScenarios, loadScenarios,
      isLoadingHypothesis, hypothesisError,
      isNewObsModalOpen, setIsNewObsModalOpen,
      executeHypothesisUpdate,
      knownObjectResult, isLoadingKnownObject, knownObjectError,
      executeKnownObjectValidation,
      isScanning, setIsScanning,
      scanProgress, setScanProgress,
      detected, setDetected,
      candidates, setCandidates,
      selectedCandidate, setSelectedCandidate,
      statusText, setStatusText,
      isFocusMode, setIsFocusMode
    }}>
      {children}
    </SkyContext.Provider>
  );
}

export const useSky = () => useContext(SkyContext);
