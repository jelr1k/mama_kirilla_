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
  const { connected, assistantName } = useAssistant();
  const CurrentView = TABS[activeTab].component;

  const displayName = assistantName || 'Kirieshcka';

  useEffect(() => {
    document.title = `${displayName} v2`;
  }, [displayName]);

  const handleQuickExit = async () => {
    if (!window.confirm(`Завершить работу ${displayName} v2?`)) return;
    try {
      await fetch('/api/shutdown', { method: 'POST' });
    } catch (e) {}
    window.close();
  };

  const badgeLetters = displayName.slice(0, 2).toUpperCase();

  return (
    <div className="app">
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

      <main>
        <CurrentView key={activeTab} />
      </main>

      <HistoryModal isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />
    </div>
  );
}
