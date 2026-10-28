import React, { useState, useEffect } from 'react';
import { apiGet, apiPost, apiDelete } from '../services/api';
import { Icon } from './Icons';

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
            <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 600 }}>Профиль:</span>
            <select
              value={activeProfile}
              onChange={(e) => handleSelectProfile(e.target.value)}
              style={{
                background: '#1e293b',
                color: '#f8fafc',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {Object.entries(profiles).map(([pid, name]) => (
                <option key={pid} value={pid}>
                  {name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowNewProfileModal(true)}
              style={{
                background: '#0284c7',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 10px',
                fontSize: '12px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
              title="Создать новый профиль пользователя"
            >
              + Профиль
            </button>
            {activeProfile !== 'default' && (
              <button
                onClick={handleDeleteProfile}
                style={{
                  background: '#991b1b',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '6px 10px',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
                title="Удалить текущий профиль"
              >
                Удалить
              </button>
            )}
          </div>
        </header>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#64748b' }}>Загрузка протоколов...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', marginTop: '12px' }}>
            {/* Левая колонка: список сценариев */}
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                height: 'calc(100vh - 200px)',
                overflowY: 'auto',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#94a3b8' }}>
                  Протоколы ({protocols.length})
                </span>
                <button
                  onClick={handleNewProtocol}
                  style={{
                    background: '#0284c7',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '12px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  + Новый
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {protocols.map((proto) => {
                  const isSelected = selectedProtocolId === proto.id;
                  const isRunning = executingId === proto.id;
                  return (
                    <div
                      key={proto.id}
                      onClick={() => handleSelectProtocol(proto)}
                      style={{
                        padding: '10px',
                        borderRadius: '6px',
                        background: isSelected ? '#1e293b' : '#141e33',
                        border: isSelected ? '1px solid #38bdf8' : '1px solid #1e293b',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, color: isSelected ? '#38bdf8' : '#e2e8f0', fontSize: '14px' }}>
                          {proto.name}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleExecuteProtocol(proto.id, proto.name);
                          }}
                          disabled={isRunning}
                          style={{
                            background: isRunning ? '#64748b' : '#059669',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '3px 8px',
                            fontSize: '11px',
                            cursor: isRunning ? 'default' : 'pointer',
                            fontWeight: 600,
                          }}
                          title="Запустить сценарий прямо сейчас"
                        >
                          {isRunning ? '...' : 'Старт'}
                        </button>
                      </div>
                      {proto.description && (
                        <p style={{ fontSize: '11px', color: '#94a3b8', margin: 0, lineHeight: 1.3 }}>
                          {proto.description}
                        </p>
                      )}
                      {proto.phrases && proto.phrases.length > 0 && (
                        <div style={{ fontSize: '10px', color: '#64748b', marginTop: '2px' }}>
                          голос: «{proto.phrases[0]}»
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Правая колонка: детальный редактор */}
            {editingProtocol ? (
              <div
                style={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  height: 'calc(100vh - 200px)',
                  overflowY: 'auto',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
                    {selectedProtocolId === '__new__' ? 'Создание протокола' : `Редактирование: ${editingProtocol.name}`}
                  </h2>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={handleSaveProtocol}
                      style={{
                        background: '#0284c7',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '6px',
                        padding: '8px 16px',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Сохранить
                    </button>
                    {selectedProtocolId !== '__new__' && (
                      <>
                        <button
                          onClick={() => handleExecuteProtocol(editingProtocol.id, editingProtocol.name)}
                          style={{
                            background: '#059669',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '8px 14px',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Запустить тест
                        </button>
                        <button
                          onClick={handleDeleteProtocol}
                          style={{
                            background: '#991b1b',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '8px 12px',
                            cursor: 'pointer',
                          }}
                        >
                          Удалить
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Основные поля */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                      Название сценария:
                    </label>
                    <input
                      type="text"
                      value={editingProtocol.name || ''}
                      onChange={(e) => setEditingProtocol({ ...editingProtocol, name: e.target.value })}
                      placeholder="Например: Стрим, Доброе утро, Чистый стол"
                      style={{
                        width: '100%',
                        padding: '8px',
                        borderRadius: '6px',
                        background: '#1e293b',
                        border: '1px solid #334155',
                        color: '#fff',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                      Фразы активации (через запятую):
                    </label>
                    <input
                      type="text"
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
                      style={{
                        width: '100%',
                        padding: '8px',
                        borderRadius: '6px',
                        background: '#1e293b',
                        border: '1px solid #334155',
                        color: '#fff',
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                    Описание:
                  </label>
                  <input
                    type="text"
                    value={editingProtocol.description || ''}
                    onChange={(e) => setEditingProtocol({ ...editingProtocol, description: e.target.value })}
                    placeholder="Краткое описание действий сценария..."
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      color: '#fff',
                    }}
                  />
                </div>

                {/* Запуск программ */}
                <div style={{ background: '#141e33', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#38bdf8', marginBottom: '6px' }}>
                    Запуск программ (открыть)
                  </label>
                  <input
                    type="text"
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
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      color: '#fff',
                      marginBottom: '8px',
                    }}
                  />

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>Быстро добавить:</span>
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
                        onClick={() => handleAddQuickApp(item.key)}
                        style={{
                          background: '#1e293b',
                          color: '#94a3b8',
                          border: '1px solid #334155',
                          borderRadius: '4px',
                          padding: '2px 8px',
                          fontSize: '11px',
                          cursor: 'pointer',
                        }}
                      >
                        + {item.label}
                      </button>
                    ))}

                    {steamInstalled && (
                      <button
                        onClick={() => setShowSteamModal(true)}
                        style={{
                          background: '#172554',
                          color: '#93c5fd',
                          border: '1px solid #1e40af',
                          borderRadius: '4px',
                          padding: '2px 8px',
                          fontSize: '11px',
                          cursor: 'pointer',
                          fontWeight: 500,
                        }}
                      >
                        + Игра Steam ({steamGames.length})
                      </button>
                    )}
                  </div>
                </div>

                {/* Закрытие программ */}
                <div style={{ background: '#141e33', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#f43f5e', marginBottom: '6px' }}>
                    Закрытие программ
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                        Режим закрытия:
                      </label>
                      <select
                        value={editingProtocol.close_mode || 'none'}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, close_mode: e.target.value })}
                        style={{
                          width: '100%',
                          padding: '8px',
                          borderRadius: '6px',
                          background: '#1e293b',
                          border: '1px solid #334155',
                          color: '#fff',
                        }}
                      >
                        <option value="none">Не закрывать программы</option>
                        <option value="steam_games">Закрывать игры Steam (Wallpaper Engine сохраняется)</option>
                        <option value="cinema">Режим Кино (закрыть игры, Discord и Steam оставить)</option>
                        <option value="game">Режим Игра (закрыть браузер и программы, Steam и Discord на связи)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                        Дополнительно закрыть (через запятую):
                      </label>
                      <input
                        type="text"
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
                        style={{
                          width: '100%',
                          padding: '8px',
                          borderRadius: '6px',
                          background: '#1e293b',
                          border: '1px solid #334155',
                          color: '#fff',
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Системные действия и звук */}
                <div style={{ background: '#141e33', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#a855f7', marginBottom: '6px' }}>
                    Звук и системные действия Windows
                  </label>
                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ fontSize: '12px', color: '#94a3b8', marginRight: '10px' }}>
                      Громкость Windows:
                    </label>
                    <select
                      value={editingProtocol.volume_mode || 'none'}
                      onChange={(e) => setEditingProtocol({ ...editingProtocol, volume_mode: e.target.value })}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '6px',
                        background: '#1e293b',
                        border: '1px solid #334155',
                        color: '#fff',
                      }}
                    >
                      <option value="none">Не изменять</option>
                      <option value="max">100% (Максимум)</option>
                      <option value="mute">Без звука (Mute)</option>
                    </select>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(editingProtocol.pause_media)}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, pause_media: e.target.checked })}
                      />
                      Поставить плеер / музыку на паузу
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(editingProtocol.lock_screen)}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, lock_screen: e.target.checked })}
                      />
                      Заблокировать компьютер (Win + L)
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(editingProtocol.clean_recycle_bin)}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, clean_recycle_bin: e.target.checked })}
                      />
                      Очистить системную корзину Windows
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(editingProtocol.briefing)}
                        onChange={(e) => setEditingProtocol({ ...editingProtocol, briefing: e.target.checked })}
                      />
                      Озвучить брифинг (время, дата и погода в Москве)
                    </label>
                  </div>
                </div>

                {/* Ответ JARVIS */}
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                    Ответ ассистента:
                  </label>
                  <input
                    type="text"
                    value={editingProtocol.response_text || ''}
                    onChange={(e) => setEditingProtocol({ ...editingProtocol, response_text: e.target.value })}
                    placeholder="Оставь пустым — и JARVIS сгенерирует остроумный ответ сам через ИИ..."
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '6px',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      color: '#fff',
                    }}
                  />
                  <span style={{ fontSize: '11px', color: '#64748b' }}>
                    Если поле пустое, ассистент использует нейросеть или фирменные реплики Старка.
                  </span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>
                Выберите сценарий слева для редактирования или создайте новый
              </div>
            )}
          </div>
        )}

        {/* Модалка выбора игры Steam */}
        {showSteamModal && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
            }}
          >
            <div
              style={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '20px',
                width: '450px',
                maxHeight: '80vh',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <h3 style={{ margin: 0, color: '#f8fafc' }}>Установленные игры Steam</h3>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                Выберите игру, чтобы добавить её автоматический запуск в сценарий:
              </p>
              <div style={{ overflowY: 'auto', maxHeight: '300px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {steamGames.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>
                    Игры Steam не обнаружены
                  </div>
                ) : (
                  steamGames.map((game) => (
                    <button
                      key={game.appid}
                      onClick={() => handleAddSteamGame(game)}
                      style={{
                        background: '#1e293b',
                        color: '#f8fafc',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        padding: '8px 12px',
                        textAlign: 'left',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontWeight: 500 }}>{game.name}</span>
                      <span style={{ fontSize: '11px', color: '#38bdf8' }}>AppID: {game.appid}</span>
                    </button>
                  ))
                )}
              </div>
              <button
                onClick={() => setShowSteamModal(false)}
                style={{
                  background: '#334155',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px',
                  cursor: 'pointer',
                }}
              >
                Закрыть
              </button>
            </div>
          </div>
        )}

        {/* Модалка создания нового профиля */}
        {showNewProfileModal && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
            }}
          >
            <form
              onSubmit={handleCreateProfile}
              style={{
                background: '#0f172a',
                border: '1px solid #334155',
                borderRadius: '8px',
                padding: '20px',
                width: '380px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <h3 style={{ margin: 0, color: '#f8fafc' }}>Новый профиль сценариев</h3>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                  Имя пользователя / Название профиля:
                </label>
                <input
                  type="text"
                  autoFocus
                  value={newProfileName}
                  onChange={(e) => setNewProfileName(e.target.value)}
                  placeholder="Например: Гость, Брат, Стример"
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '6px',
                    background: '#1e293b',
                    border: '1px solid #334155',
                    color: '#fff',
                  }}
                />
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#cbd5e1', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={copyFromActive}
                  onChange={(e) => setCopyFromActive(e.target.checked)}
                />
                Скопировать протоколы из текущего профиля
              </label>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <button
                  type="button"
                  onClick={() => setShowNewProfileModal(false)}
                  style={{
                    background: '#334155',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    cursor: 'pointer',
                  }}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  style={{
                    background: '#0284c7',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '6px 14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
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
