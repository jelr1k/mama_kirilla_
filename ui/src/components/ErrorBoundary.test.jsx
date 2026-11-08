import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ErrorBoundary } from './ErrorBoundary';

function ProblemChild({ shouldThrow }) {
  if (shouldThrow) {
    throw new Error('Test crash');
  }
  return <div>Всё в порядке</div>;
}

describe('ErrorBoundary component', () => {
  it('renders children when no errors occur', () => {
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Всё в порядке')).toBeInTheDocument();
  });

  it('catches render error and displays fallback UI', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Ошибка отображения раздела')).toBeInTheDocument();
    expect(screen.getByText(/Test crash/)).toBeInTheDocument();

    const retryBtn = screen.getByText('Попробовать снова');
    expect(retryBtn).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
