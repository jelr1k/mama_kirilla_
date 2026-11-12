import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import Chat from './Chat';
import { useAssistant } from '../services/useAssistant';
import { apiFetch } from '../services/api';

vi.mock('../services/useAssistant', () => ({
  useAssistant: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiFetch: vi.fn(),
}));

describe('Chat component', () => {
  const baseAssistantState = {
    connected: true,
    status: 'idle',
    assistantName: 'Kirieshcka',
    model: 'qwen3:1.7b',
    voskText: '',
    currentChunk: '',
    isStreaming: false,
    messages: [
      { id: 1, sender: 'user', text: 'привет', time: '12:00' },
      {
        id: 2,
        sender: 'assistant',
        text: '<think>внутренняя мысль</think>Привет! Чем помочь?',
        time: '12:01',
      },
    ],
    sendChatMessage: vi.fn(),
    clearChatMessages: vi.fn(),
    startVoice: vi.fn(),
    stopVoice: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    apiFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ settings: { voice: { wake_word: 'кириешка' } } }),
    });
    useAssistant.mockReturnValue({ ...baseAssistantState });
  });

  it('renders messages, toggles thinking block, and loads wake word', async () => {
    await act(async () => {
      render(<Chat />);
    });

    expect(screen.getByText('привет')).toBeInTheDocument();
    expect(screen.getByText('Привет! Чем помочь?')).toBeInTheDocument();
    expect(screen.getByText('Вызов: «кириешка»')).toBeInTheDocument();
    expect(screen.queryByText('внутренняя мысль')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Размышление модели'));
    expect(screen.getByText('внутренняя мысль')).toBeInTheDocument();
  });

  it('sends typed message on Enter and toggles reasoning flag', async () => {
    const sendChatMessage = vi.fn();
    useAssistant.mockReturnValue({ ...baseAssistantState, sendChatMessage });

    await act(async () => {
      render(<Chat />);
    });

    fireEvent.click(screen.getByText('Рассуждения'));
    const textarea = screen.getByPlaceholderText(/Введите команду или вопрос/);
    fireEvent.change(textarea, { target: { value: '  сколько времени  ' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(sendChatMessage).toHaveBeenCalledWith('сколько времени', true);
    expect(textarea.value).toBe('');
  });

  it('triggers quick command chip, voice toggle, and chat clearing', async () => {
    vi.useFakeTimers();
    const sendChatMessage = vi.fn();
    const clearChatMessages = vi.fn();
    const startVoice = vi.fn();
    const stopVoice = vi.fn();

    useAssistant.mockReturnValue({
      ...baseAssistantState,
      status: 'idle',
      sendChatMessage,
      clearChatMessages,
      startVoice,
      stopVoice,
    });

    await act(async () => {
      render(<Chat />);
    });

    fireEvent.click(screen.getByText('Нагрузка'));
    expect(sendChatMessage).toHaveBeenCalledWith('телеметрия', false);

    fireEvent.click(screen.getByTitle('Голосовой ввод'));
    expect(startVoice).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTitle('Очистить историю сообщений'));
    act(() => {
      vi.advanceTimersByTime(250);
    });
    expect(clearChatMessages).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
