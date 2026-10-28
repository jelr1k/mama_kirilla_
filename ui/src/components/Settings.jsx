import { apiFetch } from '../services/api';
import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';

function Tip({ text }) {
  return (
    <span className="tooltip-badge" tabIndex={0}>
      ?
      <span className="tooltip-text">{text}</span>
    </span>
  );
}

function Toggle({ value, onChange, label }) {
  return (
    <button
      className={`tg ${value ? 'on' : ''}`}
      onClick={() => onChange(!value)}
      role="switch"
      aria-checked={value}
      aria-label={label}
    />
  );
}

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3500);
  };

  // App & Identity
  const [appTitle, setAppTitle] = useState('Kirieshcka v2');
  const [assistantName, setAssistantName] = useState('Kirieshcka');
  const [autostart, setAutostart] = useState(false);

  // Updates
  const [currentVersion, setCurrentVersion] = useState('0.1.7');
  const [latestVersion, setLatestVersion] = useState('');
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [releaseUrl, setReleaseUrl] = useState('');
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [applyingUpdate, setApplyingUpdate] = useState(false);
  const [updateStatus, setUpdateStatus] = useState('idle');
  const [updateProgress, setUpdateProgress] = useState(0);
  const [updateSpeed, setUpdateSpeed] = useState(0);
  const [archiveSize, setArchiveSize] = useState(0);

  // Ollama & LLM
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [model, setModel] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [temperature, setTemperature] = useState(0.7);
  const [contextLength, setContextLength] = useState(32768);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [routerOnlyMode, setRouterOnlyMode] = useState(false);
  const [ollamaBusy, setOllamaBusy] = useState(false);

  // Voice & STT
  const [microphones, setMicrophones] = useState([]);
  const [selectedMic, setSelectedMic] = useState(null);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [wakeWordText, setWakeWordText] = useState('шпрота');
  const [whisperModel, setWhisperModel] = useState('small');
  const [customWhisperPath, setCustomWhisperPath] = useState('');
  const [whisperStatuses, setWhisperStatuses] = useState({});
  const [whisperDownloading, setWhisperDownloading] = useState({});
  const [cpuThreads, setCpuThreads] = useState(4);
  const [beamSize, setBeamSize] = useState(5);
  const [vadFilter, setVadFilter] = useState(true);
  const [silenceDuration, setSilenceDuration] = useState(2.0);
  const [micTesting, setMicTesting] = useState(false);

  // TTS
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [ttsVoice, setTtsVoice] = useState('ru_RU-dmitri-medium');
  const [ttsStatuses, setTtsStatuses] = useState({});
  const [ttsDownloading, setTtsDownloading] = useState({});
  const [ttsSpeed, setTtsSpeed] = useState(1.0);
  const [ttsVolume, setTtsVolume] = useState(0.85);

  // Workspace
  const [allowOutsideWorkspace, setAllowOutsideWorkspace] = useState(false);

  // ROFL & Secret word
  const [roflSecret, setRoflSecret] = useState('');
  const [roflUnlocked, setRoflUnlocked] = useState(false);
  const [roflChance, setRoflChance] = useState(12.0);
  const [roflDemonChance, setRoflDemonChance] = useState(15.0);
  const [roflSaving, setRoflSaving] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/api/settings');
      const data = await res.json();
      const cfg = data.settings || {};

      setAppTitle(cfg.app_title || 'Kirieshcka v2');
      setAssistantName(cfg.assistant_name || 'Kirieshcka');
      setModel(cfg.model || '');
      setTemperature(cfg.temperature !== undefined ? cfg.temperature : 0.7);
      setContextLength(cfg.context_length || 32768);
      setMaxTokens(cfg.max_tokens || 4096);
      setRouterOnlyMode(Boolean(cfg.router_only_mode));
      setAllowOutsideWorkspace(Boolean(cfg.allow_outside_workspace));

      const ollama = cfg.ollama || {};
      setOllamaUrl(ollama.base_url || 'http://localhost:11434');

      const voice = cfg.voice || {};
      setWakeWordEnabled(voice.wake_word_enabled !== false);
      setWakeWordText(voice.wake_word || 'шпрота');
      const vModel = voice.model || 'small';
      if (['small', 'medium', 'large-v3'].includes(vModel)) {
        setWhisperModel(vModel);
      } else {
        setWhisperModel('custom');
        setCustomWhisperPath(vModel);
      }
      setCpuThreads(voice.cpu_threads || 4);
      setBeamSize(voice.beam_size || 5);
      setVadFilter(voice.vad_filter !== false);
      setSilenceDuration(voice.silence_duration || 2.0);
      setSelectedMic(voice.input_device !== undefined ? voice.input_device : null);

      const tts = cfg.tts || {};
      setTtsEnabled(Boolean(tts.enabled));
      setTtsVoice(tts.voice || 'ru_RU-dmitri-medium');
      setTtsSpeed(tts.speed || 1.0);
      setTtsVolume(tts.volume !== undefined ? tts.volume : 0.85);

      // Base config is ready, instantly show the page!
      setLoading(false);

      // Fetch background lists (mics, models, statuses) non-blockingly
      fetchAutostart();
      fetchMicrophones();
      fetchModels();
      fetchWhisperStatuses();
      fetchTtsStatuses();
    } catch (err) {
      console.error('Failed to load settings:', err);
      showStatus('Ошибка загрузки настроек', true);
      setLoading(false);
    }
  };

  const fetchAutostart = async () => {
    try {
      const res = await apiFetch('/api/autostart');
      const data = await res.json();
      setAutostart(Boolean(data.enabled));
    } catch (e) {}
  };

  const fetchMicrophones = async () => {
    try {
      const res = await apiFetch('/api/microphones');
      const data = await res.json();
      setMicrophones(data.devices || []);
    } catch (e) {}
  };

  const fetchModels = async () => {
    try {
      const res = await apiFetch('/api/models');
      const data = await res.json();
      setAvailableModels(data.ollama_models || []);
    } catch (e) {}
  };

  const fetchWhisperStatuses = async () => {
    try {
      const res = await apiFetch('/api/whisper/status');
      const data = await res.json();
      setWhisperStatuses(data.statuses || {});
    } catch (e) {}
  };

  const fetchTtsStatuses = async () => {
    try {
      const res = await apiFetch('/api/tts/status');
      const data = await res.json();
      setTtsStatuses(data.statuses || {});
    } catch (e) {}
  };

  const handleDownloadWhisper = async (modelName) => {
    try {
      setWhisperDownloading((prev) => ({ ...prev, [modelName]: true }));
      showStatus(`Начата фоновая загрузка модели Whisper «${modelName}»...`);
      const res = await apiFetch('/api/whisper/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: modelName }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus(`Загрузка модели «${modelName}» запущена в фоне`);
        // Poll status every 4 seconds
        const timer = setInterval(async () => {
          const sRes = await apiFetch('/api/whisper/status');
          const sData = await sRes.json();
          setWhisperStatuses(sData.statuses || {});
          if (sData.statuses?.[modelName] === 'installed') {
            clearInterval(timer);
            setWhisperDownloading((prev) => ({ ...prev, [modelName]: false }));
            showStatus(`Модель Whisper «${modelName}» успешно установлена!`);
          }
        }, 4000);
      } else {
        setWhisperDownloading((prev) => ({ ...prev, [modelName]: false }));
        showStatus(data.error || 'Ошибка запуска скачивания', true);
      }
    } catch (e) {
      setWhisperDownloading((prev) => ({ ...prev, [modelName]: false }));
      showStatus('Ошибка скачивания модели', true);
    }
  };

  const handleDownloadTts = async (voiceId) => {
    try {
      setTtsDownloading((prev) => ({ ...prev, [voiceId]: true }));
      showStatus(`Начато скачивание голоса «${voiceId}» (~63 МБ)...`);
      const res = await apiFetch('/api/tts/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice: voiceId }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus(`Скачивание голоса «${voiceId}» запущено`);
        const timer = setInterval(async () => {
          const sRes = await apiFetch('/api/tts/status');
          const sData = await sRes.json();
          setTtsStatuses(sData.statuses || {});
          if (sData.statuses?.[voiceId] === 'installed') {
            clearInterval(timer);
            setTtsDownloading((prev) => ({ ...prev, [voiceId]: false }));
            showStatus(`Голос «${voiceId}» готов к озвучке!`);
          }
        }, 3000);
      } else {
        setTtsDownloading((prev) => ({ ...prev, [voiceId]: false }));
        showStatus(data.error || 'Ошибка скачивания голоса', true);
      }
    } catch (e) {
      setTtsDownloading((prev) => ({ ...prev, [voiceId]: false }));
      showStatus('Ошибка скачивания голоса', true);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const effectiveWhisperModel = whisperModel === 'custom' ? (customWhisperPath.trim() || 'small') : whisperModel;

      const payload = {
        app_title: appTitle.trim() || 'Kirieshcka v2',
        assistant_name: assistantName.trim(),
        model: model.trim(),
        temperature: parseFloat(temperature),
        context_length: parseInt(contextLength, 10),
        max_tokens: parseInt(maxTokens, 10),
        router_only_mode: routerOnlyMode,
        allow_outside_workspace: allowOutsideWorkspace,
        ollama: {
          base_url: ollamaUrl.trim(),
        },
        voice: {
          wake_word_enabled: wakeWordEnabled,
          wake_word: wakeWordText.trim(),
          model: effectiveWhisperModel,
          cpu_threads: parseInt(cpuThreads, 10),
          beam_size: parseInt(beamSize, 10),
          vad_filter: vadFilter,
          silence_duration: parseFloat(silenceDuration),
          input_device: selectedMic === 'default' || selectedMic === null ? null : parseInt(selectedMic, 10),
        },
        tts: {
          enabled: ttsEnabled,
          voice: ttsVoice,
          speed: parseFloat(ttsSpeed),
          volume: parseFloat(ttsVolume),
        },
      };

      const res = await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      await apiFetch('/api/autostart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: autostart }),
      });

      const data = await res.json();
      if (data.success) {
        showStatus('Все параметры успешно сохранены и применены');
        document.title = `${assistantName.trim()} v2`;
      } else {
        showStatus(data.error || 'Ошибка сохранения', true);
      }
    } catch (err) {
      showStatus('Ошибка сохранения', true);
    } finally {
      setSaving(false);
    }
  };

  const handleCheckUpdates = async () => {
    try {
      setCheckingUpdates(true);
      const res = await apiFetch('/api/updates');
      const data = await res.json();
      setCurrentVersion(data.current_version || currentVersion);
      setLatestVersion(data.latest_version || currentVersion);
      const hasUpd = Boolean(data.has_update || data.update_available);
      setUpdateAvailable(hasUpd);
      setReleaseUrl(data.html_url || '');
      setArchiveSize(data.archive_size || 0);
      if (hasUpd) {
        showStatus(`Доступна новая версия: ${data.latest_version}`);
      } else {
        showStatus(`Установлена актуальная версия (${data.current_version})`);
      }
    } catch (e) {
      showStatus('Ошибка проверки обновлений', true);
    } finally {
      setCheckingUpdates(false);
    }
  };

  const handleApplyUpdate = async () => {
    if (!window.confirm(`Скачать и установить обновление v${latestVersion} сейчас? Программа автоматически создаст резервную копию и перезапустится.`)) {
      return;
    }
    try {
      setApplyingUpdate(true);
      showStatus('Запуск процесса автоматического обновления...');
      const res = await apiFetch('/api/updates/apply', { method: 'POST' });
      const data = await res.json();
      if (!data.success) {
        showStatus(data.error || 'Ошибка запуска обновления', true);
        setApplyingUpdate(false);
      } else {
        const timer = setInterval(async () => {
          try {
            const uRes = await apiFetch('/api/updates');
            const uData = await uRes.json();
            setUpdateStatus(uData.status);
            setUpdateProgress(uData.progress_percent || 0);
            setUpdateSpeed(uData.download_speed_mb || 0);
            if (uData.status === 'relaunching') {
              clearInterval(timer);
              showStatus('Обновление готово! Перезапуск Jarvis...');
            } else if (uData.status === 'error') {
              clearInterval(timer);
              setApplyingUpdate(false);
              showStatus(uData.error || 'Ошибка в процессе обновления', true);
            }
          } catch (e) {
            clearInterval(timer);
            showStatus('Приложение перезапускается с новой версией...');
          }
        }, 1000);
      }
    } catch (e) {
      showStatus('Сетевая ошибка при запросе обновления', true);
      setApplyingUpdate(false);
    }
  };

  const handleRestartOllama = async () => {
    try {
      setOllamaBusy(true);
      const res = await apiFetch('/api/ollama/restart', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showStatus('Служба Ollama доступна и перезапущена');
        fetchModels();
      } else {
        showStatus(data.error || 'Ошибка подключения к Ollama', true);
      }
    } catch (e) {
      showStatus('Не удалось подключиться к Ollama', true);
    } finally {
      setOllamaBusy(false);
    }
  };

  const handleTestTts = async () => {
    try {
      showStatus('Воспроизведение тестовой фразы...');
      await apiFetch('/api/tts/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: `Привет, я ${assistantName}. Синтез речи работает отлично!` }),
      });
    } catch (e) {}
  };

  const handleTestMic = async () => {
    try {
      setMicTesting(true);
      const res = await apiFetch('/api/microphones/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device: selectedMic === 'default' ? null : selectedMic }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus(`Сигнал микрофона OK: Peak: ${(data.peak || 0).toFixed(2)}, RMS: ${(data.rms || 0).toFixed(3)}`);
      } else {
        showStatus('Ошибка теста микрофона', true);
      }
    } catch (e) {
      showStatus('Ошибка проверки звука', true);
    } finally {
      setMicTesting(false);
    }
  };

  const handleShutdown = async () => {
    if (!window.confirm('Завершить работу приложения и фонового ядра?')) return;
    try {
      await apiFetch('/api/shutdown', { method: 'POST' });
    } catch (e) {}
    window.close();
  };

  const handleCheckRoflSecret = async (val) => {
    setRoflSecret(val);
    if (val.trim().toLowerCase() === 'джарвис') {
      try {
        const res = await apiFetch('/api/rofl/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ secret: val.trim() }),
        });
        const data = await res.json();
        if (data.unlocked) {
          setRoflUnlocked(true);
          setRoflChance((data.chance ?? 0.12) * 100);
          setRoflDemonChance((data.demon_chance ?? 0.15) * 100);
          setRoflSecret('');
          showStatus('Служебный раздел рофлов разблокирован!');
        }
      } catch (err) {}
    }
  };

  const handleSaveRofl = async () => {
    try {
      setRoflSaving(true);
      const res = await apiFetch('/api/rofl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          secret: 'джарвис',
          chance: roflChance / 100.0,
          demon_chance: roflDemonChance / 100.0,
        }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus('Настройки рофлов сохранены!');
      } else {
        showStatus(data.error || 'Ошибка сохранения рофлов', true);
      }
    } catch (e) {
      showStatus('Ошибка сети при сохранении рофлов', true);
    } finally {
      setRoflSaving(false);
    }
  };

  const handleResetRofl = () => {
    setRoflChance(12.0);
    setRoflDemonChance(15.0);
    showStatus('Значения сброшены до стандартных (12% и 15%)');
  };

  if (loading) {
    return (
      <div className="page standard-page">
        <div className="page-container">
          <div className="skeleton-bar header" style={{ height: '40px', width: '320px', marginBottom: '24px' }} />
          <div className="skeleton-card" style={{ height: '120px', marginBottom: '16px' }} />
          <div className="skeleton-card" style={{ height: '180px', marginBottom: '16px' }} />
          <div className="skeleton-card" style={{ height: '220px' }} />
        </div>
      </div>
    );
  }

  const currentWhisperStatus = whisperStatuses[whisperModel] || 'unknown';
  const currentTtsStatus = ttsStatuses[ttsVoice] || 'missing';

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Параметры и конфигурация</h1>
            <p className="page-desc">Полный контроль над звуком, моделями ИИ, песочницей и системой</p>
          </div>
          <div className="header-actions">
            <button className="btn-secondary" onClick={handleCheckUpdates} disabled={checkingUpdates}>
              <Icon name="refresh" className={checkingUpdates ? 'spin-icon' : ''} />
              <span>{checkingUpdates ? 'Проверка...' : `v${currentVersion}`}</span>
            </button>
            <button className="primary-action-btn" onClick={handleSave} disabled={saving}>
              <Icon name="save" />
              <span>{saving ? 'Сохранение...' : 'Сохранить настройки'}</span>
            </button>
          </div>
        </header>

        {updateAvailable && (
          <div
            className="status-banner success"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              padding: '14px 16px',
              background: 'rgba(14, 165, 233, 0.08)',
              border: '1px solid rgba(14, 165, 233, 0.3)',
              borderRadius: '8px',
              marginBottom: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Icon name="sparkles" />
                <span>
                  Доступно обновление <strong>v{latestVersion}</strong> (у вас v{currentVersion})
                  {archiveSize > 0 && ` • ${(archiveSize / (1024 * 1024)).toFixed(1)} МБ`}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                {releaseUrl && (
                  <a
                    href={releaseUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '12px' }}
                  >
                    Релиз на GitHub
                  </a>
                )}
                <button
                  className="btn-primary"
                  onClick={handleApplyUpdate}
                  disabled={applyingUpdate}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Icon name="check" />
                  <span>
                    {applyingUpdate
                      ? updateStatus === 'downloading'
                        ? `Скачивание ${updateProgress}% (${updateSpeed} МБ/с)`
                        : updateStatus === 'validating'
                        ? 'Проверка архива...'
                        : updateStatus === 'backing_up'
                        ? 'Создание бэкапа...'
                        : updateStatus === 'relaunching'
                        ? 'Перезапуск...'
                        : 'Установка...'
                      : 'Скачать и установить в 1 клик'}
                  </span>
                </button>
              </div>
            </div>

            {applyingUpdate && (
              <div style={{ width: '100%', background: 'rgba(0,0,0,0.3)', borderRadius: '4px', overflow: 'hidden', height: '6px' }}>
                <div
                  style={{
                    width: `${updateProgress}%`,
                    height: '100%',
                    background: '#0ea5e9',
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
            )}
          </div>
        )}

        {statusMsg && (
          <div className={`status-banner ${statusMsg.isError ? 'error' : 'success'}`}>
            <Icon name={statusMsg.isError ? 'bell' : 'check'} />
            <span>{statusMsg.text}</span>
          </div>
        )}

        <div className="settings-sections">
          {/* Секция 1: Имя и Автозапуск */}
          <div className="settings-card">
            <div className="card-section-title">
              <Icon name="sparkles" />
              <span>Общие параметры</span>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Именование приложения
                <Tip text="Название окна приложения и заголовок в верхней панели." />
              </div>
              <input
                type="text"
                className="text-input"
                style={{ width: '220px' }}
                value={appTitle}
                onChange={(e) => setAppTitle(e.target.value)}
                placeholder="Kirieshcka v2"
              />
            </div>

            <div className="settings-row">
              <div className="row-label">
                Имя ассистента
                <Tip text="Имя, которое отображается в окне, заголовках и интерфейсе." />
              </div>
              <input
                type="text"
                className="text-input"
                style={{ width: '220px' }}
                value={assistantName}
                onChange={(e) => setAssistantName(e.target.value)}
                placeholder="Kirieshcka"
              />
            </div>

            <div className="settings-row">
              <div className="row-label">
                Автозапуск с Windows
                <Tip text="Запуск фонового демона и UI при входе в систему (запись в реестр HKCU\\...\\Run)." />
              </div>
              <Toggle value={autostart} onChange={setAutostart} label="Автозапуск" />
            </div>
          </div>

          {/* Секция 2: Ollama & LLM */}
          <div className="settings-card">
            <div className="card-section-title">
              <Icon name="brain" />
              <span>Нейросеть (Ollama & Параметры генерации)</span>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Адрес сервера Ollama
                <Tip text="Локальный эндпоинт Ollama API (по умолчанию http://localhost:11434)." />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  className="text-input small"
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                />
                <button className="btn-secondary" onClick={handleRestartOllama} disabled={ollamaBusy}>
                  {ollamaBusy ? '...' : 'Проверить'}
                </button>
              </div>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Активная модель LLM
                <Tip text="Модель Ollama для генерации ответов и команд." />
              </div>
              <select
                className="select-input"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                {availableModels.length > 0 ? (
                  availableModels.map((m, i) => (
                    <option key={i} value={m}>
                      {m}
                    </option>
                  ))
                ) : (
                  <option value={model}>{model || 'qwen3:1.7b'}</option>
                )}
              </select>
            </div>

            {/* Slider 1: Температура */}
            <div className="settings-row">
              <div className="row-label">
                Температура: <strong style={{ color: 'var(--accent)' }}>{temperature}</strong>
                <Tip text="Степень вариативности ответов (0.2 - точно, 0.7 - стандарт, 1.2+ - свободнее)." />
              </div>
              <div className="slider-control-group" style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '240px' }}>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  style={{ '--v': `${(parseFloat(temperature) / 2) * 100}%` }}
                />
              </div>
            </div>

            {/* Slider 2: Контекст диалога */}
            <div className="settings-row">
              <div className="row-label">
                Контекст диалога: <strong style={{ color: 'var(--accent)' }}>{contextLength} токенов</strong>
                <Tip text="Размер контекстного окна модели (рекомендуется от 2048 до 65536)." />
              </div>
              <div className="slider-control-group" style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '280px' }}>
                <input
                  type="range"
                  min="2048"
                  max="65536"
                  step="1024"
                  value={contextLength}
                  onChange={(e) => setContextLength(parseInt(e.target.value, 10))}
                  style={{ '--v': `${((parseInt(contextLength, 10) - 2048) / (65536 - 2048)) * 100}%` }}
                />
                <input
                  type="number"
                  min="512"
                  max="131072"
                  step="512"
                  className="text-input number-input"
                  style={{ width: '90px' }}
                  value={contextLength}
                  onChange={(e) => setContextLength(e.target.value)}
                />
              </div>
            </div>

            {/* Slider 3: Максимум токенов */}
            <div className="settings-row">
              <div className="row-label">
                Максимум ответа: <strong style={{ color: 'var(--accent)' }}>{maxTokens} токенов</strong>
                <Tip text="Максимальное количество токенов генерации на один ответ." />
              </div>
              <div className="slider-control-group" style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '280px' }}>
                <input
                  type="range"
                  min="512"
                  max="8192"
                  step="256"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))}
                  style={{ '--v': `${((parseInt(maxTokens, 10) - 512) / (8192 - 512)) * 100}%` }}
                />
                <input
                  type="number"
                  min="128"
                  max="16384"
                  step="256"
                  className="text-input number-input"
                  style={{ width: '90px' }}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(e.target.value)}
                />
              </div>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Режим «Только роутер»
                <Tip text="Быстрое выполнение системных команд без обращения к нейросети (минимальное время отклика)." />
              </div>
              <Toggle value={routerOnlyMode} onChange={setRouterOnlyMode} label="Только роутер" />
            </div>
          </div>

          {/* Секция 3: Голос и STT (Whisper + Vosk) */}
          <div className="settings-card">
            <div className="card-section-title">
              <Icon name="mic" />
              <span>Распознавание речи (STT & Whisper)</span>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Устройство ввода (Микрофон)
                <Tip text="Микрофон в совместном режиме Windows WASAPI Shared (не мешает Discord и играм)." />
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  className="select-input"
                  value={selectedMic === null ? 'default' : selectedMic}
                  onChange={(e) => setSelectedMic(e.target.value === 'default' ? null : e.target.value)}
                >
                  <option value="default">Системный по умолчанию</option>
                  {microphones.map((m, i) => (
                    <option key={i} value={m.index}>
                      {m.name}
                    </option>
                  ))}
                </select>
                <button className="btn-secondary" onClick={handleTestMic} disabled={micTesting}>
                  {micTesting ? '...' : 'Тест'}
                </button>
              </div>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Голосовой триггер (Wake Word)
                <Tip text="Фоновое распознавание слова пробуждения через Vosk." />
              </div>
              <div className="inline-group">
                <input
                  type="text"
                  className="text-input wake-word-input"
                  value={wakeWordText}
                  onChange={(e) => setWakeWordText(e.target.value)}
                  placeholder="шпрота"
                  disabled={!wakeWordEnabled}
                />
                <Toggle value={wakeWordEnabled} onChange={setWakeWordEnabled} label="Вейкворд" />
              </div>
            </div>

            {/* Выбор и загрузка модели Whisper */}
            <div className="settings-row">
              <div className="row-label">
                Модель Whisper
                <Tip text="Модель faster-whisper. Small (~460 МБ) - быстрая, Medium (~1.4 ГБ) - высокая точность, Custom - локальная папка." />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <select
                    className="select-input"
                    value={whisperModel}
                    onChange={(e) => setWhisperModel(e.target.value)}
                  >
                    <option value="small">Small (Оптимальная, ~460 МБ)</option>
                    <option value="medium">Medium (Высокая точность, ~1.4 ГБ)</option>
                    <option value="large-v3">Large-v3 (Максимум, ~3 ГБ)</option>
                    <option value="custom">Пользовательская локальная папка...</option>
                  </select>

                  {whisperModel !== 'custom' && (
                    currentWhisperStatus === 'installed' ? (
                      <span className="status-tag ok" style={{ fontSize: '11px' }}>
                        Установлена [OK]
                      </span>
                    ) : (
                      <button
                        className="btn-accent small"
                        onClick={() => handleDownloadWhisper(whisperModel)}
                        disabled={whisperDownloading[whisperModel]}
                      >
                        {whisperDownloading[whisperModel] ? 'Скачивание...' : 'Скачать'}
                      </button>
                    )
                  )}
                </div>

                {whisperModel === 'custom' && (
                  <input
                    type="text"
                    placeholder="Путь к локальной папке модели (напр. models/faster-whisper-small)"
                    value={customWhisperPath}
                    onChange={(e) => setCustomWhisperPath(e.target.value)}
                    className="text-input small"
                    style={{ width: '320px' }}
                  />
                )}
              </div>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Потоки CPU для Whisper
                <Tip text="Число ядер процессора под распознавание (4-6 под Ryzen 5 3600)." />
              </div>
              <input
                type="number"
                min="1"
                max="12"
                className="text-input number-input"
                value={cpuThreads}
                onChange={(e) => setCpuThreads(e.target.value)}
              />
            </div>

            <div className="settings-row">
              <div className="row-label">
                Beam size: {beamSize}
                <Tip text="Ширина лучевого поиска при распознавании речи (1 - быстрее, 5 - точнее)." />
              </div>
              <input
                type="number"
                min="1"
                max="20"
                className="text-input number-input"
                value={beamSize}
                onChange={(e) => setBeamSize(e.target.value)}
              />
            </div>

            <div className="settings-row">
              <div className="row-label">
                Голосовой фильтр активности (VAD)
                <Tip text="Отсекает паузы и тишину, сокращая время распознавания речи." />
              </div>
              <Toggle value={vadFilter} onChange={setVadFilter} label="VAD фильтр" />
            </div>

            <div className="settings-row">
              <div className="row-label">
                Тишина до автоотправки: {silenceDuration}с
                <Tip text="Сколько секунд тишины после фразы ждать перед отправкой в нейросеть." />
              </div>
              <input
                type="number"
                min="0.5"
                max="10.0"
                step="0.1"
                className="text-input number-input"
                value={silenceDuration}
                onChange={(e) => setSilenceDuration(e.target.value)}
              />
            </div>
          </div>

          {/* Секция 4: Синтез речи (TTS) */}
          <div className="settings-card">
            <div className="card-section-title">
              <Icon name="vol" />
              <span>Озвучка ответов (TTS)</span>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Озвучивать ответы голосом
                <Tip text="Воспроизведение речи через локальные модели Piper." />
              </div>
              <Toggle value={ttsEnabled} onChange={setTtsEnabled} label="TTS" />
            </div>

            {ttsEnabled && (
              <>
                <div className="settings-row">
                  <div className="row-label">
                    Голос диктора
                    <Tip text="Локальный русскоязычный нейроголос Piper." />
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <select
                      className="select-input"
                      value={ttsVoice}
                      onChange={(e) => setTtsVoice(e.target.value)}
                    >
                      <option value="ru_RU-dmitri-medium">Дмитрий (medium)</option>
                      <option value="ru_RU-irina-medium">Ирина (medium)</option>
                      <option value="ru_RU-ruslan-medium">Руслан (medium)</option>
                    </select>

                    {currentTtsStatus === 'installed' ? (
                      <span className="status-tag ok" style={{ fontSize: '11px' }}>
                        Готов [OK]
                      </span>
                    ) : (
                      <button
                        className="btn-accent small"
                        onClick={() => handleDownloadTts(ttsVoice)}
                        disabled={ttsDownloading[ttsVoice]}
                      >
                        {ttsDownloading[ttsVoice] ? 'Скачивание...' : 'Скачать (~63 МБ)'}
                      </button>
                    )}

                    <button className="btn-secondary" onClick={handleTestTts}>
                      Проверить
                    </button>
                  </div>
                </div>

                <div className="settings-row">
                  <div className="row-label">
                    Скорость речи: {ttsSpeed}x
                  </div>
                  <div className="slider-control-group" style={{ minWidth: '220px' }}>
                    <input
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.05"
                      value={ttsSpeed}
                      onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
                      style={{ '--v': `${((ttsSpeed - 0.5) / (2.0 - 0.5)) * 100}%` }}
                    />
                  </div>
                </div>

                <div className="settings-row">
                  <div className="row-label">
                    Громкость речи: {Math.round(ttsVolume * 100)}%
                  </div>
                  <div className="slider-control-group" style={{ minWidth: '220px' }}>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={ttsVolume}
                      onChange={(e) => setTtsVolume(parseFloat(e.target.value))}
                      style={{ '--v': `${ttsVolume * 100}%` }}
                    />
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Секция 5: Безопасность */}
          <div className="settings-card">
            <div className="card-section-title">
              <Icon name="shield" />
              <span>Безопасность и Доступ</span>
            </div>

            <div className="settings-row">
              <div className="row-label">
                Разрешить запуск приложений вне Workspace
                <Tip text="Позволяет ассистенту запускать любые системные программы, а не только файлы из песочницы." />
              </div>
              <Toggle
                value={allowOutsideWorkspace}
                onChange={setAllowOutsideWorkspace}
                label="Доступ вне Workspace"
              />
            </div>
          </div>

          {/* Секция 6: Служебные настройки (РОФЛы и секретное слово) */}
          <div className="settings-card">
            <div className="card-section-title">
              <Icon name="sparkles" />
              <span>Служебные настройки (Юмор и пасхалки)</span>
            </div>

            {!roflUnlocked ? (
              <div className="settings-row">
                <div className="row-label">
                  Служебное слово
                  <Tip text="Введите секретное служебное слово для доступа к тонкой настройке юмора ассистента." />
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="password"
                    className="input-text"
                    placeholder="Служебное слово..."
                    value={roflSecret}
                    onChange={(e) => handleCheckRoflSecret(e.target.value)}
                    style={{ width: '180px' }}
                  />
                  <button
                    className="btn-secondary"
                    onClick={() => handleCheckRoflSecret(roflSecret)}
                  >
                    Ввод
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '10px' }}>
                <div className="settings-row">
                  <div className="row-label">
                    Шанс обычного рофла: <strong>{roflChance.toFixed(1)}%</strong>
                    <Tip text="Вероятность саркастичного или шутливого комментария при выполнении системных команд." />
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={roflChance}
                    onChange={(e) => setRoflChance(parseFloat(e.target.value))}
                    className="range-slider"
                    style={{ width: '180px' }}
                  />
                </div>

                <div className="settings-row">
                  <div className="row-label">
                    Шанс демонического рофла: <strong>{roflDemonChance.toFixed(1)}%</strong>
                    <Tip text="Вероятность особо дерзкого или мемного ответа." />
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={roflDemonChance}
                    onChange={(e) => setRoflDemonChance(parseFloat(e.target.value))}
                    className="range-slider"
                    style={{ width: '180px' }}
                  />
                </div>

                <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
                  <button className="btn-secondary" onClick={handleResetRofl}>
                    Сбросить до дефолта
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => setRoflUnlocked(false)}
                  >
                    Скрыть
                  </button>
                  <button
                    className="btn-primary"
                    onClick={handleSaveRofl}
                    disabled={roflSaving}
                  >
                    <Icon name="check" />
                    <span>Сохранить рофлы</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Секция 6: Выключение */}
          <div className="danger-zone-card">
            <div className="danger-content">
              <div>
                <h4 className="danger-title">Завершить работу приложения</h4>
                <p className="danger-desc">
                  Полная остановка фонового ядра, освобождение микрофона и закрытие окна.
                </p>
              </div>
              <button className="btn-danger" onClick={handleShutdown}>
                <Icon name="exit" />
                <span>Завершить работу</span>
              </button>
            </div>
          </div>
          {/* Sticky floating save footer */}
          <div className="settings-sticky-footer">
            <div className="sticky-footer-inner">
              <span className="sticky-footer-hint">
                {saving ? 'Сохранение изменений...' : 'Все параметры готовы к применению'}
              </span>
              <button className="primary-action-btn sticky-save-btn" onClick={handleSave} disabled={saving}>
                <Icon name="save" />
                <span>{saving ? 'Сохранение...' : 'Сохранить изменения'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
