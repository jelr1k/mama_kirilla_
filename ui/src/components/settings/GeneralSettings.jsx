import React from 'react';
import { Icon } from '../Icons';
import { Tip, Toggle } from './common';

export default function GeneralSettings({
  appTitle,
  setAppTitle,
  assistantName,
  setAssistantName,
  autostart,
  setAutostart,
  theme,
  setTheme,
}) {
  return (
    <div className="settings-card">
      <div className="card-section-title">
        <Icon name="sparkles" />
        <span>Общие параметры</span>
      </div>

      <div className="settings-row">
        <div className="row-label">
          Именование приложения
          <Tip text="Название окна приложения и заголовок в верхней панели." />
        </div>
        <input
          type="text"
          className="text-input"
          style={{ width: '220px' }}
          value={appTitle}
          onChange={(e) => setAppTitle(e.target.value)}
          placeholder="Kirieshcka v2"
        />
      </div>

      <div className="settings-row">
        <div className="row-label">
          Имя ассистента
          <Tip text="Имя, которое отображается в окне, заголовках и интерфейсе." />
        </div>
        <input
          type="text"
          className="text-input"
          style={{ width: '220px' }}
          value={assistantName}
          onChange={(e) => setAssistantName(e.target.value)}
          placeholder="Kirieshcka"
        />
      </div>

      <div className="settings-row">
        <div className="row-label">
          Тема оформления
          <Tip text="Переключение между глубокой тёмной темой (OLED / Pitch Black) и дефолтной темой (индиго-киберпанк)." />
        </div>
        <select
          className="select-input"
          style={{ width: '220px' }}
          value={theme || 'dark'}
          onChange={(e) => setTheme(e.target.value)}
          data-testid="theme-select"
        >
          <option value="dark">Тёмная (Full Dark / OLED)</option>
          <option value="default">Дефолтная (Индиго-киберпанк)</option>
        </select>
      </div>

      <div className="settings-row">
        <div className="row-label">
          Автозапуск с Windows
          <Tip text="Запуск фонового демона и UI при входе в систему (запись в реестр HKCU\\...\\Run)." />
        </div>
        <Toggle value={autostart} onChange={setAutostart} label="Автозапуск" />
      </div>
    </div>
  );
}
