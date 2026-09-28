import React from 'react';
import { useSky } from '../context/SkyContext';
import { 
  CheckCircle, 
  AlertTriangle, 
  RefreshCw, 
  HelpCircle, 
  X, 
  Compass, 
  ArrowRight, 
  Sparkles,
  ShieldCheck
} from 'lucide-react';

export default function HypothesisUpdateCard({ onClose }) {
  const { hypothesisResult, hypothesis, setIsNewObsModalOpen } = useSky();

  if (!hypothesisResult) return null;

  const res = hypothesisResult;
  const comp = res.evidence_comparison;
  const pred = res.trajectory_prediction;

  const getVerdictStyle = (classification) => {
    switch (classification) {
      case 'STRENGTHENED':
        return {
          bg: 'bg-emerald-500/15 border-emerald-400/50 text-emerald-300',
          dot: 'bg-emerald-400 shadow-[0_0_12px_#34d399]',
          badge: 'bg-emerald-400/20 text-emerald-300 border-emerald-400/40',
          icon: CheckCircle
        };
      case 'WEAKENED':
        return {
          bg: 'bg-rose-500/15 border-rose-400/50 text-rose-300',
          dot: 'bg-rose-400 shadow-[0_0_12px_#f87171]',
          badge: 'bg-rose-400/20 text-rose-300 border-rose-400/40',
          icon: AlertTriangle
        };
      case 'CHANGED':
        return {
          bg: 'bg-amber-500/15 border-amber-400/50 text-amber-300',
          dot: 'bg-amber-400 shadow-[0_0_12px_#fbbf24]',
          badge: 'bg-amber-400/20 text-amber-300 border-amber-400/40',
          icon: RefreshCw
        };
      case 'INCONCLUSIVE':
      default:
        return {
          bg: 'bg-cyan-500/15 border-cyan-400/50 text-cyan-300',
          dot: 'bg-cyan-400 shadow-[0_0_12px_#22d3ee]',
          badge: 'bg-cyan-400/20 text-cyan-300 border-cyan-400/40',
          icon: HelpCircle
        };
    }
  };

  const style = getVerdictStyle(res.new_classification);
  const VerdictIcon = style.icon;

  // Mini Trajectory Vector Geometry for SVG visualization
  // Scale positions into a 240x120 SVG coordinate box
  const hasMeasured = comp.measured_ra !== null && comp.measured_dec !== null;
  const residualArcsec = comp.angular_residual_arcsec ?? 0;
  
  // Coordinates mapping: E1 = [40, 60], E2 = [110, 60], Pred = [180, 60]
  // Measured point offset by residual angle or deviation
  const paDevDeg = comp.position_angle_residual_deg ?? 0;
  const isDeviation = res.new_classification === 'WEAKENED';
  const isStationary = res.new_classification === 'CHANGED';

  let measX = 180;
  let measY = 60;
  if (isStationary) {
    // Coincident with Epoch 1
    measX = 42;
    measY = 58;
  } else if (isDeviation) {
    // Significant deviation off trajectory
    measX = 165;
    measY = 100;
  } else if (hasMeasured) {
    // Minor residual offset
    measX = 183;
    measY = 63;
  }

  return (
    <div className="fixed right-6 top-24 w-[min(440px,calc(100vw-32px))] p-5 glass rounded-3xl text-xs z-30 shadow-2xl animate-in fade-in slide-in-from-right-4 duration-300 border border-cyan-400/30 max-h-[calc(100vh-140px)] overflow-y-auto space-y-4">
      {/* Top Header */}
      <div className="flex items-start justify-between border-b border-white/10 pb-3">
        <div>
          <div className="text-[10px] tracking-[0.3em] text-cyan-400 font-bold uppercase flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>HYPOTHESIS UPDATE RESULT</span>
          </div>
          <h3 className="text-lg font-light tracking-wide text-white mt-0.5">
            "The New Observation"
          </h3>
        </div>

        <button 
          onClick={onClose}
          aria-label="Close"
          className="p-1 text-slate-400 hover:text-white transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Prominent Classification Banner */}
      <div className={`p-4 rounded-2xl border flex items-start gap-3.5 ${style.bg}`}>
        <VerdictIcon className="w-6 h-6 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold tracking-widest uppercase">
              HYPOTHESIS {res.new_classification}
            </span>
            <span className={`text-[10px] px-2 py-0.2 rounded-full border font-mono ${style.badge}`}>
              {res.confidence.toUpperCase()} CONFIDENCE
            </span>
          </div>
          <p className="text-xs text-slate-200 leading-snug">
            {res.summary_verdict}
          </p>
        </div>
      </div>

      {/* "Why?" Evidence-based Explanation */}
      <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-2">
        <span className="text-[11px] font-semibold text-cyan-300 tracking-wider uppercase block">
          Why Did the Hypothesis Update?
        </span>
        <p className="text-xs text-slate-300 leading-relaxed font-sans">
          {res.explanation}
        </p>

        {/* Detailed quantitative reasons */}
        {res.detailed_reasons.length > 0 && (
          <ul className="space-y-1 pt-2 border-t border-white/10 text-[11px] text-slate-400 list-disc list-inside">
            {res.detailed_reasons.map((r, idx) => (
              <li key={idx} className="leading-tight">{r}</li>
            ))}
          </ul>
        )}
      </div>

      {/* Before vs After Evidence Table */}
      <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-2.5">
        <span className="text-[11px] font-semibold text-slate-300 tracking-wider uppercase block">
          Before vs After Evidence Comparison
        </span>

        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
          {/* Before */}
          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5 space-y-1">
            <span className="text-[10px] text-slate-400 block tracking-wider uppercase font-sans font-semibold">
              BEFORE (2 Epochs)
            </span>
            <div className="flex justify-between text-slate-300">
              <span>Displacement:</span>
              <span className="text-cyan-300">{pred.baseline_displacement_arcsec.toFixed(1)}″</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Speed:</span>
              <span className="text-slate-200">{pred.baseline_angular_speed_arcsec_day.toFixed(2)}″/d</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Direction:</span>
              <span className="text-slate-200">{pred.baseline_direction}</span>
            </div>
            <div className="flex justify-between text-slate-400 text-[10px] pt-1 border-t border-white/5">
              <span>Status:</span>
              <span className="text-orange-400">{res.previous_classification}</span>
            </div>
          </div>

          {/* After */}
          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5 space-y-1">
            <span className="text-[10px] text-slate-400 block tracking-wider uppercase font-sans font-semibold">
              NEW OBSERVATION (E3)
            </span>
            <div className="flex justify-between text-slate-300">
              <span>Residual:</span>
              <span className={comp.angular_residual_arcsec && comp.angular_residual_arcsec <= 9.24 ? 'text-emerald-300 font-bold' : 'text-rose-300 font-bold'}>
                {comp.angular_residual_arcsec !== null ? `${comp.angular_residual_arcsec.toFixed(2)}″` : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>Pixel Err:</span>
              <span className="text-slate-200">
                {comp.angular_residual_pixels !== null ? `${comp.angular_residual_pixels.toFixed(2)} px` : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span>SNR:</span>
              <span className="text-slate-200">{comp.snr !== null ? comp.snr.toFixed(1) : 'N/A'}</span>
            </div>
            <div className="flex justify-between text-slate-400 text-[10px] pt-1 border-t border-white/5">
              <span>Updated:</span>
              <span className="font-bold text-white">{res.new_classification}</span>
            </div>
          </div>
        </div>

        {/* Coordinate Readout */}
        <div className="pt-2 border-t border-white/10 space-y-1 font-mono text-[11px]">
          <div className="flex justify-between text-slate-400">
            <span>Expected Trajectory Pos:</span>
            <span className="text-slate-200">RA {pred.predicted_ra.toFixed(4)}°, DEC {pred.predicted_dec.toFixed(4)}°</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Measured New Position:</span>
            <span className={hasMeasured ? 'text-cyan-300' : 'text-rose-400 italic'}>
              {hasMeasured ? `RA ${comp.measured_ra.toFixed(4)}°, DEC ${comp.measured_dec.toFixed(4)}°` : 'Not reliably detected'}
            </span>
          </div>
        </div>
      </div>

      {/* Trajectory Astrometric Vector Diagram */}
      <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-2">
        <span className="text-[11px] font-semibold text-slate-300 tracking-wider uppercase block">
          Celestial Trajectory Geometry
        </span>
        <div className="bg-black/80 rounded-xl p-2 border border-white/10 flex flex-col items-center">
          <svg viewBox="0 0 240 120" className="w-full h-24">
            {/* Trajectory line E1 -> E2 -> Expected */}
            <line x1="40" y1="60" x2="110" y2="60" stroke="#67e8f9" strokeWidth="1.5" />
            <line x1="110" y1="60" x2="180" y2="60" stroke="#67e8f9" strokeWidth="1.5" strokeDasharray="3 3" />

            {/* Epoch 1 point */}
            <circle cx="40" cy="60" r="4" fill="#67e8f9" />
            <text x="40" y="80" fill="#94a3b8" fontSize="9" textAnchor="middle" fontFamily="monospace">E1</text>

            {/* Epoch 2 point */}
            <circle cx="110" cy="60" r="4" fill="#fb923c" />
            <text x="110" y="80" fill="#94a3b8" fontSize="9" textAnchor="middle" fontFamily="monospace">E2</text>

            {/* Expected point */}
            <circle cx="180" cy="60" r="4" fill="none" stroke="#67e8f9" strokeWidth="1.5" strokeDasharray="2 2" />
            <text x="180" y="48" fill="#67e8f9" fontSize="9" textAnchor="middle" fontFamily="monospace">Expected</text>

            {/* Measured point & residual if detected */}
            {hasMeasured && (
              <>
                {/* Residual line */}
                <line x1="180" y1="60" x2={measX} y2={measY} stroke={isDeviation ? "#f87171" : isStationary ? "#fbbf24" : "#34d399"} strokeWidth="1.5" />
                <circle cx={measX} cy={measY} r="4" fill={isDeviation ? "#f87171" : isStationary ? "#fbbf24" : "#34d399"} />
                <text x={measX} y={measY + 18} fill={isDeviation ? "#f87171" : isStationary ? "#fbbf24" : "#34d399"} fontSize="9" textAnchor="middle" fontFamily="monospace">
                  {isStationary ? 'Meas (Stat)' : 'Measured'}
                </text>
              </>
            )}
          </svg>

          <div className="flex justify-between w-full text-[10px] text-slate-400 font-mono px-2 mt-1">
            <span>Baseline Vector: {pred.baseline_direction}</span>
            <span>Residual: {comp.angular_residual_arcsec !== null ? `${comp.angular_residual_arcsec.toFixed(1)}″` : 'No detection'}</span>
          </div>
        </div>
      </div>

      {/* Action to test another scenario */}
      <button
        type="button"
        onClick={() => setIsNewObsModalOpen(true)}
        className="w-full py-2.5 rounded-xl bg-cyan-400/20 hover:bg-cyan-400/30 border border-cyan-400/50 text-cyan-200 font-semibold tracking-wider flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md shadow-cyan-500/10 text-xs"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        <span>TEST ANOTHER NEW OBSERVATION</span>
      </button>

      {/* Scientific disclaimer */}
      <p className="text-[10px] text-slate-500 leading-tight border-t border-white/10 pt-2 m-0">
        Scientific Integrity Notice: Hypothesis update evaluations are deterministic astrometric comparisons and do not confirm astronomical discovery.
      </p>
    </div>
  );
}
