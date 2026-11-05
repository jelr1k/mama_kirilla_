import React from 'react';
import { Icon } from '../Icons';

export default function DangerZone({ handleShutdown }) {
  return (
    <div className="danger-zone-card">
      <div className="danger-content">
        <div>
          <h4 className="danger-title">Завершить работу приложения</h4>
          <p className="danger-desc">
            Полная остановка фонового ядра, освобождение микрофона и закрытие окна.
          </p>
        </div>
        <button className="btn-danger" onClick={handleShutdown}>
          <Icon name="exit" />
          <span>Завершить работу</span>
        </button>
      </div>
    </div>
  );
}
