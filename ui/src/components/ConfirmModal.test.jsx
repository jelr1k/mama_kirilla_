import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ConfirmModal from './ConfirmModal';

describe('ConfirmModal component', () => {
  it('does not render when isOpen is false', () => {
    const { container } = render(
      <ConfirmModal
        isOpen={false}
        title="Удалить?"
        message="Вы уверены?"
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders modal details and handles confirm/close clicks', () => {
    const handleConfirm = vi.fn();
    const handleClose = vi.fn();

    render(
      <ConfirmModal
        isOpen={true}
        title="Подтверждение теста"
        message="Сообщение подтверждения"
        confirmText="Да, удалить"
        cancelText="Отмена"
        isDanger={true}
        onConfirm={handleConfirm}
        onClose={handleClose}
      />
    );

    expect(screen.getByText('Подтверждение теста')).toBeInTheDocument();
    expect(screen.getByText('Сообщение подтверждения')).toBeInTheDocument();

    const cancelBtn = screen.getByText('Отмена');
    fireEvent.click(cancelBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);

    const confirmBtn = screen.getByText('Да, удалить');
    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledTimes(1);
  });
});
