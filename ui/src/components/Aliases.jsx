import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';
import WebsitesSubtab from './WebsitesSubtab';

const CATEGORIES = [
  { id: 'all', label: 'Все алиасы', icon: 'tag' },
  { id: 'applications', label: 'Приложения', icon: 'game' },
  { id: 'files', label: 'Файлы', icon: 'folder' },
  { id: 'folders', label: 'Папки', icon: 'workspace' },
  { id: 'actions', label: 'Действия', icon: 'cmd' },
];

export default function Aliases() {
  const [currentSection, setCurrentSection] = useState('aliases'); // 'aliases' | 'websites'
  const [activeCategory, setActiveCategory] = useState('all');
  const [aliasesList, setAliasesList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
  const [isAdding, setIsAdding] = useState(false);
  const [editingItem, setEditingItem] = useState(null); // { originalCategory, originalTarget, category, target, triggersText }
  const [statusMsg, setStatusMsg] = useState(null);

  // New alias form fields
  const [newTarget, setNewTarget] = useState('');
  const [newCategory, setNewCategory] = useState('applications');
  const [newTriggers, setNewTriggers] = useState('');

  const fetchAliases = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/aliases');
      const data = await res.json();
      setAliasesList(data.aliases || []);
    } catch (err) {
      console.error('Failed to load aliases:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAliases();
  }, []);

  const handleSaveAlias = async (category, target, triggers, oldKey = null) => {
    try {
      const res = await fetch('/api/aliases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          target,
          aliases: triggers,
        }),
      });
      const data = await res.json();
      if (data.success) {
        // If editing an existing alias and the target or category changed, delete old one
        if (oldKey && (oldKey.category !== category || oldKey.target !== target)) {
          await fetch('/api/aliases', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: oldKey.category, target: oldKey.target }),
          });
        }
        showStatus('Алиас успешно сохранен');
        fetchAliases();
        setIsAdding(false);
        setEditingItem(null);
        setNewTarget('');
        setNewTriggers('');
      } else {
        showStatus(data.error || 'Ошибка сохранения', true);
      }
    } catch (err) {
      showStatus('Ошибка подключения к серверу', true);
    }
  };

  const handleDeleteAlias = async (category, target) => {
    if (!window.confirm(`Удалить алиас для «${target}» и все привязанные фразы?`)) return;
    try {
      const res = await fetch('/api/aliases', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, target }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus('Алиас удален');
        fetchAliases();
        if (editingItem && editingItem.originalTarget === target) {
          setEditingItem(null);
        }
      }
    } catch (err) {
      showStatus('Ошибка удаления', true);
    }
  };

  const startEdit = (item) => {
    setEditingItem({
      originalCategory: item.category,
      originalTarget: item.target,
      category: item.category,
      target: item.target,
      triggersText: (item.aliases || []).join('\n'),
    });
    setIsAdding(false);
  };

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const filteredItems = aliasesList.filter((item) => {
    if (activeCategory !== 'all' && item.category !== activeCategory) return false;
    const q = search.toLowerCase();
    const targetMatch = (item.target || '').toLowerCase().includes(q);
    const aliasMatch = (item.aliases || []).some((a) => a.toLowerCase().includes(q));
    return targetMatch || aliasMatch;
  });

  return (
    <div className="page standard-page">
      <div className="page-container">
        {/* Subtabs Selector: Aliases vs Websites */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <button
            className={`btn-subtab ${currentSection === 'aliases' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCurrentSection('aliases')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Icon name="tag" />
            <span>Программы и файлы</span>
          </button>
          <button
            className={`btn-subtab ${currentSection === 'websites' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setCurrentSection('websites')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Icon name="web" />
            <span>Ссылки и сайты</span>
          </button>
        </div>

        {currentSection === 'websites' ? (
          <WebsitesSubtab />
        ) : (
          <>
            <header className="page-header">
              <div className="header-left">
                <h1 className="page-title">Голосовые алиасы</h1>
                <p className="page-desc">Привязка естественных речевых фраз к системным программам, файлам и папкам</p>
              </div>
              <div className="header-actions">
                {/* View Mode Switcher */}
                <div className="view-mode-toggle">
                  <button
                    className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                    onClick={() => setViewMode('grid')}
                    title="Отображение плиткой (карточками)"
                  >
                    <Icon name="sparkles" />
                    <span>Панелями</span>
                  </button>
                  <button
                    className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                    onClick={() => setViewMode('list')}
                    title="Отображение компактным списком"
                  >
                    <Icon name="cmd" />
                    <span>Списком</span>
                  </button>
                </div>

                <button
                  className="primary-action-btn"
                  onClick={() => {
                    setIsAdding(!isAdding);
                    setEditingItem(null);
                  }}
                >
                  <Icon name={isAdding ? 'check' : 'plus'} />
                  <span>{isAdding ? 'Отмена' : 'Добавить алиас'}</span>
                </button>
              </div>
            </header>

        {statusMsg && (
          <div className={`status-banner ${statusMsg.isError ? 'error' : 'success'}`}>
            <Icon name={statusMsg.isError ? 'bell' : 'check'} />
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Create New Alias Panel */}
        {isAdding && (
          <div className="card-add-panel">
            <h3 className="section-subtitle">Создание нового голосового алиаса</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Категория:</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="select-input"
                >
                  <option value="applications">Приложения</option>
                  <option value="files">Файлы</option>
                  <option value="folders">Папки</option>
                  <option value="actions">Действия</option>
                </select>
              </div>
              <div className="form-group">
                <label>Имя цели (Target / Название файла или процесса):</label>
                <input
                  type="text"
                  placeholder="Discord.exe / Steam.lnk / tasks.md"
                  value={newTarget}
                  onChange={(e) => setNewTarget(e.target.value)}
                  className="text-input"
                />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label>Голосовые фразы (по одной на строку или через запятую):</label>
                <textarea
                  placeholder="дискорд&#10;войс&#10;дс"
                  value={newTriggers}
                  onChange={(e) => setNewTriggers(e.target.value)}
                  className="textarea-input"
                  rows={3}
                />
              </div>
            </div>
            <div className="form-actions">
              <button
                className="btn-accent"
                onClick={() => {
                  if (!newTarget.trim()) return showStatus('Укажите цель', true);
                  const list = newTriggers
                    .split(/[\n,]+/)
                    .map((s) => s.trim())
                    .filter(Boolean);
                  handleSaveAlias(newCategory, newTarget.trim(), list);
                }}
              >
                Сохранить связку
              </button>
            </div>
          </div>
        )}

        {/* Edit Existing Alias Modal / Panel */}
        {editingItem && (
          <div className="card-add-panel edit-active">
            <div className="modal-title-row" style={{ marginBottom: '14px' }}>
              <Icon name="tag" />
              <h3 className="section-subtitle" style={{ margin: 0 }}>
                Редактирование алиаса: {editingItem.originalTarget}
              </h3>
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label>Категория:</label>
                <select
                  value={editingItem.category}
                  onChange={(e) => setEditingItem({ ...editingItem, category: e.target.value })}
                  className="select-input"
                >
                  <option value="applications">Приложения</option>
                  <option value="files">Файлы</option>
                  <option value="folders">Папки</option>
                  <option value="actions">Действия</option>
                </select>
              </div>
              <div className="form-group">
                <label>Реальное имя / путь (Target):</label>
                <input
                  type="text"
                  value={editingItem.target}
                  onChange={(e) => setEditingItem({ ...editingItem, target: e.target.value })}
                  className="text-input"
                />
              </div>
              <div className="form-group" style={{ gridColumn: 'span 2' }}>
                <label>Голосовые синонимы (по одному на строку):</label>
                <textarea
                  value={editingItem.triggersText}
                  onChange={(e) => setEditingItem({ ...editingItem, triggersText: e.target.value })}
                  className="textarea-input"
                  rows={4}
                  placeholder="По одной фразе на строку..."
                />
              </div>
            </div>
            <div className="form-actions" style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                className="btn-secondary"
                onClick={() => setEditingItem(null)}
              >
                Отмена
              </button>
              <button
                className="btn-danger"
                onClick={() => handleDeleteAlias(editingItem.originalCategory, editingItem.originalTarget)}
              >
                Удалить
              </button>
              <button
                className="btn-accent"
                onClick={() => {
                  if (!editingItem.target.trim()) return showStatus('Укажите имя цели', true);
                  const triggers = editingItem.triggersText
                    .split('\n')
                    .map((s) => s.trim())
                    .filter(Boolean);
                  handleSaveAlias(
                    editingItem.category,
                    editingItem.target.trim(),
                    triggers,
                    { category: editingItem.originalCategory, target: editingItem.originalTarget }
                  );
                }}
              >
                Сохранить изменения
              </button>
            </div>
          </div>
        )}

        {/* Toolbar: Categories + Search */}
        <div className="toolbar-row">
          <div className="category-tabs">
            {CATEGORIES.map((cat) => {
              const count = cat.id === 'all'
                ? aliasesList.length
                : aliasesList.filter((a) => a.category === cat.id).length;
              return (
                <button
                  key={cat.id}
                  className={`tab-pill ${activeCategory === cat.id ? 'active' : ''}`}
                  onClick={() => setActiveCategory(cat.id)}
                >
                  <Icon name={cat.icon} />
                  <span>{cat.label}</span>
                  <span className="badge-count">{count}</span>
                </button>
              );
            })}
          </div>

          <div className="search-box">
            <input
              type="text"
              placeholder="Поиск по фразам или файлам..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            <Icon name="refresh" className="spin-icon" />
            <p>Загрузка алиасов из ядра...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">
            <Icon name="tag" />
            <p>Ничего не найдено</p>
            <span className="empty-sub">Проверьте запрос или создайте новый алиас</span>
          </div>
        ) : viewMode === 'grid' ? (
          /* Grid View Mode */
          <div className="aliases-grid">
            {filteredItems.map((item, idx) => (
              <div key={idx} className="alias-card">
                <div className="alias-header">
                  <div className="alias-title-row">
                    <Icon name={item.category === 'applications' ? 'game' : item.category === 'folders' ? 'workspace' : 'folder'} />
                    <span className="alias-name">{item.target}</span>
                  </div>
                  <div className="alias-card-actions">
                    <button
                      className="btn-icon-subtle"
                      title="Настройки и редактирование алиаса"
                      onClick={() => startEdit(item)}
                    >
                      <Icon name="set" />
                    </button>
                    <button
                      className="btn-icon-danger"
                      title="Удалить алиас"
                      onClick={() => handleDeleteAlias(item.category, item.target)}
                    >
                      <Icon name="trash" />
                    </button>
                  </div>
                </div>

                <div className="alias-triggers">
                  <div className="triggers-label">Голосовые фразы активации:</div>
                  <div className="trigger-tags">
                    {(item.aliases || []).length > 0 ? (
                      item.aliases.map((tag, tIdx) => (
                        <span key={tIdx} className="trigger-tag">
                          «{tag}»
                        </span>
                      ))
                    ) : (
                      <span className="no-triggers">Нет привязанных фраз</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* List View Mode */
          <div className="aliases-list-table">
            <div className="alias-table-header">
              <span className="col-target">Объект / Цель</span>
              <span className="col-cat">Категория</span>
              <span className="col-phrases">Фразы активации</span>
              <span className="col-actions">Действия</span>
            </div>
            {filteredItems.map((item, idx) => (
              <div key={idx} className="alias-table-row">
                <div className="col-target">
                  <Icon name={item.category === 'applications' ? 'game' : item.category === 'folders' ? 'workspace' : 'folder'} />
                  <strong className="table-target-name">{item.target}</strong>
                </div>
                <div className="col-cat">
                  <span className="cat-badge">{item.category}</span>
                </div>
                <div className="col-phrases">
                  {(item.aliases || []).length > 0 ? (
                    item.aliases.map((tag, tIdx) => (
                      <span key={tIdx} className="trigger-tag compact">
                        «{tag}»
                      </span>
                    ))
                  ) : (
                    <span className="no-triggers">—</span>
                  )}
                </div>
                <div className="col-actions">
                  <button
                    className="btn-table-action"
                    onClick={() => startEdit(item)}
                    title="Редактировать алиас"
                  >
                    <Icon name="set" />
                    <span>Настроить</span>
                  </button>
                  <button
                    className="btn-table-action danger"
                    onClick={() => handleDeleteAlias(item.category, item.target)}
                    title="Удалить алиас"
                  >
                    <Icon name="trash" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
}
