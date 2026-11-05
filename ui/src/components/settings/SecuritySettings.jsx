import React from 'react';
import { Icon } from '../Icons';
import { Tip, Toggle } from './common';

export default function SecuritySettings({
  allowOutsideWorkspace,
  setAllowOutsideWorkspace,
}) {
  return (
    <div className="settings-card">
      <div className="card-section-title">
        <Icon name="shield" />
        <span>Безопасность и Доступ</span>
      </div>

      <div className="settings-row">
        <div className="row-label">
          Разрешить запуск приложений вне Workspace
          <Tip text="Позволяет ассистенту запускать любые системные программы, а не только файлы из песочницы." />
        </div>
        <Toggle
          value={allowOutsideWorkspace}
          onChange={setAllowOutsideWorkspace}
          label="Доступ вне Workspace"
        />
      </div>
    </div>
  );
}
