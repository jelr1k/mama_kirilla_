import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Settings from './Settings';
import { apiFetch } from '../services/api';

vi.mock('../services/api', () => ({
  apiFetch: vi.fn(),
}));

describe('Settings component', () => {
  const defaultGetMap = {
    '/api/settings': {
      settings: {
        app_title: 'Kirieshcka v2',
        assistant_name: 'Kirieshcka',
        model: 'qwen3:1.7b',
        temperature: 0.7,
        context_length: 32768,
        max_tokens: 4096,
        router_only_mode: false,
        allow_outside_workspace: false,
        ollama: { base_url: 'http://localhost:11434', autoload_model: false },
        voice: { wake_word_enabled: true, wake_word: 'шпрота', model: 'small' },
        tts: { enabled: false, voice: 'ru_RU-dmitri-medium', speed: 1.0, volume: 0.85 },
        telegram: { enabled: false, bot_token: '', allowed_chat_ids: [101] },
        rofl: { unlocked: false, chance: 0.12, demon_chance: 0.15 },
      },
    },
    '/api/updates': { current_version: '0.1.8', latest_version: '0.1.8', has_update: false },
    '/api/autostart': { enabled: true },
    '/api/microphones': { devices: [] },
    '/api/models': { ollama_models: ['qwen3:1.7b'] },
    '/api/whisper/status': { statuses: { small: 'installed' } },
    '/api/tts/status': { statuses: {} },
    '/api/telegram/status': { running: false },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    apiFetch.mockImplementation(async (url, opts) => {
      if (!opts || !opts.method || opts.method === 'GET') {
        return { ok: true, json: async () => defaultGetMap[url] || {} };
      }
      if (url === '/api/settings' && opts.method === 'POST') {
        return { ok: true, json: async () => ({ success: true }) };
      }
      if (url === '/api/autostart' && opts.method === 'POST') {
        return { ok: true, json: async () => ({ success: true }) };
      }
      return { ok: true, json: async () => ({ success: false }) };
    });
  });

  it('loads settings and saves updated payload', async () => {
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText('Сохранить изменения')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Сохранить изменения'));

    await waitFor(() => {
      const saveCall = apiFetch.mock.calls.find(
        ([url, opts]) => url === '/api/settings' && opts?.method === 'POST',
      );
      expect(saveCall).toBeDefined();
      const parsed = JSON.parse(saveCall[1].body);
      expect(parsed.assistant_name).toBe('Kirieshcka');
      expect(parsed.telegram.allowed_chat_ids).toEqual([101]);
      expect(screen.getByText('Все параметры успешно сохранены и применены')).toBeInTheDocument();
    });
  });

  it('displays error banner when saving settings fails', async () => {
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByText('Сохранить изменения')).toBeInTheDocument();
    });

    apiFetch.mockImplementation(async (url, opts) => {
      if (url === '/api/settings' && opts?.method === 'POST') {
        return { ok: true, json: async () => ({ success: false, error: 'Bad config' }) };
      }
      return { ok: true, json: async () => defaultGetMap[url] || {} };
    });

    fireEvent.click(screen.getByText('Сохранить изменения'));

    await waitFor(() => {
      expect(screen.getByText('Bad config')).toBeInTheDocument();
    });
  });

  it('allows switching theme and updates document attributes', async () => {
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByTestId('theme-select')).toBeInTheDocument();
    });

    const select = screen.getByTestId('theme-select');
    fireEvent.change(select, { target: { value: 'default' } });

    expect(localStorage.getItem('kirieshcka_theme')).toBe('default');
    expect(document.documentElement.getAttribute('data-theme')).toBe('default');

    fireEvent.change(select, { target: { value: 'dark' } });
    expect(localStorage.getItem('kirieshcka_theme')).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('allows switching UI mode and persists to localStorage', async () => {
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByTestId('ui-mode-select')).toBeInTheDocument();
    });

    const uiSelect = screen.getByTestId('ui-mode-select');
    fireEvent.change(uiSelect, { target: { value: 'motion' } });
    expect(localStorage.getItem('assistant_ui_mode')).toBe('motion');

    fireEvent.change(uiSelect, { target: { value: 'classic' } });
    expect(localStorage.getItem('assistant_ui_mode')).toBe('classic');
  });

  it('groups TTS voices by engine and switches voice when engine changes', async () => {
    render(<Settings />);

    const voiceTab = await screen.findByRole('tab', { name: 'Голос и речь' });
    fireEvent.click(voiceTab);

    await waitFor(() => {
      expect(screen.getByLabelText('Озвучка')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('Озвучка'));

    const engineSelect = await screen.findByLabelText('Движок синтеза');
    const voiceSelect = screen.getByLabelText('Голос диктора');

    expect(engineSelect.value).toBe('piper');
    expect(voiceSelect.value).toBe('ru_RU-dmitri-medium');
    expect(Array.from(voiceSelect.options).map((o) => o.value)).toEqual([
      'ru_RU-dmitri-medium',
      'ru_RU-irina-medium',
      'ru_RU-ruslan-medium',
    ]);

    fireEvent.change(engineSelect, { target: { value: 'silero' } });

    expect(engineSelect.value).toBe('silero');
    expect(voiceSelect.value).toBe('silero:baya');
    expect(Array.from(voiceSelect.options).map((o) => o.value)).toEqual([
      'silero:baya',
      'silero:kseniya',
      'silero:xenia',
    ]);
  });

  it('navigates between Discord-style settings subtabs without losing unsaved state', async () => {
    render(<Settings />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Основные' })).toHaveAttribute('aria-selected', 'true');
    });

    const assistantInput = screen.getByPlaceholderText('Ассистент');
    fireEvent.change(assistantInput, { target: { value: 'JarvisTest' } });

    fireEvent.click(screen.getByRole('tab', { name: 'Нейросеть (Ollama)' }));
    expect(await screen.findByText('Нейросеть (Ollama & Параметры генерации)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Telegram-бот' }));
    expect(await screen.findByText('Telegram Бот (Удалённое управление ПК)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Безопасность' }));
    expect(await screen.findByText('Безопасность и Доступ')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Служебные и питание' }));
    expect(await screen.findByText('Завершить работу приложения')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Сохранить изменения'));

    await waitFor(() => {
      const saveCall = apiFetch.mock.calls.find(
        ([url, opts]) => url === '/api/settings' && opts?.method === 'POST',
      );
      expect(saveCall).toBeDefined();
      const parsed = JSON.parse(saveCall[1].body);
      expect(parsed.assistant_name).toBe('JarvisTest');
    });
  });
});
