import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AssistantSocket } from './assistantSocket.js';
import * as api from './api.js';

// Mock api.js
vi.mock('./api.js', () => ({
  fetchSessionToken: vi.fn(),
}));

class MockWebSocket {
  static instances = [];
  static OPEN = 1;
  static CLOSED = 3;
  static CONNECTING = 0;
  static CLOSING = 2;

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.send = vi.fn();
    this.close = vi.fn(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) this.onclose({ wasClean: true });
    });
    this.onopen = null;
    this.onclose = null;
    this.onmessage = null;
    this.onerror = null;
    MockWebSocket.instances.push(this);
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) this.onopen();
  }

  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: typeof data === 'string' ? data : JSON.stringify(data) });
    }
  }

  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) this.onclose({ code, reason });
  }

  simulateError(err = new Error('Socket error')) {
    if (this.onerror) this.onerror(err);
  }
}

describe('AssistantSocket service', () => {
  let originalWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    MockWebSocket.instances = [];
    originalWebSocket = globalThis.WebSocket;
    globalThis.WebSocket = MockWebSocket;
    vi.mocked(api.fetchSessionToken).mockResolvedValue(null);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    globalThis.WebSocket = originalWebSocket;
    vi.restoreAllMocks();
  });

  describe('Initialization & LocalStorage messages', () => {
    it('initializes with default state and welcome message when localStorage is empty', () => {
      const socket = new AssistantSocket();
      expect(socket.state.connected).toBe(false);
      expect(socket.state.status).toBe('idle');
      expect(socket.state.assistantName).toBe('Kirieshcka');

      const messages = socket.getMessages();
      expect(messages).toHaveLength(1);
      expect(messages[0].sender).toBe('assistant');
      expect(messages[0].text).toContain('Привет! Я готов к работе');
    });

    it('loads stored messages from localStorage if present', () => {
      const stored = [
        { id: 10, sender: 'user', text: 'Как дела?', time: '12:00' },
        { id: 11, sender: 'assistant', text: 'Всё отлично!', time: '12:00' },
      ];
      localStorage.setItem('kirieshcka_chat_messages_v2', JSON.stringify(stored));

      const socket = new AssistantSocket();
      const messages = socket.getMessages();
      expect(messages).toHaveLength(2);
      expect(messages[0].text).toBe('Как дела?');
      expect(messages[1].text).toBe('Всё отлично!');
    });

    it('falls back to default message if localStorage JSON is corrupted', () => {
      localStorage.setItem('kirieshcka_chat_messages_v2', 'not a valid json');
      const socket = new AssistantSocket();
      const messages = socket.getMessages();
      expect(messages).toHaveLength(1);
      expect(messages[0].sender).toBe('assistant');
    });
  });

  describe('Chat message deduplication & management', () => {
    it('adds a valid chat message and persists to localStorage', () => {
      const socket = new AssistantSocket();
      const listener = vi.fn();
      socket.on('messages_change', listener);

      socket.addChatMessage({ sender: 'user', text: 'Привет, помощник!' });

      const messages = socket.getMessages();
      expect(messages).toHaveLength(2);
      expect(messages[1].sender).toBe('user');
      expect(messages[1].text).toBe('Привет, помощник!');
      expect(listener).toHaveBeenCalledWith(messages);

      const saved = JSON.parse(localStorage.getItem('kirieshcka_chat_messages_v2'));
      expect(saved).toHaveLength(2);
      expect(saved[1].text).toBe('Привет, помощник!');
    });

    it('ignores empty or whitespace-only messages', () => {
      const socket = new AssistantSocket();
      socket.addChatMessage(null);
      socket.addChatMessage({ sender: 'user', text: '' });
      socket.addChatMessage({ sender: 'user', text: '   ' });

      expect(socket.getMessages()).toHaveLength(1);
    });

    it('deduplicates rapid identical messages from the same sender', () => {
      const socket = new AssistantSocket();
      socket.addChatMessage({ sender: 'user', text: 'Тестовый запрос' });
      expect(socket.getMessages()).toHaveLength(2);

      // Repeat exactly identical message from same sender
      socket.addChatMessage({ sender: 'user', text: 'Тестовый запрос' });
      expect(socket.getMessages()).toHaveLength(2);

      // Different sender or different text should be accepted
      socket.addChatMessage({ sender: 'assistant', text: 'Тестовый запрос' });
      expect(socket.getMessages()).toHaveLength(3);

      socket.addChatMessage({ sender: 'assistant', text: 'Другой ответ' });
      expect(socket.getMessages()).toHaveLength(4);
    });

    it('caps message history at 100 items', () => {
      const socket = new AssistantSocket();
      for (let i = 0; i < 110; i++) {
        socket.addChatMessage({ sender: 'user', text: `Сообщение ${i}` });
      }

      const messages = socket.getMessages();
      expect(messages).toHaveLength(100);
      expect(messages[messages.length - 1].text).toBe('Сообщение 109');
    });

    it('clears chat history and resets to intro message', () => {
      const socket = new AssistantSocket();
      socket.addChatMessage({ sender: 'user', text: 'Тест' });
      expect(socket.getMessages()).toHaveLength(2);

      const listener = vi.fn();
      socket.on('messages_change', listener);
      socket.clearChatMessages();

      const messages = socket.getMessages();
      expect(messages).toHaveLength(1);
      expect(messages[0].text).toContain('История диалога очищена');
      expect(listener).toHaveBeenCalledWith(messages);
    });
  });

  describe('Connection & Session Token', () => {
    it('appends session token as query param if token exists', async () => {
      vi.mocked(api.fetchSessionToken).mockResolvedValue('secret-token-123');
      const socket = new AssistantSocket('ws://127.0.0.1:8765/ws');

      await socket.connect();

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.instances[0].url).toBe('ws://127.0.0.1:8765/ws?token=secret-token-123');
    });

    it('handles url with existing query params correctly when adding token', async () => {
      vi.mocked(api.fetchSessionToken).mockResolvedValue('token456');
      const socket = new AssistantSocket('ws://127.0.0.1:8765/ws?client=desktop');

      await socket.connect();

      expect(MockWebSocket.instances[0].url).toBe('ws://127.0.0.1:8765/ws?client=desktop&token=token456');
    });

    it('handles successful connection open', async () => {
      const socket = new AssistantSocket();
      const connListener = vi.fn();
      const stateListener = vi.fn();
      socket.on('connection_change', connListener);
      socket.on('state_change', stateListener);

      await socket.connect();
      const wsInstance = MockWebSocket.instances[0];

      wsInstance.simulateOpen();

      expect(socket.isConnected).toBe(true);
      expect(socket.state.connected).toBe(true);
      expect(socket.state.error).toBeNull();
      expect(connListener).toHaveBeenCalledWith(true);
      expect(stateListener).toHaveBeenCalled();
    });

    it('does not re-create websocket if already OPEN or CONNECTING', async () => {
      const socket = new AssistantSocket();
      await socket.connect();
      const firstWs = MockWebSocket.instances[0];
      expect(MockWebSocket.instances).toHaveLength(1);

      // Still CONNECTING -> connect() should be no-op
      await socket.connect();
      expect(MockWebSocket.instances).toHaveLength(1);

      firstWs.simulateOpen();
      // Already OPEN -> connect() should be no-op
      await socket.connect();
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it('schedules reconnect if fetchSessionToken fails', async () => {
      vi.mocked(api.fetchSessionToken).mockRejectedValueOnce(new Error('Network fail'));
      const socket = new AssistantSocket();

      await socket.connect();
      expect(MockWebSocket.instances).toHaveLength(0);
      expect(socket.reconnectTimer).not.toBeNull();
    });

    it('emits error event on socket error', async () => {
      const socket = new AssistantSocket();
      const errorListener = vi.fn();
      socket.on('error', errorListener);

      await socket.connect();
      const err = new Error('Connection refused');
      MockWebSocket.instances[0].simulateError(err);

      expect(errorListener).toHaveBeenCalledWith(err);
    });
  });

  describe('Reconnection & Exponential Backoff', () => {
    it('applies exponential backoff on close and resets delay after open', async () => {
      const socket = new AssistantSocket();
      expect(socket.currentDelay).toBe(1500);

      await socket.connect();
      const ws1 = MockWebSocket.instances[0];

      // Connection drops -> triggers reconnect in 1500ms
      ws1.simulateClose();
      expect(socket.isConnected).toBe(false);
      expect(socket.state.connected).toBe(false);

      // Fast-forward 1499ms (reconnect should not fire yet)
      vi.advanceTimersByTime(1499);
      expect(MockWebSocket.instances).toHaveLength(1);

      // Advance by 1ms -> timer fires, calls connect()
      vi.advanceTimersByTime(1);
      // Wait microtasks for async connect
      await Promise.resolve();
      expect(MockWebSocket.instances).toHaveLength(2);
      expect(socket.currentDelay).toBe(2250); // 1500 * 1.5

      // Second drop -> next delay is 2250 * 1.5 = 3375ms
      const ws2 = MockWebSocket.instances[1];
      ws2.simulateClose();

      vi.advanceTimersByTime(2250);
      await Promise.resolve();
      expect(MockWebSocket.instances).toHaveLength(3);
      expect(socket.currentDelay).toBe(3375);

      // Successful open resets delay back to 1500ms
      const ws3 = MockWebSocket.instances[2];
      ws3.simulateOpen();
      expect(socket.currentDelay).toBe(1500);
    });
  });

  describe('Actions & Commands sending', () => {
    it('returns false when trying to send on disconnected socket', () => {
      vi.spyOn(console, 'warn').mockImplementation(() => {});
      const socket = new AssistantSocket();
      const result = socket.send('test.action', { foo: 'bar' });
      expect(result).toBe(false);
    });

    it('sends JSON serialized action when socket is open', async () => {
      const socket = new AssistantSocket();
      await socket.connect();
      const ws = MockWebSocket.instances[0];
      ws.simulateOpen();

      const result = socket.send('telemetry.get', { extra: 1 });
      expect(result).toBe(true);
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'telemetry.get', extra: 1 }));
    });

    it('sendChatMessage adds message to chat history and sends chat.send', async () => {
      const socket = new AssistantSocket();
      await socket.connect();
      const ws = MockWebSocket.instances[0];
      ws.simulateOpen();

      socket.sendChatMessage('Привет!', true);

      expect(socket.state.lastTranscript).toBe('Привет!');
      const lastMsg = socket.getMessages().slice(-1)[0];
      expect(lastMsg.text).toBe('Привет!');
      expect(lastMsg.sender).toBe('user');
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({
        action: 'chat.send',
        text: 'Привет!',
        thinking: true,
      }));
    });

    it('convenience helper methods send correct actions', async () => {
      const socket = new AssistantSocket();
      await socket.connect();
      const ws = MockWebSocket.instances[0];
      ws.simulateOpen();

      socket.startVoice();
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'voice.start' }));

      socket.stopVoice();
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'voice.stop' }));

      socket.toggleWakeWord(false);
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'wake_word.toggle', enabled: false }));

      socket.requestTelemetry();
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'telemetry.get' }));

      socket.stopTts();
      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ action: 'tts.stop' }));
      expect(socket.state.status).toBe('idle');
    });
  });

  describe('Event listeners (on / off / _emit)', () => {
    it('allows subscribing and unsubscribing via returned callback and off()', () => {
      const socket = new AssistantSocket();
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      const unsub1 = socket.on('custom_evt', handler1);
      socket.on('custom_evt', handler2);

      socket._emit('custom_evt', 'arg1', 'arg2');
      expect(handler1).toHaveBeenCalledWith('arg1', 'arg2');
      expect(handler2).toHaveBeenCalledWith('arg1', 'arg2');

      unsub1();
      socket.off('custom_evt', handler2);

      socket._emit('custom_evt', 'arg3');
      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(1);
    });

    it('catches listener errors without crashing emit loop', () => {
      vi.spyOn(console, 'error').mockImplementation(() => {});
      const socket = new AssistantSocket();
      const badHandler = vi.fn(() => {
        throw new Error('Boom');
      });
      const goodHandler = vi.fn();

      socket.on('crash_test', badHandler);
      socket.on('crash_test', goodHandler);

      expect(() => {
        socket._emit('crash_test');
      }).not.toThrow();

      expect(goodHandler).toHaveBeenCalled();
    });
  });

  describe('State Machine & WebSocket Messages Handling', () => {
    let socket;
    let ws;

    beforeEach(async () => {
      socket = new AssistantSocket();
      await socket.connect();
      ws = MockWebSocket.instances[0];
      ws.simulateOpen();
    });

    it('updates state and telemetry upon "state" and "telemetry" payload', () => {
      ws.simulateMessage({
        type: 'state',
        assistant_name: 'Джарвис',
        app_title: 'Jarvis Super',
        model: 'llama3:latest',
        telemetry: { cpu: 15 },
      });

      expect(socket.state.assistantName).toBe('Джарвис');
      expect(socket.state.appTitle).toBe('Jarvis Super');
      expect(socket.state.model).toBe('llama3:latest');
      expect(socket.state.telemetry).toEqual({ cpu: 15 });

      ws.simulateMessage({
        type: 'telemetry',
        data: { cpu: 35, ram: 50 },
      });
      expect(socket.state.telemetry).toEqual({ cpu: 35, ram: 50 });
    });

    it('trims wake_word.recognized to last 7 words when long', () => {
      ws.simulateMessage({
        type: 'wake_word.recognized',
        text: 'один два три четыре пять шесть семь восемь девять десять',
      });
      expect(socket.state.voskText).toBe('... четыре пять шесть семь восемь девять десять');

      ws.simulateMessage({
        type: 'wake_word.recognized',
        text: 'короткая фраза',
      });
      expect(socket.state.voskText).toBe('короткая фраза');
    });

    it('transitions to "listen" on wake_word.detected and voice.status listening', () => {
      ws.simulateMessage({ type: 'wake_word.detected' });
      expect(socket.state.status).toBe('listen');
      expect(socket.state.lastTranscript).toBe('');

      socket._updateState({ status: 'idle' });
      ws.simulateMessage({ type: 'voice.status', status: 'listening' });
      expect(socket.state.status).toBe('listen');
    });

    it('transitions to "listen" and back to "idle" via voice.listening', () => {
      ws.simulateMessage({ type: 'voice.listening', active: true });
      expect(socket.state.status).toBe('listen');

      ws.simulateMessage({ type: 'voice.listening', active: false });
      expect(socket.state.status).toBe('idle');
    });

    it('transitions to "think" on voice.transcribing active', () => {
      ws.simulateMessage({ type: 'voice.transcribing', active: true });
      expect(socket.state.status).toBe('think');
    });

    it('records user message on voice.transcription', () => {
      ws.simulateMessage({ type: 'voice.transcription', text: 'Сколько время?' });
      expect(socket.state.lastTranscript).toBe('Сколько время?');

      const last = socket.getMessages().slice(-1)[0];
      expect(last.sender).toBe('user');
      expect(last.text).toBe('Сколько время?');
    });

    it('handles chat streaming chunks and transitions to speak on idle status', () => {
      // 1. Thinking starts
      ws.simulateMessage({ type: 'chat.status', status: 'thinking' });
      expect(socket.state.status).toBe('think');
      expect(socket.state.isStreaming).toBe(true);
      expect(socket.state.currentChunk).toBe('');

      // 2. Chunks arrive
      ws.simulateMessage({ type: 'chat.chunk', chunk: 'Привет' });
      ws.simulateMessage({ type: 'chat.chunk', chunk: ', мир!' });
      expect(socket.state.currentChunk).toBe('Привет, мир!');

      // 3. Streaming finishes
      ws.simulateMessage({ type: 'chat.status', status: 'idle' });
      expect(socket.state.status).toBe('speak');
      expect(socket.state.lastResponse).toBe('Привет, мир!');

      const last = socket.getMessages().slice(-1)[0];
      expect(last.sender).toBe('assistant');
      expect(last.text).toBe('Привет, мир!');
    });

    it('handles direct chat.response message', () => {
      ws.simulateMessage({ type: 'chat.response', text: 'Готово, сэр.' });
      expect(socket.state.status).toBe('speak');
      expect(socket.state.lastResponse).toBe('Готово, сэр.');

      const last = socket.getMessages().slice(-1)[0];
      expect(last.text).toBe('Готово, сэр.');
    });

    it('calculates reading animation timeout and resets to idle when TTS is inactive', () => {
      // For short response "Привет", duration = max(2200, 6 * 45) = 2200ms
      ws.simulateMessage({ type: 'chat.response', text: 'Привет' });
      expect(socket.state.status).toBe('speak');
      expect(socket.speakTimeout).not.toBeNull();

      vi.advanceTimersByTime(2199);
      expect(socket.state.status).toBe('speak');

      vi.advanceTimersByTime(2);
      expect(socket.state.status).toBe('idle');
      expect(socket.speakTimeout).toBeNull();
    });

    it('cancels reading timeout if real TTS activates (tts.state speaking/synthesizing)', () => {
      ws.simulateMessage({ type: 'chat.response', text: 'Привет' });
      expect(socket.speakTimeout).not.toBeNull();

      // TTS starts
      ws.simulateMessage({ type: 'tts.state', state: 'speaking' });
      expect(socket.isTtsActive).toBe(true);
      expect(socket.speakTimeout).toBeNull();
      expect(socket.state.status).toBe('speak');

      // Advancing past reading timeout duration shouldn't reset to idle because TTS is active
      vi.advanceTimersByTime(10000);
      expect(socket.state.status).toBe('speak');

      // When TTS finishes -> status returns to idle
      ws.simulateMessage({ type: 'tts.state', state: 'idle' });
      expect(socket.isTtsActive).toBe(false);
      expect(socket.state.status).toBe('idle');
    });

    it('handles chat.error and voice.error resetting status to idle', () => {
      socket._updateState({ status: 'think' });
      ws.simulateMessage({ type: 'chat.error', error: 'Ollama model timeout' });
      expect(socket.state.status).toBe('idle');
      expect(socket.state.error).toBe('Ollama model timeout');

      socket._updateState({ status: 'listen' });
      ws.simulateMessage({ type: 'voice.error', error: 'Mic unavailable' });
      expect(socket.state.status).toBe('idle');
      expect(socket.state.error).toBe('Mic unavailable');
    });

    it('ignores invalid JSON in websocket onmessage safely', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      expect(() => {
        ws.simulateMessage('INVALID {JSON}');
      }).not.toThrow();
      expect(warnSpy).toHaveBeenCalledWith('Failed to parse websocket message:', expect.any(Error));
    });
  });

  describe('Disconnect', () => {
    it('cleans up socket, timers and resets active flags on disconnect', async () => {
      const socket = new AssistantSocket();
      await socket.connect();
      const ws = MockWebSocket.instances[0];
      ws.simulateOpen();

      // Trigger a speak timeout
      socket._triggerSpeakState('Тестовая реплика для проверки отключения');
      expect(socket.speakTimeout).not.toBeNull();

      socket.disconnect();

      expect(socket.speakTimeout).toBeNull();
      expect(socket.isTtsActive).toBe(false);
      expect(socket.ws).toBeNull();
      expect(ws.close).toHaveBeenCalled();
    });
  });
});
