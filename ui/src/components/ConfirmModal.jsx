import React from 'react';
import { Icon } from './Icons';

export default function ConfirmModal({
  isOpen,
  title = 'Подтверждение действия',
  message = 'Вы уверены, что хотите продолжить?',
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  isDanger = true,
  onConfirm,
  onClose,
}) {
  if (!isOpen) return null;

  return (
    <div className="confirm-modal-overlay" onClick={onClose}>
      <div
        className="confirm-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="confirm-modal-header">
          <div className={`confirm-modal-icon-wrap ${isDanger ? 'danger' : 'accent'}`}>
            <Icon name={isDanger ? 'exit' : 'alert'} />
          </div>
          <div className="confirm-modal-titles">
            <h3 className="confirm-modal-title">{title}</h3>
            <p className="confirm-modal-desc">{message}</p>
          </div>
        </div>

        <div className="confirm-modal-actions">
          <button
            type="button"
            className="btn-secondary confirm-btn-cancel"
            onClick={onClose}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={isDanger ? 'btn-danger confirm-btn-action' : 'btn-primary confirm-btn-action'}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
