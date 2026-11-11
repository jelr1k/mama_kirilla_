import React, { useState, useEffect } from 'react';
import Home from './components/Home';
import Chat from './components/Chat';
import Commands from './components/Commands';
import Network from './components/Network';
import Aliases from './components/Aliases';
import Ollama from './components/Ollama';
import Workspace from './components/Workspace';
import Protocols from './components/Protocols';
import Settings from './components/Settings';
import { apiPost } from './services/api';
import HistoryModal from './components/HistoryModal';
import { Icon } from './components/Icons';
import { useAssistant } from './services/useAssistant';
import { ErrorBoundary } from './components/ErrorBoundary';
import TitleBar from './components/TitleBar';
import ConfirmModal from './components/ConfirmModal';
import IslandApp from './components/IslandApp';

const TABS = [
  { id: 'home', label: 'Главная', icon: 'home', component: Home },
  { id: 'chat', label: 'Чат', icon: 'chat', component: Chat },
  { id: 'network', label: 'Сеть', icon: 'shield', component: Network },
  { id: 'protocols', label: 'Протоколы', icon: 'zap', component: Protocols },
  { id: 'cmd', label: 'Команды', icon: 'cmd', component: Commands },
  { id: 'alias', label: 'Алиасы', icon: 'alias', component: Aliases },
  { id: 'ollama', label: 'Ollama и Тулы', icon: 'brain', component: Ollama },
  { id: 'workspace', label: 'Воркспейс', icon: 'workspace', component: Workspace },
  { id: 'set', label: 'Настройки', icon: 'set', component: Settings },
];

const readSavedIslandAnchor = () => {
  try {
    const raw = localStorage.getItem('kirieshcka_island_pos');
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.centerX === 'number' && typeof parsed?.y === 'number') {
      return {
        anchorCenterX: Math.round(parsed.centerX),
        anchorY: Math.round(parsed.y),
      };
    }
  } catch {
    return null;
  }
  return null;
};

export default function App() {
  const [activeTab, setActiveTab] = useState(0);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const [splashFading, setSplashFading] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => {
      setSplashFading(true);
    }, 700);
    const removeTimer = setTimeout(() => {
      setShowSplash(false);
    }, 1150);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(removeTimer);
    };
  }, []);
  const { connected, assistantName, appTitle } = useAssistant();
  const [compactMode, setCompactMode] = useState(false);
  const [islandEnabled, setIslandEnabled] = useState(() => {
    try {
      return localStorage.getItem('kirieshcka_island_enabled') === 'true';
    } catch {
      return false;
    }
  });
  const [showShutdownConfirm, setShowShutdownConfirm] = useState(false);
  const CurrentView = TABS[activeTab].component;

  useEffect(() => {
    if (!window.__TAURI_INTERNALS__) return undefined;
    let unlisten = null;
    const syncInitial = async () => {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const { listen } = await import('@tauri-apps/api/event');
        let initialEnabled = false;
        try {
          initialEnabled = localStorage.getItem('kirieshcka_island_enabled') === 'true';
        } catch {}
        if (initialEnabled) {
          await invoke('set_island_visible', {
            visible: true,
            ...(readSavedIslandAnchor() || {}),
          });
        }
        unlisten = await listen('island-visibility', (event) => {
          const next = Boolean(event.payload);
          setIslandEnabled(next);
          try {
            localStorage.setItem('kirieshcka_island_enabled', String(next));
          } catch {}
        });
      } catch (e) {
        console.warn('Failed to initialize island sync:', e);
      }
    };
    syncInitial();
    return () => {
      if (typeof unlisten === 'function') unlisten();
    };
  }, []);

  const handleToggleIsland = async () => {
    const next = !islandEnabled;
    setIslandEnabled(next);
    try {
      localStorage.setItem('kirieshcka_island_enabled', String(next));
    } catch {}
    if (window.__TAURI_INTERNALS__) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('set_island_visible', {
          visible: next,
          ...(next ? (readSavedIslandAnchor() || {}) : {}),
        });
      } catch (e) {
        console.warn('Failed to toggle island:', e);
      }
    }
  };

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

  useEffect(() => {
    window.scrollTo(0, 0);
    if (document.documentElement) document.documentElement.scrollTop = 0;
    if (document.body) document.body.scrollTop = 0;
  }, [activeTab]);

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

  const handleQuickExit = () => {
    setShowShutdownConfirm(true);
  };

  const handleConfirmShutdown = async () => {
    setShowShutdownConfirm(false);
    try {
      await apiPost('/api/shutdown');
    } catch (e) {}
    if (Boolean(window.__TAURI_INTERNALS__)) {
      try {
        const { getCurrentWindow } = await import('@tauri-apps/api/window');
        await getCurrentWindow().destroy();
      } catch (e) {
        window.close();
      }
    } else {
      window.close();
    }
  };

  const badgeLetters = displayName.slice(0, 2).toUpperCase();

  return (
    <div
      className={`app-shell ${compactMode ? 'compact-layout' : ''}`}
      onScroll={(e) => {
        if (e.currentTarget.scrollTop !== 0) e.currentTarget.scrollTop = 0;
        if (e.currentTarget.scrollLeft !== 0) e.currentTarget.scrollLeft = 0;
      }}
    >
      <TitleBar
        title={currentAppTitle}
        compact={compactMode}
        onToggleCompact={handleToggleCompact}
        islandEnabled={islandEnabled}
        onToggleIsland={handleToggleIsland}
        connected={connected}
      />
      <div className={`app ${compactMode ? 'compact-mode' : ''}`}>
        <nav className={`app-sidebar ${compactMode ? "collapsed" : ""}`} style={{ '--i': activeTab }}>
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

      <main>
        <ErrorBoundary resetKey={activeTab}>
          <CurrentView key={activeTab} />
        </ErrorBoundary>
      </main>

      </div>

      <HistoryModal isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />

      <ConfirmModal
        isOpen={showShutdownConfirm}
        title="Завершение работы"
        message={`Завершить работу ассистента ${displayName} и остановить фоновое ядро?`}
        confirmText="Завершить работу"
        cancelText="Отмена"
        isDanger={true}
        onConfirm={handleConfirmShutdown}
        onClose={() => setShowShutdownConfirm(false)}
      />

      {!window.__TAURI_INTERNALS__ && islandEnabled && (
        <IslandApp previewMode={true} onClosePreview={handleToggleIsland} />
      )}

      {showSplash && (
        <div className={`app-splash-overlay ${splashFading ? 'fading-out' : ''}`}>
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
