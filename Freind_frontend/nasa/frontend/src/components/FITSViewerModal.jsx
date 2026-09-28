import React, { useState, useEffect } from 'react';
import { useSky } from '../context/SkyContext';
import { getPreviewUrl } from '../services/api';
import { X, Layers, SplitSquareVertical, Play, Pause, Compass, ZoomIn } from 'lucide-react';

export default function FITSViewerModal({ isOpen, onClose }) {
  const {
    cutout1,
    cutout2,
    selectedObs1,
    selectedObs2,
    motionResult,
    blinkSpeed,
    candidates
  } = useSky();

  const [viewerMode, setViewerMode] = useState('blink'); // 'blink' | 'side-by-side'
  const [activeFrame, setActiveFrame] = useState('1'); // '1' | '2'
  const [isPlaying, setIsPlaying] = useState(true);

  // Blink interval timer
  useEffect(() => {
    if (!isOpen || viewerMode !== 'blink' || !isPlaying) return;
    const intervalMs = Math.max(100, (11 - blinkSpeed) * 120);
    const timer = setInterval(() => {
      setActiveFrame((prev) => (prev === '1' ? '2' : '1'));
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isOpen, viewerMode, isPlaying, blinkSpeed]);

  if (!isOpen) return null;

  const prevUrl1 = cutout1?.preview_filename ? getPreviewUrl(cutout1.preview_filename) : null;
  const prevUrl2 = cutout2?.preview_filename ? getPreviewUrl(cutout2.preview_filename) : null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-5xl max-h-[92vh] glass rounded-3xl p-6 overflow-y-auto space-y-4 shadow-2xl border border-cyan-400/30 text-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-3">
            <Layers className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="text-lg font-semibold tracking-wider text-white">
                SPHEREx FITS PREVIEW & BLINK COMPARISON
              </h2>
              <p className="text-[11px] text-slate-400">
                Visualizing calibrated science HDU cutouts with astrometric WCS coordinates.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex border border-blue-400/30 rounded-full overflow-hidden bg-slate-900/60 text-xs">
              <button
                type="button"
                onClick={() => setViewerMode('blink')}
                className={`px-3 py-1 font-medium transition-colors ${
                  viewerMode === 'blink' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Blink Mode
              </button>
              <button
                type="button"
                onClick={() => setViewerMode('side-by-side')}
                className={`px-3 py-1 font-medium transition-colors ${
                  viewerMode === 'side-by-side' ? 'bg-cyan-400/30 text-white font-semibold' : 'text-slate-400 hover:text-white'
                }`}
              >
                Side-by-Side
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-full border border-white/20 hover:bg-white/10 text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Missing cutouts empty state */}
        {(!prevUrl1 || !prevUrl2) && (
          <div className="text-center py-16 space-y-2">
            <div className="text-slate-400 text-sm">No FITS cutouts loaded yet.</div>
            <p className="text-xs text-slate-500">
              Select two observation epochs in the SPHEREx Archive panel and run Motion Analysis to download real FITS cutouts.
            </p>
          </div>
        )}

        {/* Blink Viewer */}
        {prevUrl1 && prevUrl2 && viewerMode === 'blink' && (
          <div className="space-y-3">
            <div className="relative aspect-video max-h-[480px] w-full bg-black rounded-2xl overflow-hidden border border-white/10 flex items-center justify-center">
              <img
                src={activeFrame === '1' ? prevUrl1 : prevUrl2}
                alt={`Epoch ${activeFrame}`}
                className="w-full h-full object-contain"
              />

              {/* Epoch Indicator Tag */}
              <div className="absolute top-4 left-4 px-3 py-1.5 rounded-xl bg-slate-950/80 backdrop-blur border border-white/20 font-mono text-xs flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${activeFrame === '1' ? 'bg-cyan-400 shadow-[0_0_8px_#22d3ee]' : 'bg-orange-400 shadow-[0_0_8px_#fb923c]'}`} />
                <span className="font-bold text-white">EPOCH {activeFrame}</span>
                <span className="text-slate-400">
                  {activeFrame === '1' ? (selectedObs1?.observation_time_utc || '').split('T')[0] : (selectedObs2?.observation_time_utc || '').split('T')[0]}
                </span>
                <span className="text-slate-400">({activeFrame === '1' ? selectedObs1?.bandpass : selectedObs2?.bandpass})</span>
              </div>
            </div>

            {/* Play/Pause & Frame Selector */}
            <div className="flex items-center justify-between px-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="px-3 py-1.5 rounded-full bg-cyan-400/20 hover:bg-cyan-400/30 border border-cyan-400/50 text-cyan-200 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  <span>{isPlaying ? 'Pause Blink' : 'Resume Blink'}</span>
                </button>

                <div className="flex border border-white/10 rounded-full overflow-hidden text-xs">
                  <button
                    type="button"
                    onClick={() => { setIsPlaying(false); setActiveFrame('1'); }}
                    className={`px-3 py-1 ${activeFrame === '1' ? 'bg-cyan-400/30 text-white font-bold' : 'text-slate-400'}`}
                  >
                    Epoch 1 (A)
                  </button>
                  <button
                    type="button"
                    onClick={() => { setIsPlaying(false); setActiveFrame('2'); }}
                    className={`px-3 py-1 ${activeFrame === '2' ? 'bg-orange-400/30 text-white font-bold' : 'text-slate-400'}`}
                  >
                    Epoch 2 (B)
                  </button>
                </div>
              </div>

              {motionResult?.time_difference && (
                <div className="text-xs font-mono text-slate-400">
                  Elapsed Time: <span className="text-slate-200 font-semibold">{motionResult.time_difference.days.toFixed(1)} days</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Side-by-Side Viewer */}
        {prevUrl1 && prevUrl2 && viewerMode === 'side-by-side' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono text-cyan-300">
                <span className="font-semibold">EPOCH 1 (A)</span>
                <span className="text-slate-400">{selectedObs1?.observation_id}</span>
              </div>
              <div className="aspect-video bg-black rounded-2xl overflow-hidden border border-cyan-400/30 flex items-center justify-center">
                <img src={prevUrl1} alt="Epoch 1 FITS Cutout" className="w-full h-full object-contain" />
              </div>
              <div className="text-[11px] font-mono text-slate-400 flex justify-between">
                <span>{selectedObs1?.observation_time_utc}</span>
                <span>{selectedObs1?.bandpass}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-mono text-orange-300">
                <span className="font-semibold">EPOCH 2 (B)</span>
                <span className="text-slate-400">{selectedObs2?.observation_id}</span>
              </div>
              <div className="aspect-video bg-black rounded-2xl overflow-hidden border border-orange-400/30 flex items-center justify-center">
                <img src={prevUrl2} alt="Epoch 2 FITS Cutout" className="w-full h-full object-contain" />
              </div>
              <div className="text-[11px] font-mono text-slate-400 flex justify-between">
                <span>{selectedObs2?.observation_time_utc}</span>
                <span>{selectedObs2?.bandpass}</span>
              </div>
            </div>
          </div>
        )}

        {/* FITS Metadata & Detection Summary Footer */}
        {motionResult && (
          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-white/10 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-sans">Epoch 1 Sources</span>
              <span className="text-cyan-300 font-bold">{motionResult.source_statistics?.sources_detected_epoch_1 || 0}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-sans">Epoch 2 Sources</span>
              <span className="text-orange-300 font-bold">{motionResult.source_statistics?.sources_detected_epoch_2 || 0}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-sans">Cross-Matched</span>
              <span className="text-slate-200 font-bold">{motionResult.source_statistics?.matched_sources || 0}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-sans">Moving Candidates</span>
              <span className="text-orange-400 font-bold">{motionResult.source_statistics?.candidate_count || 0}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
