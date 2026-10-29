/**
 * Real-time WebSocket bridge between Kirieshcka v2 UI and Python Core.
 */
class AssistantSocket {
  constructor(url = 'ws://127.0.0.1:8765/ws') {
    this.url = url;
    this.ws = null;
    this.listeners = new Map();
    this.reconnectDelay = 1500;
    this.maxReconnectDelay = 10000;
    this.currentDelay = this.reconnectDelay;
    this.reconnectTimer = null;
    this.isConnected = false;
    this.speakTimeout = null;
    this.isTtsActive = false;

    this.state = {
      connected: false,
      status: 'idle', // 'idle' | 'listen' | 'think' | 'speak'
      assistantName: 'Kirieshcka',
      appTitle: 'Kirieshcka v2',
      model: '',
      telemetry: null,
      voskText: '',
      lastTranscript: '',
      lastResponse: '',
      lastResponseId: null,
      isStreaming: false,
      currentChunk: '',
      error: null,
    };

    this.messages = this._loadStoredMessages();
  }

  _clearSpeakTimeout() {
    if (this.speakTimeout) {
      clearTimeout(this.speakTimeout);
      this.speakTimeout = null;
    }
  }

  _triggerSpeakState(text = '') {
    this._clearSpeakTimeout();
    const cleanText = typeof text === 'string' ? text.trim() : '';
    this._updateState({
      status: 'speak',
      lastResponse: cleanText || this.state.lastResponse,
      lastResponseId: Date.now() + Math.random(),
      currentChunk: '',
      isStreaming: false,
    });

    // Reading animation duration when TTS is disabled:
    // Minimum 2200ms, ~45ms per character, capped at 6000ms.
    // If real TTS activates ('tts.state' -> 'speaking'), this timeout is cancelled.
    const charLen = cleanText ? cleanText.length : 20;
    const duration = Math.min(Math.max(2200, charLen * 45), 6000);

    this.speakTimeout = setTimeout(() => {
      this.speakTimeout = null;
      if (!this.isTtsActive && this.state.status === 'speak') {
        this._updateState({ status: 'idle' });
      }
    }, duration);
  }

  _loadStoredMessages() {
    try {
      const raw = localStorage.getItem('kirieshcka_chat_messages_v2');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {}
    return [
      {
        id: 1,
        sender: 'assistant',
        text: 'Привет! Я готов к работе. Напиши команду, выбери из быстрых подсказок или нажми кнопку голосового ввода.',
        time: 'только что',
      },
    ];
  }

  getMessages() {
    return this.messages;
  }

  addChatMessage(msg) {
    if (!msg || !msg.text) return;
    const text = String(msg.text).trim();
    if (!text) return;

    // Check last message to prevent rapid duplicates
    const last = this.messages[this.messages.length - 1];
    if (last && last.sender === msg.sender && last.text === text) {
      return;
    }

    const fullMsg = {
      id: Date.now() + Math.random(),
      sender: msg.sender || 'assistant',
      text: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    this.messages = [...this.messages, fullMsg];
    if (this.messages.length > 100) {
      this.messages = this.messages.slice(-100);
    }

    try {
      localStorage.setItem('kirieshcka_chat_messages_v2', JSON.stringify(this.messages));
    } catch (e) {}

    this._emit('messages_change', this.messages);
  }

  clearChatMessages() {
    const fresh = [
      {
        id: Date.now(),
        sender: 'assistant',
        text: 'История диалога очищена. Чем могу помочь?',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];
    this.messages = fresh;
    try {
      localStorage.setItem('kirieshcka_chat_messages_v2', JSON.stringify(fresh));
    } catch (e) {}
    this._emit('messages_change', this.messages);
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);
    } catch (err) {
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.isConnected = true;
      this.currentDelay = this.reconnectDelay;
      this._updateState({ connected: true, error: null });
      this._emit('connection_change', true);
    };

    this.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        this._handleMessage(payload);
      } catch (err) {
        console.warn('Failed to parse websocket message:', err);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this._clearSpeakTimeout();
      this.isTtsActive = false;
      this._updateState({ connected: false, status: 'idle' });
      this._emit('connection_change', false);
      this._scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      this._emit('error', err);
    };
  }

  _scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.currentDelay = Math.min(this.currentDelay * 1.5, this.maxReconnectDelay);
      this.connect();
    }, this.currentDelay);
  }

  _handleMessage(payload) {
    const type = payload.type;

    if (type === 'show_window') {
      if (Boolean(window.__TAURI_INTERNALS__)) {
        import('@tauri-apps/api/window').then(async ({ getCurrentWindow }) => {
          const win = getCurrentWindow();
          await win.show();
          await win.unminimize();
          await win.setFocus();
        }).catch(() => {});
      }
      return;
    }

    if (type === 'state') {
      this._updateState({
        assistantName: payload.assistant_name || this.state.assistantName,
        appTitle: payload.app_title || this.state.appTitle,
        model: payload.model || this.state.model,
        telemetry: payload.telemetry || this.state.telemetry,
      });
    } else if (type === 'telemetry') {
      this._updateState({ telemetry: payload.data });
    } else if (type === 'wake_word.recognized') {
      const raw = (payload.text || '').trim();
      const words = raw.split(/\s+/).filter(Boolean);
      const trimmed = words.length > 7 ? '... ' + words.slice(-7).join(' ') : words.join(' ');
      this._updateState({ voskText: trimmed });
    } else if (type === 'wake_word.detected') {
      this._clearSpeakTimeout();
      this.isTtsActive = false;
      this._updateState({ status: 'listen', lastTranscript: '' });
    } else if (type === 'voice.status') {
      if (payload.status === 'listening') {
        this._clearSpeakTimeout();
        this.isTtsActive = false;
        this._updateState({ status: 'listen' });
      }
    } else if (type === 'voice.listening') {
      if (payload.active) {
        this._clearSpeakTimeout();
        this.isTtsActive = false;
        this._updateState({ status: 'listen' });
      } else if (this.state.status === 'listen') {
        this._updateState({ status: 'idle' });
      }
    } else if (type === 'voice.transcribing') {
      if (payload.active) {
        this._clearSpeakTimeout();
        this.isTtsActive = false;
        this._updateState({ status: 'think' });
      }
    } else if (type === 'voice.transcription') {
      this._updateState({ lastTranscript: payload.text });
      if (payload.text) {
        this.addChatMessage({ sender: 'user', text: payload.text });
      }
    } else if (type === 'chat.status') {
      if (payload.status === 'thinking') {
        this._clearSpeakTimeout();
        this.isTtsActive = false;
        this._updateState({ status: 'think', isStreaming: true, currentChunk: '' });
      } else if (payload.status === 'idle') {
        const finalChunk = (this.state.currentChunk || '').trim();
        if (finalChunk && this.state.status === 'think' && !this.speakTimeout) {
          this._triggerSpeakState(finalChunk);
          this.addChatMessage({ sender: 'assistant', text: finalChunk });
        } else {
          const patch = { isStreaming: false, currentChunk: '' };
          if (!this.speakTimeout && !this.isTtsActive && this.state.status !== 'speak') {
            patch.status = 'idle';
          }
          this._updateState(patch);
        }
      }
    } else if (type === 'chat.chunk') {
      const text = payload.chunk || payload.text || '';
      this._updateState({
        currentChunk: (this.state.currentChunk || '') + text,
      });
    } else if (type === 'chat.response') {
      const respText = typeof payload.text === 'string' ? payload.text : String(payload.text || '');
      this._triggerSpeakState(respText);
      if (respText) {
        this.addChatMessage({ sender: 'assistant', text: respText });
      }
    } else if (type === 'tts.state') {
      if (payload.state === 'speaking' || payload.state === 'synthesizing') {
        this._clearSpeakTimeout();
        this.isTtsActive = true;
        this._updateState({ status: 'speak' });
      } else if (payload.state === 'idle') {
        this._clearSpeakTimeout();
        this.isTtsActive = false;
        this._updateState({ status: 'idle' });
      }
    } else if (type === 'chat.error' || type === 'voice.error') {
      this._clearSpeakTimeout();
      this.isTtsActive = false;
      this._updateState({ error: payload.error, status: 'idle' });
    }

    this._emit(type, payload);
    this._emit('message', payload);
  }

  _updateState(patch) {
    this.state = { ...this.state, ...patch };
    this._emit('state_change', this.state);
  }

  send(action, data = {}) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send action, websocket disconnected:', action);
      return false;
    }
    const message = JSON.stringify({ action, ...data });
    this.ws.send(message);
    return true;
  }

  sendChatMessage(text, thinking = false) {
    this._clearSpeakTimeout();
    this.isTtsActive = false;
    if (text) {
      this.addChatMessage({ sender: 'user', text });
      this._updateState({ lastTranscript: text });
    }
    return this.send('chat.send', { text, thinking });
  }

  startVoice() {
    this._clearSpeakTimeout();
    this.isTtsActive = false;
    return this.send('voice.start');
  }

  stopVoice() {
    return this.send('voice.stop');
  }

  toggleWakeWord(enabled) {
    return this.send('wake_word.toggle', { enabled });
  }

  stopTts() {
    this._clearSpeakTimeout();
    this.isTtsActive = false;
    this._updateState({ status: 'idle' });
    return this.send('tts.stop');
  }

  requestTelemetry() {
    return this.send('telemetry.get');
  }

  on(event, handler) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(handler);
    }
  }

  _emit(event, ...args) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((fn) => {
        try {
          fn(...args);
        } catch (e) {
          console.error(`Error in socket listener for ${event}:`, e);
        }
      });
    }
  }

  disconnect() {
    this._clearSpeakTimeout();
    this.isTtsActive = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const assistantSocket = new AssistantSocket();
