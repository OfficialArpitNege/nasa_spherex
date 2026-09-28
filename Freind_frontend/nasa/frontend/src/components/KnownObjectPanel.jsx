import React, { useEffect } from 'react';
import { useSky } from '../context/SkyContext';
import { getPreviewUrl } from '../services/api';
import { CheckCircle, AlertTriangle, XCircle, Info, RefreshCw, X, ShieldAlert } from 'lucide-react';

export default function KnownObjectPanel() {
  const {
    mode,
    switchMode,
    knownObjectResult,
    isLoadingKnownObject,
    knownObjectError,
    executeKnownObjectValidation
  } = useSky();

  useEffect(() => {
    if (mode === 'validation' && !knownObjectResult && !isLoadingKnownObject) {
      executeKnownObjectValidation();
    }
  }, [mode, knownObjectResult, isLoadingKnownObject, executeKnownObjectValidation]);

  if (mode !== 'validation') return null;

  const res = knownObjectResult;

  const renderStatusBadge = (status) => {
    if (status === 'DETECTED') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 text-[11px] font-bold">
          <CheckCircle className="w-3.5 h-3.5" /> DETECTED
        </span>
      );
    }
    if (status === 'AMBIGUOUS') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-400/50 text-amber-300 text-[11px] font-bold">
          <AlertTriangle className="w-3.5 h-3.5" /> AMBIGUOUS
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-500/20 border border-rose-400/50 text-rose-300 text-[11px] font-bold">
        <XCircle className="w-3.5 h-3.5" /> NOT DETECTED
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="w-full max-w-4xl max-h-[90vh] glass rounded-3xl p-6 overflow-y-auto space-y-6 shadow-2xl border border-cyan-400/30 text-slate-200 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/10 pb-4">
          <div>
            <div className="text-[11px] tracking-[0.3em] text-cyan-400 font-semibold uppercase">
              KNOWN MOVING OBJECT VALIDATION
            </div>
            <h2 className="text-2xl sm:text-3xl font-light tracking-wide text-white mt-1">
              Interstellar Comet 3I/ATLAS
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Official NASA/IPAC IRSA SPHEREx observation table validation.
              Validates target association by distinguishing external ephemeris predictions from independent image measurements.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => executeKnownObjectValidation()}
              disabled={isLoadingKnownObject}
              title="Re-run validation"
              className="p-2 rounded-full border border-blue-400/30 hover:bg-white/10 text-slate-300 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingKnownObject ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
            <button
              onClick={() => switchMode('compare')}
              className="p-2 rounded-full border border-blue-400/30 hover:bg-white/10 text-slate-300 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Loading state */}
        {isLoadingKnownObject && (
          <div className="text-center py-16 space-y-3">
            <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto" />
            <div className="text-sm font-semibold tracking-wider text-cyan-300">
              Loading 3I/ATLAS SPHEREx observations from NASA/IRSA...
            </div>
            <p className="text-xs text-slate-400">
              Retrieving FITS cutouts, computing WCS astrometry, and evaluating target associations.
            </p>
          </div>
        )}

        {/* Error state */}
        {knownObjectError && !isLoadingKnownObject && (
          <div className="p-4 rounded-2xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-xs space-y-2">
            <div className="font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Validation Error
            </div>
            <div>{knownObjectError}</div>
            <button
              onClick={() => executeKnownObjectValidation()}
              className="px-4 py-1.5 rounded-full bg-rose-500/30 hover:bg-rose-500/50 text-white font-medium text-[11px] transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Results */}
        {res && !isLoadingKnownObject && (
          <div className="space-y-6">
            {/* Motion Decision Banner */}
            <div className={`p-4 rounded-2xl border flex items-start gap-3.5 ${
              res.two_epoch_motion_measurable
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-200'
                : 'bg-amber-500/15 border-amber-500/40 text-amber-200'
            }`}>
              <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold text-sm tracking-wide">
                  {res.two_epoch_motion_measurable
                    ? 'Target Reliably Detected in Both Epochs'
                    : 'Two-Epoch Target Motion: NOT MEASURABLE'}
                </div>
                <div className="text-xs mt-1 text-slate-300 leading-relaxed">
                  {res.motion_decision}
                </div>
              </div>
            </div>

            {/* Epoch Comparison Grid: Predicted vs Measured */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Epoch 1 */}
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[10px] tracking-widest text-cyan-400 font-bold block">
                      EPOCH 1 · 2025-08-07 10:13:39 UTC
                    </span>
                    <span className="text-xs font-mono text-slate-300">
                      {res.observation_1?.obs_id || 'SPHEREx Observation'}
                    </span>
                  </div>
                  {renderStatusBadge(res.epoch_1?.status)}
                </div>

                <div className="space-y-2 pt-2 border-t border-white/10 font-mono text-xs">
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase block tracking-wider font-sans">
                      External Prediction (IRSA Ephemeris):
                    </span>
                    <span className="text-slate-200">
                      RA {res.epoch_1?.predicted_ra?.toFixed(6)}° &nbsp;·&nbsp; DEC {res.epoch_1?.predicted_dec?.toFixed(6)}°
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 text-[10px] uppercase block tracking-wider font-sans">
                      Measured Image Centroid:
                    </span>
                    {res.epoch_1?.status === 'DETECTED' && res.epoch_1?.measured_ra !== null ? (
                      <span className="text-cyan-300">
                        RA {res.epoch_1.measured_ra.toFixed(6)}° &nbsp;·&nbsp; DEC {res.epoch_1.measured_dec.toFixed(6)}°
                      </span>
                    ) : (
                      <span className="text-rose-400 italic">Target not reliably detected in image</span>
                    )}
                  </div>

                  {res.epoch_1?.separation_arcsec !== null && (
                    <div className="flex justify-between text-[11px] text-slate-300 pt-1">
                      <span>Predicted-to-Measured Separation:</span>
                      <span className="text-cyan-400 font-bold">
                        {res.epoch_1.separation_arcsec.toFixed(2)}″ ({res.epoch_1.separation_pixels?.toFixed(2)} px)
                      </span>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 pt-1 border-t border-white/5 font-sans">
                    {res.epoch_1?.evaluation_note}
                  </div>
                </div>

                {res.preview_url_1 && (
                  <div className="mt-2 rounded-xl overflow-hidden border border-white/10 aspect-video bg-black flex items-center justify-center">
                    <img
                      src={getPreviewUrl(res.preview_url_1)}
                      alt="3I/ATLAS Epoch 1 Preview"
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}
              </div>

              {/* Epoch 2 */}
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[10px] tracking-widest text-orange-400 font-bold block">
                      EPOCH 2 · 2025-08-07 10:48:47 UTC
                    </span>
                    <span className="text-xs font-mono text-slate-300">
                      {res.observation_2?.obs_id || 'SPHEREx Observation'}
                    </span>
                  </div>
                  {renderStatusBadge(res.epoch_2?.status)}
                </div>

                <div className="space-y-2 pt-2 border-t border-white/10 font-mono text-xs">
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase block tracking-wider font-sans">
                      External Prediction (IRSA Ephemeris):
                    </span>
                    <span className="text-slate-200">
                      RA {res.epoch_2?.predicted_ra?.toFixed(6)}° &nbsp;·&nbsp; DEC {res.epoch_2?.predicted_dec?.toFixed(6)}°
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-400 text-[10px] uppercase block tracking-wider font-sans">
                      Measured Image Centroid:
                    </span>
                    {res.epoch_2?.status === 'DETECTED' && res.epoch_2?.measured_ra !== null ? (
                      <span className="text-emerald-300 font-semibold">
                        RA {res.epoch_2.measured_ra.toFixed(6)}° &nbsp;·&nbsp; DEC {res.epoch_2.measured_dec.toFixed(6)}°
                      </span>
                    ) : (
                      <span className="text-rose-400 italic">Target not reliably detected in image</span>
                    )}
                  </div>

                  {res.epoch_2?.separation_arcsec !== null && (
                    <div className="flex justify-between text-[11px] text-slate-300 pt-1">
                      <span>Predicted-to-Measured Separation:</span>
                      <span className="text-emerald-400 font-bold">
                        {res.epoch_2.separation_arcsec.toFixed(2)}″ ({res.epoch_2.separation_pixels?.toFixed(2)} px)
                      </span>
                    </div>
                  )}

                  {res.epoch_2?.matched_source?.snr && (
                    <div className="flex justify-between text-[11px] text-slate-300">
                      <span>Signal-to-Noise Ratio (SNR):</span>
                      <span className="text-slate-200">{res.epoch_2.matched_source.snr.toFixed(2)}</span>
                    </div>
                  )}

                  <div className="text-[10px] text-slate-400 pt-1 border-t border-white/5 font-sans">
                    {res.epoch_2?.evaluation_note}
                  </div>
                </div>

                {res.preview_url_2 && (
                  <div className="mt-2 rounded-xl overflow-hidden border border-white/10 aspect-video bg-black flex items-center justify-center">
                    <img
                      src={getPreviewUrl(res.preview_url_2)}
                      alt="3I/ATLAS Epoch 2 Preview"
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Validation Plot Image */}
            {res.validation_plot_url && (
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-white/10 space-y-2">
                <span className="text-[11px] tracking-widest text-slate-300 font-semibold uppercase block">
                  Astrometric Comparison & Target Association Plot
                </span>
                <div className="rounded-xl overflow-hidden border border-white/10 bg-black flex items-center justify-center">
                  <img
                    src={getPreviewUrl(res.validation_plot_url)}
                    alt="3I/ATLAS Validation Plot"
                    className="w-full max-h-[380px] object-contain"
                  />
                </div>
              </div>
            )}

            {/* Scientific Disclaimer */}
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-blue-400/20 text-[11px] text-slate-400 leading-relaxed">
              <span className="text-cyan-400 font-semibold mr-1">SCIENTIFIC INTEGRITY NOTICE:</span>
              {res.scientific_disclaimer}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
