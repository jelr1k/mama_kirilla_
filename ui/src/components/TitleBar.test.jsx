import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TitleBar from './TitleBar';

describe('TitleBar component', () => {
  it('renders application title and status dot', () => {
    render(<TitleBar title="Test App" connected={true} />);
    expect(screen.getByText('Test App')).toBeInTheDocument();
    const statusDot = document.querySelector('.titlebar-status-dot');
    expect(statusDot).toHaveClass('online');
  });

  it('renders offline status when disconnected', () => {
    render(<TitleBar title="Test App" connected={false} />);
    const statusDot = document.querySelector('.titlebar-status-dot');
    expect(statusDot).toHaveClass('offline');
  });

  it('calls onToggleCompact when compact toggle is clicked', () => {
    const handleToggle = vi.fn();
    render(
      <TitleBar
        title="Test App"
        compact={false}
        onToggleCompact={handleToggle}
        connected={true}
      />
    );
    const compactBtn = screen.getByLabelText('Компактный режим');
    fireEvent.click(compactBtn);
    expect(handleToggle).toHaveBeenCalledTimes(1);
  });

  it('calls onToggleIsland independently from compact toggle', () => {
    const handleCompact = vi.fn();
    const handleIsland = vi.fn();
    render(
      <TitleBar
        title="Test App"
        compact={false}
        onToggleCompact={handleCompact}
        islandEnabled={true}
        onToggleIsland={handleIsland}
        connected={true}
      />
    );
    const islandBtn = screen.getByLabelText('Dynamic Island');
    expect(islandBtn).toHaveClass('active');
    fireEvent.click(islandBtn);
    expect(handleIsland).toHaveBeenCalledTimes(1);
    expect(handleCompact).not.toHaveBeenCalled();
  });
});
