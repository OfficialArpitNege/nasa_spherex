import React, { useState } from 'react';

export default function LandingPage({ onOpenApp }) {
  const [blinkView, setBlinkView] = useState('blink');
  const [showDetected, setShowDetected] = useState(false);

  return (
    <div className="relative z-10 max-w-6xl mx-auto px-6 py-4 text-[#e4ecff]">
      {/* Top Header */}
      <header className="flex justify-between items-center py-6">
        <div className="font-semibold tracking-wider text-lg">
          SPHEREx <span className="text-slate-400 font-normal">Sky Watcher</span>
        </div>
        <button 
          onClick={onOpenApp}
          className="px-6 py-2.5 rounded-full border border-blue-400/20 text-white font-medium hover:border-cyan-400 hover:bg-cyan-400/10 transition-all cursor-pointer"
        >
          Open the app
        </button>
      </header>

      {/* Hero Section */}
      <main className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center py-12">
        <div>
          <h1 className="text-4xl md:text-6xl font-serif font-light leading-tight mb-6">
            Find what changed in the sky.
          </h1>
          <p className="text-slate-400 text-lg mb-4 leading-relaxed">
            Explore repeated SPHEREx observations and identify moving-object candidates. Two visits to the same patch of sky, compared using automated source detection and astrometric cross-matching to spot candidates with significant apparent motion.
          </p>
          <div className="p-3 mb-8 rounded-xl bg-slate-900/60 border border-blue-400/20 text-xs text-slate-400 leading-relaxed">
            <span className="text-cyan-400 font-semibold mr-1">SCIENTIFIC CONTEXT:</span>
            Planet X / Planet Nine is a scientific motivation for this exploration. This tool identifies moving-object candidates and does not claim to detect or confirm Planet X.
          </div>
          <div className="flex flex-wrap gap-4">
            <button
              onClick={onOpenApp}
              className="px-7 py-3.5 rounded-full bg-cyan-400 text-slate-950 font-semibold hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20 cursor-pointer"
            >
              Start exploring
            </button>
            <a 
              href="#how"
              className="px-7 py-3.5 rounded-full border border-blue-400/20 text-slate-200 font-medium hover:border-cyan-400 hover:bg-cyan-400/10 transition-all"
            >
              How it works
            </a>
          </div>
        </div>

        {/* Demo Plate Plate SVG */}
        <div className="flex flex-col items-center">
          <div className="relative w-full max-w-[360px] aspect-square rounded-full border border-blue-400/20 bg-gradient-to-br from-[#0d1a44] to-[#050a1f] shadow-2xl overflow-hidden">
            <svg viewBox="0 0 400 400" className="w-full h-full">
              {/* Demo stars */}
              <circle cx="100" cy="120" r="1.5" fill="#c8deff" opacity="0.8" />
              <circle cx="280" cy="90" r="2" fill="#ffe4cd" opacity="0.9" />
              <circle cx="150" cy="300" r="1.2" fill="#c8deff" opacity="0.7" />
              <circle cx="320" cy="220" r="2.5" fill="#c8deff" opacity="0.8" />
              
              {/* Moving object */}
              <circle 
                cx={blinkView === 'b' ? 214 : 128} 
                cy={blinkView === 'b' ? 186 : 236} 
                r="3.2" 
                fill="#f4f9ff" 
              />
              
              {/* Variable brightness object */}
              <circle 
                cx="290" 
                cy="278" 
                r={blinkView === 'b' ? 6.2 : 2.6} 
                fill="#f4f9ff" 
                opacity={blinkView === 'b' ? 1 : 0.55} 
              />

              {showDetected && (
                <g fill="none" stroke="#ff7a3d" strokeWidth="1.6">
                  <circle cx="128" cy="236" r="16" strokeDasharray="4 3" />
                  <circle cx="214" cy="186" r="16" />
                  <line x1="128" y1="236" x2="214" y2="186" strokeDasharray="3 4" strokeWidth="1" />
                  <circle cx="290" cy="278" r="16" />
                </g>
              )}
            </svg>
            <div className="absolute inset-x-0 top-6 text-center text-xs tracking-wider text-slate-400">
              {blinkView === 'b' ? <span><b>B</b> &nbsp;18 Dec 2025</span> : <span><b>A</b> &nbsp;14 Jun 2025</span>}
            </div>
          </div>

          <div className="w-full max-w-[360px] mt-4 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex border border-blue-400/20 rounded-full overflow-hidden bg-slate-950/40">
                <button 
                  onClick={() => setBlinkView('a')}
                  className={`px-3 py-1 text-xs transition-colors ${blinkView === 'a' ? 'bg-cyan-400/20 text-white' : 'text-slate-400'}`}
                >
                  A
                </button>
                <button 
                  onClick={() => setBlinkView('b')}
                  className={`px-3 py-1 text-xs transition-colors ${blinkView === 'b' ? 'bg-cyan-400/20 text-white' : 'text-slate-400'}`}
                >
                  B
                </button>
                <button 
                  onClick={() => setBlinkView('blink')}
                  className={`px-3 py-1 text-xs transition-colors ${blinkView === 'blink' ? 'bg-cyan-400/20 text-white' : 'text-slate-400'}`}
                >
                  Blink
                </button>
              </div>

              <button 
                onClick={() => setShowDetected(!showDetected)}
                className="px-3 py-1 rounded-full border border-orange-500/60 text-orange-300 text-xs hover:bg-orange-500/10 transition-colors"
              >
                {showDetected ? 'Hide markers' : 'Detect changes'}
              </button>
            </div>

            <p className="text-xs text-slate-400 text-center m-0">
              {showDetected 
                ? '2 possible changes: one moving source, one brightness change.' 
                : 'Watch closely. Two things are different between A and B.'}
            </p>
          </div>
        </div>
      </main>

      {/* How it works section */}
      <section id="how" className="py-16 border-t border-blue-400/20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-serif font-light mb-4">The trick astronomers have used for a century.</h2>
            <p className="text-slate-400 leading-relaxed">
              Flip between two images of the same sky and anything that moved or brightened seems to jump. Your eye finds it because everything else holds still.
            </p>
          </div>
          <ol className="space-y-6">
            <li className="flex gap-4">
              <span className="w-8 h-8 rounded-full border border-cyan-400 text-cyan-400 flex items-center justify-center shrink-0 font-serif">1</span>
              <div>
                <h3 className="text-xl font-serif mb-1">Observe</h3>
                <p className="text-slate-400 text-sm">SPHEREx, a NASA space telescope, maps the entire sky and then does it again.</p>
              </div>
            </li>
            <li className="flex gap-4">
              <span className="w-8 h-8 rounded-full border border-cyan-400 text-cyan-400 flex items-center justify-center shrink-0 font-serif">2</span>
              <div>
                <h3 className="text-xl font-serif mb-1">Compare</h3>
                <p className="text-slate-400 text-sm">Repeat visits give you two looks at the same region, so differences show up.</p>
              </div>
            </li>
            <li className="flex gap-4">
              <span className="w-8 h-8 rounded-full border border-cyan-400 text-cyan-400 flex items-center justify-center shrink-0 font-serif">3</span>
              <div>
                <h3 className="text-xl font-serif mb-1">Discover</h3>
                <p className="text-slate-400 text-sm">Objects that appear to move or change are flagged as candidates for a closer look.</p>
              </div>
            </li>
          </ol>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 text-center border-t border-blue-400/20">
        <h2 className="text-3xl md:text-4xl font-serif font-light mb-6">Six months apart. What changed?</h2>
        <button 
          onClick={onOpenApp}
          className="px-8 py-3.5 rounded-full bg-cyan-400 text-slate-950 font-semibold hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20 cursor-pointer"
        >
          Open Sky Watcher
        </button>
      </section>

      <footer className="py-8 border-t border-blue-400/20 text-xs text-slate-400 text-center leading-relaxed">
        SPHEREx Moving Object Explorer · Powered by real NASA/IPAC IRSA SPHEREx archive data and Astropy WCS astrometry.<br />
        Planet X / Planet Nine is a scientific motivation for this exploration. This tool identifies moving-object candidates and does not claim to detect or confirm Planet X.
      </footer>
    </div>
  );
}
