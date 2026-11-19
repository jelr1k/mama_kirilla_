import React, { useEffect, useRef } from 'react';

export default function OscilloscopeCanvas({
  listening = false,
  volume = 72,
  mode = 'wave', // 'wave' | 'matrix'
  accent = '#ff4d00',
}) {
  const canvasRef = useRef(null);
  const pointerRef = useRef({ x: 0.5, y: 0.5, active: false });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    if (!ctx) return undefined;

    let rafId = 0;
    let t = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width || 600;
      const h = rect.height || 300;
      ctx.clearRect(0, 0, w, h);

      const ampBase = listening ? 24 + (volume / 100) * 34 : 7 + (volume / 100) * 6;
      const speed = listening ? 0.085 : 0.028;
      t += speed;

      const px = pointerRef.current.x * w;
      const py = pointerRef.current.y * h;

      if (mode === 'matrix') {
        const cols = 36;
        const rows = 14;
        const cellW = w / cols;
        const cellH = h / rows;

        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const cx = (c + 0.5) * cellW;
            const cy = (r + 0.5) * cellH;
            const dist = Math.hypot(cx - px, cy - py);
            const mouseBoost = pointerRef.current.active ? Math.max(0, 1 - dist / 150) : 0;
            const waveVal = Math.sin(c * 0.35 + t * 1.4) * Math.cos(r * 0.45 - t);
            const intensity = Math.max(0.08, Math.min(1, (waveVal + 1) * 0.35 * (listening ? 1.35 : 0.55) + mouseBoost * 0.7));

            ctx.fillStyle = intensity > 0.62 ? accent : `rgba(235, 238, 245, ${intensity * 0.42})`;
            const radius = 1.4 + intensity * (listening ? 2.6 : 1.5);
            ctx.beginPath();
            ctx.arc(cx, cy, radius, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      } else {
        // Multi-harmonic oscilloscope
        const midY = h / 2;
        const layers = [
          { freq: 0.018, phase: t, amp: ampBase, color: accent, width: 2.2, alpha: 0.95 },
          { freq: 0.031, phase: -t * 1.3, amp: ampBase * 0.55, color: '#b8ff3b', width: 1.3, alpha: 0.65 },
          { freq: 0.011, phase: t * 0.7, amp: ampBase * 0.38, color: '#e2e8f0', width: 1.0, alpha: 0.3 },
        ];

        // Center baseline
        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, midY);
        ctx.lineTo(w, midY);
        ctx.stroke();

        for (const layer of layers) {
          ctx.save();
          ctx.globalAlpha = layer.alpha;
          ctx.strokeStyle = layer.color;
          ctx.lineWidth = layer.width;
          ctx.beginPath();

          for (let x = 0; x <= w; x += 4) {
            const env = Math.sin((x / w) * Math.PI);
            const dist = pointerRef.current.active ? Math.abs(x - px) : 9999;
            const pull = dist < 130 ? (1 - dist / 130) * ((py - midY) * 0.35) : 0;
            const y =
              midY +
              Math.sin(x * layer.freq + layer.phase) * layer.amp * env +
              Math.sin(x * layer.freq * 2.3 - layer.phase * 1.6) * (layer.amp * 0.25) * env +
              pull;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.stroke();
          ctx.restore();
        }
      }

      rafId = requestAnimationFrame(draw);
    };

    rafId = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', resize);
    };
  }, [listening, volume, mode, accent]);

  const handleMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    pointerRef.current = {
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
      active: true,
    };
  };

  return (
    <canvas
      ref={canvasRef}
      className="te-osc-canvas"
      onMouseMove={handleMove}
      onMouseLeave={() => {
        pointerRef.current.active = false;
      }}
    />
  );
}
