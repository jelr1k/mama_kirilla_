import { apiFetch } from '../services/api';
import React, { useState, useEffect, useMemo } from 'react';
import { Icon } from './Icons';
import CategoryTabs from './CategoryTabs';

const CATEGORIES = [
  { id: 'all', label: 'Все команды', icon: 'cmd' },
  { id: 'media', label: 'Музыка и Звук', icon: 'vol' },
  { id: 'protocols', label: 'Протоколы', icon: 'sparkles' },
  { id: 'system', label: 'Система и ПК', icon: 'cpu' },
  { id: 'network', label: 'Сеть, VPN и Запрет', icon: 'web' },
  { id: 'apps', label: 'Приложения и Поиск', icon: 'game' },
  { id: 'files', label: 'Файлы и Папки', icon: 'folder' },
  { id: 'ai', label: 'ИИ и Ollama', icon: 'sparkles' },
  { id: 'devices', label: 'Девайсы и Мышь', icon: 'set' },
];

export default function Commands() {
  const [commandsData, setCommandsData] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [toastMsg, setToastMsg] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState({});
  const [executingCmd, setExecutingCmd] = useState(null);

  const showToast = (text) => {
    setToastMsg(text);
    setTimeout(() => {
      setToastMsg((curr) => (curr === text ? null : curr));
    }, 2500);
  };

  useEffect(() => {
    apiFetch('/api/commands')
      .then((r) => r.json())
      .then((data) => {
        setCommandsData(data.commands || []);
      })
      .catch((e) => console.error('Failed to load commands:', e))
      .finally(() => setLoading(false));
  }, []);

  const categorizedData = useMemo(() => {
    return commandsData.map((group, idx) => ({
      ...group,
      id: group.id || idx,
      category: group.category || 'system',
    }));
  }, [commandsData]);

  const toggleGroupExpand = (id) => {
    setExpandedGroups((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCopyPhrase = (phrase) => {
    try {
      navigator.clipboard.writeText(phrase);
      showToast(`Фраза «${phrase}» скопирована`);
    } catch (e) {}
  };

  const handleExecute = async (phrase) => {
    setExecutingCmd(phrase);
    try {
      const res = await apiFetch('/api/commands/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: phrase }),
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Выполняю «${phrase}»...`);
      } else {
        showToast(`Ошибка выполнения: ${data.error || 'неизвестно'}`);
      }
    } catch (e) {
      showToast('Ошибка вызова команды на сервере');
    } finally {
      setTimeout(() => setExecutingCmd(null), 1000);
    }
  };

  const filteredGroups = categorizedData.filter((group) => {
    if (activeCategory !== 'all' && group.category !== activeCategory) return false;
    const q = search.toLowerCase().trim();
    if (!q) return true;
    const nameMatch = (group.name || '').toLowerCase().includes(q);
    const descMatch = (group.description || '').toLowerCase().includes(q);
    const cmdMatch = (group.commands || []).some((c) => c.toLowerCase().includes(q));
    return nameMatch || descMatch || cmdMatch;
  });

  const getCategoryIcon = (category) => {
    switch (category) {
      case 'media':
        return 'vol';
      case 'protocols':
        return 'sparkles';
      case 'system':
        return 'cpu';
      case 'network':
        return 'web';
      case 'apps':
        return 'game';
      case 'files':
        return 'folder';
      case 'ai':
        return 'sparkles';
      case 'devices':
        return 'set';
      default:
        return 'cmd';
    }
  };

  const getCategoryLabel = (category) => {
    const found = CATEGORIES.find((c) => c.id === category);
    return found ? found.label : category;
  };

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Справочник голосовых команд</h1>
            <p className="page-desc">
              Все возможности, сценарии и системные действия, которые ассистент распознаёт голосом и в чате
            </p>
          </div>
          {toastMsg && (
            <div className="executed-toast">
              <Icon name="check" />
              <span>{toastMsg}</span>
            </div>
          )}
        </header>

        <div className="toolbar-row commands-toolbar">
          <CategoryTabs
            categories={CATEGORIES.map((cat) => ({
              ...cat,
              count:
                cat.id === 'all'
                  ? categorizedData.length
                  : categorizedData.filter((c) => c.category === cat.id).length,
            }))}
            activeId={activeCategory}
            onChange={setActiveCategory}
            className="commands-category-tabs"
          />

          <div className="search-box">
            <input
              type="text"
              placeholder="Поиск по фразам, действиям, описаниям..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            <Icon name="refresh" className="spin-icon" />
            <p>Загрузка справочника команд из ядра...</p>
          </div>
        ) : filteredGroups.length === 0 ? (
          <div className="empty-state">
            <Icon name="cmd" />
            <p>Команды не найдены</p>
            <span className="empty-sub">Попробуйте изменить категорию или поисковый запрос</span>
          </div>
        ) : (
          <div className="commands-list-container animated-commands-view" key={activeCategory}>
            {filteredGroups.map((group, index) => {
              const commands = group.commands || [];
              const primaryCmd = commands[0] || group.name;
              const hasMore = commands.length > 1;
              const isExpanded = Boolean(expandedGroups[group.id]);
              const visibleVariations = isExpanded ? commands.slice(1) : commands.slice(1, 5);
              const isParametric = primaryCmd.includes('<') || primaryCmd.includes('...');

              return (
                <div
                  key={group.id}
                  className="command-group-card"
                  style={{ animationDelay: `${Math.min(index * 20, 250)}ms` }}
                >
                  <div className="command-group-header">
                    <div className="group-title-row">
                      <Icon name={getCategoryIcon(group.category)} />
                      <h3 className="command-group-title">{group.name}</h3>
                      <span className="group-category-tag">{getCategoryLabel(group.category)}</span>
                    </div>

                    <div className="command-header-actions">
                      {!isParametric && (
                        <button
                          type="button"
                          className="btn-command-execute"
                          title="Тестовый запуск команды через чат-роутер"
                          onClick={() => handleExecute(primaryCmd)}
                          disabled={executingCmd === primaryCmd}
                        >
                          <Icon name="play" style={{ width: '12px', height: '12px' }} />
                          <span>{executingCmd === primaryCmd ? 'Запуск...' : 'Тест'}</span>
                        </button>
                      )}

                      <div
                        className="primary-phrase-badge"
                        onClick={() => handleCopyPhrase(primaryCmd)}
                        title="Кликните, чтобы скопировать фразу"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: 'color-mix(in srgb, var(--accent) 12%, transparent)',
                          border: '1px solid color-mix(in srgb, var(--accent) 35%, transparent)',
                          color: 'var(--accent)',
                          padding: '6px 12px',
                          borderRadius: '8px',
                          fontSize: '13px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          userSelect: 'none',
                        }}
                      >
                        <Icon name="mic" style={{ width: '14px', height: '14px' }} />
                        <span>«{primaryCmd}»</span>
                      </div>
                    </div>
                  </div>

                  {group.description && (
                    <div className="command-desc">
                      {group.description}
                    </div>
                  )}

                  {hasMore && (
                    <div className="command-synonyms-block">
                      <span className="synonyms-title">Варианты произношения:</span>
                      <div className="command-triggers-wrap">
                        {visibleVariations.map((cmd, cIdx) => (
                          <span
                            key={cIdx}
                            className="command-trigger-chip"
                            onClick={() => handleCopyPhrase(cmd)}
                            title="Кликните, чтобы скопировать"
                          >
                            «{cmd}»
                          </span>
                        ))}

                        {commands.length > 5 && (
                          <button
                            type="button"
                            className="btn-toggle-expand"
                            onClick={() => toggleGroupExpand(group.id)}
                          >
                            {isExpanded ? 'Свернуть' : `+ еще ${commands.length - 5}`}
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
