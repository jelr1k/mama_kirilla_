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
  const [selectedProtocolId, setSelectedProtocolId] = useState(null);
  const [editingProtocol, setEditingProtocol] = useState(null);
  const [steamGames, setSteamGames] = useState([]);
  const [steamInstalled, setSteamInstalled] = useState(false);
  const [showSteamModal, setShowSteamModal] = useState(false);
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

  useEffect(() => {
    loadProtocols();
    loadSteamData();
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

  const handleAddQuickApp = (appKey) => {
    if (!editingProtocol) return;
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
            <h1 className="page-title">Сценарии и Протоколы JARVIS</h1>
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
              <div className="protocol-editor">
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
                    placeholder="opera, discord, steam или абсолютные пути к .exe"
                    style={{ marginBottom: '4px' }}
                  />

                  <div className="protocol-chips-row">
                    <span style={{ fontSize: '11px', color: 'var(--mut)' }}>Быстро добавить:</span>
                    {[
                      { label: 'Opera GX', key: 'opera' },
                      { label: 'Discord', key: 'discord' },
                      { label: 'Steam', key: 'steam' },
                      { label: 'Antigravity', key: 'antigravity' },
                      { label: 'Unlocker', key: 'unlocker' },
                      { label: 'Telegram', key: 'telegram' },
                      { label: 'Spotify', key: 'spotify' },
                    ].map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        className="protocol-chip-btn"
                        onClick={() => handleAddQuickApp(item.key)}
                      >
                        + {item.label}
                      </button>
                    ))}

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

                {/* Ответ JARVIS */}
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
                      placeholder="Оставь пустым — и JARVIS сгенерирует остроумный ответ сам через ИИ..."
                    />
                    <span style={{ fontSize: '11.5px', color: 'var(--mut)', marginTop: '2px' }}>
                      Если поле пустое, ассистент использует нейросеть или фирменные реплики Старка.
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
      </div>
    </div>
  );
}
