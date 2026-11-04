import React, { useState, useEffect } from 'react';
import { apiFetch } from '../services/api';
import { Icon } from './Icons';

export default function AppsSubtab({ onAddAliasForApp }) {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [statusMsg, setStatusMsg] = useState(null);
  const [viewMode, setViewMode] = useState(() => {
    return localStorage.getItem('apps_subtab_view_mode') || 'list';
  });

  const handleSetViewMode = (mode) => {
    setViewMode(mode);
    localStorage.setItem('apps_subtab_view_mode', mode);
  };

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
    <div className="websites-container apps-subtab-container apps-animated-wrapper">
      <header className="page-header">
        <div className="header-left">
          <h1 className="page-title">Программы ПК (App Indexer)</h1>
          <p className="page-desc">
            Автоматически обнаруженный софт из меню «Пуск» и реестра Windows. Запуск голосом без ручной настройки путей.
          </p>
        </div>
        <div className="header-actions">
          {/* View mode toggle */}
          <div className="view-mode-toggle">
            <button
              type="button"
              className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => handleSetViewMode('list')}
              title="Отображение компактным списком"
            >
              <Icon name="cmd" />
              <span>Списком</span>
            </button>
            <button
              type="button"
              className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => handleSetViewMode('grid')}
              title="Отображение карточками"
            >
              <Icon name="sparkles" />
              <span>Карточками</span>
            </button>
          </div>

          <button
            type="button"
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
            <button type="button" className="clear-btn" onClick={() => setSearch('')}>
              ×
            </button>
          )}
        </div>
        <div className="apps-count-badge" style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Всего софта: <strong>{apps.length}</strong> {filtered.length !== apps.length && `(найдено: ${filtered.length})`}
        </div>
      </div>

      {/* List / Grid of applications */}
      {loading ? (
        <div className="empty-state">
          <Icon name="refresh" className="spin-icon" />
          <p>Сканирование установленного софта на ПК...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <Icon name="game" />
          <p>{search ? 'По запросу ничего не найдено' : 'Программы не найдены'}</p>
        </div>
      ) : viewMode === 'list' ? (
        /* Compact List (Table) Mode */
        <div className="apps-list-table apps-animated-appear">
          <div className="apps-table-header">
            <span className="col-app-name">Программа</span>
            <span className="col-app-path">Путь (EXE / Ярлык)</span>
            <span className="col-app-triggers">Голосовые фразы</span>
            <span className="col-app-actions">Действия</span>
          </div>
          {filtered.map((app, index) => (
            <div
              key={app.id || app.executable || app.name}
              className="apps-table-row"
              style={{ animationDelay: `${Math.min(index * 15, 300)}ms` }}
            >
              <div className="col-app-name" title={app.name}>
                <Icon name="game" />
                <span className="app-row-title">{app.name}</span>
              </div>
              <div className="col-app-path" title={app.executable || app.shortcut}>
                <span className="app-path-text">{app.executable || app.shortcut}</span>
              </div>
              <div className="col-app-triggers">
                {(app.aliases || []).length > 0 ? (
                  <div className="apps-chips-inline">
                    {(app.aliases || []).slice(0, 4).map((al, idx) => (
                      <span key={idx} className="app-trigger-chip">
                        «{al}»
                      </span>
                    ))}
                    {(app.aliases || []).length > 4 && (
                      <span className="app-trigger-more">
                        +{(app.aliases || []).length - 4}
                      </span>
                    )}
                  </div>
                ) : (
                  <span style={{ color: 'var(--muted)', fontSize: '11px' }}>—</span>
                )}
              </div>
              <div className="col-app-actions">
                <button
                  type="button"
                  className="btn-table-action play"
                  title="Запустить программу"
                  onClick={() => handleLaunch(app)}
                >
                  <Icon name="play" />
                  <span>Запуск</span>
                </button>
                {onAddAliasForApp && (
                  <button
                    type="button"
                    className="btn-table-action"
                    title="Добавить кастомный алиас"
                    onClick={() => onAddAliasForApp(app)}
                  >
                    <Icon name="plus" />
                    <span>Алиас</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Compact Grid Mode */
        <div className="apps-grid-compact apps-animated-appear">
          {filtered.map((app, index) => (
            <div
              key={app.id || app.executable || app.name}
              className="app-compact-card"
              style={{ animationDelay: `${Math.min(index * 15, 300)}ms` }}
            >
              <div className="app-compact-header">
                <div className="app-compact-title-wrap" title={app.name}>
                  <Icon name="game" />
                  <span className="app-compact-title">{app.name}</span>
                </div>
                <div className="app-compact-actions">
                  <button
                    type="button"
                    className="action-icon-btn"
                    title="Запустить программу"
                    onClick={() => handleLaunch(app)}
                    style={{ color: 'var(--accent, #00f0ff)' }}
                  >
                    <Icon name="play" />
                  </button>
                  {onAddAliasForApp && (
                    <button
                      type="button"
                      className="action-icon-btn"
                      title="Добавить кастомный алиас"
                      onClick={() => onAddAliasForApp(app)}
                    >
                      <Icon name="plus" />
                    </button>
                  )}
                </div>
              </div>

              <div className="app-compact-path" title={app.executable || app.shortcut}>
                {app.executable || app.shortcut}
              </div>

              <div className="app-compact-triggers">
                {(app.aliases || []).slice(0, 5).map((al, idx) => (
                  <span key={idx} className="app-trigger-chip">
                    «{al}»
                  </span>
                ))}
                {(app.aliases || []).length > 5 && (
                  <span className="app-trigger-more">
                    +{(app.aliases || []).length - 5}
                  </span>
                )}
                {(!app.aliases || app.aliases.length === 0) && (
                  <span style={{ color: 'var(--muted)', fontSize: '11px' }}>Нет фраз</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
