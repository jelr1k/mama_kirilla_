import React from 'react';
import { Icon } from '../Icons';
import { Tip, Toggle } from './common';

export default function NeuralSettings({
  ollamaUrl,
  setOllamaUrl,
  handleRestartOllama,
  ollamaBusy,
  model,
  setModel,
  availableModels,
  autoloadModel,
  setAutoloadModel,
  temperature,
  setTemperature,
  contextLength,
  setContextLength,
  maxTokens,
  setMaxTokens,
  routerOnlyMode,
  setRouterOnlyMode,
}) {
  return (
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

      <div className="settings-row">
        <div className="row-label">
          Автозапуск модели при старте
          <Tip text="Если включено, рабочая модель автоматически загружается в память в фоне при запуске приложения. По умолчанию выключено — модель не грузится до первого запроса." />
        </div>
        <Toggle
          value={autoloadModel}
          onChange={setAutoloadModel}
          label="Автозапуск модели при старте"
        />
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
  );
}
