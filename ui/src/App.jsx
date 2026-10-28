import React, { useState, useEffect } from 'react';
import Home from './components/Home';
import Chat from './components/Chat';
import Commands from './components/Commands';
import Aliases from './components/Aliases';
import Ollama from './components/Ollama';
import Workspace from './components/Workspace';
import Settings from './components/Settings';
import HistoryModal from './components/HistoryModal';
import { Icon } from './components/Icons';
import { useAssistant } from './services/useAssistant';
import { ErrorBoundary } from './components/ErrorBoundary';
import TitleBar from './components/TitleBar';

const TABS = [
  { id: 'home', label: 'Главная', icon: 'home', component: Home },
  { id: 'chat', label: 'Чат', icon: 'chat', component: Chat },
  { id: 'cmd', label: 'Команды', icon: 'cmd', component: Commands },
  { id: 'alias', label: 'Алиасы', icon: 'alias', component: Aliases },
  { id: 'ollama', label: 'Ollama и Тулы', icon: 'brain', component: Ollama },
  { id: 'workspace', label: 'Воркспейс', icon: 'workspace', component: Workspace },
  { id: 'set', label: 'Настройки', icon: 'set', component: Settings },
];

export default function App() {
  const [activeTab, setActiveTab] = useState(0);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 900);
    return () => clearTimeout(timer);
  }, []);
  const { connected, assistantName, appTitle } = useAssistant();
  const [compactMode, setCompactMode] = useState(false);
  const CurrentView = TABS[activeTab].component;

  const displayName = assistantName || 'Kirieshcka';
  const currentAppTitle = appTitle || `${displayName} v2`;

  useEffect(() => {
    document.title = currentAppTitle;
    if (Boolean(window.__TAURI_INTERNALS__)) {
      import('@tauri-apps/api/window').then(({ getCurrentWindow }) => {
        getCurrentWindow().setTitle(currentAppTitle).catch(() => {});
      }).catch(() => {});
    }
  }, [currentAppTitle]);

  const handleToggleCompact = async () => {
    const nextCompact = !compactMode;
    setCompactMode(nextCompact);
    if (nextCompact) {
      setActiveTab(0);
    }
    if (Boolean(window.__TAURI_INTERNALS__)) {
      try {
        const { getCurrentWindow, LogicalSize } = await import('@tauri-apps/api/window');
        const win = getCurrentWindow();
        if (nextCompact) {
          await win.setSize(new LogicalSize(390, 620));
        } else {
          await win.setSize(new LogicalSize(1120, 760));
        }
      } catch (e) {
        console.warn('Failed to resize window:', e);
      }
    }
  };

  const handleQuickExit = async () => {
    if (!window.confirm(`Завершить работу ${displayName} v2?`)) return;
    try {
      await fetch('/api/shutdown', { method: 'POST' });
    } catch (e) {}
    window.close();
  };

  const badgeLetters = displayName.slice(0, 2).toUpperCase();

  return (
    <div className={`app-shell ${compactMode ? 'compact-layout' : ''}`}>
      <TitleBar
        title={currentAppTitle}
        compact={compactMode}
        onToggleCompact={handleToggleCompact}
        connected={connected}
      />
      <div className={`app ${compactMode ? 'compact-mode' : ''}`}>
        {!compactMode && (
          <nav style={{ '--i': activeTab }}>
        <div
          className="nav-logo"
          title={
            connected
              ? `${displayName} v2 (Подключено к ядру)`
              : `${displayName} v2 (Офлайн / Поиск ядра)`
          }
        >
          <div className="nav-logo-badge">{badgeLetters}</div>
          <span className={`nav-status-dot ${connected ? 'online' : 'offline'}`} />
        </div>

        <div className="nav-items">
          <span className="ind" />
          {TABS.map((tab, i) => (
            <button
              key={tab.id}
              className={`nav-tab-btn ${i === activeTab ? 'on' : ''}`}
              onClick={() => setActiveTab(i)}
              aria-label={tab.label}
              title={tab.label}
            >
              <Icon name={tab.icon} />
              <span className="nav-tab-label">{tab.label}</span>
            </button>
          ))}
        </div>

        <div className="nav-footer">
          <button
            className="btn-history-tray"
            onClick={() => setIsHistoryOpen(true)}
            title="Журнал активности (История)"
            aria-label="История"
          >
            <Icon name="hist" />
          </button>
          <button
            className="btn-exit-tray"
            onClick={handleQuickExit}
            title="Завершить работу ассистента"
            aria-label="Выход"
          >
            <Icon name="exit" />
          </button>
          <span className="nav-ver">v2.0</span>
        </div>
      </nav>
        )}

      <main>
        <ErrorBoundary resetKey={activeTab}>
          <CurrentView key={activeTab} />
        </ErrorBoundary>
      </main>

      </div>

      <HistoryModal isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />

      {showSplash && (
        <div className="app-splash-overlay">
          <div className="splash-logo-container">
            <div className="splash-spinning-ring outer" />
            <div className="splash-spinning-ring" />
            <div className="splash-badge-core">{badgeLetters}</div>
          </div>
          <div className="splash-title">{(displayName || 'KIRIESHCKA').toUpperCase()} V2</div>
          <div className="splash-subtitle">
            {connected ? 'Ядро подключено, запуск интерфейса...' : 'Синхронизация служб и модулей...'}
          </div>
        </div>
      )}
    </div>
  );
}
