import React, { useState } from 'react';
import { Icon } from './Icons';

const INITIAL_HISTORY = [
  { id: 1, text: 'Открой браузер', icon: 'web', time: '2 минуты назад', status: 'Выполнено', duration: '0.3s' },
  { id: 2, text: 'Включи музыку', icon: 'music', time: '15 минут назад', status: 'Выполнено', duration: '0.5s' },
  { id: 3, text: 'Громкость на 70%', icon: 'vol', time: '1 час назад', status: 'Выполнено', duration: '0.2s' },
  { id: 4, text: 'Открой папку проектов', icon: 'folder', time: '3 часа назад', status: 'Выполнено', duration: '0.4s' },
  { id: 5, text: 'Поставь таймер на 10 минут', icon: 'bell', time: 'Вчера, 19:40', status: 'Выполнено', duration: '0.3s' },
  { id: 6, text: 'Переведи экран в ночной режим', icon: 'moon', time: 'Вчера, 23:15', status: 'Выполнено', duration: '0.4s' },
  { id: 7, text: 'Проверь загрузку процессора', icon: 'cpu', time: '2 дня назад', status: 'Выполнено', duration: '0.2s' },
];

export default function History() {
  const [history, setHistory] = useState(INITIAL_HISTORY);
  const [repeatedId, setRepeatedId] = useState(null);

  const handleRepeat = (item) => {
    setRepeatedId(item.id);
    setTimeout(() => {
      setRepeatedId(null);
    }, 1800);
  };

  const handleClear = () => {
    setHistory([]);
  };

  return (
    <div className="page standard-page">
      <div className="page-container">
        <header className="page-header">
          <div className="header-left">
            <h1 className="page-title">Журнал активности</h1>
            <p className="page-desc">История выполненных голосовых запросов и системных команд</p>
          </div>
          {history.length > 0 && (
            <button className="clear-btn" onClick={handleClear} title="Очистить список">
              <Icon name="refresh" />
              <span>Очистить журнал</span>
            </button>
          )}
        </header>

        <div className="history-stats">
          <div className="stat-pill">
            <span className="stat-val">{history.length}</span>
            <span className="stat-lbl">Всего событий</span>
          </div>
          <div className="stat-pill">
            <span className="stat-val">100%</span>
            <span className="stat-lbl">Успешность</span>
          </div>
          <div className="stat-pill">
            <span className="stat-val">~0.3s</span>
            <span className="stat-lbl">Средний отклик</span>
          </div>
        </div>

        {history.length === 0 ? (
          <div className="empty-state">
            <Icon name="hist" />
            <h3>История пуста</h3>
            <p>Выполненные команды и голосовые запросы появятся здесь</p>
          </div>
        ) : (
          <div className="list">
            {history.map((item, i) => (
              <div key={item.id} className="row" style={{ '--n': i }}>
                <div className="row-icon-box">
                  <Icon name={item.icon} />
                </div>
                <div className="row-content">
                  <span className="row-title">{item.text}</span>
                  <div className="row-meta">
                    <span className="row-badge-success">{item.status}</span>
                    <span className="row-duration">{item.duration}</span>
                  </div>
                </div>
                <div className="row-right">
                  <small className="row-time">{item.time}</small>
                  <button
                    className={`repeat-btn ${repeatedId === item.id ? 'active' : ''}`}
                    onClick={() => handleRepeat(item)}
                    title="Повторить команду"
                  >
                    {repeatedId === item.id ? <Icon name="check" /> : <Icon name="play" />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
