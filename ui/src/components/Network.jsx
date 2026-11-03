import React, { useEffect, useRef, useState } from 'react';
import { apiGet, apiPost } from '../services/api';
import { Icon } from './Icons';

const CLIENT_ORDER = ['happ', 'flclash'];

function PathLine({ path }) {
  if (!path) return null;
  return (
    <div
      className="vpn-path"
      title={path}
      style={{
        fontSize: '11px',
        color: 'var(--mut)',
        lineHeight: 1.3,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        background: 'rgba(255, 255, 255, 0.03)',
        padding: '3px 8px',
        borderRadius: '6px',
        border: '1px solid var(--bdr)',
        marginTop: '6px',
      }}
    >
      📁 {path}
    </div>
  );
}

export default function Network() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  // Network availability monitor state
  const [services, setServices] = useState([]);
  const [servicesSummary, setServicesSummary] = useState(null);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [lastCheckTime, setLastCheckTime] = useState(null);

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

  const loadServices = async (force = false) => {
    try {
      setServicesLoading(true);
      const data = await apiGet(`/api/network/services${force ? '?force=true' : ''}`);
      setServices(data?.services || []);
      setServicesSummary(data?.summary || null);
      setLastCheckTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load services availability:', err);
      showToast('Не удалось проверить доступность сервисов.');
    } finally {
      setServicesLoading(false);
    }
  };

  const refreshAll = async () => {
    await Promise.all([loadStatus(true), loadServices(true)]);
  };

  useEffect(() => {
    loadStatus();
    loadServices();
    return () => window.clearTimeout(toastTimer.current);
  }, []);

  const handleZapret = async () => {
    setBusy('zapret');
    try {
      const res = await apiPost('/api/vpn/zapret');
      showToast(res.message || res.error || 'Запускаю service.bat.');
      await loadStatus(true);
      setTimeout(() => loadServices(true), 2000);
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
      setTimeout(() => loadServices(true), 2500);
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
              Мониторинг доступности ключевых сервисов без прокси, автопоиск Happ, FlClashX и service.bat на ПК.
            </p>
          </div>
          <button className="btn-secondary" onClick={refreshAll} disabled={loading || servicesLoading}>
            <Icon name="refresh" />
            {loading || servicesLoading ? 'Обновляю...' : 'Проверить всё'}
          </button>
        </header>

        {/* --- Service Availability & DPI Monitor --- */}
        <div className="card" style={{ marginBottom: '20px', width: '100%' }}>
          <div className="card-top" style={{ alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="card-icon-box">
                <Icon name="web" />
              </div>
              <div>
                <div className="card-name" style={{ fontSize: '15px', margin: 0, fontWeight: 700 }}>
                  Монитор доступности сервисов и DPI
                </div>
                <div style={{ fontSize: '11px', color: 'var(--mut)', marginTop: '2px' }}>
                  Прямой пинг шлюзов. Таймаут или сброс указывает на блокировку провайдером.
                  {lastCheckTime && ` • Обновлено в ${lastCheckTime}`}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
              <span className={`card-hotkey ${
                servicesSummary?.status === 'all_ok'
                  ? 'status-ready'
                  : 'status-disabled'
              }`}>
                {servicesSummary?.status === 'all_ok'
                  ? '● Все сервисы доступны'
                  : servicesSummary?.status === 'issues_detected'
                  ? `● Блокировка DPI (${servicesSummary?.ok_count}/${servicesSummary?.total})`
                  : servicesLoading ? '● Проверка...' : '● Нет связи'}
              </span>
              <button
                className="btn-secondary"
                onClick={() => loadServices(true)}
                disabled={servicesLoading}
                style={{ padding: '5px 10px', fontSize: '12px' }}
                title="Принудительно протестировать задержку всех сервисов"
              >
                <Icon name="refresh" />
                {servicesLoading ? 'Тест...' : 'Пинг'}
              </button>
            </div>
          </div>

          <div className="card-body" style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--bdr)' }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '10px',
            }}>
              {services.map((svc) => {
                const isOk = svc.status === 'ok';
                const isSlow = svc.status === 'slow';
                const isBlocked = svc.status === 'blocked';
                const statusDotColor = isOk ? '#22c55e' : isSlow ? '#eab308' : isBlocked ? '#ef4444' : '#94a3b8';

                return (
                  <div
                    key={svc.id}
                    style={{
                      background: 'var(--bg-elevated, rgba(255, 255, 255, 0.03))',
                      border: '1px solid var(--bdr)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--txt)' }}>
                        {svc.name}
                      </span>
                      <span
                        style={{
                          width: '9px',
                          height: '9px',
                          borderRadius: '50%',
                          backgroundColor: statusDotColor,
                          boxShadow: isOk ? '0 0 8px rgba(34, 197, 94, 0.6)' : isBlocked ? '0 0 8px rgba(239, 68, 68, 0.6)' : 'none',
                        }}
                      />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '2px' }}>
                      <span style={{
                        fontSize: '14px',
                        fontWeight: 700,
                        color: isOk ? '#22c55e' : isSlow ? '#eab308' : '#ef4444',
                        fontFamily: 'monospace',
                      }}>
                        {svc.ping_ms !== null ? `${svc.ping_ms} мс` : '—'}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--mut)' }}>
                        {svc.message}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* --- VPN Clients & Zapret Grid --- */}
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div className="card" style={{ '--n': 0, minHeight: 'unset' }}>
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
                Обход замедления и блокировок через winws.
              </div>
              <PathLine path={zapret?.path} />
            </div>
            <div className="card-footer">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', textAlign: 'left' }}>
                <span className={`card-status ${zapret?.running ? 'status-ready' : 'status-disabled'}`}>
                  ● winws: {zapret?.running ? 'работает' : 'не запущен'}
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
              <div className="card" key={clientId} style={{ '--n': index + 1, minHeight: 'unset' }}>
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
                      ? 'VPN-клиент с быстрым системным подключением.'
                      : 'Clash-прокси с подключением через интерфейс.'}
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
