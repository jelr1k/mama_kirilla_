import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';

export default function Ollama() {
  const [loading, setLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState(null);

  // Ollama states
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [model, setModel] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [temperature, setTemperature] = useState(0.7);
  const [contextLength, setContextLength] = useState(32768);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [routerOnlyMode, setRouterOnlyMode] = useState(false);
  const [ollamaBusy, setOllamaBusy] = useState(false);

  // Tools states
  const [tools, setTools] = useState([]);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [toolsSearch, setToolsSearch] = useState('');

  const showStatus = (text, isError = false) => {
    setStatusMsg({ text, isError });
    setTimeout(() => setStatusMsg(null), 3500);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    await Promise.all([fetchSettings(), fetchModels(), fetchTools()]);
    setLoading(false);
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();
      const cfg = data.settings || {};
      setModel(cfg.model || '');
      setTemperature(cfg.temperature !== undefined ? cfg.temperature : 0.7);
      setContextLength(cfg.context_length || 32768);
      setMaxTokens(cfg.max_tokens || 4096);
      setRouterOnlyMode(Boolean(cfg.router_only_mode));
      const ollama = cfg.ollama || {};
      setOllamaUrl(ollama.base_url || 'http://localhost:11434');
    } catch (err) {
      console.error(err);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch('/api/models');
      const data = await res.json();
      setAvailableModels(data.ollama_models || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchTools = async () => {
    try {
      setToolsLoading(true);
      const res = await fetch('/api/tools');
      const data = await res.json();
      setTools(data.tools || []);
    } catch (err) {
      console.error(err);
    } finally {
      setToolsLoading(false);
    }
  };

  const handleSaveOllama = async () => {
    try {
      setOllamaBusy(true);
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          temperature: parseFloat(temperature),
          context_length: parseInt(contextLength, 10),
          max_tokens: parseInt(maxTokens, 10),
          router_only_mode: routerOnlyMode,
          ollama: { base_url: ollamaUrl },
        }),
      });
      const data = await res.json();
      if (data.success) {
        showStatus('Параметры Ollama успешно сохранены!');
      } else {
        showStatus('Ошибка сохранения настроек Ollama', true);
      }
    } catch (err) {
      showStatus('Ошибка сети при сохранении', true);
    } finally {
      setOllamaBusy(false);
    }
  };

  const handleRestartOllama = async () => {
    try {
      setOllamaBusy(true);
      showStatus('Перезапуск сервиса Ollama...');
      const res = await fetch('/api/ollama/restart', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showStatus('Сервис Ollama успешно перезапущен');
        await fetchModels();
      } else {
        showStatus(data.error || 'Не удалось перезапустить Ollama', true);
      }
    } catch (err) {
      showStatus('Ошибка при попытке перезапуска Ollama', true);
    } finally {
      setOllamaBusy(false);
    }
  };

  const handleToggleTool = async (toolName, currentEnabled) => {
    const nextState = !currentEnabled;
    try {
      // Optimistic update
      setTools((prev) =>
        prev.map((t) => (t.name === toolName ? { ...t, enabled: nextState } : t))
      );
      const res = await fetch('/api/tools/permission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: toolName, enabled: nextState }),
      });
      const data = await res.json();
      if (!data.success) {
        // Rollback
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
    const q = toolsSearch.toLowerCase();
    return (
      (t.name || '').toLowerCase().includes(q) ||
      (t.title || '').toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Нейросеть Ollama и Инструменты</h1>
            <p className="page-desc">
              Управление локальной языковой моделью и разрешениями на запуск системных тулов
            </p>
          </div>
        </header>

        {statusMsg && (
          <div
            className={`status-banner ${statusMsg.isError ? 'err' : 'ok'}`}
            style={{ marginBottom: '16px' }}
          >
            {statusMsg.text}
          </div>
        )}

        {/* Ollama Section */}
        <div className="settings-section" style={{ marginBottom: '24px' }}>
          <div className="section-header">
            <Icon name="brain" />
            <h2 className="section-title">Сервис Ollama и Модель</h2>
          </div>

          <div className="settings-grid">
            <div className="setting-card">
              <label className="setting-label">URL сервера Ollama</label>
              <input
                type="text"
                className="input-text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://localhost:11434"
              />
              <span className="setting-hint">Локальный адрес REST API запущенной службы Ollama</span>
            </div>

            <div className="setting-card">
              <label className="setting-label">Активная модель</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  className="select-field"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  style={{ flex: 1 }}
                >
                  <option value="">Не выбрана (по умолчанию)</option>
                  {availableModels.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={fetchModels}
                  title="Обновить список моделей из Ollama"
                >
                  ↻
                </button>
              </div>
              <span className="setting-hint">
                Доступно моделей: {availableModels.length}. Новые модели скачиваются в консоли командой ollama pull
              </span>
            </div>

            <div className="setting-card">
              <label className="setting-label">
                Температура генерации: <strong>{temperature}</strong>
              </label>
              <input
                type="range"
                min="0.0"
                max="1.5"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                className="range-slider"
              />
              <span className="setting-hint">0.0 — точные команды, 0.7 — естественный диалог</span>
            </div>

            <div className="setting-card">
              <label className="setting-label">Длина контекста (контекстное окно)</label>
              <input
                type="number"
                className="input-text"
                value={contextLength}
                onChange={(e) => setContextLength(e.target.value)}
                step="1024"
              />
              <span className="setting-hint">Объём памяти истории диалога в токенах (обычно 8192 — 32768)</span>
            </div>

            <div className="setting-card">
              <label className="setting-label">Максимум выходных токенов</label>
              <input
                type="number"
                className="input-text"
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
                step="512"
              />
              <span className="setting-hint">Ограничение длины одного ответа нейросети</span>
            </div>

            <div className="setting-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>Режим «Только роутер»</div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>
                    Использовать только быстрый сопоставитель команд без запуска генерации диалога
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={routerOnlyMode}
                  onChange={(e) => setRouterOnlyMode(e.target.checked)}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', marginTop: '16px' }}>
            <button
              className="btn-primary"
              onClick={handleSaveOllama}
              disabled={ollamaBusy}
            >
              <Icon name="check" />
              <span>Сохранить параметры Ollama</span>
            </button>
            <button
              className="btn-secondary"
              onClick={handleRestartOllama}
              disabled={ollamaBusy}
              title="Перезапустить процесс Ollama на ПК"
            >
              Перезапустить Ollama
            </button>
          </div>
        </div>

        {/* Tools Execution Section */}
        <div className="settings-section">
          <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="cmd" />
              <h2 className="section-title">Разрешения инструментов (Tools Execution)</h2>
            </div>
            <div className="search-box" style={{ width: '260px' }}>
              <input
                type="text"
                className="search-input"
                placeholder="Поиск инструмента..."
                value={toolsSearch}
                onChange={(e) => setToolsSearch(e.target.value)}
                style={{ fontSize: '12px', padding: '6px 10px' }}
              />
            </div>
          </div>

          <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '16px' }}>
            Отключённый инструмент блокируется при попытке вызова нейросетью. Все файловые операции
            строго ограничены рабочей директорией workspace.
          </p>

          {toolsLoading ? (
            <div className="empty-state">
              <p>Загрузка инструментов...</p>
            </div>
          ) : (
            <div
              className="tools-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '12px',
              }}
            >
              {filteredTools.map((tool) => (
                <div
                  key={tool.name}
                  className="setting-card"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    border: tool.enabled ? '1px solid rgba(14, 165, 233, 0.25)' : '1px solid rgba(255,255,255,0.06)',
                    background: tool.enabled ? 'rgba(14, 165, 233, 0.04)' : 'rgba(255,255,255,0.02)',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <strong style={{ fontSize: '13px', color: tool.enabled ? '#38bdf8' : '#94a3b8' }}>
                        {tool.title}
                      </strong>
                      <input
                        type="checkbox"
                        checked={tool.enabled}
                        onChange={() => handleToggleTool(tool.name, tool.enabled)}
                        style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                      />
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace', marginBottom: '6px' }}>
                      {tool.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#94a3b8', lineHeight: 1.4 }}>
                      {tool.description}
                    </div>
                  </div>

                  {tool.requires_confirmation && (
                    <div style={{ marginTop: '8px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          color: '#f59e0b',
                          background: 'rgba(245, 158, 11, 0.1)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                        }}
                      >
                        Требует подтверждения
                      </span>
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
