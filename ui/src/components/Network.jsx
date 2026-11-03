import React, { useEffect, useRef, useState } from 'react';
import { apiGet, apiPost } from '../services/api';
import { Icon } from './Icons';

const CLIENT_ORDER = ['happ', 'flclash'];

function PathLine({ path }) {
  if (!path) return null;
  return (
    <div className="vpn-path" style={{ wordBreak: 'break-all', fontSize: '11px', color: 'var(--mut)', lineHeight: 1.4 }}>
      {path}
    </div>
  );
}

export default function Network() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  const showToast = (message) => {
    setToast(message);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 5000);
  };

  const loadStatus = async (force = false) => {
    try {
      setLoading(true);
      const data = await apiGet(`/api/vpn/status${force ? '?force=true' : ''}`);
      setStatus(data);
    } catch (err) {
      console.error('Failed to load VPN status:', err);
      showToast('Не удалось получить статус VPN.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    return () => window.clearTimeout(toastTimer.current);
  }, []);

  const handleZapret = async () => {
    setBusy('zapret');
    try {
      const res = await apiPost('/api/vpn/zapret');
      showToast(res.message || res.error || 'Запускаю service.bat.');
      await loadStatus(true);
    } catch (err) {
      showToast('Не удалось открыть service.bat.');
    } finally {
      setBusy(null);
    }
  };

  const handleConnect = async (client) => {
    setBusy(client);
    try {
      const res = await apiPost('/api/vpn/connect', { client });
      showToast(res.message || res.error || 'Запускаю VPN.');
      await loadStatus(true);
    } catch (err) {
      showToast('Не удалось запустить VPN.');
    } finally {
      setBusy(null);
    }
  };

  const zapret = status?.zapret;
  const clients = status?.clients || {};

  return (
    <div className="page standard-page">
      <div className="page-container">
        {toast && <div className="executed-toast">{toast}</div>}

        <header className="page-header">
          <div>
            <h2 className="page-title">Сеть и обход блокировок</h2>
            <p className="page-desc">
              JARVIS сам ищет Happ, FlClashX и service.bat в типовых местах на этом компьютере.
              Никаких жёстко прописанных путей.
            </p>
          </div>
          <button className="btn-secondary" onClick={() => loadStatus(true)} disabled={loading}>
            <Icon name="refresh" />
            Проверить снова
          </button>
        </header>

        <div className="grid">
          <div className="card" style={{ '--n': 0 }}>
            <div className="card-top">
              <div className="card-icon-box">
                <Icon name="shield" />
              </div>
              <span className={`card-hotkey ${zapret?.found ? 'status-ready' : 'status-disabled'}`}>
                {zapret?.found ? (zapret?.source === 'disk' ? 'на диске' : 'в архиве') : 'не найден'}
              </span>
            </div>
            <div className="card-body">
              <div className="card-name">Запрет Discord и YouTube</div>
              <div className="card-desc">
                Открывает окно service.bat из сборки Запрета. Если сборка уже есть на диске,
                запускает прямо оттуда. Если лежит только архив, распакует в данные JARVIS.
              </div>
              <PathLine path={zapret?.path} />
            </div>
            <div className="card-footer">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', textAlign: 'left' }}>
                <span className={`card-status ${zapret?.running ? 'status-ready' : 'status-disabled'}`}>
                  ● Служба winws: {zapret?.running ? 'работает' : 'не запущена'}
                </span>
                <span className="card-status status-disabled">
                  ● Источник: {zapret?.source === 'disk' ? 'папка на диске' : zapret?.source === 'archive' ? 'архив zip' : 'не найден'}
                </span>
              </div>
              <button
                className="btn-primary"
                onClick={handleZapret}
                disabled={busy !== null}
                title="Открыть service.bat"
              >
                <Icon name="zap" />
                {busy === 'zapret' ? 'Открываю...' : 'Открыть service.bat'}
              </button>
            </div>
          </div>

          {CLIENT_ORDER.map((clientId, index) => {
            const client = clients[clientId];
            if (!client) return null;
            return (
              <div className="card" key={clientId} style={{ '--n': index + 1 }}>
                <div className="card-top">
                  <div className="card-icon-box">
                    <Icon name="web" />
                  </div>
                  <span className={`card-hotkey ${client.found ? 'status-ready' : 'status-disabled'}`}>
                    {client.found ? 'найден' : 'не найден'}
                  </span>
                </div>
                <div className="card-body">
                  <div className="card-name">{client.label}</div>
                  <div className="card-desc">
                    {clientId === 'happ'
                      ? 'Запускает Happ и отправляет команду подключения через happ://connect.'
                      : 'Запускает FlClashX и нажимает кнопку подключения через UI Automation.'}
                  </div>
                  <PathLine path={client.path} />
                </div>
                <div className="card-footer">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', textAlign: 'left' }}>
                    <span className={`card-status ${client.gui_running ? 'status-ready' : 'status-disabled'}`}>
                      ● Окно: {client.gui_running ? 'открыто' : 'закрыто'}
                    </span>
                    <span className={`card-status ${client.vpn_running ? 'status-ready' : 'status-disabled'}`}>
                      ● ВПН: {client.vpn_running ? 'работает' : 'не активен'}
                    </span>
                  </div>
                  <button
                    className="btn-primary"
                    onClick={() => handleConnect(clientId)}
                    disabled={busy !== null || !client.found}
                    title={client.found ? `Запустить ${client.label} и подключить VPN` : 'Клиент не найден'}
                  >
                    <Icon name="power" />
                    {busy === clientId ? 'Запускаю...' : 'Запустить и подключить'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="status-banner" style={{ marginBottom: 0 }}>
          <Icon name="lock" />
          <span>
            Если файл не найден, JARVIS покажет сообщение «{status?.not_found_message || 'Не удалось определить местоположение нужных файлов.'}».
            Для Happ используется официальная команда подключения, для FlClashX — автоматическое нажатие кнопки.
          </span>
        </div>
      </div>
    </div>
  );
}
