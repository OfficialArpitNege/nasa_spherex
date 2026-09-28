import React, { useState } from 'react';
import { useSky } from '../context/SkyContext';
import { Compass, GitCompare, Sparkles, Info, Menu, CheckCircle, GitBranch } from 'lucide-react';

export default function Navigation() {
  const { mode, switchMode, isFocusMode, setIsNewObsModalOpen } = useSky();
  const [minimized, setMinimized] = useState(false);

  if (isFocusMode) return null;

  const items = [
    { id: 'explore', label: 'EXPLORE', icon: Compass },
    { id: 'compare', label: 'COMPARE', icon: GitCompare, isCompare: true },
    { id: 'hypothesis', label: 'HYPOTHESIS', icon: GitBranch, isHypothesis: true },
    { id: 'validation', label: '3I/ATLAS', icon: CheckCircle, isValidation: true },
    { id: 'discover', label: 'DISCOVER', icon: Sparkles },
    { id: 'about', label: 'ABOUT', icon: Info },
  ];

  const handleItemClick = (item) => {
    switchMode(item.id);
    if (item.isHypothesis) {
      setIsNewObsModalOpen(true);
    }
  };

  return (
    <nav className={`fixed left-5 top-1/2 -translate-y-1/2 z-20 glass rounded-2xl p-3 flex flex-col gap-1.5 transition-all duration-300 ${minimized ? 'w-14 h-14 overflow-hidden p-2' : 'w-44'}`}>
      <div className="flex items-center justify-between px-2 py-1 mb-1 border-b border-blue-400/20 text-xs font-semibold tracking-widest">
        {!minimized && (
          <div>
            ✦ SPHEREx
            <small className="block text-[9px] text-cyan-400 font-normal tracking-[0.35em]">SKY WATCHER</small>
          </div>
        )}
        <button 
          onClick={() => setMinimized(!minimized)} 
          aria-label={minimized ? "Open menu" : "Close menu"}
          className="p-1 rounded-lg hover:bg-white/10 text-slate-200 transition-colors ml-auto cursor-pointer"
        >
          <Menu className="w-5 h-5 text-cyan-400" />
        </button>
      </div>

      {!minimized && items.map((item) => {
        const Icon = item.icon;
        const active = mode === item.id;
        return (
          <button
            key={item.id}
            onClick={() => handleItemClick(item)}
            aria-pressed={active}
            className={`relative flex items-center gap-2.5 p-2.5 rounded-xl text-xs tracking-widest text-left transition-all cursor-pointer ${
              item.isCompare 
                ? 'py-3.5 bg-cyan-400/10 border border-cyan-400/50 text-white font-semibold shadow-lg shadow-cyan-500/20' 
                : item.isValidation
                  ? active
                    ? 'bg-emerald-400/15 text-white font-medium border border-emerald-400/40'
                    : 'text-emerald-300/80 hover:bg-emerald-400/10 border border-emerald-500/20'
                  : item.isHypothesis
                    ? active
                      ? 'bg-purple-400/20 text-white font-medium border border-purple-400/50 shadow-md shadow-purple-500/10'
                      : 'text-purple-300/90 hover:bg-purple-400/10 border border-purple-500/20'
                    : active 
                      ? 'bg-cyan-400/10 text-white font-medium border border-cyan-400/20' 
                      : 'text-slate-300 hover:bg-white/5 border border-transparent'
            }`}
          >
            {active && !item.isCompare && (
              <span className={`absolute left-[-6px] top-2 bottom-2 w-1 rounded-full ${
                item.isValidation ? 'bg-emerald-400 shadow-[0_0_10px_#34d399]' :
                item.isHypothesis ? 'bg-purple-400 shadow-[0_0_10px_#c084fc]' :
                'bg-cyan-400 shadow-[0_0_10px_#67e8f9]'
              }`} />
            )}
            <Icon className={`w-4 h-4 shrink-0 ${
              item.isValidation ? 'text-emerald-400' :
              item.isHypothesis ? 'text-purple-400' :
              'text-cyan-400'
            }`} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
