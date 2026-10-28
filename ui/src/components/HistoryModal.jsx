import { apiFetch } from '../services/api';
import React, { useState, useEffect } from 'react';
import { Icon } from './Icons';

export default function HistoryModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('benchmark'); // 'benchmark' | 'history'
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const res = await apiFetch('/api/statistics');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch statistics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  const llm = stats?.latest_llm;
  const whisper = stats?.latest_whisper;
  const telemetry = stats?.telemetry || {};
  const history = stats?.history || [];

  return (
    <div className="history-modal-overlay" onClick={onClose}>
      <div
        className="history-modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '680px', width: '92%' }}
      >
        <div className="modal-header">
          <div className="modal-title-row">
            <Icon name="hist" />
            <h2 className="modal-title">Статистика и Замеры (Бенчмарк)</h2>
          </div>
          <button className="btn-close-modal" onClick={onClose} title="Закрыть">
            ✕
          </button>
        </div>

        {/* Tab switch inside modal */}
        <div style={{ display: 'flex', gap: '8px', margin: '14px 0', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px' }}>
          <button
            className={`btn-subtab ${activeTab === 'benchmark' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('benchmark')}
            style={{ fontSize: '12px', padding: '6px 12px' }}
          >
            Текущие замеры
          </button>
          <button
            className={`btn-subtab ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('history')}
            style={{ fontSize: '12px', padding: '6px 12px' }}
          >
            Журнал генераций ({history.length})
          </button>
          <button
            className="btn-secondary"
            onClick={fetchStats}
            style={{ marginLeft: 'auto', fontSize: '12px', padding: '6px 10px' }}
            title="Обновить данные"
          >
            ↻
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
          {activeTab === 'benchmark' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* LLM Benchmarks Card */}
              <div className="command-group-card benchmark-stat-card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#38bdf8' }}>
                    <Icon name="brain" />
                    <span>Последняя генерация LLM</span>
                  </div>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                    {llm?.model ? `Модель: ${llm.model}` : 'Запросов ещё не было'}
                  </span>
                </div>

                {llm ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', fontSize: '12px' }}>
                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Скорость (TPS)</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#38bdf8' }}>
                        {llm.generation_speed_tps?.toFixed(1)} <span style={{ fontSize: '11px' }}>ток/с</span>
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Время первого токена (TTFT)</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                        {llm.ttft_s?.toFixed(3)} <span style={{ fontSize: '11px' }}>с</span>
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Время генерации</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                        {llm.generation_time_s?.toFixed(3)} <span style={{ fontSize: '11px' }}>с</span>
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Токены (Вход / Выход)</div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>
                        {llm.input_tokens} / {llm.output_tokens}
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Всего токенов</div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>
                        {llm.total_tokens}
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Общее время ответа</div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>
                        {llm.total_time_s?.toFixed(3)} с
                      </div>
                    </div>
                  </div>
                ) : (
                  <p style={{ fontSize: '12px', color: '#64748b' }}>
                    Сделайте запрос в чате или голосом, чтобы увидеть точные замеры скорости и токенов.
                  </p>
                )}
              </div>

              {/* Whisper STT Card */}
              <div className="command-group-card benchmark-stat-card stt-accent">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#34d399' }}>
                    <Icon name="mic" />
                    <span>Распознавание речи Whisper STT</span>
                  </div>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                    {whisper?.model ? `Модель: ${whisper.model}` : 'Голосовой ввод не выполнялся'}
                  </span>
                </div>

                {whisper ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', fontSize: '12px' }}>
                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Real-time factor (RTF)</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#34d399' }}>
                        {whisper.real_time_factor?.toFixed(3)}
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Время распознавания</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                        {whisper.transcription_time_s?.toFixed(3)} с
                      </div>
                    </div>

                    <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                      <div style={{ color: '#64748b', fontSize: '11px' }}>Длительность аудио</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#e2e8f0' }}>
                        {whisper.audio_duration_s?.toFixed(2)} с
                      </div>
                    </div>
                  </div>
                ) : (
                  <p style={{ fontSize: '12px', color: '#64748b' }}>
                    После распознавания голоса здесь появится время транскрипции и фактор RTF.
                  </p>
                )}
              </div>

              {/* Hardware Telemetry Card */}
              <div className="command-group-card benchmark-stat-card hw-accent">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, marginBottom: '10px' }}>
                  <Icon name="cpu" />
                  <span>Нагрузка на железо</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: '#64748b', fontSize: '11px' }}>Загрузка CPU</div>
                    <div style={{ fontSize: '15px', fontWeight: 700 }}>
                      {telemetry.cpu_percent !== undefined ? `${telemetry.cpu_percent}%` : '—'}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: '#64748b', fontSize: '11px' }}>Оперативная память</div>
                    <div style={{ fontSize: '15px', fontWeight: 700 }}>
                      {telemetry.ram_percent !== undefined ? `${telemetry.ram_percent}%` : '—'}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.25)', padding: '8px', borderRadius: '6px' }}>
                    <div style={{ color: '#64748b', fontSize: '11px' }}>Видеокарта (GPU)</div>
                    <div style={{ fontSize: '15px', fontWeight: 700 }}>
                      {telemetry.gpu_percent !== undefined ? `${telemetry.gpu_percent}%` : '—'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="history-modal-list">
              {history.length === 0 ? (
                <div className="empty-state">
                  <Icon name="hist" />
                  <p>Журнал генераций пуст</p>
                </div>
              ) : (
                history.map((item, idx) => (
                  <div key={idx} className="command-group-card history-row-card">
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>
                        Модель: {item.model || 'Не указана'}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                        Токенов: {item.total_tokens} • Время: {item.total_time_s} с
                      </div>
                    </div>

                    <span
                      className="status-tag ok"
                      style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8' }}
                    >
                      {item.generation_speed_tps} ток/с
                    </span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
