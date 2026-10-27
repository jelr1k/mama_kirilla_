import React, { useState, useEffect, useMemo } from 'react';
import { Icon } from './Icons';

const CATEGORIES = [
  { id: 'all', label: 'Все команды', icon: 'cmd' },
  { id: 'media', label: 'Звук и Медиа', icon: 'vol' },
  { id: 'system', label: 'Система и ПК', icon: 'cpu' },
  { id: 'web', label: 'Веб и Сайты', icon: 'web' },
  { id: 'files', label: 'Файлы и Диски', icon: 'folder' },
  { id: 'general', label: 'Общие', icon: 'sparkles' },
];

function categorize(name = '', commands = []) {
  const combined = (name + ' ' + commands.slice(0, 3).join(' ')).toLowerCase();
  if (
    combined.includes('громк') ||
    combined.includes('звук') ||
    combined.includes('музык') ||
    combined.includes('трек') ||
    combined.includes('пауз') ||
    combined.includes('тише')
  ) {
    return 'media';
  }
  if (
    combined.includes('блок') ||
    combined.includes('скрин') ||
    combined.includes('корзин') ||
    combined.includes('таймер') ||
    combined.includes('врем') ||
    combined.includes('дат') ||
    combined.includes('выключ') ||
    combined.includes('сон') ||
    combined.includes('процесс')
  ) {
    return 'system';
  }
  if (
    combined.includes('сайт') ||
    combined.includes('браузер') ||
    combined.includes('ютуб') ||
    combined.includes('youtube') ||
    combined.includes('вк') ||
    combined.includes('поиск') ||
    combined.includes('гугл')
  ) {
    return 'web';
  }
  if (
    combined.includes('файл') ||
    combined.includes('папк') ||
    combined.includes('каталог') ||
    combined.includes('документ') ||
    combined.includes('воркспейс')
  ) {
    return 'files';
  }
  return 'general';
}

export default function Commands() {
  const [commandsData, setCommandsData] = useState([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [lastExecuted, setLastExecuted] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState({});

  useEffect(() => {
    fetch('/api/commands')
      .then((r) => r.json())
      .then((data) => {
        setCommandsData(data.commands || []);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const categorizedData = useMemo(() => {
    return commandsData.map((group, idx) => ({
      ...group,
      id: idx,
      category: categorize(group.name, group.commands || []),
    }));
  }, [commandsData]);

  const handleExecute = async (cmdText) => {
    setLastExecuted(cmdText);
    try {
      await fetch('/api/commands/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmdText }),
      });
    } catch (err) {
      console.error(err);
    }
    setTimeout(() => {
      setLastExecuted((curr) => (curr === cmdText ? null : curr));
    }, 2500);
  };

  const toggleGroupExpand = (id) => {
    setExpandedGroups((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredGroups = categorizedData.filter((group) => {
    if (activeCategory !== 'all' && group.category !== activeCategory) return false;
    const q = search.toLowerCase();
    const nameMatch = (group.name || '').toLowerCase().includes(q);
    const cmdMatch = (group.commands || []).some((c) => c.toLowerCase().includes(q));
    return nameMatch || cmdMatch;
  });

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Каталог команд</h1>
            <p className="page-desc">Реальные голосовые и системные сценарии, доступные ассистенту</p>
          </div>
          {lastExecuted && (
            <div className="executed-toast">
              <Icon name="check" />
              <span>Выполняется: «{lastExecuted}»</span>
            </div>
          )}
        </header>

        <div className="toolbar-row">
          <div className="category-tabs">
            {CATEGORIES.map((cat) => {
              const count = cat.id === 'all'
                ? categorizedData.length
                : categorizedData.filter((c) => c.category === cat.id).length;
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
              placeholder="Поиск по фразам или действиям..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>
        </div>

        {loading ? (
          <div className="empty-state">
            <Icon name="refresh" className="spin-icon" />
            <p>Загрузка команд ядра...</p>
          </div>
        ) : filteredGroups.length === 0 ? (
          <div className="empty-state">
            <Icon name="cmd" />
            <p>Команды не найдены</p>
          </div>
        ) : (
          <div className="commands-list-container">
            {filteredGroups.map((group) => {
              const commands = group.commands || [];
              const primaryCmd = commands[0] || group.name;
              const hasMore = commands.length > 1;
              const isExpanded = Boolean(expandedGroups[group.id]);
              const visibleVariations = isExpanded ? commands.slice(1) : commands.slice(1, 4);

              return (
                <div key={group.id} className="command-group-card">
                  <div className="command-group-header">
                    <div className="group-title-row">
                      <Icon
                        name={
                          group.category === 'media'
                            ? 'vol'
                            : group.category === 'system'
                            ? 'cpu'
                            : group.category === 'web'
                            ? 'web'
                            : group.category === 'files'
                            ? 'folder'
                            : 'sparkles'
                        }
                      />
                      <h3 className="command-group-title">{group.name}</h3>
                    </div>

                    <button
                      className="primary-action-btn small"
                      onClick={() => handleExecute(primaryCmd)}
                      title="Выполнить команду сейчас"
                    >
                      <Icon name="play" />
                      <span>{primaryCmd}</span>
                    </button>
                  </div>

                  {hasMore && (
                    <div className="command-synonyms-block">
                      <span className="synonyms-title">Синонимы и речевые вариации:</span>
                      <div className="command-triggers-wrap">
                        {visibleVariations.map((cmd, cIdx) => (
                          <button
                            key={cIdx}
                            className="command-trigger-chip"
                            onClick={() => handleExecute(cmd)}
                            title="Кликните для выполнения"
                          >
                            <span>«{cmd}»</span>
                          </button>
                        ))}

                        {commands.length > 4 && (
                          <button
                            className="btn-toggle-expand"
                            onClick={() => toggleGroupExpand(group.id)}
                          >
                            {isExpanded ? 'Свернуть' : `+ еще ${commands.length - 4}`}
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
