import React from 'react';
import { useSky } from '../context/SkyContext';

const modeHeaders = {
  explore: {
    lbl: 'NASA SPHEREx MISSION',
    h: 'EXPLORE REPEATED OBSERVATIONS',
    sub: 'Explore repeated SPHEREx observations and identify moving-object candidates.'
  },
  compare: {
    lbl: 'SPHEREx TEMPORAL COMPARISON',
    h: 'COMPARE THE SKY',
    sub: 'Two real SPHEREx observations. One region of sky. Identify moving-object candidates.'
  },
  validation: {
    lbl: 'KNOWN OBJECT VALIDATION',
    h: 'INTERSTELLAR COMET 3I/ATLAS',
    sub: 'Independent astrometric verification using official NASA/IPAC IRSA SPHEREx data.'
  },
  discover: {
    lbl: 'DISCOVER MODE',
    h: 'WHAT MOVED?',
    sub: 'Inspect blinking epochs to spot moving-object candidates.'
  },
  about: {
    lbl: 'THE MISSION',
    h: 'HOW SPHEREx SEES',
    sub: 'Observe · Compare · Discover'
  }
};

export default function Header() {
  const { mode, switchMode, isFocusMode } = useSky();
  const info = modeHeaders[mode] || modeHeaders.explore;

  if (isFocusMode) return null;

  return (
    <header className="fixed left-5 sm:left-[200px] top-7 right-5 sm:right-[280px] pointer-events-none transition-opacity duration-500 z-10">
      <div className="text-[11px] tracking-[0.32em] text-cyan-400 font-medium">
        {info.lbl}
      </div>
      <h1 className="my-2 font-light tracking-[0.14em] text-2xl md:text-4xl leading-snug text-white">
        {info.h}
      </h1>
      <p className="m-0 text-slate-400 text-sm">
        {info.sub}
      </p>
      {mode === 'explore' && (
        <button 
          onClick={() => switchMode('compare')}
          className="pointer-events-auto mt-4 px-5 py-2.5 rounded-full border border-cyan-400/60 bg-cyan-400/15 text-cyan-200 text-xs tracking-widest hover:bg-cyan-400/30 transition-colors shadow-lg shadow-cyan-500/10 cursor-pointer"
        >
          COMPARE OBSERVATIONS →
        </button>
      )}
    </header>
  );
}
