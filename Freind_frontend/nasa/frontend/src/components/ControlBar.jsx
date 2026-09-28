import React from 'react';
import { useSky } from '../context/SkyContext';
import { Layers, Play, Sparkles } from 'lucide-react';

export default function ControlBar({ onDetect, onOpenFITSViewer }) {
  const { 
    mode, 
    view, 
    setView, 
    blinkSpeed, 
    setBlinkSpeed, 
    statusText, 
    candidates, 
    setSelectedCandidate,
    isFocusMode,
    selectedObs1,
    selectedObs2,
    motionResult,
    isAnalyzing,
    executeMotionAnalysis,
    cutout1,
    cutout2,
    selectedObs3,
    hypothesisResult,
    setIsNewObsModalOpen
  } = useSky();

  if (isFocusMode) return null;

  const pad2 = (n) => String(n).padStart(2, '0');

  // Real observation date metadata
  const dateA = selectedObs1 ? (selectedObs1.observation_time_utc || '').split('T')[0] : '2025-04-28';
  const dateB = selectedObs2 ? (selectedObs2.observation_time_utc || '').split('T')[0] : '2026-04-28';
  const bandA = selectedObs1?.bandpass ? `(${selectedObs1.bandpass})` : '';
  const bandB = selectedObs2?.bandpass ? `(${selectedObs2.bandpass})` : '';
  
  const elapsedDays = motionResult?.time_difference
    ? `${motionResult.time_difference.days.toFixed(1)} days`
    : selectedObs1 && selectedObs2
      ? 'Selected pair'
      : '187 days';

  const hasFITS = Boolean(cutout1 || cutout2);

  const handleDetectClick = () => {
    if (selectedObs1 && selectedObs2) {
      executeMotionAnalysis(selectedObs1, selectedObs2);
    } else if (onDetect) {
      onDetect();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 bg-slate-950/90 backdrop-blur-xl border-t border-cyan-400/25 px-4 sm:px-6 py-2.5 shadow-[0_-12px_36px_rgba(0,0,0,0.7)] text-xs text-slate-200 transition-all duration-300">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-3 sm:pl-[170px] lg:pl-[190px]">
        {/* Left Section: Observation Timeline Badges & Status */}
        <div className="flex flex-col gap-1 min-w-[240px] max-w-md w-full lg:w-auto">
          <div className="flex items-center gap-1.5 font-mono text-[11px] flex-wrap">
            <span className="px-2 py-0.5 rounded-full bg-cyan-400/15 border border-cyan-400/30 text-cyan-300 font-bold">
              A · {dateA} {bandA}
            </span>
            <span className="text-slate-500 font-bold">⇄</span>
            <span className="px-2 py-0.5 rounded-full bg-orange-400/15 border border-orange-400/30 text-orange-300 font-bold">
              B · {dateB} {bandB}
            </span>
            {selectedObs3 && (
              <>
                <span className="text-slate-500 font-bold">⇄</span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-400/15 border border-emerald-400/30 text-emerald-300 font-bold">
                  C · {(selectedObs3.observation_time_utc || '').split('T')[0]} ({selectedObs3.bandpass || 'Band'})
                </span>
              </>
            )}
            <span className="text-slate-400 text-[10px] ml-1">({elapsedDays})</span>
          </div>

          <div className={`text-[11px] truncate tracking-wider font-sans ${candidates.length > 0 ? 'text-orange-400 font-semibold' : 'text-slate-400'}`}>
            {statusText || 'Ready to analyze.'}
          </div>
        </div>

        {/* Center Section: View Controls & Speed Slider */}
        <div className="flex items-center gap-3 bg-slate-900/60 border border-white/10 px-3 py-1.5 rounded-full">
          {/* Toggle Segments */}
          <div className="flex border border-blue-400/20 rounded-full overflow-hidden bg-slate-950/60 p-0.5">
            <button 
              type="button"
              onClick={() => setView('a')}
              className={`px-3 py-1 text-xs tracking-widest rounded-full transition-colors ${view === 'a' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
            >
              A
            </button>
            <button 
              type="button"
              onClick={() => setView('b')}
              className={`px-3 py-1 text-xs tracking-widest rounded-full transition-colors ${view === 'b' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
            >
              B
            </button>
            <button 
              type="button"
              onClick={() => setView('blink')}
              className={`px-3 py-1 text-xs tracking-widest rounded-full transition-colors ${view === 'blink' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'}`}
            >
              BLINK
            </button>
          </div>

          {/* Speed Slider */}
          <label className="flex items-center gap-2 text-[10px] tracking-widest text-cyan-400 font-medium whitespace-nowrap">
            SPEED
            <input 
              type="range" 
              min="1" 
              max="10" 
              value={blinkSpeed}
              onChange={(e) => setBlinkSpeed(Number(e.target.value))}
              className="w-16 accent-cyan-400 cursor-pointer"
            />
          </label>
        </div>

        {/* Right Section: Action Buttons */}
        <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
          {/* FITS Viewer Button */}
          {hasFITS && onOpenFITSViewer && (
            <button
              type="button"
              onClick={onOpenFITSViewer}
              className="px-3 py-1.5 rounded-full border border-blue-400/30 hover:bg-white/10 text-cyan-300 text-xs tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>FITS IMAGES</span>
            </button>
          )}

          {/* New Observation Challenge Button */}
          <button
            type="button"
            onClick={() => setIsNewObsModalOpen(true)}
            className="px-3.5 py-1.5 rounded-full border border-purple-400/50 bg-purple-500/15 hover:bg-purple-500/25 text-purple-200 text-xs tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer shadow-sm shadow-purple-500/10 font-medium"
          >
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>NEW OBSERVATION</span>
            {hypothesisResult && (
              <span className={`ml-1 text-[9px] px-1.5 py-0.5 rounded font-bold uppercase font-mono ${
                hypothesisResult.new_classification === 'STRENGTHENED' ? 'bg-emerald-400 text-slate-950' :
                hypothesisResult.new_classification === 'WEAKENED' ? 'bg-rose-400 text-white' :
                hypothesisResult.new_classification === 'CHANGED' ? 'bg-amber-400 text-slate-950' :
                'bg-cyan-400 text-slate-950'
              }`}>
                {hypothesisResult.new_classification}
              </span>
            )}
          </button>

          {/* Detect / Analyze Button */}
          {mode === 'compare' && (
            <button
              type="button"
              onClick={handleDetectClick}
              disabled={isAnalyzing}
              className="px-4 py-2 rounded-full border border-cyan-400/70 bg-cyan-400/20 text-cyan-100 text-xs tracking-widest hover:bg-cyan-400/35 transition-colors shadow-md shadow-cyan-500/20 font-semibold cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
            >
              {isAnalyzing ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-cyan-300 border-t-transparent rounded-full animate-spin" />
                  <span>ANALYZING...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>DETECT CHANGES</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Candidate Chips Row (if any candidates detected) */}
      {candidates.length > 0 && (
        <div className="max-w-7xl mx-auto flex items-center gap-2 mt-2 pt-2 border-t border-white/10 sm:pl-[170px] lg:pl-[190px] overflow-x-auto">
          <span className="text-[10px] text-slate-400 tracking-wider uppercase font-mono shrink-0">
            CANDIDATES:
          </span>
          {candidates.map((cand) => (
            <button
              type="button"
              key={cand.n || cand.candidate_id}
              onClick={() => setSelectedCandidate({ ...cand, title: 'MOVING-OBJECT CANDIDATE' })}
              title={`Candidate ${pad2(cand.n)} — ${cand.label}`}
              className="px-2.5 py-1 rounded-full border border-orange-500/50 bg-orange-500/15 text-xs text-slate-200 hover:bg-orange-500/30 transition-colors font-semibold cursor-pointer shrink-0 flex items-center gap-1"
            >
              <b className="text-orange-400">{pad2(cand.n)}</b>
              {cand.displacement_arcsec !== undefined && (
                <span className="text-[10px] text-slate-300">
                  {cand.displacement_arcsec.toFixed(1)}″
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
