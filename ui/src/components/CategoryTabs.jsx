import React, { useRef, useState, useLayoutEffect, useEffect, useCallback } from 'react';
import { Icon } from './Icons';

export default function CategoryTabs({
  categories = [],
  activeId,
  onChange,
  className = '',
  variant = 'pills',
}) {
  const containerRef = useRef(null);
  const [indicatorStyle, setIndicatorStyle] = useState({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
    opacity: 0,
    ready: false,
  });

  const updateIndicator = useCallback(() => {
    if (!containerRef.current) return;
    const activeBtn = containerRef.current.querySelector(`[data-tab-id="${activeId}"]`);
    if (activeBtn) {
      setIndicatorStyle((prev) => ({
        x: activeBtn.offsetLeft,
        y: activeBtn.offsetTop,
        width: activeBtn.offsetWidth,
        height: activeBtn.offsetHeight,
        opacity: 1,
        ready: prev.ready || prev.opacity > 0,
      }));
    } else {
      setIndicatorStyle((prev) => ({ ...prev, opacity: 0 }));
    }
  }, [activeId]);

  useLayoutEffect(() => {
    updateIndicator();
  }, [updateIndicator, categories]);

  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      updateIndicator();
      // Second tick to ensure font rendering & metrics are 100% computed
      requestAnimationFrame(updateIndicator);
    });

    const handleResize = () => updateIndicator();
    window.addEventListener('resize', handleResize);
    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
    };
  }, [updateIndicator]);

  const isSubtabs = variant === 'subtabs';
  const containerClass = isSubtabs
    ? `subtabs-nav-bar animated-subtabs ${className}`
    : `category-tabs animated-category-tabs ${className}`;
  const btnClass = isSubtabs ? 'subtab-nav-btn' : 'tab-pill';

  return (
    <div className={containerClass} ref={containerRef}>
      <span
        className={isSubtabs ? 'subtab-pill-indicator' : 'tab-pill-indicator'}
        style={{
          transform: `translate3d(${indicatorStyle.x}px, ${indicatorStyle.y}px, 0)`,
          width: `${indicatorStyle.width}px`,
          height: `${indicatorStyle.height}px`,
          opacity: indicatorStyle.opacity,
          transition: indicatorStyle.ready
            ? 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), width 0.28s cubic-bezier(0.16, 1, 0.3, 1), height 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.15s ease'
            : 'opacity 0.2s ease',
        }}
        aria-hidden="true"
      />
      {categories.map((cat) => {
        const isActive = activeId === cat.id;
        return (
          <button
            type="button"
            key={cat.id}
            data-tab-id={cat.id}
            className={`${btnClass} ${isActive ? 'active' : ''}`}
            onClick={() => onChange(cat.id)}
            aria-pressed={isActive}
            title={cat.title || cat.label}
          >
            {cat.icon && <Icon name={cat.icon} />}
            <span>{cat.label}</span>
            {cat.count !== undefined && <span className="badge-count">{cat.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
