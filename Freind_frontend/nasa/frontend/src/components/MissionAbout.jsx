import React from 'react';
import { useSky } from '../context/SkyContext';

export default function MissionAbout() {
  const { mode } = useSky();

  if (mode !== 'about') return null;

  return (
    <div className="fixed left-1/2 sm:left-[calc(50%+90px)] bottom-10 -translate-x-1/2 w-[min(760px,calc(100vw-40px))] flex flex-col sm:flex-row gap-3.5 z-20 transition-all duration-500">
      <div className="flex-1 p-4 glass rounded-2xl">
        <b className="block text-cyan-400 text-xs tracking-widest mb-1.5 font-medium">01 OBSERVE</b>
        <span className="text-xs text-slate-300">SPHEREx repeatedly maps the entire sky.</span>
      </div>
      <div className="flex-1 p-4 glass rounded-2xl">
        <b className="block text-cyan-400 text-xs tracking-widest mb-1.5 font-medium">02 COMPARE</b>
        <span className="text-xs text-slate-300">Repeated observations allow scientists to identify changes.</span>
      </div>
      <div className="flex-1 p-4 glass rounded-2xl">
        <b className="block text-cyan-400 text-xs tracking-widest mb-1.5 font-medium">03 DISCOVER</b>
        <span className="text-xs text-slate-300">Potentially moving or changing objects can be investigated further.</span>
      </div>
    </div>
  );
}
