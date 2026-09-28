import React from 'react';
import { useSky } from '../context/SkyContext';

export default function HUD() {
  const { coords, isFocusMode, backendStatus } = useSky();

  if (isFocusMode) return null;

  return (
    <div className="fixed right-6 top-7 text-right font-mono text-xs leading-relaxed text-slate-400 pointer-events-none transition-opacity duration-500 z-10 hidden sm:block">
      {/* Subtle backend connection indicator */}
      <div className="flex items-center justify-end gap-1.5 mb-1.5">
        <span
          className={`w-2 h-2 rounded-full ${
            backendStatus === 'connected'
              ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
              : backendStatus === 'connecting'
                ? 'bg-amber-400 animate-pulse'
                : 'bg-rose-400 shadow-[0_0_8px_#f87171]'
          }`}
        />
        <span className="text-[10px] tracking-widest uppercase font-sans text-slate-400">
          {backendStatus === 'connected'
            ? 'FastAPI Connected'
            : backendStatus === 'connecting'
              ? 'Connecting...'
              : 'Backend Unavailable'}
        </span>
      </div>

      <b className="text-cyan-400 tracking-widest font-medium block mb-1">
        {coords.region}
      </b>
      <div>RA <span className="text-slate-200">{coords.ra_deg !== undefined ? `${coords.ra_deg.toFixed(4)}°` : coords.ra}</span></div>
      <div>DEC <span className="text-slate-200">{coords.dec_deg !== undefined ? `${coords.dec_deg.toFixed(4)}°` : coords.dec}</span></div>
    </div>
  );
}
