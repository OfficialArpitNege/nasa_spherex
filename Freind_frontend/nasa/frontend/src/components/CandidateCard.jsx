import React, { useState } from 'react';
import { useSky } from '../context/SkyContext';
import { getPreviewUrl } from '../services/api';
import { X, ExternalLink, Image as ImageIcon, Compass } from 'lucide-react';

export default function CandidateCard() {
  const { selectedCandidate, setSelectedCandidate, motionResult } = useSky();
  const [showTrailImage, setShowTrailImage] = useState(false);

  if (!selectedCandidate) return null;

  const pad2 = (n) => String(n).padStart(2, '0');
  const cand = selectedCandidate;

  // Real astronomical candidate properties (from FastAPI backend MotionAnalysisResult)
  const isRealBackendCandidate = Boolean(cand.position_epoch_1 && cand.position_epoch_2);

  // Position Epoch 1
  const posA = isRealBackendCandidate
    ? `RA ${cand.position_epoch_1.ra.toFixed(5)}°, DEC ${cand.position_epoch_1.dec.toFixed(5)}°`
    : `x: ${cand.bx?.toFixed(1) || 0}, y: ${cand.by?.toFixed(1) || 0}`;

  // Position Epoch 2
  const posB = isRealBackendCandidate
    ? `RA ${cand.position_epoch_2.ra.toFixed(5)}°, DEC ${cand.position_epoch_2.dec.toFixed(5)}°`
    : `x: ${((cand.bx || 0) + (cand.vx || 0)).toFixed(1)}, y: ${((cand.by || 0) + (cand.vy || 0)).toFixed(1)}`;

  // Angular displacement
  const displacementStr = isRealBackendCandidate
    ? `${cand.angular_displacement.arcsec.toFixed(2)}″ (${cand.angular_displacement.arcmin.toFixed(3)}′)`
    : `${(Math.hypot(cand.vx || 0, cand.vy || 0) * 0.096).toFixed(1)} arcmin`;

  // Angular speed
  const speedStr = isRealBackendCandidate
    ? `${cand.average_angular_speed.arcsec_per_day.toFixed(2)}″/day (${cand.average_angular_speed.arcsec_per_hour.toFixed(3)}″/hr)`
    : null;

  // Position angle & direction
  const directionStr = isRealBackendCandidate
    ? `${cand.position_angle_deg.toFixed(1)}° (${cand.direction_label})`
    : null;

  // Elapsed interval
  const intervalStr = motionResult?.time_difference
    ? `${motionResult.time_difference.days.toFixed(1)} days`
    : 'Multi-epoch';

  // Scientific status label
  const statusLabel = cand.status === 'moving-object-candidate'
    ? 'Moving-object candidate'
    : cand.status === 'possible-motion'
      ? 'Possible motion'
      : cand.status === 'stationary'
        ? 'Stationary / no significant motion'
        : 'Potential moving source';

  return (
    <div className="fixed right-6 bottom-24 sm:bottom-28 w-[min(380px,calc(100vw-32px))] p-5 glass rounded-2xl text-xs z-30 shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-300 border border-orange-500/30">
      <button 
        onClick={() => setSelectedCandidate(null)}
        aria-label="Close"
        className="absolute right-3 top-3 p-1 text-slate-400 hover:text-white transition-colors cursor-pointer"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="text-[11px] tracking-widest text-orange-400 font-semibold uppercase mb-1">
        {cand.title || 'MOVING-OBJECT CANDIDATE'}
      </div>

      <div className="flex items-baseline justify-between pr-6">
        <h3 className="m-0 text-xl font-light tracking-widest text-white">
          CANDIDATE {pad2(cand.n || 1)}
        </h3>
        {cand.quality?.confidence && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-orange-400/20 text-orange-300 border border-orange-400/40">
            {cand.quality.confidence.toUpperCase()} CONFIDENCE
          </span>
        )}
      </div>
      
      <p className="text-orange-300 my-1 mb-3 text-xs font-medium">
        {statusLabel}
      </p>

      {/* Astronomical Coordinate Table */}
      <div className="space-y-1.5 border-t border-b border-white/10 py-2.5 font-mono text-[11px]">
        <div className="flex justify-between text-slate-400">
          <span>Measured Epoch 1</span>
          <span className="text-slate-200 text-right truncate max-w-[210px]">{posA}</span>
        </div>
        <div className="flex justify-between text-slate-400">
          <span>Measured Epoch 2</span>
          <span className="text-slate-200 text-right truncate max-w-[210px]">{posB}</span>
        </div>
        <div className="flex justify-between text-slate-400">
          <span>Displacement</span>
          <span className="text-cyan-300 font-semibold">{displacementStr}</span>
        </div>
        {speedStr && (
          <div className="flex justify-between text-slate-400">
            <span>Angular Speed</span>
            <span className="text-slate-200">{speedStr}</span>
          </div>
        )}
        {directionStr && (
          <div className="flex justify-between text-slate-400">
            <span>Position Angle</span>
            <span className="text-slate-200 flex items-center gap-1">
              <Compass className="w-3 h-3 text-cyan-400" />
              {directionStr}
            </span>
          </div>
        )}
        {cand.quality?.snr_epoch_1 !== undefined && (
          <div className="flex justify-between text-slate-400">
            <span>SNR (E1 / E2)</span>
            <span className="text-slate-200">
              {cand.quality.snr_epoch_1?.toFixed(1) || 'N/A'} / {cand.quality.snr_epoch_2?.toFixed(1) || 'N/A'}
            </span>
          </div>
        )}
        <div className="flex justify-between text-slate-400">
          <span>Epoch Interval</span>
          <span className="text-slate-200">{intervalStr}</span>
        </div>
      </div>

      {/* Motion Trail Image Toggle */}
      {cand.motion_trail_path && (
        <div className="mt-2.5">
          <button
            type="button"
            onClick={() => setShowTrailImage(!showTrailImage)}
            className="w-full py-1 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] text-cyan-300 flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
          >
            <ImageIcon className="w-3.5 h-3.5" />
            <span>{showTrailImage ? 'Hide Motion Trail Plot' : 'View Motion Trail Plot'}</span>
          </button>

          {showTrailImage && (
            <div className="mt-2 rounded-xl overflow-hidden border border-white/10 bg-black aspect-video flex items-center justify-center">
              <img
                src={getPreviewUrl(cand.motion_trail_path)}
                alt={`Motion Trail ${cand.candidate_id}`}
                className="w-full h-full object-contain"
              />
            </div>
          )}
        </div>
      )}

      {/* Scientific disclaimer */}
      <p className="mt-2.5 mb-0.5 text-slate-300 text-[11px] leading-relaxed">
        Status: <span className="font-semibold">{statusLabel}</span> — requires further independent scientific investigation.
      </p>
      
      <p className="m-0 text-slate-500 text-[10px] leading-tight">
        Candidate classification does not confirm astronomical discovery.
      </p>
    </div>
  );
}
