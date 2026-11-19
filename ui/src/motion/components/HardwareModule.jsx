import React from 'react';
import { motion } from 'framer-motion';

export default function HardwareModule({
  id,
  title,
  code,
  dragConstraints,
  zIndex,
  onFocus,
  collapsed,
  onToggleCollapse,
  expanded,
  onToggleExpand,
  resetTick,
  defaultPos = { x: 0, y: 0 },
  width = 340,
  children,
  accentDot = '#ff4d00',
}) {
  return (
    <motion.section
      key={`${id}-${resetTick}`}
      layoutId={`module-${id}`}
      drag={!expanded}
      dragConstraints={dragConstraints}
      dragElastic={0.12}
      dragMomentum={true}
      dragTransition={{ bounceStiffness: 340, bounceDamping: 26 }}
      onPointerDown={() => onFocus(id)}
      initial={{ opacity: 0, scale: 0.94, x: defaultPos.x, y: defaultPos.y }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 420, damping: 30 }}
      className={`te-module ${expanded ? 'expanded' : ''} ${collapsed ? 'collapsed' : ''}`}
      style={{
        zIndex: expanded ? 70 : zIndex,
        width: expanded ? undefined : width,
      }}
    >
      {/* Screw marks */}
      <span className="te-screw tl" />
      <span className="te-screw tr" />

      <div className="te-module-rail" title="Перетащить блок">
        <div className="te-rail-left">
          <span className="te-led" style={{ background: accentDot, boxShadow: `0 0 8px ${accentDot}` }} />
          <span className="te-module-code">{code}</span>
          <span className="te-module-title">{title}</span>
        </div>

        <div className="te-rail-grip" aria-hidden="true">
          <span /><span /><span /><span /><span /><span />
        </div>

        <div className="te-rail-actions" onPointerDown={(e) => e.stopPropagation()}>
          <motion.button
            type="button"
            className="te-rail-btn"
            whileTap={{ y: 1 }}
            onClick={() => onToggleCollapse(id)}
            title={collapsed ? 'Развернуть блок' : 'Свернуть в плашку'}
            aria-label={`Свернуть ${title}`}
          >
            {collapsed ? '+' : '—'}
          </motion.button>
          <motion.button
            type="button"
            className="te-rail-btn"
            whileTap={{ y: 1 }}
            onClick={() => onToggleExpand(id)}
            title={expanded ? 'Вернуть на стол' : 'Развернуть на весь экран'}
            aria-label={`Развернуть ${title}`}
          >
            {expanded ? '×' : '□'}
          </motion.button>
        </div>
      </div>

      {!collapsed && <div className="te-module-body">{children}</div>}
    </motion.section>
  );
}
