import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import IslandApp, { fixKeyboardLayout, formatTimer } from './IslandApp';

const mockUseAssistant = vi.fn();

vi.mock('../services/useAssistant', () => ({
  useAssistant: () => mockUseAssistant(),
}));

vi.mock('../services/api', () => ({
  apiGet: vi.fn((url) => {
    if (url === '/api/media/status') return Promise.resolve({ volume: 42, muted: false });
    if (url === '/api/protocols') {
      return Promise.resolve({
        protocols: [{ id: 'p1', name: 'Игровой режим' }],
      });
    }
    if (url === '/api/apps') {
      return Promise.resolve({
        apps: [{ name: 'Discord' }],
      });
    }
    if (url === '/api/commands') {
      return Promise.resolve({
        commands: [
          { id: 'zapret_start', name: 'Запрет Discord/YouTube (service.bat)', category: 'network', commands: ['запрет'] },
          { id: 'jarvis_minimize', name: 'Свернуть окно', category: 'system', commands: ['свернись'] },
          { id: 'search_google', name: 'Поиск в Google', category: 'apps', commands: ['загугли <запрос>'] },
          { id: 'protocol_game', name: 'Протокол «Игра»', category: 'protocols', commands: ['игра'] },
        ],
      });
    }
    return Promise.resolve({});
  }),
  apiPost: vi.fn(() => Promise.resolve({ success: true, volume: 42, muted: false })),
}));

describe('IslandApp helpers', () => {
  it('converts English QWERTY text to Russian layout and back', () => {
    expect(fixKeyboardLayout('ghbdtn')).toBe('привет');
    expect(fixKeyboardLayout('руддщ')).toBe('hello');
    expect(fixKeyboardLayout('')).toBe('');
  });

  it('formats timer seconds into MM:SS', () => {
    expect(formatTimer(0)).toBe('00:00');
    expect(formatTimer(65)).toBe('01:05');
    expect(formatTimer(1500)).toBe('25:00');
  });
});

describe('IslandApp component', () => {
  beforeEach(() => {
    localStorage.clear();
    mockUseAssistant.mockReturnValue({
      connected: true,
      status: 'idle',
      assistantName: 'Kirieshcka',
      voskText: '',
      lastTranscript: '',
      lastResponse: '',
      currentChunk: '',
      isStreaming: false,
      telemetry: { cpu_percent: 18, ram_percent: 54 },
      messages: [{ id: 1, sender: 'assistant', text: 'Привет!', time: '12:00' }],
      sendChatMessage: vi.fn(),
      clearChatMessages: vi.fn(),
      startVoice: vi.fn(),
      stopVoice: vi.fn(),
      stopTts: vi.fn(),
    });
  });

  it('renders collapsed notch with assistant name and CPU badge', () => {
    render(<IslandApp previewMode={true} />);
    expect(screen.getByText('Kirieshcka')).toBeInTheDocument();
    expect(screen.getByText('18%')).toBeInTheDocument();
  });

  it('shows listening equalizer and live voskText when status is listen', () => {
    mockUseAssistant.mockReturnValue({
      ...mockUseAssistant(),
      status: 'listen',
      voskText: 'открой телеграм',
    });
    render(<IslandApp previewMode={true} />);
    expect(screen.getByText('открой телеграм')).toBeInTheDocument();
    expect(screen.getByTestId('dynamic-island-shell')).toHaveClass('status-listen', 'has-activity');
  });

  it('expands on click, switches tabs, and triggers close callback in preview mode', async () => {
    const onClose = vi.fn();
    render(<IslandApp previewMode={true} onClosePreview={onClose} />);

    fireEvent.click(screen.getByLabelText('Открыть Dynamic Island'));

    await waitFor(() => {
      expect(screen.getByTestId('dynamic-island-shell')).toHaveClass('expanded');
    });

    // Protocols tab (only protocols, no Start Menu / app clutter)
    fireEvent.click(screen.getByRole('tab', { name: 'Протоколы' }));
    await waitFor(() => {
      expect(screen.getByText('⚡ Игровой режим')).toBeInTheDocument();
    });
    expect(screen.queryByText('Discord')).not.toBeInTheDocument();

    // Tools tab (Notes + Timer + Layout fix)
    fireEvent.click(screen.getByRole('tab', { name: 'Утилиты' }));
    expect(screen.getByText('05:00')).toBeInTheDocument();
    fireEvent.click(screen.getByText('25м'));
    expect(screen.getByText('25:00')).toBeInTheDocument();

    const layoutInput = screen.getByPlaceholderText('Текст для фикса раскладки / JSON...');
    fireEvent.change(layoutInput, { target: { value: 'ghbdtn' } });
    fireEvent.click(screen.getByText('Раскладка EN↔RU'));
    expect(layoutInput.value).toBe('привет');

    // Disable button
    fireEvent.click(screen.getByLabelText('Отключить остров'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('allows customizing visible tabs, prevents hiding the last tab, and persists config', async () => {
    const { unmount } = render(<IslandApp previewMode={true} />);

    fireEvent.click(screen.getByLabelText('Открыть Dynamic Island'));
    await waitFor(() => {
      expect(screen.getByTestId('dynamic-island-shell')).toHaveClass('expanded');
    });

    // Open customization panel
    fireEvent.click(screen.getByLabelText('Настроить остров'));
    expect(screen.getByText('Вкладки островка')).toBeInTheDocument();

    // Turn off "Главное" and "Утилиты", leaving only "Протоколы" and "Чат"
    fireEvent.click(screen.getByRole('button', { name: 'Главное' }));
    fireEvent.click(screen.getByRole('button', { name: 'Утилиты' }));

    expect(screen.queryByRole('tab', { name: 'Главное' })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Утилиты' })).not.toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Протоколы' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Чат' })).toBeInTheDocument();

    // Trying to turn off both remaining: last one must stay active
    fireEvent.click(screen.getByRole('button', { name: 'Протоколы' }));
    expect(screen.queryByRole('tab', { name: 'Протоколы' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Чат' }));
    expect(screen.getAllByText('Нужна хотя бы одна вкладка').length).toBeGreaterThan(0);
    expect(screen.getByRole('tab', { name: 'Чат' })).toBeInTheDocument();

    // Restore "Протоколы" and close settings
    fireEvent.click(screen.getByRole('button', { name: 'Протоколы' }));
    fireEvent.click(screen.getByRole('button', { name: 'Готово' }));

    expect(screen.getByRole('tab', { name: 'Протоколы' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Чат' })).toBeInTheDocument();

    // Persistence across remount
    unmount();
    render(<IslandApp previewMode={true} />);
    fireEvent.click(screen.getByLabelText('Открыть Dynamic Island'));
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Протоколы' })).toBeInTheDocument();
    });
    expect(screen.queryByRole('tab', { name: 'Главное' })).not.toBeInTheDocument();
  });

  it('supports dragging position and resetting back to top-center', async () => {
    render(<IslandApp previewMode={true} />);
    const collapsed = screen.getByLabelText('Открыть Dynamic Island');

    fireEvent.pointerDown(collapsed, { button: 0, clientX: 100, clientY: 10 });
    fireEvent.pointerMove(window, { clientX: 240, clientY: 95 });
    fireEvent.pointerUp(window, { clientX: 240, clientY: 95 });

    const shell = screen.getByTestId('dynamic-island-shell');
    expect(shell).toHaveClass('floating');
    const savedPos = JSON.parse(localStorage.getItem('kirieshcka_island_pos'));
    expect(savedPos.y).toBe(85);
    expect(savedPos.dockedTop).toBe(false);

    // Click immediately after drag should be suppressed (does not open accidentally)
    fireEvent.click(collapsed);
    expect(shell).toHaveClass('collapsed');

    // Subsequent click opens it cleanly
    fireEvent.click(collapsed);
    await waitFor(() => {
      expect(shell).toHaveClass('expanded');
    });

    fireEvent.click(screen.getByLabelText('Настроить остров'));
    fireEvent.click(screen.getByRole('button', { name: 'В центр верха' }));

    expect(shell).not.toHaveClass('floating');
    expect(localStorage.getItem('kirieshcka_island_pos')).toBeNull();
  });

  it('uses smooth closing transition before removing expanded view', async () => {
    vi.useFakeTimers();
    try {
      render(<IslandApp previewMode={true} />);

      fireEvent.click(screen.getByLabelText('Открыть Dynamic Island'));
      const shell = screen.getByTestId('dynamic-island-shell');
      expect(shell).toHaveClass('expanded');

      fireEvent.click(screen.getByLabelText('Свернуть остров'));
      expect(shell).toHaveClass('closing');
      expect(shell).not.toHaveClass('expanded');
      expect(screen.getByRole('tablist')).toBeInTheDocument();

      await vi.advanceTimersByTimeAsync(320);
      expect(shell).toHaveClass('collapsed');
      expect(shell).not.toHaveClass('closing');
    } finally {
      vi.useRealTimers();
    }
  });

  it('keeps volume slider --v progress CSS var in sync with volume level and omits drag tooltip', async () => {
    render(<IslandApp previewMode={true} />);
    fireEvent.click(screen.getByLabelText('Открыть Dynamic Island'));

    const slider = await screen.findByLabelText('Громкость');
    await waitFor(() => {
      expect(slider).toHaveValue('42');
      expect(slider.style.getPropertyValue('--v')).toBe('42%');
    });

    fireEvent.change(slider, { target: { value: '85' } });
    expect(slider.style.getPropertyValue('--v')).toBe('85%');

    const dragHandle = screen.getByTestId('island-drag-handle');
    expect(dragHandle).not.toHaveAttribute('title');
  });

  it('allows adding and removing commands in Quick Actions without including protocols', async () => {
    const { apiPost } = await import('../services/api');
    render(<IslandApp previewMode={true} />);
    fireEvent.click(screen.getByLabelText('Открыть Dynamic Island'));

    await waitFor(() => {
      expect(screen.getByText('Скриншот')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Настроить' }));
    const zapretBtn = await screen.findByRole('button', { name: /Запрет Discord\/YouTube/i });
    const binBtn = screen.getByRole('button', { name: /Корзина/i });

    // Protocols must never appear inside Quick Actions settings
    expect(screen.queryByRole('button', { name: /Игровой режим/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Протокол «Игра»/i })).not.toBeInTheDocument();

    // Add Zapret command and remove Recycle Bin
    fireEvent.click(zapretBtn);
    fireEvent.click(binBtn);
    fireEvent.click(screen.getByRole('button', { name: 'Готово' }));

    expect(screen.getByRole('button', { name: /Запрет Discord\/YouTube/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Корзина' })).not.toBeInTheDocument();

    const savedConfig = JSON.parse(localStorage.getItem('kirieshcka_island_config'));
    expect(savedConfig.quickActions).toContain('cmd:zapret_start');
    expect(savedConfig.quickActions).not.toContain('sys:empty_bin');

    fireEvent.click(screen.getByRole('button', { name: /Запрет Discord\/YouTube/i }));
    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith('/api/commands/execute', { command: 'запрет' });
    });
  });
});
