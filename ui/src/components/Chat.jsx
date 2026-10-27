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
    lastTranscript,
    lastResponse,
    currentChunk,
    isStreaming,
    sendChatMessage,
    startVoice,
    stopVoice,
  } = useAssistant();

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'assistant',
      text: 'Привет! Я готов к работе. Напиши команду, выбери из быстрых подсказок или нажми кнопку голосового ввода.',
      time: 'только что',
    },
  ]);
  const [input, setInput] = useState('');
  const [thinkingMode, setThinkingMode] = useState(false);
  const [wakeWordText, setWakeWordText] = useState('шпрота');
  const chatBottomRef = useRef(null);

  // Load wake word from settings
  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((data) => {
        const v = data.settings?.voice?.wake_word;
        if (v) setWakeWordText(v);
      })
      .catch(() => {});
  }, []);

  // Sync last transcript from voice into chat as user message
  const lastTranscriptRef = useRef('');
  useEffect(() => {
    if (lastTranscript && lastTranscript !== lastTranscriptRef.current) {
      lastTranscriptRef.current = lastTranscript;
      const userMsg = {
        id: Date.now(),
        sender: 'user',
        text: lastTranscript,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, userMsg]);
    }
  }, [lastTranscript]);

  // Sync assistant response into chat
  const lastResponseRef = useRef('');
  useEffect(() => {
    if (lastResponse && lastResponse !== lastResponseRef.current) {
      lastResponseRef.current = lastResponse;
      const assistMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: lastResponse,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistMsg]);
    }
  }, [lastResponse]);

  // Scroll to bottom when messages or chunks update
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentChunk, status]);

  const handleSend = (textToSend = input) => {
    const text = textToSend.trim();
    if (!text) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');

    sendChatMessage(text, thinkingMode);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
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

          <button
            className="btn-clear-chat"
            onClick={handleClearChat}
            title="Очистить историю сообщений на экране"
          >
            <Icon name="trash" />
            <span>Очистить</span>
          </button>
        </div>

        {/* Message Stream */}
        <div className="chat-messages-container">
          {messages.map((m) => (
            <MessageBubble key={m.id} msg={m} assistantName={assistantName} />
          ))}

          {/* Real-time Streaming Chunk Bubble */}
          {status === 'think' && isStreaming && currentChunk && (
            <div className="chat-message assistant-msg streaming">
              <div className="message-sender-row">
                <span className="sender-badge">{assistantName || 'Kirieshcka'}</span>
                <span className="streaming-indicator">печатает...</span>
              </div>
              <div className="message-body">
                {currentChunk}
                <span className="chat-cursor" />
              </div>
            </div>
          )}

          {status === 'think' && !currentChunk && (
            <div className="thinking-indicator-row">
              <div className="thinking-dots">
                <span />
                <span />
                <span />
              </div>
              <span className="thinking-label">Нейромодуль обдумывает ответ...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Quick Prompts Chips Bar */}
        <div className="chat-quick-chips">
          <div className="chips-label">Быстрые команды:</div>
          <div className="chips-scroll">
            {QUICK_COMMANDS.map((q, idx) => (
              <button
                key={idx}
                className="quick-chip-btn"
                onClick={() => handleSend(q.cmd)}
                title={`Отправить «${q.cmd}»`}
              >
                <Icon name={q.icon} />
                <span>{q.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="chat-input-bar">
          <textarea
            className="chat-textarea"
            placeholder="Спроси что угодно, введи команду или используй голосовой ввод (Enter — отправить)..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
          />

          <div className="chat-input-actions">
            <button
              className={`btn-thinking-toggle ${thinkingMode ? 'active' : ''}`}
              onClick={() => setThinkingMode(!thinkingMode)}
              title="Включает режим глубокого раздумывания для сложных запросов (DeepSeek/Qwen Thinking)"
            >
              <Icon name="brain" />
              <span>Размышление</span>
            </button>

            <button
              className={`btn-voice-stt ${status === 'listen' ? 'recording' : ''}`}
              onClick={handleVoiceToggle}
              title={status === 'listen' ? 'Остановить запись и распознать' : 'Начать голосовой ввод (микрофон)'}
            >
              <Icon name="mic" />
              <span>{status === 'listen' ? 'Стоп' : 'Голос'}</span>
            </button>

            <button
              className="btn-send-message"
              onClick={() => handleSend()}
              disabled={!input.trim()}
              title="Отправить сообщение"
            >
              <Icon name="zap" />
              <span>Отправить</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
