import { apiFetch } from '../services/api';
import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';

export default function Ollama() {
  const [loading, setLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState(null);

  // Model & Server states
  const [model, setModel] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [loadedModels, setLoadedModels] = useState([]);
  const [ollamaBusy, setOllamaBusy] = useState(false);
  const [ollamaOnline, setOllamaOnline] = useState(false);

  // Tools states
  const [tools, setTools] = useState([]);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [toolsSearch, setToolsSearch] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'enabled' | 'disabled'

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3500);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      await Promise.all([fetchModelsAndSettings(), fetchTools()]);
    } catch (err) {
      console.error('Error loading Ollama data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchModelsAndSettings = async () => {
    try {
      const [modelsRes, settingsRes] = await Promise.all([
        apiFetch('/api/models'),
        apiFetch('/api/settings'),
      ]);
      const modelsData = await modelsRes.json();
      const settingsData = await settingsRes.json();

      const modelsList = modelsData.ollama_models || [];
      const current = settingsData.settings?.model || modelsData.current_model || (modelsList[0] || 'qwen3:1.7b');

      setAvailableModels(modelsList);
      setModel(current);
      setLoadedModels(modelsData.loaded_models || []);
      setOllamaOnline(modelsList.length > 0 || (modelsData.loaded_models && modelsData.loaded_models.length > 0));
    } catch (err) {
      console.error('Failed to load Ollama models:', err);
      setOllamaOnline(false);
    }
  };

  const fetchTools = async () => {
    try {
      setToolsLoading(true);
      const res = await apiFetch('/api/tools');
      const data = await res.json();
      setTools(data.tools || []);
    } catch (err) {
      console.error('Failed to load tools:', err);
    } finally {
      setToolsLoading(false);
    }
  };

  const handleSelectModel = async (newModel) => {
    setModel(newModel);
    try {
      setOllamaBusy(true);
      const res = await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: newModel }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus(`Активная модель изменена на «${newModel}»`);
      } else {
        showStatus(data.error || 'Ошибка смены модели', true);
      }
    } catch (err) {
      showStatus('Ошибка сети при смене модели', true);
    } finally {
      setOllamaBusy(false);
    }
  };

  const handleUnloadModel = async () => {
    try {
      setOllamaBusy(true);
      showStatus('Выгрузка модели из памяти видеокарты (VRAM)...');
      const res = await apiFetch('/api/ollama/unload', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showStatus(data.message || 'Память видеокарты успешно освобождена!');
        await fetchModelsAndSettings();
      } else {
        showStatus(data.error || 'Не удалось выгрузить модель', true);
      }
    } catch (err) {
      showStatus('Ошибка при отправке запроса выгрузки', true);
    } finally {
      setOllamaBusy(false);
    }
  };

  const handleRestartOllama = async () => {
    try {
      setOllamaBusy(true);
      showStatus('Перезапуск службы Ollama...');
      const res = await apiFetch('/api/ollama/restart', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showStatus('Служба Ollama перезапущена');
        await fetchModelsAndSettings();
      } else {
        showStatus(data.error || 'Ошибка перезапуска службы Ollama', true);
      }
    } catch (err) {
      showStatus('Ошибка сети при перезапуске', true);
    } finally {
      setOllamaBusy(false);
    }
  };

  const handleToggleTool = async (toolName, currentEnabled) => {
    const nextState = !currentEnabled;
    try {
      setTools((prev) =>
        prev.map((t) => (t.name === toolName ? { ...t, enabled: nextState } : t))
      );
      const res = await apiFetch('/api/tools/permission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: toolName, enabled: nextState }),
      });
      const data = await res.json();
      if (!data.success) {
        setTools((prev) =>
          prev.map((t) => (t.name === toolName ? { ...t, enabled: currentEnabled } : t))
        );
        showStatus(`Ошибка изменения разрешения для ${toolName}`, true);
      } else {
        showStatus(`Инструмент «${toolName}» ${nextState ? 'включен' : 'отключен'}`);
      }
    } catch (err) {
      setTools((prev) =>
        prev.map((t) => (t.name === toolName ? { ...t, enabled: currentEnabled } : t))
      );
      showStatus('Сетевая ошибка при изменении разрешения', true);
    }
  };

  const filteredTools = tools.filter((t) => {
    if (filterMode === 'enabled' && !t.enabled) return false;
    if (filterMode === 'disabled' && t.enabled) return false;

    const q = toolsSearch.toLowerCase().trim();
    if (!q) return true;
    return (
      (t.name || '').toLowerCase().includes(q) ||
      (t.title || '').toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q)
    );
  });

  const isModelInMemory = loadedModels.length > 0 || loadedModels.includes(model);

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Нейромодуль и Инструменты</h1>
            <p className="page-desc">Управление локальной моделью Ollama и правами вызова системных инструментов</p>
          </div>
        </header>

        {statusMsg && (
          <div className={`status-banner ${statusMsg.isError ? 'error' : 'success'}`}>
            <Icon name={statusMsg.isError ? 'bell' : 'check'} />
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Compact Ollama Control Bar */}
        <div className="command-group-card ollama-service-card">
          <div className="command-group-header">
            <div className="group-title-row">
              <span className={`service-status-dot ${ollamaOnline ? 'online' : 'offline'}`} />
              <h3 className="command-group-title">Сервис Ollama</h3>
              <span className={`status-pill ${ollamaOnline ? 'success' : 'warning'}`}>
                {ollamaOnline ? 'Подключен' : 'Недоступен'}
              </span>
            </div>

            {isModelInMemory && (
              <span className="vram-badge">
                <Icon name="cpu" />
                <span>Загружена в VRAM: {loadedModels.join(', ') || model}</span>
              </span>
            )}
          </div>

          <div className="service-controls-row">
            <div className="model-select-group">
              <label className="field-label">Рабочая языковая модель:</label>
              <select
                className="select-field"
                value={model}
                onChange={(e) => handleSelectModel(e.target.value)}
                disabled={ollamaBusy}
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
                {!availableModels.includes(model) && model && (
                  <option value={model}>{model} (Текущая)</option>
                )}
              </select>
            </div>

            <div className="service-action-buttons">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleUnloadModel}
                disabled={ollamaBusy}
                title="Освободить видеопамять (VRAM)"
              >
                <Icon name="trash" />
                <span>Выгрузить модель</span>
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={handleRestartOllama}
                disabled={ollamaBusy}
                title="Перезапустить службу Ollama"
              >
                <Icon name="refresh" className={ollamaBusy ? 'spin-icon' : ''} />
                <span>Перезапуск</span>
              </button>
            </div>
          </div>
        </div>

        {/* Tools Section */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="toolbar-row" style={{ marginTop: '8px' }}>
            <div className="category-tabs">
              <button
                className={`tab-pill ${filterMode === 'all' ? 'active' : ''}`}
                onClick={() => setFilterMode('all')}
              >
                <span>Все инструменты</span>
                <span className="badge-count">{tools.length}</span>
              </button>
              <button
                className={`tab-pill ${filterMode === 'enabled' ? 'active' : ''}`}
                onClick={() => setFilterMode('enabled')}
              >
                <span>Включены</span>
                <span className="badge-count">{tools.filter((t) => t.enabled).length}</span>
              </button>
              <button
                className={`tab-pill ${filterMode === 'disabled' ? 'active' : ''}`}
                onClick={() => setFilterMode('disabled')}
              >
                <span>Отключены</span>
                <span className="badge-count">{tools.filter((t) => !t.enabled).length}</span>
              </button>
            </div>

            <div className="search-box">
              <input
                type="text"
                className="search-input"
                placeholder="Поиск инструмента..."
                value={toolsSearch}
                onChange={(e) => setToolsSearch(e.target.value)}
              />
            </div>
          </div>

          {toolsLoading ? (
            <div className="empty-state">
              <Icon name="refresh" className="spin-icon" />
              <p>Загрузка разрешений инструментов...</p>
            </div>
          ) : filteredTools.length === 0 ? (
            <div className="empty-state">
              <Icon name="cmd" />
              <p>Инструменты не найдены</p>
            </div>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '12px',
              }}
            >
              {filteredTools.map((tool) => (
                <div
                  key={tool.name}
                  className={`command-group-card tool-card ${tool.enabled ? 'tool-enabled' : ''}`}
                >
                  <div className="command-group-header">
                    <div className="group-title-row">
                      <Icon name="zap" />
                      <div>
                        <h3 className="command-group-title">{tool.title}</h3>
                        <span className="tool-code-id">{tool.name}</span>
                      </div>
                    </div>
                    <button
                      className={`tg ${tool.enabled ? 'on' : ''}`}
                      onClick={() => handleToggleTool(tool.name, tool.enabled)}
                      role="switch"
                      aria-checked={tool.enabled}
                      aria-label={`Переключить ${tool.title}`}
                    />
                  </div>

                  <p className="tool-description-text">{tool.description}</p>

                  {tool.requires_confirmation && (
                    <div className="tool-card-footer">
                      <span className="warning-chip">Требует подтверждения</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
