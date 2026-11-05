import React from 'react';
import { Icon } from '../Icons';
import { Tip, Toggle } from './common';

export default function VoiceSettings({
  // STT
  microphones,
  selectedMic,
  setSelectedMic,
  handleTestMic,
  micTesting,
  wakeWordEnabled,
  setWakeWordEnabled,
  wakeWordText,
  setWakeWordText,
  whisperModel,
  setWhisperModel,
  customWhisperPath,
  setCustomWhisperPath,
  currentWhisperStatus,
  whisperDownloading,
  handleDownloadWhisper,
  handleTestRecognition,
  testRecognitionBusy,
  testRecognitionResult,
  cpuThreads,
  setCpuThreads,
  beamSize,
  setBeamSize,
  vadFilter,
  setVadFilter,
  silenceDuration,
  setSilenceDuration,
  // TTS
  ttsEnabled,
  setTtsEnabled,
  ttsVoice,
  setTtsVoice,
  currentTtsStatus,
  ttsDownloading,
  handleDownloadTts,
  handleTestTts,
  ttsSpeed,
  setTtsSpeed,
  ttsVolume,
  setTtsVolume,
}) {
  return (
    <>
      {/* Секция: Распознавание речи */}
      <div className="settings-card">
        <div className="card-section-title">
          <Icon name="mic" />
          <span>Распознавание речи</span>
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
            <Tip text="Фоновое распознавание ключевого слова для вызова ассистента." />
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
            <Toggle value={wakeWordEnabled} onChange={setWakeWordEnabled} label="Голосовой вызов" />
          </div>
        </div>

        {/* Выбор и загрузка модели распознавания */}
        <div className="settings-row">
          <div className="row-label">
            Модель распознавания речи
            <Tip text="Модель распознавания речи: Base (~145 МБ) - быстрая и лёгкая, Small (~460 МБ) - оптимальная, Medium (~1.4 ГБ) - высокая точность, Пользовательская - своя папка." />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <select
                className="select-input"
                value={whisperModel}
                onChange={(e) => setWhisperModel(e.target.value)}
              >
                <option value="base">Base (Лёгкая, ~145 МБ)</option>
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
                placeholder="Путь к локальной папке модели на диске..."
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
            Проверка распознавания речи
            <Tip text="Записывает короткий фрагмент речи с микрофона (~3.5 сек) и проверяет точность распознавания выбранной моделью. Текст никуда не отправляется и очищается при переключении вкладки." />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
            <button
              type="button"
              className="btn-secondary small"
              onClick={handleTestRecognition}
              disabled={testRecognitionBusy}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Icon name="mic" style={{ width: '13px', height: '13px' }} />
              {testRecognitionBusy ? 'Слушаю и распознаю...' : 'Проверить распознавание'}
            </button>
            {testRecognitionResult !== null && (
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  maxWidth: '380px',
                  fontSize: '12.5px',
                  lineHeight: '1.4',
                  color: testRecognitionResult ? 'var(--tx)' : 'var(--mut)',
                  wordBreak: 'break-word',
                }}
              >
                {testRecognitionResult ? (
                  <>
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Распознано: </span>
                    «{testRecognitionResult}»
                  </>
                ) : (
                  <span style={{ fontStyle: 'italic' }}>Речь не распознана (тишина или слишком тихо)</span>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="settings-row">
          <div className="row-label">
            Выделенные ядра процессора
            <Tip text="Число потоков процессора для обработки голоса (4-6 под Ryzen 5 3600)." />
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
            Точность распознавания: {beamSize}
            <Tip text="Глубина перебора вариантов слов при распознавании (1 - быстрее, 5 - точнее)." />
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
            Фильтрация тишины и пауз
            <Tip text="Отсекает паузы и фоновую тишину, сокращая время распознавания." />
          </div>
          <Toggle value={vadFilter} onChange={setVadFilter} label="Отсекать тишину" />
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

      {/* Секция: Озвучка ответов */}
      <div className="settings-card">
        <div className="card-section-title">
          <Icon name="vol" />
          <span>Озвучка ответов</span>
        </div>

        <div className="settings-row">
          <div className="row-label">
            Озвучивать ответы голосом
            <Tip text="Голосовое воспроизведение ответов ассистента." />
          </div>
          <Toggle value={ttsEnabled} onChange={setTtsEnabled} label="Озвучка" />
        </div>

        {ttsEnabled && (
          <>
            <div className="settings-row">
              <div className="row-label">
                Голос диктора
                <Tip text="Выбор голоса диктора для озвучивания ответов." />
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
                  Проверить голос
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
    </>
  );
}
