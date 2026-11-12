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
});
