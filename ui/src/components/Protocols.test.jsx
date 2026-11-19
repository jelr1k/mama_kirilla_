import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Protocols from './Protocols';
import { apiGet, apiPost, apiDelete } from '../services/api';

vi.mock('../services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

describe('Protocols component', () => {
  const protocolsResponse = {
    profiles: { default: 'Основной', gaming: 'Игровой' },
    active_profile: 'default',
    protocols: [
      {
        id: 'work_mode',
        name: 'Работа',
        description: 'Открывает IDE',
        phrases: ['к работе'],
        open_apps: ['vscode'],
        close_mode: 'none',
        close_apps: [],
        volume_mode: 'none',
        pause_media: false,
        lock_screen: false,
        clean_recycle_bin: false,
        briefing: false,
        response_text: '',
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    apiGet.mockImplementation(async (url) => {
      if (url === '/api/protocols') return protocolsResponse;
      if (url === '/api/steam') return { installed: false, games: [] };
      if (url === '/api/protocols/suggestions') {
        return {
          suggestions: [
            { key: 'vivaldi', label: 'Vivaldi', category: 'browser', aliases: ['вивальди'] },
            { key: 'steam', label: 'Steam', category: 'gaming', aliases: ['стим'] },
          ],
          total: 2,
        };
      }
      return {};
    });
    apiPost.mockResolvedValue({ success: true, result: 'Выполнено' });
    apiDelete.mockResolvedValue({ success: true });
  });

  it('loads protocols, switches profile, and executes selected protocol', async () => {
    render(<Protocols />);

    await waitFor(() => {
      expect(screen.getByText('Работа')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Старт'));
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/api/protocols/execute', {
        protocol_id: 'work_mode',
        profile_id: 'default',
      });
      expect(screen.getByText('«Работа»: Выполнено')).toBeInTheDocument();
    });

    apiPost.mockResolvedValueOnce({
      success: true,
      protocols: [
        {
          ...protocolsResponse.protocols[0],
          id: 'game_mode',
          name: 'Игровой режим',
        },
      ],
    });

    const profileSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(profileSelect, { target: { value: 'gaming' } });

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/api/protocols/profile/select', {
        profile_id: 'gaming',
      });
      expect(screen.getByText('Игровой режим')).toBeInTheDocument();
    });
  });

  it('saves protocol changes via POST /api/protocols', async () => {
    render(<Protocols />);

    await waitFor(() => {
      expect(screen.getByText('Редактирование: Работа')).toBeInTheDocument();
    });

    apiPost.mockResolvedValueOnce({ success: true, protocol_id: 'work_mode' });
    fireEvent.click(screen.getByText('Сохранить'));

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        '/api/protocols',
        expect.objectContaining({
          profile_id: 'default',
          protocol: expect.objectContaining({ id: 'work_mode', name: 'Работа' }),
        }),
      );
      expect(screen.getByText('Сценарий «Работа» сохранён')).toBeInTheDocument();
    });
  });

  it('renders dynamic app suggestions without hardcoded Opera GX and prevents duplicates', async () => {
    render(<Protocols />);

    await waitFor(() => {
      expect(screen.getAllByText('+ Vivaldi')).toHaveLength(2);
    });

    expect(screen.queryByText('+ Opera GX')).not.toBeInTheDocument();

    // Кликаем по чипу в "Запуск программ", остаётся только чип в "Закрытие программ"
    fireEvent.click(screen.getAllByText('+ Vivaldi')[0]);

    await waitFor(() => {
      expect(screen.getAllByText('+ Vivaldi')).toHaveLength(1);
      expect(screen.getAllByText('+ Steam')).toHaveLength(2);
    });

    // Кликаем по оставшемуся чипу в "Закрытие программ" — больше не повторяется нигде
    fireEvent.click(screen.getByText('+ Vivaldi'));

    await waitFor(() => {
      expect(screen.queryByText('+ Vivaldi')).not.toBeInTheDocument();
    });
  });
});
