import { apiFetch } from '../services/api';
import React, { useState, useEffect, useRef } from 'react';
import { Icon } from './Icons';
import ConfirmModal from './ConfirmModal';
import WebsitesSubtab from './WebsitesSubtab';
import AppsSubtab from './AppsSubtab';
import CategoryTabs from './CategoryTabs';

const ALIAS_SUBTABS = [
  { id: 'aliases', label: 'Голосовые алиасы', icon: 'tag' },
  { id: 'apps', label: 'Программы ПК', icon: 'game' },
  { id: 'websites', label: 'Ссылки и сайты', icon: 'web' },
];

const CATEGORIES = [
  { id: 'all', label: 'Все алиасы', icon: 'tag' },
  { id: 'applications', label: 'Приложения', icon: 'game' },
  { id: 'files', label: 'Файлы', icon: 'folder' },
  { id: 'folders', label: 'Папки', icon: 'workspace' },
  { id: 'actions', label: 'Действия', icon: 'cmd' },
];

function formatTargetName(target) {
  if (!target) return '';
  return target.replace(/\.(exe|lnk|bat|cmd|url)$/i, '');
}

export default function Aliases() {
  const [currentSection, setCurrentSection] = useState('aliases'); // 'aliases' | 'apps' | 'websites'
  const [activeCategory, setActiveCategory] = useState('all');
  const [aliasesList, setAliasesList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
  const [isAdding, setIsAdding] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState({ isOpen: false, category: null, target: null });
  const [deletingKey, setDeletingKey] = useState(null);
  const [recentAddedKey, setRecentAddedKey] = useState(null);

  const pageContainerRef = useRef(null);

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3000);
  };

  // New alias form fields
  const [newTarget, setNewTarget] = useState('');
  const [newCategory, setNewCategory] = useState('applications');
  const [newTriggers, setNewTriggers] = useState('');

  const handleAddAliasForApp = (app) => {
    setCurrentSection('aliases');
    setActiveCategory('applications');
    setNewCategory('applications');
    setNewTarget(app.name || '');
    setNewTriggers((app.aliases || []).join('\n'));
    setIsAdding(true);
    setEditingItem(null);
  };

  const fetchAliases = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const res = await apiFetch('/api/aliases');
      const data = await res.json();
      setAliasesList(data.aliases || []);
    } catch (err) {
      console.error('Failed to load aliases:', err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAliases();
  }, []);

  const handleSaveAlias = async (category, target, triggers, oldKey = null) => {
    try {
      const res = await apiFetch('/api/aliases', {
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
        if (oldKey && (oldKey.category !== category || oldKey.target !== target)) {
          await apiFetch('/api/aliases', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category: oldKey.category, target: oldKey.target }),
          });
        }
        showStatus('Алиас успешно сохранен');
        const itemKey = `${category}:${target}`;
        setRecentAddedKey(itemKey);
        setTimeout(() => setRecentAddedKey(null), 2500);

        fetchAliases(true);
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

  const requestDeleteAlias = (category, target) => {
    setDeleteConfirm({ isOpen: true, category, target });
  };

  const handleConfirmDelete = async () => {
    const { category, target } = deleteConfirm;
    setDeleteConfirm({ isOpen: false, category: null, target: null });
    if (!target) return;

    const itemKey = `${category}:${target}`;
    
    // Remember current scroll position of the page container
    const scrollParent = pageContainerRef.current?.closest('.page');
    const savedScrollTop = scrollParent ? scrollParent.scrollTop : null;

    // 1. Mark for graceful exit animation
    setDeletingKey(itemKey);

    // Wait for the CSS shrink/fade animation to complete before removing from state
    setTimeout(async () => {
      setAliasesList((prev) => prev.filter((item) => !(item.category === category && item.target === target)));
      setDeletingKey(null);

      // Restore scroll position cleanly
      if (scrollParent && savedScrollTop !== null) {
        requestAnimationFrame(() => {
          scrollParent.scrollTop = savedScrollTop;
        });
      }

      try {
        const res = await apiFetch('/api/aliases', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category, target }),
        });
        const data = await res.json();
        if (data.success) {
          showStatus('Алиас удален');
          fetchAliases(true);
          if (editingItem && editingItem.originalTarget === target) {
            setEditingItem(null);
          }
        } else {
          showStatus(data.error || 'Ошибка удаления', true);
          fetchAliases(true);
        }
      } catch (err) {
        showStatus('Ошибка удаления', true);
        fetchAliases(true);
      }
    }, 220);
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

  const filteredItems = aliasesList.filter((item) => {
    if (activeCategory !== 'all' && item.category !== activeCategory) return false;
    const q = search.toLowerCase();
    const targetMatch = (item.target || '').toLowerCase().includes(q);
    const aliasMatch = (item.aliases || []).some((a) => a.toLowerCase().includes(q));
    return targetMatch || aliasMatch;
  });

  return (
    <div className="page standard-page" ref={pageContainerRef}>
      <div className="page-container">
        {/* Animated Subtabs Navigation Bar */}
        <CategoryTabs
          variant="subtabs"
          categories={ALIAS_SUBTABS}
          activeId={currentSection}
          onChange={setCurrentSection}
        />

        {/* Dynamic Section Content with Smooth Cross-fade Animation */}
        <div className="subtab-animated-content" key={currentSection}>
          {currentSection === 'websites' ? (
            <WebsitesSubtab />
          ) : currentSection === 'apps' ? (
            <AppsSubtab onAddAliasForApp={handleAddAliasForApp} />
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
                      type="button"
                      className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`}
                      onClick={() => setViewMode('grid')}
                      title="Отображение плиткой (карточками)"
                    >
                      <Icon name="sparkles" />
                      <span>Панелями</span>
                    </button>
                    <button
                      type="button"
                      className={`view-btn ${viewMode === 'list' ? 'active' : ''}`}
                      onClick={() => setViewMode('list')}
                      title="Отображение компактным списком"
                    >
                      <Icon name="cmd" />
                      <span>Списком</span>
                    </button>
                  </div>

                  <button
                    type="button"
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

              {/* Create New Alias Panel with Expand Animation */}
              {isAdding && (
                <div className="card-add-panel animated-expand">
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
                      type="button"
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

              {/* Edit Existing Alias Panel */}
              {editingItem && (
                <div className="card-add-panel edit-active animated-expand">
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
                      type="button"
                      className="btn-secondary"
                      onClick={() => setEditingItem(null)}
                    >
                      Отмена
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => requestDeleteAlias(editingItem.originalCategory, editingItem.originalTarget)}
                    >
                      Удалить
                    </button>
                    <button
                      type="button"
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
                <CategoryTabs
                  categories={CATEGORIES.map((cat) => ({
                    ...cat,
                    count:
                      cat.id === 'all'
                        ? aliasesList.length
                        : aliasesList.filter((a) => a.category === cat.id).length,
                  }))}
                  activeId={activeCategory}
                  onChange={setActiveCategory}
                />

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
                  {filteredItems.map((item) => {
                    const itemKey = `${item.category}:${item.target}`;
                    const isDeleting = deletingKey === itemKey;
                    const isRecent = recentAddedKey === itemKey;

                    return (
                      <div
                        key={itemKey}
                        className={`alias-card ${isDeleting ? 'item-exit-anim' : ''} ${isRecent ? 'item-enter-highlight' : ''}`}
                      >
                        <div className="alias-header">
                          <div className="alias-title-row">
                            <Icon name={item.category === 'applications' ? 'game' : item.category === 'folders' ? 'workspace' : 'folder'} />
                            <span className="alias-name" title={item.target}>{formatTargetName(item.target)}</span>
                          </div>
                          <div className="alias-card-actions">
                            <button
                              type="button"
                              className="btn-icon-subtle"
                              title="Настройки и редактирование алиаса"
                              onClick={() => startEdit(item)}
                            >
                              <Icon name="set" />
                            </button>
                            <button
                              type="button"
                              className="btn-icon-danger"
                              title="Удалить алиас"
                              onClick={() => requestDeleteAlias(item.category, item.target)}
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
                    );
                  })}
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
                  {filteredItems.map((item) => {
                    const itemKey = `${item.category}:${item.target}`;
                    const isDeleting = deletingKey === itemKey;
                    const isRecent = recentAddedKey === itemKey;

                    return (
                      <div
                        key={itemKey}
                        className={`alias-table-row ${isDeleting ? 'item-exit-anim' : ''} ${isRecent ? 'item-enter-highlight' : ''}`}
                      >
                        <div className="col-target">
                          <Icon name={item.category === 'applications' ? 'game' : item.category === 'folders' ? 'workspace' : 'folder'} />
                          <strong className="table-target-name" title={item.target}>{formatTargetName(item.target)}</strong>
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
                            type="button"
                            className="btn-table-action"
                            onClick={() => startEdit(item)}
                            title="Редактировать алиас"
                          >
                            <Icon name="set" />
                            <span>Настроить</span>
                          </button>
                          <button
                            type="button"
                            className="btn-table-action danger"
                            onClick={() => requestDeleteAlias(item.category, item.target)}
                            title="Удалить алиас"
                          >
                            <Icon name="trash" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteConfirm.isOpen}
        title="Удаление голосового алиаса"
        message={`Удалить голосовой алиас для «${formatTargetName(deleteConfirm.target)}» и все привязанные фразы?`}
        confirmText="Удалить"
        cancelText="Отмена"
        isDanger={true}
        onClose={() => setDeleteConfirm({ isOpen: false, category: null, target: null })}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
