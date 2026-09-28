import React, { useState } from 'react';
import { useSky } from '../context/SkyContext';
import { Search, Calendar, Sliders, ChevronDown, ChevronUp, Check, Play, AlertCircle, Sparkles, Database } from 'lucide-react';

export default function SearchPanel() {
  const {
    searchParams,
    setSearchParams,
    isSearching,
    searchError,
    observations,
    selectedObs1,
    setSelectedObs1,
    selectedObs2,
    setSelectedObs2,
    selectedObs3,
    setSelectedObs3,
    setIsNewObsModalOpen,
    hypothesisResult,
    executeSearch,
    isAnalyzing,
    analysisStage,
    analysisError,
    executeMotionAnalysis,
    motionResult,
    isFocusMode
  } = useSky();

  const [isExpanded, setIsExpanded] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  if (isFocusMode) return null;

  // Coordinate presets
  const presets = [
    { label: 'SPHEREx NEP Deep Field', ra: 276.26, dec: 64.82, radius: 30.0 },
    { label: '3I/ATLAS Comet Field', ra: 248.3655, dec: -16.9991, radius: 15.0 },
  ];

  const handleApplyPreset = (p) => {
    setSearchParams(prev => ({
      ...prev,
      ra: p.ra,
      dec: p.dec,
      radius_arcmin: p.radius
    }));
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    executeSearch();
  };

  // Group observations by calendar date
  const groupedByDate = observations.reduce((acc, obs) => {
    const dateStr = (obs.observation_time_utc || '').split('T')[0] || 'Unknown Date';
    if (!acc[dateStr]) acc[dateStr] = [];
    acc[dateStr].push(obs);
    return acc;
  }, {});

  const dates = Object.keys(groupedByDate).sort();

  return (
    <div className={`fixed left-5 sm:left-[200px] top-28 sm:top-32 z-20 w-[min(410px,calc(100vw-220px))] glass rounded-2xl transition-all duration-300 ${
      isExpanded 
        ? 'h-[calc(100vh-12.5rem)] max-h-[calc(100vh-12.5rem)] flex flex-col shadow-2xl border border-cyan-400/30' 
        : 'max-h-14 overflow-hidden border border-white/10'
    }`}>
      {/* Header bar */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between p-3.5 border-b border-blue-400/20 cursor-pointer select-none bg-slate-950/60 shrink-0"
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-semibold tracking-widest text-white">
            SPHEREx ARCHIVE EXPLORER
          </span>
          {observations.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 text-[10px] font-mono">
              {observations.length} OBS
            </span>
          )}
        </div>
        <button className="text-slate-400 hover:text-white p-1">
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {isExpanded && (
        <div className="p-4 overflow-y-auto flex-1 space-y-3.5 text-xs">
          {/* Quick Presets */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] text-slate-400 tracking-wider uppercase font-medium mr-1">Presets:</span>
            {presets.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => handleApplyPreset(p)}
                className="px-2.5 py-1 rounded-full bg-cyan-400/10 hover:bg-cyan-400/20 border border-cyan-400/30 text-cyan-300 text-[11px] transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Search Coordinates Form */}
          <form onSubmit={handleSearchSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-[10px] font-mono text-cyan-400 tracking-wider mb-1">
                  RA (0° – 360°)
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="360"
                  required
                  value={searchParams.ra}
                  onChange={(e) => setSearchParams({ ...searchParams, ra: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-1.5 rounded-xl bg-slate-900/80 border border-blue-400/20 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                />
              </div>
              <div>
                <label className="block text-[10px] font-mono text-cyan-400 tracking-wider mb-1">
                  DEC (-90° – +90°)
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="-90"
                  max="90"
                  required
                  value={searchParams.dec}
                  onChange={(e) => setSearchParams({ ...searchParams, dec: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-1.5 rounded-xl bg-slate-900/80 border border-blue-400/20 text-white font-mono text-xs focus:outline-none focus:border-cyan-400"
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-3">
              <div className="flex-1">
                <label className="block text-[10px] font-mono text-slate-400 tracking-wider mb-1">
                  RADIUS: {searchParams.radius_arcmin} arcmin
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="60"
                  step="0.5"
                  value={searchParams.radius_arcmin}
                  onChange={(e) => setSearchParams({ ...searchParams, radius_arcmin: parseFloat(e.target.value) })}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
              </div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-slate-400 hover:text-white p-1 text-[11px] flex items-center gap-1 mt-3"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Filters</span>
              </button>
            </div>

            {showAdvanced && (
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-white/10">
                <div>
                  <label className="block text-[10px] text-slate-400 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={searchParams.start_date || ''}
                    onChange={(e) => setSearchParams({ ...searchParams, start_date: e.target.value })}
                    className="w-full px-2 py-1 rounded bg-slate-900/80 border border-blue-400/20 text-white text-[11px]"
                  />
                </div>
                <div>
                  <label className="block text-[10px] text-slate-400 mb-1">End Date</label>
                  <input
                    type="date"
                    value={searchParams.end_date || ''}
                    onChange={(e) => setSearchParams({ ...searchParams, end_date: e.target.value })}
                    className="w-full px-2 py-1 rounded bg-slate-900/80 border border-blue-400/20 text-white text-[11px]"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSearching}
              className="w-full py-2.5 rounded-xl bg-cyan-400/20 hover:bg-cyan-400/30 border border-cyan-400/50 text-cyan-200 font-semibold tracking-wider flex items-center justify-center gap-2 transition-all shadow-md shadow-cyan-500/10 cursor-pointer disabled:opacity-50"
            >
              {isSearching ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-cyan-300 border-t-transparent rounded-full animate-spin" />
                  <span>Querying NASA/IRSA TAP...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>SEARCH SPHEREx ARCHIVE</span>
                </>
              )}
            </button>
          </form>

          {searchError && (
            <div className="p-2.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{searchError}</span>
            </div>
          )}

          {/* Observation Timeline & Epoch Selector */}
          {observations.length > 0 && (
            <div className="pt-3 border-t border-white/10 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-300 tracking-wider">
                  REAL OBSERVATION TIMELINE
                </span>
                <span className="text-[10px] text-slate-400">
                  {dates.length} calendar visit{dates.length > 1 ? 's' : ''}
                </span>
              </div>

              {/* Epoch Pair Selection Status */}
              <div className="p-2.5 rounded-xl bg-slate-950/60 border border-cyan-400/20 flex flex-col gap-1.5 font-mono text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-cyan-400 font-semibold">EPOCH 1 (A):</span>
                  <span className="text-slate-200 truncate max-w-[240px]">
                    {selectedObs1 ? `${selectedObs1.observation_id} (${(selectedObs1.observation_time_utc || '').split('T')[0]})` : 'Select an observation'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-orange-400 font-semibold">EPOCH 2 (B):</span>
                  <span className="text-slate-200 truncate max-w-[240px]">
                    {selectedObs2 ? `${selectedObs2.observation_id} (${(selectedObs2.observation_time_utc || '').split('T')[0]})` : 'Select an observation'}
                  </span>
                </div>
                {selectedObs3 && (
                  <div className="flex items-center justify-between border-t border-white/5 pt-1">
                    <span className="text-emerald-400 font-semibold">EPOCH 3 (C):</span>
                    <span className="text-slate-200 truncate max-w-[240px]">
                      {`${selectedObs3.observation_id} (${(selectedObs3.observation_time_utc || '').split('T')[0]})`}
                    </span>
                  </div>
                )}
              </div>

              {/* Grouped Observations List */}
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {dates.map((d) => (
                  <div key={d} className="rounded-xl border border-white/5 bg-slate-900/40 p-2">
                    <div className="text-[10px] text-cyan-300 font-semibold tracking-wider mb-1 flex items-center gap-1.5">
                      <Calendar className="w-3 h-3" />
                      <span>{d} ({groupedByDate[d].length} obs)</span>
                    </div>

                    <div className="space-y-1">
                      {groupedByDate[d].slice(0, 4).map((obs) => {
                        const is1 = selectedObs1?.observation_id === obs.observation_id;
                        const is2 = selectedObs2?.observation_id === obs.observation_id;
                        const is3 = selectedObs3?.observation_id === obs.observation_id;
                        return (
                          <div
                            key={obs.observation_id}
                            className={`p-1.5 rounded-lg border text-[10px] flex items-center justify-between transition-colors ${
                              is1 
                                ? 'bg-cyan-500/15 border-cyan-400/50 text-cyan-200' 
                                : is2 
                                  ? 'bg-orange-500/15 border-orange-400/50 text-orange-200' 
                                  : is3
                                    ? 'bg-emerald-500/15 border-emerald-400/50 text-emerald-200'
                                    : 'bg-slate-950/30 border-transparent hover:border-white/10 text-slate-300'
                            }`}
                          >
                            <div className="truncate mr-2 font-mono">
                              <span className="font-semibold">{obs.observation_id}</span>
                              <span className="text-slate-400 ml-1.5">{obs.bandpass || 'Band'}</span>
                            </div>

                            <div className="flex items-center gap-1 shrink-0">
                              <button
                                type="button"
                                onClick={() => setSelectedObs1(obs)}
                                className={`px-2 py-0.5 rounded text-[9px] font-bold tracking-wider ${
                                  is1 ? 'bg-cyan-400 text-slate-950' : 'bg-white/10 hover:bg-white/20 text-slate-300'
                                }`}
                              >
                                SET A
                              </button>
                              <button
                                type="button"
                                onClick={() => setSelectedObs2(obs)}
                                className={`px-2 py-0.5 rounded text-[9px] font-bold tracking-wider ${
                                  is2 ? 'bg-orange-400 text-slate-950' : 'bg-white/10 hover:bg-white/20 text-slate-300'
                                }`}
                              >
                                SET B
                              </button>
                              <button
                                type="button"
                                onClick={() => setSelectedObs3(obs)}
                                title="Select as 3rd observation for hypothesis update"
                                className={`px-2 py-0.5 rounded text-[9px] font-bold tracking-wider ${
                                  is3 ? 'bg-emerald-400 text-slate-950' : 'bg-white/10 hover:bg-white/20 text-slate-300'
                                }`}
                              >
                                SET C
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Action: Run Motion Analysis */}
              <button
                type="button"
                disabled={!selectedObs1 || !selectedObs2 || isAnalyzing}
                onClick={() => executeMotionAnalysis(selectedObs1, selectedObs2)}
                className="w-full py-2.5 rounded-xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/60 text-orange-200 font-bold tracking-wider flex items-center justify-center gap-2 transition-all shadow-md shadow-orange-500/10 cursor-pointer disabled:opacity-40"
              >
                {isAnalyzing ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-orange-300 border-t-transparent rounded-full animate-spin" />
                    <span>{analysisStage || 'Analyzing Motion...'}</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>ANALYZE MOTION (A ⇄ B)</span>
                  </>
                )}
              </button>

              {analysisError && (
                <div className="p-2 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-[11px]">
                  {analysisError}
                </div>
              )}
            </div>
          )}

          {observations.length === 0 && !isSearching && (
            <div className="text-center py-4 text-slate-500 text-xs">
              Enter target coordinates or select a preset, then click Search.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
