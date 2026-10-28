import { apiFetch } from '../services/api';
import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';

export default function Workspace() {
  const [items, setItems] = useState([]);
  const [workspaceDir, setWorkspaceDir] = useState('');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [msg, setMsg] = useState(null);
  const [expandedCards, setExpandedCards] = useState({});

  const showMsg = (text, isError = false) => {
    setMsg({ text, isError });
    setTimeout(() => setMsg(null), 3000);
  };

  const fetchWorkspace = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/api/workspace');
      const data = await res.json();
      setItems(data.items || []);
      setWorkspaceDir(data.workspace_dir || '');
    } catch (err) {
      console.error('Failed to load workspace:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, []);

  const handleOpenFolder = async () => {
    try {
      await apiFetch('/api/workspace/open', { method: 'POST' });
      showMsg('Папка открыта в Проводнике Windows');
    } catch (err) {
      showMsg('Ошибка открытия папки', true);
    }
  };

  const toggleCard = (id) => {
    setExpandedCards((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredItems = items.filter((item) => {
    const q = search.toLowerCase().trim();
    if (!q) return true;
    return (
      (item.name || '').toLowerCase().includes(q) ||
      (item.path || '').toLowerCase().includes(q) ||
      (item.user_aliases || []).some((a) => a.toLowerCase().includes(q))
    );
  });

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Рабочая область (Workspace)</h1>
            <p className="page-desc">
              Изолированная среда для безопасной работы ассистента с документами, скриптами и данными
            </p>
          </div>
          <div className="header-actions">
            <button className="primary-action-btn" onClick={handleOpenFolder}>
              <Icon name="folder" />
              <span>Открыть в Проводнике</span>
            </button>
          </div>
        </header>

        {msg && (
          <div className={`status-banner ${msg.isError ? 'error' : 'success'}`}>
            <Icon name={msg.isError ? 'bell' : 'check'} />
            <span>{msg.text}</span>
          </div>
        )}

        <div className="workspace-info-card">
          <div className="info-icon">
            <Icon name="shield" />
          </div>
          <div className="info-details">
            <div className="info-title">Безопасная песочница:</div>
            <code className="path-code">{workspaceDir || 'Директория workspace/...'}</code>
          </div>
          <button className="btn-secondary" onClick={fetchWorkspace} title="Обновить список">
            <Icon name="refresh" />
            <span>Обновить</span>
          </button>
        </div>

        <div className="toolbar-row">
          <div className="stat-pill">
            <span className="stat-val">{items.length}</span>
            <span className="stat-lbl">Объектов в рабочей области</span>
          </div>

          <div className="search-box">
            <input
              type="text"
              placeholder="Поиск по файлам или алиасам..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            <Icon name="refresh" className="spin-icon" />
            <p>Сканирование рабочей области...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">
            <Icon name="folder" />
            <p>В рабочей области пока нет файлов</p>
            <span className="empty-sub">
              Поместите документы или скрипты в папку workspace, чтобы ассистент мог с ними взаимодействовать
            </span>
          </div>
        ) : (
          <div className="workspace-grid">
            {filteredItems.map((item, idx) => {
              const allAliases = [...(item.user_aliases || []), ...(item.automatic_aliases || [])];
              const isExpanded = Boolean(expandedCards[idx]);

              return (
                <div
                  key={idx}
                  className={`workspace-card ${isExpanded ? 'expanded' : ''}`}
                  onClick={() => toggleCard(idx)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="card-top">
                    <div className="card-file-icon">
                      <Icon name={item.is_dir ? 'folder' : 'alias'} />
                    </div>
                    <div className="card-file-meta">
                      <div className="file-name" title={item.path}>
                        {item.name}
                      </div>
                      <div className="file-sub">{item.path}</div>
                    </div>
                  </div>

                  <div className="card-aliases" style={{ marginTop: '10px' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '12px',
                        color: isExpanded ? 'var(--accent)' : 'var(--tx-dim)',
                      }}
                    >
                      <span>
                        Голосовые фразы ({allAliases.length})
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--mut)' }}>
                        {isExpanded ? '▲ Скрыть' : '▼ Показать'}
                      </span>
                    </div>

                    {isExpanded && (
                      <div className="trigger-tags" style={{ marginTop: '8px' }}>
                        {allAliases.length > 0 ? (
                          allAliases.map((a, aIdx) => (
                            <span key={aIdx} className="trigger-tag">
                              «{a}»
                            </span>
                          ))
                        ) : (
                          <span className="no-triggers">Нет привязанных триггеров</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
