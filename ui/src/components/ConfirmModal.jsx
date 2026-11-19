import React from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';
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

  const modalContent = (
    <motion.div
      className="confirm-modal-overlay"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.16 }}
    >
      <motion.div
        className="confirm-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        initial={{ opacity: 0, scale: 0.92, y: 14 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 460, damping: 28 }}
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
          <motion.button
            type="button"
            className="btn-secondary confirm-btn-cancel"
            onClick={onClose}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.94 }}
          >
            {cancelText}
          </motion.button>
          <motion.button
            type="button"
            className={isDanger ? 'btn-danger confirm-btn-action' : 'btn-primary confirm-btn-action'}
            onClick={onConfirm}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.94 }}
          >
            {confirmText}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );

  if (typeof document !== 'undefined' && document.body) {
    return createPortal(modalContent, document.body);
  }

  return modalContent;
}
