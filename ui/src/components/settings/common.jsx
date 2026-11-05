import React from 'react';

export function Tip({ text }) {
  return (
    <span className="tooltip-badge" tabIndex={0}>
      ?
      <span className="tooltip-text">{text}</span>
    </span>
  );
}

export function Toggle({ value, onChange, label }) {
  return (
    <button
      className={`tg ${value ? 'on' : ''}`}
      onClick={() => onChange(!value)}
      role="switch"
      aria-checked={value}
      aria-label={label}
    />
  );
}
