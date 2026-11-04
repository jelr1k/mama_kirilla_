import React, { useState, useEffect } from 'react';
import { apiFetch } from '../services/api';
import { Icon } from './Icons';

export default function AppsSubtab({ onAddAliasForApp }) {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [statusMsg, setStatusMsg] = useState(null);

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const fetchApps = async (force = false) => {
    try {
      if (force) setRefreshing(true);
      else setLoading(true);

      const endpoint = force ? '/api/apps/refresh' : '/api/apps';
      const method = force ? 'POST' : 'GET';
      const res = await apiFetch(endpoint, { method });
      const data = await res.json();
      setApps(data.apps || []);
      if (force) {
        showStatus(`Найдено программ: ${data.total || (data.apps && data.apps.length) || 0}`);
      }
    } catch (err) {
      console.error('Failed to load apps:', err);
      showStatus('Ошибка сканирования установленных программ', true);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchApps();
  }, []);

  const handleLaunch = async (app) => {
    try {
      const res = await apiFetch('/api/apps/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app: app.name, path: app.shortcut || app.executable }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus(`Запускаю «${app.name}»...`);
      } else {
        showStatus(data.error || 'Ошибка запуска приложения', true);
      }
    } catch (err) {
      showStatus('Не удалось запустить приложение', true);
    }
  };

  const filtered = apps.filter((app) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    const nameMatch = (app.name || '').toLowerCase().includes(q);
    const exeMatch = (app.executable || app.shortcut || '').toLowerCase().includes(q);
    const aliasMatch = (app.aliases || []).some((a) => a.toLowerCase().includes(q));
    return nameMatch || exeMatch || aliasMatch;
  });

  return (
    <div className="websites-container apps-subtab-container">
      <header className="page-header">
        <div className="header-left">
          <h1 className="page-title">Программы ПК (App Indexer)</h1>
          <p className="page-desc">
            Автоматически обнаруженный софт из меню «Пуск» и реестра Windows. Запуск голосом без ручной настройки путей.
          </p>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={() => fetchApps(true)}
            disabled={refreshing || loading}
            title="Пересканировать установленный софт"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Icon name="sparkles" />
            <span>{refreshing ? 'Сканирование...' : 'Обновить софт'}</span>
          </button>
        </div>
      </header>

      {statusMsg && (
        <div className={`status-banner ${statusMsg.isError ? 'error' : 'success'}`}>
          <Icon name={statusMsg.isError ? 'bell' : 'check'} />
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Search Toolbar */}
      <div className="toolbar-row">
        <div className="search-bar" style={{ maxWidth: '420px', width: '100%' }}>
          <Icon name="search" />
          <input
            type="text"
            className="search-input"
            placeholder="Ищи Discord, OBS, Photoshop, Steam..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="clear-btn" onClick={() => setSearch('')}>
              ×
            </button>
          )}
        </div>
        <div className="apps-count-badge" style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Всего софта: <strong>{apps.length}</strong> {filtered.length !== apps.length && `(найдено: ${filtered.length})`}
        </div>
      </div>

      {/* Grid of applications */}
      {loading ? (
        <div className="empty-state">
          <p>Сканирование установленного софта на ПК...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <Icon name="game" />
          <p>{search ? 'По запросу ничего не найдено' : 'Программы не найдены'}</p>
        </div>
      ) : (
        <div className="alias-grid">
          {filtered.map((app) => (
            <div key={app.id || app.name} className="alias-card">
              <div className="alias-card-header">
                <div className="alias-target-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="game" />
                  <span style={{ fontWeight: 600 }} title={app.name}>
                    {app.name}
                  </span>
                </div>
                <div className="card-actions" style={{ display: 'flex', gap: '4px' }}>
                  <button
                    className="action-icon-btn"
                    title="Запустить программу"
                    onClick={() => handleLaunch(app)}
                    style={{ color: 'var(--accent, #00f0ff)' }}
                  >
                    <Icon name="play" />
                  </button>
                  {onAddAliasForApp && (
                    <button
                      className="action-icon-btn"
                      title="Добавить кастомный алиас"
                      onClick={() => onAddAliasForApp(app)}
                    >
                      <Icon name="plus" />
                    </button>
                  )}
                </div>
              </div>

              <div
                className="alias-meta"
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  marginTop: '4px',
                  marginBottom: '8px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                title={app.executable || app.shortcut}
              >
                {app.executable || app.shortcut}
              </div>

              <div className="alias-triggers">
                <div className="triggers-label" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Голосовые фразы:
                </div>
                <div className="trigger-tags" style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {(app.aliases || []).slice(0, 6).map((al, idx) => (
                    <span key={idx} className="tag" style={{ fontSize: '0.78rem' }}>
                      {al}
                    </span>
                  ))}
                  {(app.aliases || []).length > 6 && (
                    <span className="tag" style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                      +{(app.aliases || []).length - 6}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
