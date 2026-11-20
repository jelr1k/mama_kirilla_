import React, { useState, useEffect } from 'react';
import { apiGet, apiPost, apiDelete } from '../services/api';
import { Icon } from './Icons';

function Toggle({ value, onChange, label }) {
  return (
    <button
      type="button"
      className={`tg ${value ? 'on' : ''}`}
      onClick={() => onChange(!value)}
      role="switch"
      aria-checked={value}
      aria-label={label}
    />
  );
}

export default function Protocols() {
  const [profiles, setProfiles] = useState({});
  const [activeProfile, setActiveProfile] = useState('default');
  const [protocols, setProtocols] = useState([]);
  const [roles, setRoles] = useState({ browser: 'opera', messenger: 'discord', gaming: 'steam', work: 'antigravity' });
  const [showRolesModal, setShowRolesModal] = useState(false);
  const [selectedProtocolId, setSelectedProtocolId] = useState(null);
  const [editingProtocol, setEditingProtocol] = useState(null);
  const [steamGames, setSteamGames] = useState([]);
  const [steamInstalled, setSteamInstalled] = useState(false);
  const [showSteamModal, setShowSteamModal] = useState(false);
  const [suggestedApps, setSuggestedApps] = useState([]);
  const [showAppsModal, setShowAppsModal] = useState(false);
  const [appsModalTarget, setAppsModalTarget] = useState('open');
  const [appsSearch, setAppsSearch] = useState('');
  const [allIndexedApps, setAllIndexedApps] = useState([]);
  const [showHiddenApps, setShowHiddenApps] = useState(false);
  const [showNewProfileModal, setShowNewProfileModal] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [copyFromActive, setCopyFromActive] = useState(true);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);
  const [executingId, setExecutingId] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 3500);
  };

  const loadProtocols = async () => {
    try {
      const data = await apiGet('/api/protocols');
      setProfiles(data.profiles || {});
      setActiveProfile(data.active_profile || 'default');
      if (data.roles && typeof data.roles === 'object') {
        setRoles(data.roles);
      }
      const list = data.protocols || [];
      setProtocols(list);
      if (list.length > 0) {
        if (!selectedProtocolId || !list.some((p) => p.id === selectedProtocolId)) {
          setSelectedProtocolId(list[0].id);
          setEditingProtocol({ ...list[0] });
        } else {
          const current = list.find((p) => p.id === selectedProtocolId);
          setEditingProtocol(current ? { ...current } : { ...list[0] });
        }
      } else {
        setSelectedProtocolId(null);
        setEditingProtocol(null);
      }
    } catch (err) {
      console.error('Failed to load protocols:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSteamData = async () => {
    try {
      const data = await apiGet('/api/steam');
      setSteamInstalled(Boolean(data.installed));
      setSteamGames(data.games || []);
    } catch (err) {
      console.error('Failed to load Steam info:', err);
    }
  };

  const loadSuggestedApps = async () => {
    try {
      const data = await apiGet('/api/protocols/suggestions');
      setSuggestedApps(Array.isArray(data.suggestions) ? data.suggestions : []);
    } catch (err) {
      console.error('Failed to load protocol app suggestions:', err);
    }
  };

  const loadAllIndexedApps = async () => {
    try {
      const data = await apiGet('/api/apps');
      setAllIndexedApps(Array.isArray(data.apps) ? data.apps : []);
    } catch (err) {
      console.error('Failed to load installed apps:', err);
    }
  };

  const handleToggleAppVisibility = async (appKey, nextHidden) => {
    try {
      const res = await apiPost('/api/apps/visibility', { key: appKey, hidden: nextHidden });
      if (res.success) {
        await Promise.all([loadSuggestedApps(), loadAllIndexedApps()]);
      }
    } catch (err) {
      console.error('Failed to toggle app visibility:', err);
    }
  };

  useEffect(() => {
    loadProtocols();
    loadSteamData();
    loadSuggestedApps();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectProfile = async (profileId) => {
    if (profileId === activeProfile) return;
    try {
      setLoading(true);
      const res = await apiPost('/api/protocols/profile/select', { profile_id: profileId });
      if (res.success) {
        setActiveProfile(profileId);
        const list = res.protocols || [];
        setProtocols(list);
        if (list.length > 0) {
          setSelectedProtocolId(list[0].id);
          setEditingProtocol({ ...list[0] });
        } else {
          setSelectedProtocolId(null);
          setEditingProtocol(null);
        }
        showToast(`Профиль переключён на: ${profiles[profileId] || profileId}`);
      }
    } catch (err) {
      console.error('Profile switch failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProfile = async (e) => {
    e.preventDefault();
    if (!newProfileName.trim()) return;
    try {
      const res = await apiPost('/api/protocols/profile', {
        name: newProfileName.trim(),
        copy_from_active: copyFromActive,
      });
      if (res.success) {
        setShowNewProfileModal(false);
        setNewProfileName('');
        await loadProtocols();
        showToast(`Создан новый профиль: ${newProfileName}`);
      }
    } catch (err) {
      console.error('Failed to create profile:', err);
    }
  };

  const handleDeleteProfile = async () => {
    if (activeProfile === 'default') {
      alert('Нельзя удалить основной профиль "default"!');
      return;
    }
    const profileName = profiles[activeProfile] || activeProfile;
    if (!window.confirm(`Вы уверены, что хотите удалить профиль "${profileName}"?`)) return;
    try {
      const res = await apiDelete(`/api/protocols/profile/${activeProfile}`);
      if (res.success) {
        await loadProtocols();
        showToast(`Профиль "${profileName}" удалён`);
      }
    } catch (err) {
      console.error('Delete profile failed:', err);
    }
  };

  const handleSelectProtocol = (proto) => {
    setSelectedProtocolId(proto.id);
    setEditingProtocol({ ...proto });
  };

  const handleNewProtocol = () => {
    const newProto = {
      id: '',
      name: 'Новый сценарий',
      description: 'Описание сценария...',
      phrases: ['новый сценарий'],
      open_apps: [],
      close_mode: 'none',
      close_apps: [],
      blocked_open_apps: [],
      blocked_close_apps: [],
      steps: [],
      volume_mode: 'none',
      pause_media: false,
      lock_screen: false,
      clean_recycle_bin: false,
      briefing: false,
      response_text: '',
    };
    setSelectedProtocolId('__new__');
    setEditingProtocol(newProto);
  };

  const handleSaveProtocol = async () => {
    if (!editingProtocol || !editingProtocol.name.trim()) {
      alert('Введите название сценария');
      return;
    }
    try {
      const payload = {
        protocol: {
          ...editingProtocol,
          phrases: Array.isArray(editingProtocol.phrases)
            ? editingProtocol.phrases
            : String(editingProtocol.phrases || '')
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
          open_apps: Array.isArray(editingProtocol.open_apps)
            ? editingProtocol.open_apps
            : String(editingProtocol.open_apps || '')
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
          close_apps: Array.isArray(editingProtocol.close_apps)
            ? editingProtocol.close_apps
            : String(editingProtocol.close_apps || '')
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
          blocked_open_apps: Array.isArray(editingProtocol.blocked_open_apps)
            ? editingProtocol.blocked_open_apps
            : String(editingProtocol.blocked_open_apps || '')
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
          blocked_close_apps: Array.isArray(editingProtocol.blocked_close_apps)
            ? editingProtocol.blocked_close_apps
            : String(editingProtocol.blocked_close_apps || '')
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean),
          steps: Array.isArray(editingProtocol.steps) ? editingProtocol.steps : [],
        },
        profile_id: activeProfile,
      };

      const res = await apiPost('/api/protocols', payload);
      if (res.success) {
        showToast(`Сценарий «${editingProtocol.name}» сохранён`);
        await loadProtocols();
        if (res.protocol_id) {
          setSelectedProtocolId(res.protocol_id);
        }
      }
    } catch (err) {
      console.error('Failed to save protocol:', err);
      alert('Ошибка при сохранении протокола');
    }
  };

  const handleDeleteProtocol = async () => {
    if (!selectedProtocolId || selectedProtocolId === '__new__') return;
    const protoName = editingProtocol?.name || selectedProtocolId;
    if (!window.confirm(`Удалить протокол «${protoName}»?`)) return;
    try {
      const res = await apiDelete(`/api/protocols/${selectedProtocolId}`);
      if (res.success) {
        showToast(`Протокол «${protoName}» удалён`);
        await loadProtocols();
      }
    } catch (err) {
      console.error('Failed to delete protocol:', err);
    }
  };

  const handleExecuteProtocol = async (protoId, protoName) => {
    try {
      setExecutingId(protoId);
      const res = await apiPost('/api/protocols/execute', {
        protocol_id: protoId,
        profile_id: activeProfile,
      });
      if (res.success) {
        showToast(`«${protoName || protoId}»: ${res.result || 'Готово'}`);
      }
    } catch (err) {
      console.error('Execute protocol failed:', err);
      showToast(`Ошибка выполнения «${protoName || protoId}»`);
    } finally {
      setExecutingId(null);
    }
  };

  const normalizeAppToken = (val) => String(val || '').trim().toLowerCase();

  const parseAppsField = (raw) =>
    (Array.isArray(raw) ? raw : String(raw || '').split(','))
      .map((s) => s.trim())
      .filter(Boolean);

  const filterSuggestionsExcluding = (items, currentList) => {
    const currentSet = new Set(currentList.map(normalizeAppToken));
    return items.filter((item) => {
      const tokens = [
        item.key,
        item.label,
        item.executable,
        ...(Array.isArray(item.aliases) ? item.aliases : []),
      ]
        .map(normalizeAppToken)
        .filter(Boolean);
      return !tokens.some((tok) => currentSet.has(tok));
    });
  };

  const currentOpenAppsList = editingProtocol ? parseAppsField(editingProtocol.open_apps) : [];
  const currentCloseAppsList = editingProtocol ? parseAppsField(editingProtocol.close_apps) : [];
  const currentBlockedOpenList = editingProtocol ? parseAppsField(editingProtocol.blocked_open_apps) : [];
  const currentBlockedCloseList = editingProtocol ? parseAppsField(editingProtocol.blocked_close_apps) : [];

  const availableSuggestions = filterSuggestionsExcluding(suggestedApps, currentOpenAppsList);
  const availableCloseSuggestions = filterSuggestionsExcluding(suggestedApps, currentCloseAppsList);
  const availableBlockOpenSuggestions = filterSuggestionsExcluding(suggestedApps, currentBlockedOpenList);
  const availableBlockCloseSuggestions = filterSuggestionsExcluding(suggestedApps, currentBlockedCloseList);

  const modalBaseList = showHiddenApps && allIndexedApps.length > 0
    ? allIndexedApps
        .filter((a) => a.hidden)
        .map((a) => ({
          key: a.name,
          label: a.name,
          category: a.category,
          executable: a.executable,
          aliases: a.aliases || [],
          hidden: true,
        }))
    : (
        appsModalTarget === 'close'
          ? availableCloseSuggestions
          : appsModalTarget === 'block_open'
            ? availableBlockOpenSuggestions
            : appsModalTarget === 'block_close'
              ? availableBlockCloseSuggestions
              : availableSuggestions
      );

  const filteredModalApps = modalBaseList.filter((item) => {
    const q = appsSearch.trim().toLowerCase();
    if (!q) return true;
    return (
      String(item.label || '').toLowerCase().includes(q) ||
      String(item.key || '').toLowerCase().includes(q) ||
      (Array.isArray(item.aliases) && item.aliases.some((a) => String(a).toLowerCase().includes(q)))
    );
  });

  const openAppsPickerModal = (target) => {
    setAppsModalTarget(target);
    setAppsSearch('');
    setShowHiddenApps(false);
    setShowAppsModal(true);
    loadAllIndexedApps();
  };

  const handleAddQuickApp = (appKey) => {
    if (!editingProtocol) return;
    const current = [...currentOpenAppsList];
    const targetNorm = normalizeAppToken(appKey);
    if (!current.some((item) => normalizeAppToken(item) === targetNorm)) {
      current.push(appKey);
      setEditingProtocol({ ...editingProtocol, open_apps: current });
    }
  };

  const handleAddCloseApp = (appKey) => {
    if (!editingProtocol) return;
    const current = [...currentCloseAppsList];
    const targetNorm = normalizeAppToken(appKey);
    if (!current.some((item) => normalizeAppToken(item) === targetNorm)) {
      current.push(appKey);
      setEditingProtocol({ ...editingProtocol, close_apps: current });
    }
  };

  const handleAddBlockedOpenApp = (appKey) => {
    if (!editingProtocol) return;
    const current = [...currentBlockedOpenList];
    const targetNorm = normalizeAppToken(appKey);
    if (!current.some((item) => normalizeAppToken(item) === targetNorm)) {
      current.push(appKey);
      setEditingProtocol({ ...editingProtocol, blocked_open_apps: current });
    }
  };

  const handleAddBlockedCloseApp = (appKey) => {
    if (!editingProtocol) return;
    const current = [...currentBlockedCloseList];
    const targetNorm = normalizeAppToken(appKey);
    if (!current.some((item) => normalizeAppToken(item) === targetNorm)) {
      current.push(appKey);
      setEditingProtocol({ ...editingProtocol, blocked_close_apps: current });
    }
  };

  const handleSaveRoles = async (e) => {
    e.preventDefault();
    try {
      const res = await apiPost('/api/protocols/roles', {
        profile_id: activeProfile,
        roles,
      });
      if (res.success) {
        if (res.roles) setRoles(res.roles);
        setShowRolesModal(false);
        showToast('Роли профиля сохранены');
      }
    } catch (err) {
      console.error('Failed to save roles:', err);
      showToast('Ошибка при сохранении ролей');
    }
  };

  const handleAddStep = (type) => {
    if (!editingProtocol) return;
    const currentSteps = Array.isArray(editingProtocol.steps) ? [...editingProtocol.steps] : [];
    if (type === 'open_urls') {
      currentSteps.push({ type: 'open_urls', browser: 'role:browser', profile: '', urls: [], new_window: false });
    } else if (type === 'launch_app') {
      currentSteps.push({ type: 'launch_app', target: '', args: '', wait_window: true, focus: true });
    }
    setEditingProtocol({ ...editingProtocol, steps: currentSteps });
  };

  const handleUpdateStep = (idx, patch) => {
    if (!editingProtocol) return;
    const currentSteps = Array.isArray(editingProtocol.steps) ? [...editingProtocol.steps] : [];
    currentSteps[idx] = { ...currentSteps[idx], ...patch };
    setEditingProtocol({ ...editingProtocol, steps: currentSteps });
  };

  const handleRemoveStep = (idx) => {
    if (!editingProtocol) return;
    const currentSteps = Array.isArray(editingProtocol.steps) ? [...editingProtocol.steps] : [];
    currentSteps.splice(idx, 1);
    setEditingProtocol({ ...editingProtocol, steps: currentSteps });
  };

  const handleAddSteamGame = (game) => {
    if (!editingProtocol) return;
    const appKey = `steam:${game.appid}`;
    const current = Array.isArray(editingProtocol.open_apps)
      ? [...editingProtocol.open_apps]
      : String(editingProtocol.open_apps || '')
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
    if (!current.includes(appKey)) {
      current.push(appKey);
      setEditingProtocol({ ...editingProtocol, open_apps: current });
    }
    setShowSteamModal(false);
  };

  return (
    <div className="page standard-page">
      <div className="page-container">
        {toastMessage && <div className="executed-toast">{toastMessage}</div>}

        <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="header-left">
            <h1 className="page-title">Сценарии и Протоколы</h1>
            <p className="page-desc">
              Настройка фирменных сценариев автоматизации: запуск рабочих сред, игровой режим, чистка и системные действия
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', color: 'var(--tx-dim)', fontWeight: 600 }}>Профиль:</span>
            <select
              value={activeProfile}
              onChange={(e) => handleSelectProfile(e.target.value)}
              className="select-input"
              style={{ padding: '6px 32px 6px 12px', fontSize: '13px' }}
            >
              {Object.entries(profiles).map(([pid, name]) => (
                <option key={pid} value={pid}>
                  {name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                loadAllIndexedApps();
                setShowRolesModal(true);
              }}
              style={{ padding: '6px 12px', fontSize: '12px' }}
              title="Назначить основной браузер, мессенджер и т.д. для этого ПК"
            >
              <span>Роли ПК</span>
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={() => setShowNewProfileModal(true)}
              style={{ padding: '6px 12px', fontSize: '12px' }}
              title="Создать новый профиль пользователя"
            >
              <Icon name="check" style={{ width: '13px', height: '13px' }} />
              <span>+ Профиль</span>
            </button>
            {activeProfile !== 'default' && (
              <button
                type="button"
                className="btn-danger"
                onClick={handleDeleteProfile}
                style={{ padding: '6px 12px', fontSize: '12px' }}
                title="Удалить текущий профиль"
              >
                <Icon name="trash" style={{ width: '13px', height: '13px' }} />
                <span>Удалить</span>
              </button>
            )}
          </div>
        </header>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--mut)' }}>Загрузка протоколов...</div>
        ) : (
          <div className="protocols-grid">
            {/* Левая колонка: список сценариев */}
            <div className="protocol-sidebar">
              <div className="protocol-sidebar-header">
                <span className="protocol-count-badge">
                  Протоколы ({protocols.length})
                </span>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleNewProtocol}
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                >
                  + Новый
                </button>
              </div>

              <div className="protocol-list">
                {protocols.map((proto) => {
                  const isSelected = selectedProtocolId === proto.id;
                  const isRunning = executingId === proto.id;
                  return (
                    <div
                      key={proto.id}
                      onClick={() => handleSelectProtocol(proto)}
                      className={`protocol-card-item ${isSelected ? 'selected' : ''}`}
                    >
                      <div className="protocol-card-top">
                        <div className="group-title-row">
                          <Icon name="sparkles" style={{ width: '15px', height: '15px', color: 'var(--accent)' }} />
                          <span className="protocol-card-title">
                            {proto.name}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleExecuteProtocol(proto.id, proto.name);
                          }}
                          disabled={isRunning}
                          className="protocol-action-badge"
                          title="Запустить сценарий прямо сейчас"
                        >
                          <Icon name="zap" style={{ width: '11px', height: '11px' }} />
                          <span>{isRunning ? '...' : 'Старт'}</span>
                        </button>
                      </div>
                      {proto.description && (
                        <p className="protocol-card-desc">
                          {proto.description}
                        </p>
                      )}
                      {proto.phrases && proto.phrases.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                          <span className="command-trigger-chip" style={{ fontSize: '11px', padding: '3px 8px', cursor: 'default' }}>
                            «{proto.phrases[0]}»
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Правая колонка: детальный редактор */}
            {editingProtocol ? (
              <div className="protocol-editor" key={selectedProtocolId || "new"}>
                <div className="protocol-editor-header">
                  <div className="group-title-row">
                    <Icon name="zap" style={{ width: '18px', height: '18px', color: 'var(--accent)' }} />
                    <h2 className="protocol-editor-title">
                      {selectedProtocolId === '__new__' ? 'Создание протокола' : `Редактирование: ${editingProtocol.name}`}
                    </h2>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={handleSaveProtocol}
                    >
                      <Icon name="check" />
                      <span>Сохранить</span>
                    </button>
                    {selectedProtocolId !== '__new__' && (
                      <>
                        <button
                          type="button"
                          className="btn-protocol-test"
                          onClick={() => handleExecuteProtocol(editingProtocol.id, editingProtocol.name)}
                        >
                          <Icon name="sparkles" />
                          <span>Запустить тест</span>
                        </button>
                        <button
                          type="button"
                          className="btn-danger"
                          onClick={handleDeleteProtocol}
                        >
                          <Icon name="trash" />
                          <span>Удалить</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Основные параметры */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title">
                    <div className="group-title-row">
                      <Icon name="set" style={{ width: '16px', height: '16px', color: 'var(--accent)' }} />
                      <span>Основные параметры</span>
                    </div>
                    <span className="group-badge">Параметры</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div className="form-field">
                      <label>Название сценария:</label>
                      <input
                        type="text"
                        className="text-input"
                        value={editingProtocol.name || ''}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, name: e.target.value })}
                        placeholder="Например: Стрим, Доброе утро, Чистый стол"
                      />
                    </div>

                    <div className="form-field">
                      <label>Фразы активации (через запятую):</label>
                      <input
                        type="text"
                        className="text-input"
                        value={
                          Array.isArray(editingProtocol.phrases)
                            ? editingProtocol.phrases.join(', ')
                            : editingProtocol.phrases || ''
                        }
                        onChange={(e) =>
                          setEditingProtocol({
                            ...editingProtocol,
                            phrases: e.target.value.split(',').map((s) => s.trim()),
                          })
                        }
                        placeholder="стрим, режим стрим, погнали стримить"
                      />
                    </div>
                  </div>

                  <div className="form-field">
                    <label>Описание сценария:</label>
                    <input
                      type="text"
                      className="text-input"
                      value={editingProtocol.description || ''}
                      onChange={(e) => setEditingProtocol({ ...editingProtocol, description: e.target.value })}
                      placeholder="Краткое описание действий сценария..."
                    />
                  </div>
                </div>

                {/* Запуск программ */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title accent">
                    <div className="group-title-row">
                      <Icon name="workspace" style={{ width: '16px', height: '16px', color: 'var(--accent)' }} />
                      <span>Запуск программ (открыть)</span>
                    </div>
                    <span className="group-badge">Автозапуск</span>
                  </div>
                  <input
                    type="text"
                    className="text-input"
                    value={
                      Array.isArray(editingProtocol.open_apps)
                        ? editingProtocol.open_apps.join(', ')
                        : editingProtocol.open_apps || ''
                    }
                    onChange={(e) =>
                      setEditingProtocol({
                        ...editingProtocol,
                        open_apps: e.target.value.split(',').map((s) => s.trim()),
                      })
                    }
                    placeholder="Ключ, имя программы или абсолютный путь к .exe"
                    style={{ marginBottom: '4px' }}
                  />

                  <div className="protocol-chips-row">
                    <span style={{ fontSize: '11px', color: 'var(--mut)' }}>Быстро добавить:</span>
                    <button
                      type="button"
                      className="protocol-chip-btn"
                      onClick={() => handleAddQuickApp('role:browser')}
                      title={`Роль браузера (${roles.browser || 'не задан'})`}
                    >
                      + Роль: Браузер
                    </button>
                    <button
                      type="button"
                      className="protocol-chip-btn"
                      onClick={() => handleAddQuickApp('role:messenger')}
                      title={`Роль мессенджера (${roles.messenger || 'не задан'})`}
                    >
                      + Роль: Мессенджер
                    </button>
                    {availableSuggestions.slice(0, 6).map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        className="protocol-chip-btn"
                        onClick={() => handleAddQuickApp(item.key)}
                      >
                        + {item.label}
                      </button>
                    ))}

                    {availableSuggestions.length > 0 && (
                      <button
                        type="button"
                        className="protocol-chip-btn"
                        onClick={() => openAppsPickerModal('open')}
                      >
                        + Программы ({availableSuggestions.length})
                      </button>
                    )}

                    {steamInstalled && (
                      <button
                        type="button"
                        className="protocol-chip-btn steam"
                        onClick={() => setShowSteamModal(true)}
                      >
                        + Игра Steam ({steamGames.length})
                      </button>
                    )}
                  </div>
                </div>

                {/* Закрытие программ */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title danger">
                    <div className="group-title-row">
                      <Icon name="trash" style={{ width: '16px', height: '16px', color: 'var(--danger)' }} />
                      <span>Закрытие программ</span>
                    </div>
                    <span className="group-badge" style={{ background: 'rgba(244, 63, 94, 0.12)', color: 'var(--danger)' }}>Процессы</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div className="form-field">
                      <label style={{ fontSize: '11px' }}>Режим закрытия:</label>
                      <select
                        value={editingProtocol.close_mode || 'none'}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, close_mode: e.target.value })}
                        className="select-input"
                      >
                        <option value="none">Не закрывать программы</option>
                        <option value="steam_games">Закрывать игры Steam (Wallpaper Engine сохраняется)</option>
                        <option value="cinema">Режим Кино (закрыть игры, Discord и Steam оставить)</option>
                        <option value="game">Режим Игра (закрыть браузер и программы, Steam и Discord на связи)</option>
                      </select>
                    </div>

                    <div className="form-field">
                      <label style={{ fontSize: '11px' }}>Дополнительно закрыть (через запятую):</label>
                      <input
                        type="text"
                        className="text-input"
                        value={
                          Array.isArray(editingProtocol.close_apps)
                            ? editingProtocol.close_apps.join(', ')
                            : editingProtocol.close_apps || ''
                        }
                        onChange={(e) =>
                          setEditingProtocol({
                            ...editingProtocol,
                            close_apps: e.target.value.split(',').map((s) => s.trim()),
                          })
                        }
                        placeholder="telegram, chrome, notepad"
                      />
                    </div>
                  </div>
                  {availableCloseSuggestions.length > 0 && (
                    <div className="protocol-chips-row" style={{ marginTop: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--mut)' }}>Быстро закрыть:</span>
                      {availableCloseSuggestions.slice(0, 6).map((item) => (
                        <button
                          key={`close_${item.key}`}
                          type="button"
                          className="protocol-chip-btn"
                          onClick={() => handleAddCloseApp(item.key)}
                        >
                          + {item.label}
                        </button>
                      ))}
                      <button
                        type="button"
                        className="protocol-chip-btn"
                        onClick={() => openAppsPickerModal('close')}
                      >
                        + Программы ({availableCloseSuggestions.length})
                      </button>
                    </div>
                  )}
                </div>

                {/* Исключения протокола (Locks) */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title">
                    <div className="group-title-row">
                      <Icon name="shield" style={{ width: '16px', height: '16px', color: 'var(--accent)' }} />
                      <span>Исключения этого протокола (Locks)</span>
                    </div>
                    <span className="group-badge">Локально</span>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--mut)', margin: '0 0 8px 0' }}>
                    Действуют только внутри «{editingProtocol.name || 'этого протокола'}» и не переносятся на остальные.
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div className="form-field">
                      <label style={{ fontSize: '11px' }}>Лок на закрытие (не закрывать):</label>
                      <input
                        type="text"
                        className="text-input"
                        value={
                          Array.isArray(editingProtocol.blocked_close_apps)
                            ? editingProtocol.blocked_close_apps.join(', ')
                            : editingProtocol.blocked_close_apps || ''
                        }
                        onChange={(e) =>
                          setEditingProtocol({
                            ...editingProtocol,
                            blocked_close_apps: e.target.value.split(',').map((s) => s.trim()),
                          })
                        }
                        placeholder="telegram, obs"
                      />
                      <div className="protocol-chips-row" style={{ marginTop: '6px' }}>
                        <button
                          type="button"
                          className="protocol-chip-btn"
                          onClick={() => openAppsPickerModal('block_close')}
                        >
                          + Выбрать прогу
                        </button>
                      </div>
                    </div>

                    <div className="form-field">
                      <label style={{ fontSize: '11px' }}>Лок на открытие (не запускать):</label>
                      <input
                        type="text"
                        className="text-input"
                        value={
                          Array.isArray(editingProtocol.blocked_open_apps)
                            ? editingProtocol.blocked_open_apps.join(', ')
                            : editingProtocol.blocked_open_apps || ''
                        }
                        onChange={(e) =>
                          setEditingProtocol({
                            ...editingProtocol,
                            blocked_open_apps: e.target.value.split(',').map((s) => s.trim()),
                          })
                        }
                        placeholder="steam, discord"
                      />
                      <div className="protocol-chips-row" style={{ marginTop: '6px' }}>
                        <button
                          type="button"
                          className="protocol-chip-btn"
                          onClick={() => openAppsPickerModal('block_open')}
                        >
                          + Выбрать прогу
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Шаги Protocols v2 */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title accent">
                    <div className="group-title-row">
                      <Icon name="zap" style={{ width: '16px', height: '16px', color: 'var(--accent)' }} />
                      <span>Дополнительные шаги (Protocols v2)</span>
                    </div>
                    <span className="group-badge">Сценарий</span>
                  </div>
                  <div className="protocol-chips-row" style={{ marginBottom: '8px' }}>
                    <button
                      type="button"
                      className="protocol-chip-btn"
                      onClick={() => handleAddStep('open_urls')}
                    >
                      + Открыть ссылки в браузере
                    </button>
                    <button
                      type="button"
                      className="protocol-chip-btn"
                      onClick={() => handleAddStep('launch_app')}
                    >
                      + Запуск с аргументами
                    </button>
                  </div>

                  {Array.isArray(editingProtocol.steps) && editingProtocol.steps.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {editingProtocol.steps.map((step, idx) => (
                        <div
                          key={`step_${idx}`}
                          style={{
                            padding: '10px',
                            borderRadius: '8px',
                            border: '1px solid var(--bd)',
                            background: 'rgba(255,255,255,0.02)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '8px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)' }}>
                              {step.type === 'open_urls' ? 'Открыть ссылки в браузере' : 'Запуск с аргументами'}
                            </span>
                            <button
                              type="button"
                              className="protocol-chip-btn"
                              onClick={() => handleRemoveStep(idx)}
                            >
                              Удалить шаг
                            </button>
                          </div>

                          {step.type === 'open_urls' ? (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                              <div className="form-field">
                                <label style={{ fontSize: '11px' }}>Браузер (или role:browser):</label>
                                <input
                                  type="text"
                                  className="text-input"
                                  value={step.browser || 'role:browser'}
                                  onChange={(e) => handleUpdateStep(idx, { browser: e.target.value })}
                                  placeholder="role:browser / vivaldi / chrome / firefox"
                                />
                              </div>
                              <div className="form-field">
                                <label style={{ fontSize: '11px' }}>Профиль браузера (опционально):</label>
                                <input
                                  type="text"
                                  className="text-input"
                                  value={step.profile || ''}
                                  onChange={(e) => handleUpdateStep(idx, { profile: e.target.value })}
                                  placeholder="Default / Profile 1"
                                />
                              </div>
                              <div className="form-field" style={{ gridColumn: '1 / -1' }}>
                                <label style={{ fontSize: '11px' }}>Ссылки (через запятую):</label>
                                <input
                                  type="text"
                                  className="text-input"
                                  value={Array.isArray(step.urls) ? step.urls.join(', ') : step.urls || ''}
                                  onChange={(e) =>
                                    handleUpdateStep(idx, {
                                      urls: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                                    })
                                  }
                                  placeholder="https://github.com, https://youtube.com"
                                />
                              </div>
                            </div>
                          ) : (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                              <div className="form-field">
                                <label style={{ fontSize: '11px' }}>Программа (ключ, путь или role:...):</label>
                                <input
                                  type="text"
                                  className="text-input"
                                  value={step.target || ''}
                                  onChange={(e) => handleUpdateStep(idx, { target: e.target.value })}
                                  placeholder="obs / role:work / C:\...\app.exe"
                                />
                              </div>
                              <div className="form-field">
                                <label style={{ fontSize: '11px' }}>Аргументы запуска:</label>
                                <input
                                  type="text"
                                  className="text-input"
                                  value={step.args || ''}
                                  onChange={(e) => handleUpdateStep(idx, { args: e.target.value })}
                                  placeholder="--startreplaybuffer"
                                />
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Системные действия и звук */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title purple">
                    <div className="group-title-row">
                      <Icon name="vol" style={{ width: '16px', height: '16px', color: '#c084fc' }} />
                      <span>Звук и системные действия Windows</span>
                    </div>
                    <span className="group-badge">Система</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--tx-dim)', fontWeight: 600 }}>
                      Громкость Windows:
                    </label>
                    <select
                      value={editingProtocol.volume_mode || 'none'}
                      onChange={(e) => setEditingProtocol({ ...editingProtocol, volume_mode: e.target.value })}
                      className="select-input"
                      style={{ padding: '6px 30px 6px 10px', fontSize: '12px' }}
                    >
                      <option value="none">Не изменять</option>
                      <option value="max">100% (Максимум)</option>
                      <option value="mute">Без звука (Mute)</option>
                    </select>
                  </div>

                  <div className="protocol-toggles-grid">
                    <div className="protocol-toggle-row">
                      <Toggle
                        value={Boolean(editingProtocol.pause_media)}
                        onChange={(v) => setEditingProtocol({ ...editingProtocol, pause_media: v })}
                        label="Пауза плеера"
                      />
                      <span
                        className="protocol-toggle-label"
                        onClick={() =>
                          setEditingProtocol({
                            ...editingProtocol,
                            pause_media: !editingProtocol.pause_media,
                          })
                        }
                      >
                        Поставить плеер / музыку на паузу
                      </span>
                    </div>

                    <div className="protocol-toggle-row">
                      <Toggle
                        value={Boolean(editingProtocol.lock_screen)}
                        onChange={(v) => setEditingProtocol({ ...editingProtocol, lock_screen: v })}
                        label="Блокировка ПК"
                      />
                      <span
                        className="protocol-toggle-label"
                        onClick={() =>
                          setEditingProtocol({
                            ...editingProtocol,
                            lock_screen: !editingProtocol.lock_screen,
                          })
                        }
                      >
                        Заблокировать компьютер (Win + L)
                      </span>
                    </div>

                    <div className="protocol-toggle-row">
                      <Toggle
                        value={Boolean(editingProtocol.clean_recycle_bin)}
                        onChange={(v) => setEditingProtocol({ ...editingProtocol, clean_recycle_bin: v })}
                        label="Очистить корзину"
                      />
                      <span
                        className="protocol-toggle-label"
                        onClick={() =>
                          setEditingProtocol({
                            ...editingProtocol,
                            clean_recycle_bin: !editingProtocol.clean_recycle_bin,
                          })
                        }
                      >
                        Очистить системную корзину Windows
                      </span>
                    </div>

                    <div className="protocol-toggle-row">
                      <Toggle
                        value={Boolean(editingProtocol.briefing)}
                        onChange={(v) => setEditingProtocol({ ...editingProtocol, briefing: v })}
                        label="Озвучить брифинг"
                      />
                      <span
                        className="protocol-toggle-label"
                        onClick={() =>
                          setEditingProtocol({
                            ...editingProtocol,
                            briefing: !editingProtocol.briefing,
                          })
                        }
                      >
                        Озвучить брифинг (время, дата и погода в Москве)
                      </span>
                    </div>
                  </div>
                </div>

                {/* Ответ ассистента */}
                <div className="protocol-section-card">
                  <div className="protocol-section-title">
                    <div className="group-title-row">
                      <Icon name="chat" style={{ width: '16px', height: '16px', color: 'var(--accent)' }} />
                      <span>Ответ ассистента</span>
                    </div>
                    <span className="group-badge">Реплика</span>
                  </div>
                  <div className="form-field">
                    <input
                      type="text"
                      className="text-input"
                      value={editingProtocol.response_text || ''}
                      onChange={(e) => setEditingProtocol({ ...editingProtocol, response_text: e.target.value })}
                      placeholder="Оставь пустым — и ассистент сгенерирует остроумный ответ сам через ИИ..."
                    />
                    <span style={{ fontSize: '11.5px', color: 'var(--mut)', marginTop: '2px' }}>
                      Если поле пустое, ассистент использует нейросеть или фирменные реплики ассистента.
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px', color: 'var(--mut)' }}>
                Выберите сценарий слева для редактирования или создайте новый
              </div>
            )}
          </div>
        )}

        {/* Модалка выбора установленной программы */}
        {showAppsModal && (
          <div className="protocol-modal-overlay" onClick={() => setShowAppsModal(false)}>
            <div
              className="protocol-modal-card"
              style={{ width: '500px', maxHeight: '80vh' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, color: 'var(--tx)' }}>
                  {showHiddenApps
                    ? 'Скрытые программы'
                    : appsModalTarget === 'close'
                      ? 'Закрыть программы'
                      : 'Установленные программы'}
                </h3>
                <button
                  type="button"
                  className="protocol-chip-btn"
                  onClick={() => setShowHiddenApps((v) => !v)}
                >
                  {showHiddenApps ? 'К обычным' : 'Показать скрытые'}
                </button>
              </div>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--tx-dim)' }}>
                {showHiddenApps
                  ? 'Программы, скрытые из подсказок протоколов:'
                  : 'Показаны найденные на ПК приложения, которых ещё нет в списке:'}
              </p>
              <input
                type="text"
                autoFocus
                className="text-input"
                value={appsSearch}
                onChange={(e) => setAppsSearch(e.target.value)}
                placeholder="Поиск программы..."
              />
              <div className="protocol-steam-list">
                {filteredModalApps.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: 'var(--mut)' }}>
                    {showHiddenApps ? 'Скрытых программ нет' : 'Подходящих программ не найдено'}
                  </div>
                ) : (
                  filteredModalApps.map((app) => (
                    <div
                      key={app.key}
                      className="protocol-steam-item"
                      style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}
                    >
                      <button
                        type="button"
                        onClick={() => {
                          if (!showHiddenApps) {
                            if (appsModalTarget === 'close') {
                              handleAddCloseApp(app.key);
                            } else if (appsModalTarget === 'block_open') {
                              handleAddBlockedOpenApp(app.key);
                            } else if (appsModalTarget === 'block_close') {
                              handleAddBlockedCloseApp(app.key);
                            } else {
                              handleAddQuickApp(app.key);
                            }
                            setShowAppsModal(false);
                          }
                        }}
                        style={{
                          flex: 1,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          background: 'transparent',
                          border: 'none',
                          color: 'inherit',
                          cursor: showHiddenApps ? 'default' : 'pointer',
                          padding: 0,
                          textAlign: 'left',
                        }}
                      >
                        <span style={{ fontWeight: 500 }}>{app.label}</span>
                        <span style={{ fontSize: '11px', color: 'var(--accent)' }}>{app.key}</span>
                      </button>
                      <button
                        type="button"
                        className="protocol-chip-btn"
                        title={showHiddenApps ? 'Вернуть в подсказки' : 'Скрыть из подсказок'}
                        onClick={() => handleToggleAppVisibility(app.key, !showHiddenApps)}
                      >
                        {showHiddenApps ? 'Вернуть' : 'Скрыть'}
                      </button>
                    </div>
                  ))
                )}
              </div>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowAppsModal(false)}
                style={{ alignSelf: 'flex-end' }}
              >
                Закрыть
              </button>
            </div>
          </div>
        )}

        {/* Модалка выбора игры Steam */}
        {showSteamModal && (
          <div className="protocol-modal-overlay" onClick={() => setShowSteamModal(false)}>
            <div
              className="protocol-modal-card"
              style={{ width: '450px', maxHeight: '80vh' }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 style={{ margin: 0, color: 'var(--tx)' }}>Установленные игры Steam</h3>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--tx-dim)' }}>
                Выберите игру, чтобы добавить её автоматический запуск в сценарий:
              </p>
              <div className="protocol-steam-list">
                {steamGames.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: 'var(--mut)' }}>
                    Игры Steam не обнаружены
                  </div>
                ) : (
                  steamGames.map((game) => (
                    <button
                      key={game.appid}
                      type="button"
                      className="protocol-steam-item"
                      onClick={() => handleAddSteamGame(game)}
                    >
                      <span style={{ fontWeight: 500 }}>{game.name}</span>
                      <span style={{ fontSize: '11px', color: 'var(--accent)' }}>AppID: {game.appid}</span>
                    </button>
                  ))
                )}
              </div>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowSteamModal(false)}
                style={{ alignSelf: 'flex-end' }}
              >
                Закрыть
              </button>
            </div>
          </div>
        )}

        {/* Модалка создания нового профиля */}
        {showNewProfileModal && (
          <div className="protocol-modal-overlay" onClick={() => setShowNewProfileModal(false)}>
            <form
              onSubmit={handleCreateProfile}
              className="protocol-modal-card"
              style={{ width: '380px' }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 style={{ margin: 0, color: 'var(--tx)' }}>Новый профиль сценариев</h3>
              <div className="form-field">
                <label>Имя пользователя / Название профиля:</label>
                <input
                  type="text"
                  autoFocus
                  className="text-input"
                  value={newProfileName}
                  onChange={(e) => setNewProfileName(e.target.value)}
                  placeholder="Например: Гость, Брат, Стример"
                  required
                />
              </div>

              <div className="protocol-toggle-row">
                <Toggle
                  value={copyFromActive}
                  onChange={setCopyFromActive}
                  label="Скопировать протоколы"
                />
                <span
                  className="protocol-toggle-label"
                  onClick={() => setCopyFromActive(!copyFromActive)}
                >
                  Скопировать протоколы из текущего профиля
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowNewProfileModal(false)}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                >
                  Создать
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Модалка настройки ролей ПК */}
        {showRolesModal && (
          <div className="protocol-modal-overlay" onClick={() => setShowRolesModal(false)}>
            <form
              onSubmit={handleSaveRoles}
              className="protocol-modal-card"
              style={{ width: '460px' }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 style={{ margin: 0, color: 'var(--tx)' }}>Роли программ для этого ПК</h3>
              <p style={{ margin: '4px 0 8px 0', fontSize: '12px', color: 'var(--mut)' }}>
                Позволяет сценариям с <code>role:browser</code> и <code>role:messenger</code> работать на любом компьютере без правки самих протоколов.
              </p>

              {[
                { key: 'browser', label: 'Основной браузер (role:browser)', placeholder: 'vivaldi / chrome / firefox / opera' },
                { key: 'messenger', label: 'Мессенджер (role:messenger)', placeholder: 'discord / telegram' },
                { key: 'gaming', label: 'Игровой лаунчер (role:gaming)', placeholder: 'steam' },
                { key: 'work', label: 'Рабочая среда (role:work)', placeholder: 'antigravity / vscode' },
              ].map((item) => (
                <div className="form-field" key={item.key}>
                  <label>{item.label}:</label>
                  <input
                    type="text"
                    className="text-input"
                    value={roles[item.key] || ''}
                    onChange={(e) => setRoles({ ...roles, [item.key]: e.target.value })}
                    placeholder={item.placeholder}
                    list={`role_list_${item.key}`}
                  />
                  <datalist id={`role_list_${item.key}`}>
                    {suggestedApps.map((app) => (
                      <option key={`${item.key}_${app.key}`} value={app.key}>
                        {app.label}
                      </option>
                    ))}
                  </datalist>
                </div>
              ))}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowRolesModal(false)}
                >
                  Отмена
                </button>
                <button type="submit" className="btn-primary">
                  Сохранить роли
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
