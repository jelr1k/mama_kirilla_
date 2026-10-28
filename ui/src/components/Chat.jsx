import { apiFetch } from '../services/api';
import React, { useState, useEffect, useRef } from 'react';
import { Icon } from './Icons';
import { useAssistant } from '../services/useAssistant';

const QUICK_COMMANDS = [
  { label: 'Нагрузка', cmd: 'телеметрия', icon: 'cpu' },
  { label: 'Скриншот', cmd: 'сделай скриншот', icon: 'camera' },
  { label: 'Корзина', cmd: 'очисти корзину', icon: 'trash' },
  { label: 'Время', cmd: 'сколько времени', icon: 'clock' },
  { label: 'YouTube', cmd: 'открой ютуб', icon: 'web' },
  { label: 'Загрузки', cmd: 'открой загрузки', icon: 'folder' },
  { label: 'Блок ПК', cmd: 'заблокируй пк', icon: 'lock' },
  { label: 'Выгрузить', cmd: 'выгрузи модель', icon: 'zap' },
];

function MessageBubble({ msg, assistantName }) {
  const isUser = msg.sender === 'user';
  const [showThinking, setShowThinking] = useState(false);

  // Check if message text has thinking blocks <think>...</think>
  let thinkingContent = '';
  let cleanContent = msg.text || '';

  const thinkMatch = cleanContent.match(/<think>([\s\S]*?)<\/think>/i);
  if (thinkMatch) {
    thinkingContent = thinkMatch[1].trim();
    cleanContent = cleanContent.replace(/<think>[\s\S]*?<\/think>/i, '').trim();
  }

  return (
    <div className={`chat-message ${isUser ? 'user-msg' : 'assistant-msg'}`}>
      <div className="message-sender-row">
        <span className="sender-badge">{isUser ? 'Вы' : (assistantName || 'Kirieshcka')}</span>
        <span className="message-time">{msg.time}</span>
      </div>

      {thinkingContent && (
        <div className="thinking-block">
          <button
            className="thinking-toggle-btn"
            onClick={() => setShowThinking(!showThinking)}
          >
            <Icon name="brain" />
            <span>Размышление модели</span>
            <span className="thinking-arrow">{showThinking ? '▲ Свернуть' : '▼ Раскрыть'}</span>
          </button>
          {showThinking && (
            <div className="thinking-text">
              {thinkingContent}
            </div>
          )}
        </div>
      )}

      <div className="message-body">
        {cleanContent || (msg.isStreaming ? '...' : '')}
      </div>
    </div>
  );
}

export default function Chat() {
  const {
    connected,
    status,
    assistantName,
    model,
    voskText,
    currentChunk,
    isStreaming,
    messages,
    sendChatMessage,
    clearChatMessages,
    startVoice,
    stopVoice,
  } = useAssistant();

  const [input, setInput] = useState('');
  const [thinkingMode, setThinkingMode] = useState(false);
  const [wakeWordText, setWakeWordText] = useState('шпрота');
  const chatBottomRef = useRef(null);

  // Load wake word from settings
  useEffect(() => {
    apiFetch('/api/settings')
      .then((r) => r.json())
      .then((data) => {
        const v = data.settings?.voice?.wake_word;
        if (v) setWakeWordText(v);
      })
      .catch(() => {});
  }, []);

  // Scroll to bottom when messages or chunks update
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentChunk, status]);

  const handleSend = (textToSend = input) => {
    const text = textToSend.trim();
    if (!text) return;
    setInput('');
    sendChatMessage(text, thinkingMode);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleVoiceToggle = () => {
    if (status === 'listen') {
      stopVoice();
    } else {
      startVoice();
    }
  };

  const getVoiceStatusBadge = () => {
    if (!connected) return { text: 'Офлайн', color: 'offline' };
    if (status === 'listen') return { text: 'Слушаю вас...', color: 'listening' };
    if (status === 'think') return { text: 'Обработка...', color: 'thinking' };
    if (status === 'speak') return { text: 'Озвучивание...', color: 'speaking' };
    return { text: 'Голос: готов', color: 'ready' };
  };

  const voiceBadge = getVoiceStatusBadge();

  return (
    <div className="page standard-page chat-full-page">
      <div className="chat-layout-wrapper">
        {/* Top HUD Bar */}
        <div className="chat-hud-bar">
          <div className="hud-left-items">
            <span className={`hud-badge ${voiceBadge.color}`}>
              <span className="dot" />
              <span>{voiceBadge.text}</span>
            </span>

            <span className="hud-badge model" title="Активная модель">
              <Icon name="brain" />
              <span>{model || 'Локальное ядро'}</span>
            </span>

            <span className="hud-badge wakeword" title="Активационное слово">
              <Icon name="mic" />
              <span>Wake: «{wakeWordText}»</span>
            </span>

            <span
              className="hud-vosk-ticker"
              title="Последний текст, который распознал Vosk в реальном времени при ожидании wake word"
            >
              Vosk: <strong className="vosk-text">{voskText ? `«${voskText}»` : '—'}</strong>
            </span>
          </div>

          <div className="hud-right-items">
            <button
              className="btn-chat-clear"
              onClick={clearChatMessages}
              title="Очистить историю сообщений"
            >
              <Icon name="trash" />
              <span>Очистить</span>
            </button>
          </div>
        </div>

        {/* Messages Stream Container */}
        <div className="chat-messages-scroll-area">
          {messages.map((m) => (
            <MessageBubble key={m.id} msg={m} assistantName={assistantName} />
          ))}

          {/* Streaming Chunk (Live token by token generation) */}
          {isStreaming && currentChunk && (
            <div className="chat-message assistant-msg streaming">
              <div className="message-sender-row">
                <span className="sender-badge">{assistantName || 'Kirieshcka'}</span>
                <span className="message-time">генерация...</span>
              </div>
              <div className="message-body stream-text">
                {currentChunk}
                <span className="cursor-blink">▌</span>
              </div>
            </div>
          )}

          {/* Thinking spinner if model is loading without chunks yet */}
          {status === 'think' && !currentChunk && (
            <div className="chat-message assistant-msg thinking-indicator">
              <div className="typing-dots">
                <span />
                <span />
                <span />
              </div>
              <span className="thinking-lbl">Ассистент думает...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Quick Command Chips Toolbar */}
        <div className="chat-quick-chips">
          {QUICK_COMMANDS.map((qc, idx) => (
            <button
              key={idx}
              className="quick-chip-btn"
              onClick={() => handleSend(qc.cmd)}
              title={`Быстрая команда: «${qc.cmd}»`}
            >
              <Icon name={qc.icon} />
              <span>{qc.label}</span>
            </button>
          ))}
        </div>

        {/* Chat Input Console Bar */}
        <div className="chat-input-bar">
          <button
            type="button"
            className={`btn-chat-mic ${status === 'listen' ? 'recording' : ''}`}
            onClick={handleVoiceToggle}
            title={status === 'listen' ? 'Остановить запись' : 'Голосовой ввод'}
          >
            <Icon name={status === 'listen' ? 'check' : 'mic'} />
          </button>

          <div className="input-field-wrap">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Введите команду или вопрос ассистенту... [Enter для отправки]"
              className="chat-textarea"
            />
          </div>

          <button
            type="button"
            className={`btn-thinking-toggle ${thinkingMode ? 'active' : ''}`}
            onClick={() => setThinkingMode(!thinkingMode)}
            title="Режим размышлений (DeepSeek R1 / Reasoning chain)"
          >
            <Icon name="brain" />
            <span className="thinking-tag">Рассуждения</span>
          </button>

          <button
            type="button"
            className="btn-chat-send"
            onClick={() => handleSend()}
            disabled={!input.trim()}
            title="Отправить сообщение (Enter)"
          >
            <Icon name="play" />
          </button>
        </div>
      </div>
    </div>
  );
}
