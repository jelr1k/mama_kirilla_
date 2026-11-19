import React, { useRef } from 'react';
import { motion } from 'framer-motion';

export default function RotaryKnob({ value, onChange, label = 'GAIN' }) {
  const dragRef = useRef({ active: false, startY: 0, startVal: value });
  const angle = -135 + (value / 100) * 270;

  const handlePointerDown = (e) => {
    e.preventDefault();
    dragRef.current = { active: true, startY: e.clientY, startVal: value };

    const onMove = (ev) => {
      if (!dragRef.current.active) return;
      const dy = dragRef.current.startY - ev.clientY;
      const next = Math.max(0, Math.min(100, Math.round(dragRef.current.startVal + dy * 0.7)));
      onChange(next);
    };

    const onUp = () => {
      dragRef.current.active = false;
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 4 : -4;
    onChange(Math.max(0, Math.min(100, value + delta)));
  };

  const ticks = 15;

  return (
    <div className="te-knob-wrap" onWheel={handleWheel}>
      <div className="te-knob-ticks">
        {Array.from({ length: ticks }).map((_, i) => {
          const tickAngle = -135 + (i / (ticks - 1)) * 270;
          const lit = (i / (ticks - 1)) * 100 <= value;
          return (
            <span
              key={i}
              className={`te-knob-tick ${lit ? 'lit' : ''}`}
              style={{ transform: `rotate(${tickAngle}deg) translateY(-42px)` }}
            />
          );
        })}
        <motion.button
          type="button"
          className="te-knob-dial"
          onPointerDown={handlePointerDown}
          animate={{ rotate: angle }}
          transition={{ type: 'spring', stiffness: 420, damping: 28 }}
          whileTap={{ scale: 0.96 }}
          aria-label={label}
          title="Тяни вверх/вниз или крути колесо мыши"
        >
          <span className="te-knob-marker" />
        </motion.button>
      </div>
      <div className="te-knob-readout">
        <span className="te-mono-label">{label}</span>
        <span className="te-mono-val">{String(value).padStart(2, '0')}%</span>
      </div>
    </div>
  );
}
