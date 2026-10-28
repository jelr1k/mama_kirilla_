import { apiFetch } from '../services/api';
import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';

export default function WebsitesSubtab() {
  const [websites, setWebsites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);

  // Form fields
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [aliasesText, setAliasesText] = useState('');
  const [autoAliases, setAutoAliases] = useState(true);

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const resetForm = () => {
    setName('');
    setUrl('');
    setAliasesText('');
    setAutoAliases(true);
  };

  const fetchWebsites = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/api/websites');
      const data = await res.json();
      setWebsites(data.websites || []);
    } catch (err) {
      console.error('Failed to load websites:', err);
      showStatus('Ошибка загрузки сайтов', true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWebsites();
  }, []);

  const handleOpen = async (site) => {
    try {
      await apiFetch('/api/websites/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site_id: site.id, url: site.url }),
      });
      showStatus(`Открываю «${site.name}»...`);
    } catch (e) {
      showStatus('Ошибка открытия ссылки', true);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) {
      showStatus('Заполните название и URL', true);
      return;
    }

    const aliases = aliasesText
      .split('\n')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);

    try {
      if (editingSite) {
        const res = await apiFetch(`/api/websites/${editingSite.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, url, aliases }),
        });
        const data = await res.json();
        if (data.success) {
          showStatus(`Сайт «${name}» обновлен`);
          setEditingSite(null);
          resetForm();
          fetchWebsites();
        } else {
          showStatus(data.error || 'Ошибка сохранения', true);
        }
      } else {
        const res = await apiFetch('/api/websites', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, url, aliases, auto_aliases: autoAliases }),
        });
        const data = await res.json();
        if (data.success) {
          showStatus(`Сайт «${name}» добавлен`);
          setIsAdding(false);
          resetForm();
          fetchWebsites();
        } else {
          showStatus(data.error || 'Ошибка добавления', true);
        }
      }
    } catch (err) {
      showStatus('Сетевая ошибка при сохранении', true);
    }
  };

  const handleDelete = async (site) => {
    if (!window.confirm(`Удалить сайт «${site.name}» и его алиасы?`)) return;
    try {
      const res = await apiFetch(`/api/websites/${site.id}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        showStatus(`Сайт «${site.name}» удален`);
        fetchWebsites();
      }
    } catch (err) {
      showStatus('Ошибка при удалении', true);
    }
  };

  const handleResetDefaults = async () => {
    if (!window.confirm('Сбросить список сайтов до стандартных?')) return;
    try {
      const res = await apiFetch('/api/websites/reset', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showStatus('Список сайтов сброшен до дефолтных');
        setWebsites(data.websites || []);
      }
    } catch (err) {
      showStatus('Ошибка сброса', true);
    }
  };

  const startEdit = (site) => {
    setEditingSite(site);
    setName(site.name || '');
    setUrl(site.url || '');
    setAliasesText((site.aliases || []).join('\n'));
    setIsAdding(false);
  };



  const filtered = websites.filter((w) => {
    const q = search.toLowerCase();
    const nameMatch = (w.name || '').toLowerCase().includes(q);
    const urlMatch = (w.url || '').toLowerCase().includes(q);
    const aliasMatch = (w.aliases || []).some((a) => a.toLowerCase().includes(q));
    return nameMatch || urlMatch || aliasMatch;
  });

  return (
    <div className="websites-subtab">
      <div className="aliases-toolbar" style={{ marginTop: '16px' }}>
        <div className="search-box">
          <Icon name="sparkles" />
          <input
            type="text"
            className="search-input"
            placeholder="Поиск по названию сайта, ссылке или алиасам..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="search-clear" onClick={() => setSearch('')}>
              ✕
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn-secondary"
            onClick={handleResetDefaults}
            title="Восстановить стандартные сайты (YouTube, VK, GitHub...)"
          >
            Сброс
          </button>
          <button
            className="btn-primary"
            onClick={() => {
              resetForm();
              setEditingSite(null);
              setIsAdding(!isAdding);
            }}
          >
            <Icon name="check" />
            <span>{isAdding ? 'Отмена' : 'Добавить сайт'}</span>
          </button>
        </div>
      </div>

      {statusMsg && (
        <div
          className={`status-banner ${statusMsg.isError ? 'err' : 'ok'}`}
          style={{ marginBottom: '16px' }}
        >
          {statusMsg.text}
        </div>
      )}

      {/* Add / Edit Form */}
      {(isAdding || editingSite) && (
        <form
          className="alias-form-card"
          onSubmit={handleSave}
          style={{ marginBottom: '20px' }}
        >
          <div className="form-header">
            <h3>{editingSite ? `Редактирование «${editingSite.name}»` : 'Новый веб-сайт'}</h3>
            <button
              type="button"
              className="btn-close"
              onClick={() => {
                setIsAdding(false);
                setEditingSite(null);
                resetForm();
              }}
            >
              ✕
            </button>
          </div>

          <div className="form-grid">
            <div className="form-field">
              <label>Название сайта</label>
              <input
                type="text"
                placeholder="Например: YouTube, Кинопоиск, Git"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="form-field">
              <label>URL адрес ссылки</label>
              <input
                type="text"
                placeholder="https://..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
              />
            </div>

            <div className="form-field full-width">
              <label>
                Голосовые триггеры (по одной фразе на строку)
              </label>
              <textarea
                rows={3}
                placeholder="ютуб&#10;youtube&#10;видеохостинг"
                value={aliasesText}
                onChange={(e) => setAliasesText(e.target.value)}
              />
            </div>

            {!editingSite && (
              <div className="form-field" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="autoAliases"
                  checked={autoAliases}
                  onChange={(e) => setAutoAliases(e.target.checked)}
                />
                <label htmlFor="autoAliases" style={{ margin: 0, cursor: 'pointer' }}>
                  Сгенерировать русские транслитерации автоматически
                </label>
              </div>
            )}
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setIsAdding(false);
                setEditingSite(null);
                resetForm();
              }}
            >
              Отмена
            </button>
            <button type="submit" className="btn-primary">
              {editingSite ? 'Сохранить изменения' : 'Создать сайт'}
            </button>
          </div>
        </form>
      )}

      {/* Grid of websites */}
      {loading ? (
        <div className="empty-state">
          <p>Загрузка сайтов...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <Icon name="web" />
          <p>Веб-сайты не найдены</p>
        </div>
      ) : (
        <div className="alias-grid">
          {filtered.map((site) => (
            <div key={site.id} className="alias-card">
              <div className="alias-card-header">
                <div className="alias-target-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Icon name="web" />
                  <span style={{ fontWeight: 600 }}>{site.name}</span>
                </div>
                <div className="card-actions" style={{ display: 'flex', gap: '4px' }}>
                  <button
                    className="icon-action-btn"
                    title="Открыть ссылку в браузере"
                    onClick={() => handleOpen(site)}
                  >
                    <Icon name="sparkles" />
                  </button>
                  <button
                    className="icon-action-btn"
                    title="Редактировать"
                    onClick={() => startEdit(site)}
                  >
                    ✎
                  </button>
                  <button
                    className="icon-action-btn delete"
                    title="Удалить"
                    onClick={() => handleDelete(site)}
                  >
                    <Icon name="trash" />
                  </button>
                </div>
              </div>

              <div
                className="alias-target-path"
                title={site.url}
                style={{ fontSize: '12px', color: '#38bdf8', marginTop: '4px', wordBreak: 'break-all' }}
              >
                {site.url}
              </div>

              <div className="alias-triggers-wrap" style={{ marginTop: '10px' }}>
                <span className="triggers-label">Голосовые фразы:</span>
                <div className="trigger-chips">
                  {(site.aliases || []).map((alias, idx) => (
                    <span key={idx} className="chip">
                      {alias}
                    </span>
                  ))}
                  {(!site.aliases || site.aliases.length === 0) && (
                    <span style={{ fontSize: '11px', color: '#64748b' }}>Нет алиасов</span>
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
