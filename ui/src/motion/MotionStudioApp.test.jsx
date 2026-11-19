import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MotionStudioApp from './MotionStudioApp';

describe('MotionStudioApp (Tactile Hardware Desk)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    HTMLCanvasElement.prototype.getContext = vi.fn(() => null);
  });

  it('renders hardware modules, toggles osc mode, expands protocol pad deck, and switches to classic', () => {
    const onSwitch = vi.fn();
    render(<MotionStudioApp assistantName="Kirieshka" onSwitchToClassic={onSwitch} />);

    expect(screen.getByTestId('motion-studio-shell')).toBeInTheDocument();
    expect(screen.getByText('VOICE OSC')).toBeInTheDocument();
    expect(screen.getByText('MASTER GAIN')).toBeInTheDocument();
    expect(screen.getByText('PROTO DECK')).toBeInTheDocument();

    fireEvent.click(screen.getByText('OSC: WAVE'));
    expect(screen.getByText('OSC: MATRIX')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Развернуть PROTO DECK'));
    expect(screen.getByText(/Проверка сети и шлюза/)).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('switch-to-classic-btn'));
    expect(onSwitch).toHaveBeenCalledTimes(1);
  });
});
