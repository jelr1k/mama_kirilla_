import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, MotionConfig } from 'framer-motion';
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
import MotionStudioApp from './motion/MotionStudioApp';

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

const migrateLegacyStorage = () => {
  try {
    const pairs = [
      ['kirieshcka_island_pos', 'assistant_island_pos'],
      ['kirieshcka_theme', 'assistant_theme'],
      ['kirieshcka_island_enabled', 'assistant_island_enabled'],
    ];
    for (const [legacyKey, nextKey] of pairs) {
      const legacyVal = localStorage.getItem(legacyKey);
      if (legacyVal !== null) {
        if (localStorage.getItem(nextKey) === null) {
          localStorage.setItem(nextKey, legacyVal);
        }
        localStorage.removeItem(legacyKey);
      }
    }
  } catch {}
};

migrateLegacyStorage();

const readSavedIslandAnchor = () => {
  try {
    const raw = localStorage.getItem('assistant_island_pos');
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
  const [uiMode, setUiMode] = useState(() => {
    try {
      return localStorage.getItem('assistant_ui_mode') || 'classic';
    } catch {
      return 'classic';
    }
  });

  useEffect(() => {
    const onUiModeChange = (e) => {
      const next = e?.detail || 'classic';
      setUiMode(next);
    };
    const onStorage = (e) => {
      if (e.key === 'assistant_ui_mode') {
        setUiMode(e.newValue || 'classic');
      }
    };
    window.addEventListener('assistant-ui-mode-change', onUiModeChange);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('assistant-ui-mode-change', onUiModeChange);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('assistant_theme') || 'dark';
      document.documentElement.setAttribute('data-theme', savedTheme);
      if (document.body) {
        document.body.setAttribute('data-theme', savedTheme);
      }
    } catch {}
  }, []);

  const { connected, assistantName, appTitle } = useAssistant();
  const [compactMode, setCompactMode] = useState(false);
  const [islandEnabled, setIslandEnabled] = useState(() => {
    try {
      return localStorage.getItem('assistant_island_enabled') === 'true';
    } catch {
      return false;
    }
  });
  const [showShutdownConfirm, setShowShutdownConfirm] = useState(false);
  const CurrentView = TABS[activeTab].component;

  useEffect(() => {
    if (!window.__TAURI_INTERNALS__) return undefined;
    let unlisten = null;
    let disposed = false;
    const syncInitial = async () => {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const { listen } = await import('@tauri-apps/api/event');
        const un = await listen('island-visibility', (event) => {
          if (disposed) return;
          const next = Boolean(event.payload);
          setIslandEnabled(next);
          try {
            localStorage.setItem('assistant_island_enabled', String(next));
          } catch {}
        });
        if (disposed) {
          un();
          return;
        }
        unlisten = un;

        let initialEnabled = false;
        try {
          initialEnabled = localStorage.getItem('assistant_island_enabled') === 'true';
        } catch {}
        if (initialEnabled) {
          await invoke('set_island_visible', {
            visible: true,
            ...(readSavedIslandAnchor() || {}),
          });
        } else {
          const actualVisible = await invoke('get_island_visible');
          if (!disposed && Boolean(actualVisible) !== initialEnabled) {
            setIslandEnabled(Boolean(actualVisible));
          }
        }
      } catch (e) {
        console.warn('Failed to initialize island sync:', e);
        if (!disposed) {
          setIslandEnabled(false);
        }
      }
    };
    syncInitial();
    return () => {
      disposed = true;
      if (typeof unlisten === 'function') unlisten();
    };
  }, []);

  const handleToggleIsland = async () => {
    let next = !islandEnabled;
    if (window.__TAURI_INTERNALS__) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const currentlyVisible = await invoke('get_island_visible');
        next = !currentlyVisible;
        setIslandEnabled(next);
        try {
          localStorage.setItem('assistant_island_enabled', String(next));
        } catch {}
        await invoke('set_island_visible', {
          visible: next,
          ...(next ? (readSavedIslandAnchor() || {}) : {}),
        });
      } catch (e) {
        console.warn('Failed to toggle island:', e);
        setIslandEnabled(!next);
        try {
          localStorage.setItem('assistant_island_enabled', String(!next));
        } catch {}
      }
      return;
    }

    setIslandEnabled(next);
    try {
      localStorage.setItem('assistant_island_enabled', String(next));
    } catch {}
  };

  const displayName = assistantName || 'Assistant';
  const currentAppTitle = appTitle || displayName;

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
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('exit_application');
      } catch (e) {
        window.close();
      }
    } else {
      window.close();
    }
  };

  const badgeLetters = displayName.slice(0, 2).toUpperCase();

  const handleSwitchToClassic = () => {
    setUiMode('classic');
    try {
      localStorage.setItem('assistant_ui_mode', 'classic');
    } catch {}
  };

  if (uiMode === 'motion') {
    return (
      <ErrorBoundary resetKey="motion-studio">
        <MotionStudioApp
          assistantName={displayName}
          onSwitchToClassic={handleSwitchToClassic}
        />
      </ErrorBoundary>
    );
  }

  return (
    <MotionConfig reducedMotion="user">
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
            <motion.button
              key={tab.id}
              className={`nav-tab-btn ${i === activeTab ? 'on' : ''}`}
              onClick={() => setActiveTab(i)}
              aria-label={tab.label}
              title={tab.label}
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.92 }}
              transition={{ type: 'spring', stiffness: 500, damping: 28 }}
            >
              <Icon name={tab.icon} />
              <span className="nav-tab-label">{tab.label}</span>
            </motion.button>
          ))}
        </div>

        <div className="nav-footer">
          <motion.button
            className="btn-history-tray"
            onClick={() => setIsHistoryOpen(true)}
            title="Журнал активности (История)"
            aria-label="История"
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 500, damping: 28 }}
          >
            <Icon name="hist" />
          </motion.button>
          <motion.button
            className="btn-exit-tray"
            onClick={handleQuickExit}
            title="Завершить работу ассистента"
            aria-label="Выход"
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 500, damping: 28 }}
          >
            <Icon name="exit" />
          </motion.button>
          <span className="nav-ver">v2.0</span>
        </div>
      </nav>

      <main>
        <ErrorBoundary resetKey={activeTab}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10, scale: 0.992 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.992 }}
              transition={{ type: 'spring', stiffness: 420, damping: 32, mass: 0.75 }}
              style={{ height: '100%' }}
            >
              <CurrentView />
            </motion.div>
          </AnimatePresence>
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
    </div>
    </MotionConfig>
  );
}
