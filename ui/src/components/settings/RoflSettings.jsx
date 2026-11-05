import React from 'react';
import { Icon } from '../Icons';
import { Tip } from './common';

export default function RoflSettings({
  roflUnlocked,
  setRoflUnlocked,
  roflSecret,
  handleCheckRoflSecret,
  roflChance,
  setRoflChance,
  roflDemonChance,
  setRoflDemonChance,
  handleResetRofl,
  handleSaveRofl,
  roflSaving,
}) {
  return (
    <div className="settings-card">
      <div className="card-section-title">
        <Icon name="sparkles" />
        <span>Служебные настройки (Юмор и пасхалки)</span>
      </div>

      {!roflUnlocked ? (
        <div className="settings-row">
          <div className="row-label">
            Служебное слово
            <Tip text="Введите секретное служебное слово для доступа к тонкой настройке юмора ассистента." />
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="password"
              className="text-input"
              placeholder="Служебное слово..."
              value={roflSecret}
              onChange={(e) => handleCheckRoflSecret(e.target.value)}
              style={{ width: '180px' }}
            />
            <button
              className="btn-secondary"
              onClick={() => handleCheckRoflSecret(roflSecret)}
            >
              Ввод
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '10px' }}>
          <div className="settings-row">
            <div className="row-label">
              Шанс обычного рофла: <strong>{roflChance.toFixed(1)}%</strong>
              <Tip text="Вероятность саркастичного или шутливого комментария при выполнении системных команд." />
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={roflChance}
              onChange={(e) => setRoflChance(parseFloat(e.target.value))}
              className="range-slider"
              style={{ width: '180px' }}
            />
          </div>

          <div className="settings-row">
            <div className="row-label">
              Шанс демонического рофла: <strong>{roflDemonChance.toFixed(1)}%</strong>
              <Tip text="Вероятность особо дерзкого или мемного ответа." />
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={roflDemonChance}
              onChange={(e) => setRoflDemonChance(parseFloat(e.target.value))}
              className="range-slider"
              style={{ width: '180px' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
            <button className="btn-secondary" onClick={handleResetRofl}>
              Сбросить до дефолта
            </button>
            <button
              className="btn-secondary"
              onClick={() => setRoflUnlocked(false)}
            >
              Скрыть
            </button>
            <button
              className="btn-primary"
              onClick={handleSaveRofl}
              disabled={roflSaving}
            >
              <Icon name="check" />
              <span>Сохранить рофлы</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
