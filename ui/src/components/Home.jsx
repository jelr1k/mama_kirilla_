import React, { useState, useEffect, useRef } from 'react';
import { Icon } from './Icons';
import { useAssistant } from '../services/useAssistant';

const LABELS = {
  idle: 'Жду команду',
  listen: 'Слушаю вас...',
  think: 'Анализирую...',
  speak: 'Отвечаю...',
};

const HOME_QUICK_ACTIONS = [
  { label: 'Телеметрия', cmd: 'телеметрия', icon: 'cpu' },
  { label: 'Скриншот', cmd: 'сделай скриншот', icon: 'camera' },
  { label: 'Очистить корзину', cmd: 'очисти корзину', icon: 'trash' },
  { label: 'Сколько времени', cmd: 'сколько времени', icon: 'clock' },
  { label: 'Открыть YouTube', cmd: 'открой ютуб', icon: 'web' },
];

export default function Home() {
  const {
    connected,
    status,
    assistantName,
    model,
    voskText,
    telemetry,
    lastTranscript,
    lastResponse,
    currentChunk,
    sendChatMessage,
    startVoice,
    stopVoice,
  } = useAssistant();

  const [quickInput, setQuickInput] = useState('');

  const handleQuickSend = (e) => {
    e.preventDefault();
    const text = quickInput.trim();
    if (!text) return;
    sendChatMessage(text);
    setQuickInput('');
  };

  const handleOrbClick = () => {
    if (status === 'listen') {
      stopVoice();
    } else {
      startVoice();
    }
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        handleOrbClick();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [status]);

  const getSubtitle = () => {
    if (!connected) {
      return 'Ожидание подключения к ядру Python (127.0.0.1:8765)...';
    }
    if (status === 'listen') {
      return 'Говорите, микрофон активен...';
    }
    if (status === 'think') {
      return lastTranscript ? `«${lastTranscript}»` : 'Нейромодуль обрабатывает запрос...';
    }
    if (status === 'speak') {
      return currentChunk || lastResponse || 'Воспроизведение ответа...';
    }
    return 'Нажмите [Пробел] или кликните по ядру для голосового ввода';
  };

  return (
    <div className="page home-page">
      <div className="home-content">
        <header className="home-header">
          <div className="home-badge">
            <span className={`pulse-indicator ${connected ? 'online' : 'connecting'}`} />
            <span>{(assistantName || 'Kirieshcka').toUpperCase()} CORE V2</span>
          </div>
          <span className="home-subtitle">ЛОКАЛЬНЫЙ ГОЛОСОВОЙ АССИСТЕНТ</span>

          {/* Live Vosk Speech Recognition Ticker */}
          <div
            className="home-vosk-ticker"
            title="Текст, который непрерывно распознает локальный движок Vosk"
          >
            <span className="vosk-tag">Vosk STT</span>
            <span className="vosk-val">{voskText ? `«${voskText}»` : 'Ожидание триггерного слова...'}</span>
          </div>
        </header>

        <div className="home-center">
          <button
            className="orb"
            data-s={status}
            onClick={handleOrbClick}
            aria-label="Активация микрофона"
            title={status === 'listen' ? 'Остановить запись' : 'Кликните для голосового ввода'}
          >
            <span className="ring ring-1" />
            <span className="ring ring-2" />
            <span className="ring ring-3" />
            <span className="core" />
            <div className="orb-hover-hint">
              <Icon name={status === 'listen' ? 'check' : 'mic'} />
            </div>
          </button>

          <div className="status-block">
            <h1 className="label" data-s={status}>
              {LABELS[status] || LABELS.idle}
            </h1>

            {/* Mini-Chat Dialog Box right under the core */}
            <div className="home-mini-dialog">
              {lastTranscript && (
                <div className="mini-bubble user-mini">
                  <span className="mini-sender">Вы:</span>
                  <span className="mini-text">«{lastTranscript}»</span>
                </div>
              )}

              {(currentChunk || lastResponse || status === 'think') && (
                <div className="mini-bubble bot-mini">
                  <span className="mini-sender">{assistantName || 'Kirieshcka'}:</span>
                  <span className="mini-text">
                    {status === 'think' && !currentChunk
                      ? 'Нейромодуль думает над ответом...'
                      : (currentChunk || lastResponse)}
                  </span>
                </div>
              )}

              {!lastTranscript && !lastResponse && !currentChunk && (
                <p className="status-sub">
                  {getSubtitle()}
                </p>
              )}

              {/* Quick Text Input for home page */}
              <form className="home-quick-input-form" onSubmit={handleQuickSend}>
                <input
                  type="text"
                  className="home-quick-input"
                  placeholder="Быстрый вопрос или команда ассистенту..."
                  value={quickInput}
                  onChange={(e) => setQuickInput(e.target.value)}
                />
                <button
                  type="submit"
                  className="home-quick-send-btn"
                  title="Отправить (Enter)"
                  disabled={!quickInput.trim()}
                >
                  <Icon name="play" style={{ width: '14px', height: '14px' }} />
                </button>
              </form>
            </div>
          </div>

          <div className="wave" data-s={status}>
            {Array.from({ length: 36 }, (_, k) => (
              <i key={k} style={{ '--k': k }} />
            ))}
          </div>

          {/* Home Quick Actions */}
          <div className="home-quick-actions">
            {HOME_QUICK_ACTIONS.map((action, i) => (
              <button
                key={i}
                className="home-action-btn"
                onClick={() => sendChatMessage(action.cmd)}
                title={`Выполнить «${action.cmd}»`}
              >
                <Icon name={action.icon} />
                <span>{action.label}</span>
              </button>
            ))}
          </div>
        </div>

        <footer className="home-widgets">
          <div className="widget-card">
            <div className="widget-icon">
              <Icon name="mic" />
            </div>
            <div className="widget-info">
              <div className="widget-title">Голосовой триггер</div>
              <div className="widget-desc">
                {connected ? `Активация: «${(assistantName || 'Кириешка')}»` : 'Поиск бэкенда...'}
              </div>
            </div>
          </div>

          <div className="widget-card">
            <div className="widget-icon">
              <Icon name="cpu" />
            </div>
            <div className="widget-info">
              <div className="widget-title">Система и память</div>
              <div className="widget-desc">
                {telemetry && telemetry.cpu_percent !== undefined
                  ? `ЦП: ${telemetry.cpu_percent}% • ОЗУ: ${telemetry.ram_used_gb}/${telemetry.ram_total_gb} ГБ`
                  : 'Загрузка телеметрии...'}
              </div>
            </div>
          </div>

          <div className="widget-card">
            <div className="widget-icon">
              <Icon name="brain" />
            </div>
            <div className="widget-info">
              <div className="widget-title">Модель ИИ</div>
              <div className="widget-desc">
                {model ? `${model} (Локально)` : 'qwen3:1.7b'}
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
