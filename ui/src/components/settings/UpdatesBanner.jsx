import React from 'react';
import { Icon } from '../Icons';

export default function UpdatesBanner({
  updateAvailable,
  latestVersion,
  currentVersion,
  archiveSize,
  releaseUrl,
  handleApplyUpdate,
  applyingUpdate,
  updateStatus,
  updateProgress,
  updateSpeed,
}) {
  if (!updateAvailable) return null;

  return (
    <div
      className="status-banner success"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        padding: '14px 16px',
        background: 'rgba(14, 165, 233, 0.08)',
        border: '1px solid rgba(14, 165, 233, 0.3)',
        borderRadius: '8px',
        marginBottom: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Icon name="sparkles" />
          <span>
            Доступно обновление <strong>v{latestVersion}</strong> (у вас v{currentVersion})
            {archiveSize > 0 && ` • ${(archiveSize / (1024 * 1024)).toFixed(1)} МБ`}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {releaseUrl && (
            <a
              href={releaseUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              Релиз на GitHub
            </a>
          )}
          <button
            className="btn-primary"
            onClick={handleApplyUpdate}
            disabled={applyingUpdate}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Icon name="check" />
            <span>
              {applyingUpdate
                ? updateStatus === 'downloading'
                  ? `Скачивание ${updateProgress}% (${updateSpeed} МБ/с)`
                  : updateStatus === 'validating'
                  ? 'Проверка архива...'
                  : updateStatus === 'backing_up'
                  ? 'Создание бэкапа...'
                  : updateStatus === 'relaunching'
                  ? 'Перезапуск...'
                  : 'Установка...'
                : 'Скачать и установить в 1 клик'}
            </span>
          </button>
        </div>
      </div>

      {applyingUpdate && (
        <div style={{ width: '100%', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'hidden', height: '6px' }}>
          <div
            style={{
              width: `${updateProgress}%`,
              height: '100%',
              background: '#0ea5e9',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      )}
    </div>
  );
}
