import React, { useRef, useEffect } from 'react';
import { useSky } from '../context/SkyContext';

const hash = (a, b, c) => {
  let n = Math.imul(a | 0, 374761393) ^ Math.imul(b | 0, 668265263) ^ Math.imul(c | 0, 1274126177);
  n = Math.imul(n ^ (n >>> 13), 1103515245);
  n ^= n >>> 16;
  return (n >>> 0) / 4294967296;
};

const pad2 = (n) => String(n).padStart(2, '0');

const REGION_NAMES = [
  'COMA BERENICES FIELD',
  'VIRGO CLUSTER EDGE',
  'BOÖTES VOID MARGIN',
  'SERPENS CAUDA',
  'HERCULES FILAMENT',
  'LEO TRIPLET REGION'
];

export default function SkyCanvas({ triggerScan, setTriggerScan }) {
  const canvasRef = useRef(null);
  const { 
    mode, 
    view, 
    blinkSpeed, 
    setCoords, 
    candidates,
    setCandidates, 
    detected,
    setDetected, 
    statusText, 
    setStatusText, 
    selectedCandidate,
    setSelectedCandidate,
    setIsFocusMode
  } = useSky();

  const stateRef = useRef({
    mode,
    view,
    blinkSpeed,
    cam: { x: 400, y: 300 },
    tgt: { x: 400, y: 300 },
    zoom: 1,
    zt: 1,
    mo: { x: 0, y: 0 },
    mt: { x: 0, y: 0 },
    p: 1,
    pt: 0,
    lt: 0,
    scan: -1,
    detected: false,
    cands: [],
    pick: null,
    ptr: null,
    dn: null,
    last: 0,
    fr: 0,
    blink: true
  });

  useEffect(() => {
    stateRef.current.mode = mode;
    stateRef.current.view = view;
    stateRef.current.blinkSpeed = blinkSpeed;
    stateRef.current.blink = view === 'blink';
  }, [mode, view, blinkSpeed]);

  useEffect(() => {
    if (candidates && candidates.length > 0) {
      stateRef.current.cands = candidates;
      stateRef.current.detected = true;
    }
  }, [candidates]);

  useEffect(() => {
    if (selectedCandidate && selectedCandidate.bx !== undefined && selectedCandidate.by !== undefined) {
      stateRef.current.tgt.x = selectedCandidate.bx;
      stateRef.current.tgt.y = selectedCandidate.by;
    }
  }, [selectedCandidate]);

  useEffect(() => {
    if (triggerScan) {
      stateRef.current.scan = 0;
      stateRef.current.detected = false;
      stateRef.current.cands = [];
      setDetected(false);
      setCandidates([]);
      setStatusText('SCANNING…');
      setIsFocusMode(true);
    }
  }, [triggerScan]);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const g = cv.getContext('2d');
    let animId;

    let W = window.innerWidth;
    let H = window.innerHeight;
    let D = Math.min(window.devicePixelRatio || 1, 1.5);

    const resize = () => {
      D = Math.min(window.devicePixelRatio || 1, 1.5);
      W = window.innerWidth;
      H = window.innerHeight;
      cv.width = W * D;
      cv.height = H * D;
      g.setTransform(D, 0, 0, D, 0, 0);
    };

    window.addEventListener('resize', resize);
    resize();

    const LY = [{ d: 0.2, c: 240, n: 9, r: 0.8 }, { d: 0.5, c: 300, n: 5, r: 1.2 }, { d: 1, c: 420, n: 3, r: 1.8 }];
    const rng = (o, pad, c, Z) => [
      Math.floor((o - (Z / 2 + pad) / stateRef.current.zoom) / c),
      Math.floor((o + (Z / 2 + pad) / stateRef.current.zoom) / c)
    ];

    function stars(l, T) {
      const s = stateRef.current;
      const ox = s.cam.x * l.d, oy = s.cam.y * l.d;
      const mx = s.mo.x * l.d * 60, my = s.mo.y * l.d * 60;
      const [x0, x1] = rng(ox, 60, l.c, W);
      const [y0, y1] = rng(oy, 60, l.c, H);

      for (let a = x0; a <= x1; a++) {
        for (let b = y0; b <= y1; b++) {
          for (let i = 0; i < l.n; i++) {
            const st = hash(i, a, b);
            const x = ((a + hash(i + 40, a, b)) * l.c - ox) * s.zoom + W / 2 + mx;
            const y = ((b + hash(i + 80, a, b)) * l.c - oy) * s.zoom + H / 2 + my;
            const r = l.r * (0.35 + st * st * 1.5);
            const al = (0.4 + st * 0.6) * (0.8 + 0.2 * Math.sin(T / 900 + st * 99));

            if (st > 0.93) {
              const q = g.createRadialGradient(x, y, 0, x, y, r * 7);
              q.addColorStop(0, 'rgba(180,210,255,.45)');
              q.addColorStop(1, 'rgba(180,210,255,0)');
              g.fillStyle = q;
              g.fillRect(x - r * 7, y - r * 7, r * 14, r * 14);
            }
            g.fillStyle = `rgba(${hash(i, b, a) > 0.65 ? '255,228,205' : '200,222,255'},${al})`;
            g.beginPath();
            g.arc(x, y, r, 0, 7);
            g.fill();
          }
        }
      }
    }

    const P = [[70, 80, 230], [135, 60, 205], [40, 150, 235]];
    function neb() {
      const s = stateRef.current;
      const d = 0.3, c = 1800;
      const ox = s.cam.x * d, oy = s.cam.y * d;
      const [x0, x1] = rng(ox, 1000, c, W);
      const [y0, y1] = rng(oy, 1000, c, H);
      g.globalCompositeOperation = 'lighter';

      for (let a = x0; a <= x1; a++) {
        for (let b = y0; b <= y1; b++) {
          for (let i = 0; i < 2; i++) {
            const x = ((a + hash(i + 5, a, b)) * c - ox) * s.zoom + W / 2 + s.mo.x * d * 60;
            const y = ((b + hash(i + 6, a, b)) * c - oy) * s.zoom + H / 2 + s.mo.y * d * 60;
            const r = (500 + hash(i + 9, a, b) * 500) * s.zoom;
            const k = P[Math.floor(hash(i + 3, a, b) * 3)];
            const q = g.createRadialGradient(x, y, 0, x, y, r);
            q.addColorStop(0, `rgba(${k},.2)`);
            q.addColorStop(1, `rgba(${k},0)`);
            g.fillStyle = q;
            g.fillRect(x - r, y - r, r * 2, r * 2);
          }
        }
      }
      g.globalCompositeOperation = 'source-over';
    }

    function gal() {
      const s = stateRef.current;
      const d = 0.6, c = 800;
      const ox = s.cam.x * d, oy = s.cam.y * d;
      const [x0, x1] = rng(ox, 80, c, W);
      const [y0, y1] = rng(oy, 80, c, H);

      for (let a = x0; a <= x1; a++) {
        for (let b = y0; b <= y1; b++) {
          if (hash(1, a, b) > 0.4) continue;
          const x = ((a + hash(2, a, b)) * c - ox) * s.zoom + W / 2 + s.mo.x * d * 60;
          const y = ((b + hash(3, a, b)) * c - oy) * s.zoom + H / 2 + s.mo.y * d * 60;
          const r = (22 + hash(4, a, b) * 32) * s.zoom;

          g.save();
          g.translate(x, y);
          g.rotate(hash(5, a, b) * 3);
          g.scale(1, 0.4);
          const q = g.createRadialGradient(0, 0, 0, 0, 0, r);
          q.addColorStop(0, 'rgba(255,238,210,.9)');
          q.addColorStop(0.3, 'rgba(170,190,255,.35)');
          q.addColorStop(1, 'rgba(90,110,220,0)');
          g.fillStyle = q;
          g.beginPath();
          g.arc(0, 0, r, 0, 7);
          g.fill();
          g.restore();
        }
      }
    }

    function vis() {
      const s = stateRef.current;
      const step = 520, o = [];
      const [x0, x1] = rng(s.cam.x, 150, step, W);
      const [y0, y1] = rng(s.cam.y, 150, step, H);

      for (let a = x0; a <= x1; a++) {
        for (let b = y0; b <= y1; b++) {
          const F = (a === 0 && b === 0) || (a === 1 && b === 0) || (a === 0 && b === 1);
          if (!F && hash(1, a, b) > 0.3) continue;

          const an = hash(4, a, b) * 6.28;
          const ln = 55 + hash(5, a, b) * 70;
          const fx = (a === 1 && b === 0) || (!F && hash(6, a, b) < 0.3);

          o.push({
            bx: (a + 0.15 + hash(2, a, b) * 0.7) * step,
            by: (b + 0.15 + hash(3, a, b) * 0.7) * step,
            vx: fx ? 0 : Math.cos(an) * ln,
            vy: fx ? 0 : Math.sin(an) * ln,
            flux: fx
          });
        }
      }
      o.sort((u, v) => u.bx - v.bx).forEach((m, i) => {
        m.n = i + 1;
        m.label = m.flux ? 'Brightness changed' : i % 2 ? 'Possible moving source' : 'Movement detected';
      });
      return o;
    }

    const S = (x, y) => {
      const s = stateRef.current;
      return [(x - s.cam.x) * s.zoom + W / 2 + s.mo.x * 60, (y - s.cam.y) * s.zoom + H / 2 + s.mo.y * 60];
    };

    function dot(x, y, r, a) {
      const q = g.createRadialGradient(x, y, 0, x, y, r * 5);
      q.addColorStop(0, `rgba(220,240,255,${0.7 * a})`);
      q.addColorStop(1, 'rgba(220,240,255,0)');
      g.fillStyle = q;
      g.fillRect(x - r * 5, y - r * 5, r * 10, r * 10);
      g.fillStyle = `rgba(245,250,255,${a})`;
      g.beginPath();
      g.arc(x, y, r, 0, 7);
      g.fill();
    }

    function ring(x, y, dash, T) {
      g.setLineDash(dash ? [5, 4] : []);
      g.strokeStyle = `rgba(255,122,61,${0.8 + 0.2 * Math.sin(T / 250)})`;
      g.lineWidth = 2;
      g.beginPath();
      g.arc(x, y, 24, 0, 7);
      g.stroke();
      g.setLineDash([]);
    }

    function getCoords(x, y) {
      const dec = 15.533 - (y - 300) * 0.0016;
      const ra = (190.5 - (x - 400) * 0.0016 / Math.cos(dec * Math.PI / 180)) / 15;
      const hh = Math.floor(ra);
      const m = Math.floor((ra - hh) * 60);
      const sec = Math.floor(((ra - hh) * 60 - m) * 60);
      const ad = Math.abs(dec);
      const d = Math.floor(ad);
      const mm = Math.floor((ad - d) * 60);
      const ss = Math.floor(((ad - d) * 60 - mm) * 60);
      const z = (n) => String(n).padStart(2, '0');
      return {
        ra: `${hh}h ${z(m)}m ${z(sec)}s`,
        dec: `${dec < 0 ? '-' : '+'}${d}° ${z(mm)}' ${z(ss)}"`
      };
    }

    const frame = (T) => {
      animId = requestAnimationFrame(frame);
      const s = stateRef.current;
      const dt = Math.min(50, T - s.last);
      s.last = T;
      s.fr++;

      if (s.mode === 'explore' && !s.dn) {
        s.tgt.x += 0.05;
        s.tgt.y += 0.015;
      }

      s.cam.x += (s.tgt.x - s.cam.x) * 0.07;
      s.cam.y += (s.tgt.y - s.cam.y) * 0.07;
      s.zoom += (s.zt - s.zoom) * 0.1;
      s.mo.x += (s.mt.x - s.mo.x) * 0.06;
      s.mo.y += (s.mt.y - s.mo.y) * 0.06;

      const ms = 1900 - s.blinkSpeed * 160;
      if (s.mode === 'explore') s.pt = 1;
      else if (s.view === 'a') s.pt = 0;
      else if (s.view === 'b') s.pt = 1;
      else if (T - s.lt > ms) {
        s.lt = T;
        if (s.blink) s.pt = s.pt ? 0 : 1;
      }
      s.p += (s.pt - s.p) * 0.1;

      g.fillStyle = '#02040a';
      g.fillRect(0, 0, W, H);
      neb();

      g.strokeStyle = 'rgba(140,190,255,.07)';
      g.lineWidth = 1;
      for (const [rx, ry, r] of [[0.5, 0.18, -0.35], [0.4, 0.28, 0.5], [0.62, 0.12, 0.9]]) {
        g.beginPath();
        g.ellipse(W / 2 - s.mo.x * 25, H / 2 - s.mo.y * 25, rx * W * s.zoom, ry * W * s.zoom, r + T / 1e5, 0, 7);
        g.stroke();
      }

      gal();
      for (const l of LY) stars(l, T);

      const V = vis();
      for (const m of V) {
        const [x0, y0] = S(m.bx, m.by);
        const [x1, y1] = S(m.bx + m.vx, m.by + m.vy);
        if (m.flux) dot(x0, y0, 3, 0.25 + 0.75 * s.p);
        else {
          dot(x0, y0, 2.8, 1 - s.p);
          dot(x1, y1, 2.8, s.p);
        }
      }

      if (s.detected && s.mode === 'compare') {
        for (const c of s.cands) {
          const [x0, y0] = S(c.bx, c.by);
          const [x1, y1] = S(c.bx + c.vx, c.by + c.vy);
          g.font = '12px ui-monospace,monospace';
          if (c.flux) ring(x0, y0, 0, T);
          else {
            ring(x0, y0, 1, T);
            ring(x1, y1, 0, T);
            g.strokeStyle = 'rgba(255,122,61,.6)';
            g.setLineDash([3, 4]);
            g.beginPath();
            g.moveTo(x0, y0);
            g.lineTo(x1, y1);
            g.stroke();
            g.setLineDash([]);
          }
          g.fillStyle = '#ffb08a';
          g.fillText(pad2(c.n), x1 + 28, y1 - 24);
        }
      }

      if (s.scan >= 0) {
        s.scan += dt / 1700;
        const scanY = s.scan * H;
        const q = g.createLinearGradient(0, scanY - 90, 0, scanY);
        q.addColorStop(0, 'rgba(103,232,249,0)');
        q.addColorStop(1, 'rgba(103,232,249,.3)');
        g.fillStyle = q;
        g.fillRect(0, scanY - 90, W, 90);
        g.fillStyle = '#67e8f9';
        g.fillRect(0, scanY, W, 1.5);

        if (s.scan > 1) {
          s.scan = -1;
          s.detected = true;
          if (!s.cands || s.cands.length === 0) {
            s.cands = vis();
            setCandidates(s.cands);
          }
          setDetected(true);
          setTriggerScan(false);
          setIsFocusMode(false);
          setStatusText(s.cands.length ? `${s.cands.length} MOVING-OBJECT CANDIDATE${s.cands.length > 1 ? 'S' : ''} DETECTED` : 'Stationary / no significant motion detected.');
        }
      }

      if (s.pick) {
        const a = (T - s.pick.t) / 900;
        if (a > 1) s.pick = null;
        else {
          g.strokeStyle = `rgba(103,232,249,${1 - a})`;
          g.lineWidth = 1.5;
          g.beginPath();
          g.arc(s.pick.x, s.pick.y, 10 + a * 30, 0, 7);
          g.stroke();
        }
      }

      if (s.ptr) {
        g.strokeStyle = 'rgba(103,232,249,.4)';
        g.lineWidth = 1;
        g.beginPath();
        g.arc(s.ptr.x, s.ptr.y, 13, 0, 7);
        g.moveTo(s.ptr.x - 20, s.ptr.y); g.lineTo(s.ptr.x - 8, s.ptr.y);
        g.moveTo(s.ptr.x + 8, s.ptr.y); g.lineTo(s.ptr.x + 20, s.ptr.y);
        g.moveTo(s.ptr.x, s.ptr.y - 20); g.lineTo(s.ptr.x, s.ptr.y - 8);
        g.moveTo(s.ptr.x, s.ptr.y + 8); g.lineTo(s.ptr.x, s.ptr.y + 20);
        g.stroke();
      }

      if (s.fr % 8 === 0) {
        const rd = getCoords(s.cam.x, s.cam.y);
        const ca = Math.floor(s.cam.x / 2400);
        const cb = Math.floor(s.cam.y / 2400);
        const reg = REGION_NAMES[ca === 0 && cb === 0 ? 0 : Math.floor(hash(9, ca, cb) * 6)];
        setCoords({ ra: rd.ra, dec: rd.dec, region: reg });
      }
    };

    animId = requestAnimationFrame(frame);

    const handlePointerDown = (e) => {
      cv.setPointerCapture(e.pointerId);
      stateRef.current.dn = { x: e.clientX, y: e.clientY, cx: stateRef.current.cam.x, cy: stateRef.current.cam.y, m: 0 };
    };

    const handlePointerMove = (e) => {
      const s = stateRef.current;
      s.mt.x = e.clientX / W - 0.5;
      s.mt.y = e.clientY / H - 0.5;
      s.ptr = { x: e.clientX, y: e.clientY };

      if (s.dn) {
        const dx = e.clientX - s.dn.x;
        const dy = e.clientY - s.dn.y;
        if (Math.abs(dx) + Math.abs(dy) > 5) s.dn.m = 1;
        if (s.dn.m) {
          s.cam.x = s.tgt.x = s.dn.cx - dx / s.zoom;
          s.cam.y = s.tgt.y = s.dn.cy - dy / s.zoom;
        }
      }
    };

    const handleClick = (x, y) => {
      const s = stateRef.current;
      if (s.mode === 'explore') {
        s.tgt.x = (x - W / 2 - s.mo.x * 60) / s.zoom + s.cam.x;
        s.tgt.y = (y - H / 2 - s.mo.y * 60) / s.zoom + s.cam.y;
        return;
      }
      if (s.mode === 'about') return;

      const L = s.mode === 'compare' ? (s.detected ? s.cands : []) : vis();
      const c = L.find(m => [[m.bx, m.by], [m.bx + m.vx, m.by + m.vy]].some(q => {
        const sp = S(q[0], q[1]);
        return Math.hypot(sp[0] - x, sp[1] - y) < 38;
      }));

      if (c) {
        const targetX = c.bx + c.vx / 2;
        const targetY = c.by + c.vy / 2;
        s.tgt.x = targetX;
        s.tgt.y = targetY;
        setSelectedCandidate({ ...c, title: s.mode === 'discover' ? 'POTENTIAL MATCH FOUND' : 'POTENTIAL CANDIDATE' });
      } else if (s.mode === 'discover') {
        s.pick = { x, y, t: performance.now() };
        setStatusText('Nothing notable there — keep looking.');
        setSelectedCandidate(null);
      }
    };

    const handlePointerUp = (e) => {
      const d = stateRef.current.dn;
      stateRef.current.dn = null;
      if (d && !d.m) handleClick(e.clientX, e.clientY);
    };

    const handleWheel = (e) => {
      e.preventDefault();
      const s = stateRef.current;
      s.zt = Math.min(2.5, Math.max(0.6, s.zt * (e.deltaY < 0 ? 1.12 : 0.89)));
    };

    cv.addEventListener('pointerdown', handlePointerDown);
    cv.addEventListener('pointermove', handlePointerMove);
    cv.addEventListener('pointerup', handlePointerUp);
    cv.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
      cv.removeEventListener('pointerdown', handlePointerDown);
      cv.removeEventListener('pointermove', handlePointerMove);
      cv.removeEventListener('pointerup', handlePointerUp);
      cv.removeEventListener('wheel', handleWheel);
    };
  }, []);

  return (
    <canvas 
      ref={canvasRef} 
      className="fixed inset-0 w-full h-full cursor-grab active:cursor-grabbing touch-none z-0"
    />
  );
}
