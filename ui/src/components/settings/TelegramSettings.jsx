import React from 'react';
import { Icon } from '../Icons';
import { Tip, Toggle } from './common';

export default function TelegramSettings({
  telegramEnabled,
  setTelegramEnabled,
  telegramToken,
  setTelegramToken,
  handleTestTelegramToken,
  telegramTesting,
  telegramTestResult,
  setTelegramTestResult,
  telegramApiUrl,
  setTelegramApiUrl,
  telegramAllowedChats,
  setTelegramAllowedChats,
  telegramNotifyStartup,
  setTelegramNotifyStartup,
  telegramBotInfo,
}) {
  return (
    <div className="settings-card">
      <div className="card-section-title">
        <Icon name="send" />
        <span>Telegram Бот (Удалённое управление ПК)</span>
      </div>

      <div className="settings-row">
        <div className="row-label">
          Включить Telegram-бота
          <Tip text="Позволяет удалённо запрашивать статус ПК, мониторить VPN, делать скриншоты экрана, отправлять в спящий режим и выключать компьютер через Telegram." />
        </div>
        <Toggle
          value={telegramEnabled}
          onChange={setTelegramEnabled}
          label="Включить Telegram-бота"
        />
      </div>

      {telegramEnabled && (
        <>
          <div className="settings-row">
            <div className="row-label">
              Токен бота (BotFather)
              <Tip text="Токен бота Telegram, полученный у @BotFather в Telegram." />
            </div>
            <div style={{ display: 'flex', gap: '8px', flex: 1, maxWidth: '420px' }}>
              <input
                type="password"
                className="text-input"
                placeholder="123456789:ABCDefgh..."
                value={telegramToken}
                onChange={(e) => {
                  setTelegramToken(e.target.value);
                  setTelegramTestResult(null);
                }}
                style={{ flex: 1 }}
              />
              <button
                className="btn-secondary"
                onClick={handleTestTelegramToken}
                disabled={telegramTesting || !telegramToken.trim()}
                style={{ whiteSpace: 'nowrap' }}
              >
                {telegramTesting ? 'Проверка...' : 'Проверить'}
              </button>
            </div>
          </div>

          {telegramTestResult && (
            <div className="settings-row" style={{ paddingTop: 0 }}>
              <div className="row-label" />
              <span style={{
                fontSize: '12px',
                color: telegramTestResult.success ? '#22c55e' : '#ef4444',
                fontWeight: 600,
              }}>
                {telegramTestResult.success ? '● ' : '✕ '}
                {telegramTestResult.text}
              </span>
            </div>
          )}

          <div className="settings-row">
            <div className="row-label">
              Telegram API URL / Worker
              <Tip text="По умолчанию https://api.telegram.org. Если в РФ заблокирован IP Telegram, укажите адрес своего бесплатного Cloudflare Worker (например https://my-bot.workers.dev)." />
            </div>
            <input
              type="text"
              className="text-input"
              placeholder="https://api.telegram.org"
              value={telegramApiUrl}
              onChange={(e) => {
                setTelegramApiUrl(e.target.value);
                setTelegramTestResult(null);
              }}
              style={{ maxWidth: '420px', width: '100%' }}
            />
          </div>

          <div className="settings-row">
            <div className="row-label">
              Разрешённые Telegram Chat ID
              <Tip text="Список числовых ID пользователей через запятую. Бот не выполняет команды от посторонних. Напишите боту /start — он выдаст ваш Chat ID." />
            </div>
            <input
              type="text"
              className="text-input"
              placeholder="123456789, 987654321"
              value={telegramAllowedChats}
              onChange={(e) => setTelegramAllowedChats(e.target.value)}
              style={{ maxWidth: '420px', width: '100%' }}
            />
          </div>

          <div className="settings-row">
            <div className="row-label">
              Оповещать в Telegram при запуске ПК
              <Tip text="Отправлять сообщение в разрешённые чаты при старте приложения Kirieshcka v2." />
            </div>
            <Toggle
              value={telegramNotifyStartup}
              onChange={setTelegramNotifyStartup}
              label="Оповещать при старте"
            />
          </div>

          {telegramBotInfo && (
            <div className="settings-row" style={{ borderTop: '1px solid var(--bdr)', paddingTop: '10px' }}>
              <div className="row-label" style={{ fontSize: '12px', color: 'var(--mut)' }}>
                Текущий статус службы
              </div>
              <span style={{ fontSize: '12px', color: telegramBotInfo.running ? '#22c55e' : 'var(--mut)' }}>
                ● {telegramBotInfo.running
                  ? `Работает (@${telegramBotInfo.bot_username || 'бот'})`
                  : (telegramBotInfo.configured ? 'Остановлен (сохраните настройки для запуска)' : 'Токен не настроен')}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
