export const INITIAL_PROTOCOLS = [
  {
    id: 'morning',
    name: 'Утренний запуск',
    tag: 'WORKFLOW',
    accent: '#38bdf8',
    durationMs: 2400,
    steps: [
      { id: 's1', label: 'Проверка сети и шлюза', detail: 'Ping 12ms · DNS OK' },
      { id: 's2', label: 'Запуск рабочего окружения', detail: 'VS Code + Terminal' },
      { id: 's3', label: 'Голосовой брифинг', detail: 'Piper TTS · Dmitri' },
    ],
  },
  {
    id: 'focus',
    name: 'Режим фокуса',
    tag: 'DEEP WORK',
    accent: '#a78bfa',
    durationMs: 1800,
    steps: [
      { id: 's1', label: 'Приглушение уведомлений', detail: 'DND Active' },
      { id: 's2', label: 'Системная громкость 35%', detail: 'Master Audio' },
      { id: 's3', label: 'Таймер Помодоро 50м', detail: 'Timer Armed' },
    ],
  },
  {
    id: 'gaming',
    name: 'Игровой профиль',
    tag: 'PERFORMANCE',
    accent: '#34d399',
    durationMs: 2100,
    steps: [
      { id: 's1', label: 'Закрытие фоновых утилит', detail: 'Освобождено 1.4 ГБ RAM' },
      { id: 's2', label: 'Профиль питания High', detail: 'Ryzen Boost Ready' },
      { id: 's3', label: 'Discord + Overlay', detail: 'Окно выведено' },
    ],
  },
  {
    id: 'night',
    name: 'Ночной отбой',
    tag: 'SYSTEM',
    accent: '#fb7185',
    durationMs: 2000,
    steps: [
      { id: 's1', label: 'Сохранение сессии', detail: 'Workspace Snapshot' },
      { id: 's2', label: 'Громкость 15%', detail: 'Night Audio' },
      { id: 's3', label: 'Таймер сна 30 мин', detail: 'Shutdown Scheduled' },
    ],
  },
];

export const INITIAL_COMMANDS = [
  {
    id: 'cmd-1',
    title: 'Открыть браузер и вкладки',
    phrase: 'открой рабочий браузер',
    category: 'apps',
    categoryLabel: 'Приложения',
    latency: '18 ms',
    description: 'Динамический поиск исполняемого файла через AppIndexer и запуск профиля.',
  },
  {
    id: 'cmd-2',
    title: 'Громкость на максимум / тише',
    phrase: 'сделай потише на 20',
    category: 'system',
    categoryLabel: 'Система',
    latency: '6 ms',
    description: 'Управление системной мастер-громкостью без сторонних драйверов.',
  },
  {
    id: 'cmd-3',
    title: 'Таймер и напоминание',
    phrase: 'поставь таймер на 15 минут',
    category: 'macro',
    categoryLabel: 'Макросы',
    latency: '4 ms',
    description: 'Детерминированный планировщик с голосовым оповещением через Piper.',
  },
  {
    id: 'cmd-4',
    title: 'Быстрый скриншот области',
    phrase: 'сделай скриншот',
    category: 'system',
    categoryLabel: 'Система',
    latency: '24 ms',
    description: 'Захват экрана и копирование в буфер обмена Windows.',
  },
  {
    id: 'cmd-5',
    title: 'Переключить окно на IDE',
    phrase: 'фокус на код',
    category: 'apps',
    categoryLabel: 'Приложения',
    latency: '11 ms',
    description: 'Поиск хэндла окна через WinAPI и вывод на передний план.',
  },
  {
    id: 'cmd-6',
    title: 'Статус локальной LLM',
    phrase: 'проверь олламу',
    category: 'ai',
    categoryLabel: 'Опц. Чат',
    latency: '42 ms',
    description: 'Пинг локального сервера Ollama для изолированного режима болталки.',
  },
];

export const INITIAL_EVENTS = [
  { id: 'e1', time: '23:21:04', source: 'ROUTER', text: 'Zero-LLM роутер активен · 48 паттернов в памяти', tone: 'info' },
  { id: 'e2', time: '23:21:19', source: 'VOICE', text: 'Wake-word движок откалиброван (порог 0.72)', tone: 'success' },
  { id: 'e3', time: '23:22:02', source: 'SANDBOX', text: 'Режим изоляции UI: бэкенд не требуется', tone: 'accent' },
];

export const INITIAL_CHAT = [
  {
    id: 'm1',
    role: 'assistant',
    text: 'Motion Studio активен в автономном песочном режиме. Жми что угодно — всё анимировано и откликается локально без дёрганья ядра.',
    time: '23:20',
  },
];

export const DEMO_REPLIES = [
  'Команда перехвачена Zero-LLM роутером за 4 мс. В боевом режиме сейчас сработал бы WinAPI-хэндлер.',
  'Принято. Анимация отработала, событие записано в локальный поток телеметрии.',
  'Пружина сработала мягко. Если переключишься на вкладку «Цепочки», можно прогнать пошаговый импульс.',
  'Системная мастер-громкость скорректирована в симуляторе. Всё чётко, без лишних костылей.',
];
