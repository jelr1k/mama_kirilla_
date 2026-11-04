import React from 'react';
import { Icon } from './Icons';

const isTauri = () => Boolean(window.__TAURI_INTERNALS__);

export default function TitleBar({ title, compact, onToggleCompact, connected }) {
  const handleMinimize = async (e) => {
    if (e) e.stopPropagation();
    if (isTauri()) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        await getCurrentWindow().minimize();
      } catch (err) {
        console.warn('Minimize failed:', err);
      }
    }
  };

  const handleMaximize = async (e) => {
    if (e) e.stopPropagation();
    if (isTauri()) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        await getCurrentWindow().toggleMaximize();
      } catch (err) {
        console.warn('Maximize failed:', err);
      }
    }
  };

  const handleClose = async (e) => {
    if (e) e.stopPropagation();
    if (isTauri()) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        await getCurrentWindow().hide();
      } catch (err) {
        console.warn('Hide failed:', err);
      }
    } else {
      window.close();
    }
  };

  return (
    <div className="window-titlebar" data-tauri-drag-region>
      <div
        className="titlebar-left"
        data-tauri-drag-region
        onDoubleClick={handleMaximize}
      >
        <span className="titlebar-logo-orb" />
        <span className="titlebar-app-name" data-tauri-drag-region>
          {title || 'Kirieshcka v2'}
        </span>
        <span
          className={`titlebar-status-dot ${connected ? 'online' : 'offline'}`}
          title={connected ? 'Ядро активно' : 'Ядро отключено'}
        />
      </div>

      <div className="titlebar-actions" data-tauri-drag-region="false">
        <button
          type="button"
          data-tauri-drag-region="false"
          className={`titlebar-action-btn mode-btn ${compact ? 'active' : ''}`}
          onClick={onToggleCompact}
          title={compact ? 'Развернуть полное окно' : 'Компактный режим (Виджет)'}
          aria-label="Компактный режим"
        >
          <Icon name={compact ? 'maximize' : 'minimize'} />
          <span className="mode-btn-label">{compact ? 'Окно' : 'Виджет'}</span>
        </button>

        <button
          type="button"
          data-tauri-drag-region="false"
          className="titlebar-action-btn"
          onClick={handleMinimize}
          title="Свернуть окно"
          aria-label="Свернуть"
        >
          <svg width="10" height="2" viewBox="0 0 10 2" fill="currentColor">
            <rect width="10" height="2" rx="1" />
          </svg>
        </button>

        {!compact && (
          <button
            type="button"
            data-tauri-drag-region="false"
            className="titlebar-action-btn"
            onClick={handleMaximize}
            title="Развернуть / Восстановить"
            aria-label="Развернуть"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="1" y="1" width="8" height="8" rx="1.5" />
            </svg>
          </button>
        )}

        <button
          type="button"
          data-tauri-drag-region="false"
          className="titlebar-action-btn close-btn"
          onClick={handleClose}
          title="Свернуть в трей"
          aria-label="Закрыть"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M1 1L9 9M9 1L1 9" strokeLinecap="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
