import React, { useState } from 'react';
import { SkyProvider, useSky } from './context/SkyContext';
import SkyCanvas from './components/SkyCanvas';
import Navigation from './components/Navigation';
import HUD from './components/HUD';
import Header from './components/Header';
import ControlBar from './components/ControlBar';
import CandidateCard from './components/CandidateCard';
import MissionAbout from './components/MissionAbout';
import LandingPage from './components/LandingPage';
import SearchPanel from './components/SearchPanel';
import KnownObjectPanel from './components/KnownObjectPanel';
import FITSViewerModal from './components/FITSViewerModal';
import HypothesisUpdateCard from './components/HypothesisUpdateCard';
import NewObservationModal from './components/NewObservationModal';

function MainApp() {
  const { 
    mode, 
    isNewObsModalOpen, 
    setIsNewObsModalOpen, 
    hypothesisResult, 
    setHypothesisResult 
  } = useSky();
  const [triggerScan, setTriggerScan] = useState(false);
  const [showLanding, setShowLanding] = useState(true);
  const [isFITSViewerOpen, setIsFITSViewerOpen] = useState(false);

  if (showLanding) {
    return (
      <div className="relative min-h-screen w-full bg-[#04081a] text-slate-100 overflow-x-hidden font-sans">
        {/* Background Sky Starfield */}
        <SkyCanvas triggerScan={false} setTriggerScan={() => {}} />

        {/* Landing Page Content */}
        <LandingPage onOpenApp={() => setShowLanding(false)} />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen w-full bg-[#02040a] text-slate-100 overflow-hidden font-sans select-none">
      {/* Dynamic Starfield & Sky Canvas */}
      <SkyCanvas triggerScan={triggerScan} setTriggerScan={setTriggerScan} />

      {/* Main UI Overlay Layers */}
      <Header />
      <HUD />
      <Navigation />

      {/* Back to Home / Landing Page Button */}
      <button 
        onClick={() => setShowLanding(true)}
        className="fixed left-5 top-5 z-30 px-3.5 py-1.5 rounded-full bg-slate-950/70 backdrop-blur border border-blue-400/30 text-xs text-slate-300 hover:text-white hover:border-cyan-400 transition-colors shadow-lg cursor-pointer"
      >
        ← Home Page
      </button>

      {/* SPHEREx Archive Search & Observation Selector */}
      {mode === 'compare' && <SearchPanel />}

      {/* Interactive Controls */}
      {(mode === 'compare' || mode === 'discover' || mode === 'hypothesis') && (
        <ControlBar 
          onDetect={() => setTriggerScan(true)} 
          onOpenFITSViewer={() => setIsFITSViewerOpen(true)}
        />
      )}

      {/* 3I/ATLAS Known Object Validation Modal */}
      {mode === 'validation' && <KnownObjectPanel />}

      {/* FITS Preview & Blink Comparison Modal */}
      <FITSViewerModal 
        isOpen={isFITSViewerOpen} 
        onClose={() => setIsFITSViewerOpen(false)} 
      />

      {/* The New Observation Challenge Modal */}
      <NewObservationModal
        isOpen={isNewObsModalOpen}
        onClose={() => setIsNewObsModalOpen(false)}
      />

      {/* Hypothesis Update Result Card */}
      <HypothesisUpdateCard onClose={() => setHypothesisResult(null)} />

      {/* Info Modals & Step Overlays */}
      {mode === 'about' && <MissionAbout />}
      <CandidateCard />

      {/* Helper Interaction Hint */}
      {mode === 'explore' && (
        <div className="fixed left-1/2 sm:left-[calc(50%+90px)] bottom-6 -translate-x-1/2 text-[11px] tracking-[0.3em] text-slate-400 pointer-events-none transition-opacity duration-700 z-10 hidden sm:block">
          DRAG TO TRAVEL · CLICK TO FLY · SCROLL TO ZOOM
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <SkyProvider>
      <MainApp />
    </SkyProvider>
  );
}
