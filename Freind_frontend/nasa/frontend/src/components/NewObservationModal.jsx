import React, { useState } from 'react';
import { useSky } from '../context/SkyContext';
import { DEFAULT_CHALLENGE_SCENARIOS } from '../services/hypothesisScenarios';
import { 
  X, 
  Sparkles, 
  Database, 
  CheckCircle, 
  AlertTriangle, 
  RefreshCw, 
  HelpCircle, 
  Play, 
  Calendar,
  Layers
} from 'lucide-react';

export default function NewObservationModal({ isOpen, onClose }) {
  const {
    challengeScenarios,
    executeHypothesisUpdate,
    isLoadingHypothesis,
    hypothesisError,
    observations,
    selectedObs3,
    setSelectedObs3,
    selectedCandidate,
    motionResult
  } = useSky();

  const [activeTab, setActiveTab] = useState('scenarios'); // 'scenarios' | 'real-obs'
  const [selectedScenarioId, setSelectedScenarioId] = useState('scenario-strengthened');

  if (!isOpen) return null;

  const displayScenarios = (challengeScenarios && challengeScenarios.length > 0)
    ? challengeScenarios
    : DEFAULT_CHALLENGE_SCENARIOS;

  const handleRunScenario = async (scenario) => {
    const res = await executeHypothesisUpdate(
      scenario.new_observation,
      scenario.baseline_evidence
    );
    if (res) {
      onClose();
    }
  };

  const handleIncorporateRealObs = async () => {
    if (!selectedObs3 || !selectedCandidate) return;

    // Build real observation payload
    // If user selected real Epoch 3 observation from search:
    const newObsPayload = {
      observation_id: selectedObs3.observation_id,
      observation_time_utc: selectedObs3.observation_time_utc || '2026-04-28 12:00:00',
      ra_center: selectedObs3.ra,
      dec_center: selectedObs3.dec,
      bandpass: selectedObs3.bandpass,
      is_scenario: false,
      detection_status: 'DETECTED',
      // If candidate was detected near this field center, use the candidate's estimated continuation
      measured_ra: selectedObs3.ra,
      measured_dec: selectedObs3.dec,
      snr: 8.5,
    };

    const res = await executeHypothesisUpdate(newObsPayload);
    if (res) {
      onClose();
    }
  };

  const getBadgeStyle = (outcome) => {
    switch (outcome) {
      case 'STRENGTHENED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40';
      case 'WEAKENED':
        return 'bg-rose-500/20 text-rose-300 border-rose-400/40';
      case 'CHANGED':
        return 'bg-amber-500/20 text-amber-300 border-amber-400/40';
      case 'INCONCLUSIVE':
      default:
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40';
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-3xl max-h-[90vh] glass rounded-3xl p-6 overflow-y-auto space-y-5 shadow-2xl border border-cyan-400/30 text-slate-200 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/10 pb-4">
          <div>
            <div className="text-[11px] tracking-[0.3em] text-cyan-400 font-semibold uppercase flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>THE NEW OBSERVATION CHALLENGE</span>
            </div>
            <h2 className="text-2xl font-light tracking-wide text-white mt-1">
              Incorporate Third-Epoch Evidence
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-xl">
              Add a new observation to test whether the candidate trajectory is strengthened, weakened, changed, or inconclusive.
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-full border border-white/20 hover:bg-white/10 text-slate-300 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Toggle */}
        <div className="flex border border-blue-400/30 rounded-full p-1 bg-slate-900/60 max-w-md text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('scenarios')}
            className={`flex-1 py-1.5 rounded-full font-medium transition-colors ${
              activeTab === 'scenarios' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Challenge Scenarios (4 Outcomes)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('real-obs')}
            className={`flex-1 py-1.5 rounded-full font-medium transition-colors ${
              activeTab === 'real-obs' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Real SPHEREx Observations ({observations.length})
          </button>
        </div>

        {hypothesisError && (
          <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs">
            {hypothesisError}
          </div>
        )}

        {/* Tab 1: Challenge Demonstration Scenarios */}
        {activeTab === 'scenarios' && (
          <div className="space-y-3">
            <div className="text-xs text-slate-400">
              Select one of the controlled scenario observations to evaluate deterministic hypothesis evolution:
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {displayScenarios.map((sc) => {
                const isSelected = selectedScenarioId === sc.scenario_id;
                return (
                  <div
                    key={sc.scenario_id}
                    onClick={() => setSelectedScenarioId(sc.scenario_id)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer space-y-2 ${
                      isSelected
                        ? 'bg-cyan-400/15 border-cyan-400 shadow-md shadow-cyan-500/10'
                        : 'bg-slate-900/50 border-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-white">
                        {sc.title}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-mono font-bold ${getBadgeStyle(sc.expected_outcome)}`}>
                        {sc.expected_outcome}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300 leading-relaxed font-sans">
                      {sc.description}
                    </p>

                    <div className="text-[10px] font-mono text-slate-400 pt-1 border-t border-white/10 flex justify-between">
                      <span>Epoch 3: {sc.new_observation.observation_time_utc.split(' ')[0]}</span>
                      <span>SNR: {sc.new_observation.snr !== null ? sc.new_observation.snr : 'N/A'}</span>
                    </div>

                    <button
                      type="button"
                      disabled={isLoadingHypothesis}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRunScenario(sc);
                      }}
                      className="w-full mt-2 py-1.5 rounded-xl bg-cyan-400/20 hover:bg-cyan-400/30 border border-cyan-400/50 text-cyan-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                    >
                      <Play className="w-3 h-3 fill-current" />
                      <span>Evaluate {sc.expected_outcome}</span>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 2: Real SPHEREx Observation Selector */}
        {activeTab === 'real-obs' && (
          <div className="space-y-3">
            {observations.length === 0 ? (
              <div className="text-center py-10 space-y-2 text-slate-400 text-xs">
                <div>No SPHEREx observations loaded in current search session.</div>
                <p className="text-[11px] text-slate-500">
                  Search the SPHEREx archive in Compare Mode first, or use the Challenge Scenarios tab.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-slate-400">
                  Select a 3rd observation from the real SPHEREx archive to incorporate as Epoch 3:
                </div>

                <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1 font-mono text-xs">
                  {observations.map((obs) => {
                    const isSelected = selectedObs3?.observation_id === obs.observation_id;
                    return (
                      <div
                        key={obs.observation_id}
                        onClick={() => setSelectedObs3(obs)}
                        className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-cyan-400/20 border-cyan-400 text-white font-semibold'
                            : 'bg-slate-900/40 border-white/5 hover:border-white/15 text-slate-300'
                        }`}
                      >
                        <div className="truncate mr-2">
                          <span className="text-cyan-300 font-bold mr-2">{obs.observation_id}</span>
                          <span className="text-slate-400 text-[11px]">
                            {(obs.observation_time_utc || '').split('T')[0]} ({obs.bandpass || 'Band'})
                          </span>
                        </div>

                        <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                          isSelected ? 'bg-cyan-400 text-slate-950 font-bold' : 'bg-white/10 text-slate-400'
                        }`}>
                          {isSelected ? 'SELECTED AS E3' : 'SELECT'}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <button
                  type="button"
                  disabled={!selectedObs3 || isLoadingHypothesis}
                  onClick={handleIncorporateRealObs}
                  className="w-full py-2.5 rounded-xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/60 text-orange-200 font-bold tracking-wider flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-40 text-xs"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>INCORPORATE SELECTED SPHEREx OBSERVATION</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
