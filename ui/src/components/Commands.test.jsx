import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Commands from './Commands';
import { apiFetch } from '../services/api';

vi.mock('../services/api', () => ({
  apiFetch: vi.fn(),
}));

describe('Commands component', () => {
  const sampleCommands = [
    {
      id: 'telemetry',
      name: 'Телеметрия ПК',
      category: 'system',
      description: 'Показывает нагрузку ЦП и ОЗУ',
      commands: ['телеметрия', 'статус пк'],
    },
    {
      id: 'volume_up',
      name: 'Громче',
      category: 'media',
      description: 'Прибавить громкость',
      commands: ['сделай громче'],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    apiFetch.mockImplementation(async (url) => {
      if (url === '/api/commands') {
        return { ok: true, json: async () => ({ commands: sampleCommands }) };
      }
      if (url === '/api/commands/execute') {
        return { ok: true, json: async () => ({ success: true }) };
      }
      return { ok: false, json: async () => ({}) };
    });
  });

  it('loads command catalog and filters by search query and category', async () => {
    render(<Commands />);

    await waitFor(() => {
      expect(screen.getByText('Телеметрия ПК')).toBeInTheDocument();
    });
    expect(screen.getByText('Громче')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/Поиск по фразам/);
    fireEvent.change(searchInput, { target: { value: 'громче' } });
    expect(screen.queryByText('Телеметрия ПК')).not.toBeInTheDocument();
    expect(screen.getByText('Громче')).toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: '' } });
    fireEvent.click(screen.getByTitle('Система и ПК'));
    expect(screen.getByText('Телеметрия ПК')).toBeInTheDocument();
    expect(screen.queryByText('Громче')).not.toBeInTheDocument();
  });

  it('executes command and shows feedback toast on success and error', async () => {
    render(<Commands />);

    await waitFor(() => {
      expect(screen.getByText('Телеметрия ПК')).toBeInTheDocument();
    });

    const runButtons = screen.getAllByText('Тест');
    fireEvent.click(runButtons[0]);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/api/commands/execute',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ command: 'телеметрия' }),
        }),
      );
      expect(screen.getByText('Выполняю «телеметрия»...')).toBeInTheDocument();
    });

    apiFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: false, error: 'Router busy' }),
    });
    fireEvent.click(runButtons[1]);

    await waitFor(() => {
      expect(screen.getByText('Ошибка выполнения: Router busy')).toBeInTheDocument();
    });
  });
});
