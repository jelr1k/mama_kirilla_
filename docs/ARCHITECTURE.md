# Архитектура JARVIS (Kirieshka v2)

Документ описывает структуру проекта, ключевые архитектурные решения, поток данных и взаимодействие подсистем.

---

## 1. Общий поток данных (Data Flow)

JARVIS обрабатывает текстовые и голосовые запросы через единый конвейер с приоритетом прямого выполнения однозначных команд:

```mermaid
flowchart TD
    User["Пользователь (React UI / Микрофон STT)"] --> Normalizer["Нормализация команд (voice.command_normalizer)"]
    Normalizer --> Router["Command Router (services/command_router.py)"]
    
    Router -->|Однозначная команда / Алиас| Direct["Прямой инструмент (tools/) без LLM"]
    Router -->|Сложный / Разговорный запрос| LLM["Ollama Manager (Локальная LLM)"]
    
    Direct --> FastResult["Мгновенный результат / подтверждение"]
    FastResult --> EventBus["Шина событий EventBus"]
    
    LLM -->|Tool Calling (до 5 раундов)| ToolExec["ToolExecutor (контроль прав и песочницы)"]
    ToolExec -->|Результат инструмента| LLM
    LLM -->|Итоговый ответ / стриминг токенов| EventBus
    
    EventBus --> Gateway["GatewayService (FastAPI / WebSocket :8765)"]
    Gateway --> UI["Tauri v2 + React Frontend (ui/src/)"]
    EventBus --> TTS["Озвучка Piper TTS (если включена)"]
```

### Главный принцип
`CommandRouter` обязан отсекать типовые детерминированные действия (запуск и закрытие приложений, громкость, плеер, скриншоты, папки, телеметрию, файлы в Workspace) и исполнять их напрямую без обращения к LLM. Нейросеть привлекается только для свободного диалога, неоднозначных формулировок и многосоставных задач.

---

## 2. Основные подсистемы

### 2.1. Сетевой шлюз (Gateway) и архитектура Presentation
Python-ядро работает автономно (в headless-режиме) и взаимодействует с UI через модульный шлюз `GatewayService` (`services/gateway_service.py`):
* **Модульная структура шлюза (`services/gateway/`):**
  - `deps.py`: зависимости FastAPI, валидация запросов, сессионная аутентификация (`Bearer <token>` и `X-Session-Token`). Токен генерируется при старте ядра и пишется в `%LOCALAPPDATA%\Jarvis\session.token`.
  - `hub.py`: WebSocket-хаб рассылки событий клиентам интерфейса с проверкой токена (`/ws?token=...`).
  - `routers/`: декомпозированные роутеры FastAPI по доменам (`chat.py`, `integrations.py`, `settings.py`, `system.py`, `voice.py`).
* **FastAPI HTTP REST:**
  - Настройки и система: `/health`, `/api/settings`, `/api/autostart`, `/api/status`, `/api/telemetry`, `/api/statistics`, `/api/media/status`, `/api/media/control`, `/api/system/quick-action`, `/api/shutdown`.
  - Чат и команды: `/api/commands`, `/api/chat`, `/api/commands/execute`.
  - Модели и Ollama: `/api/models`, `/api/ollama/restart`, `/api/ollama/unload`.
  - Голос и звук: `/api/microphones`, `/api/microphones/test`, `/api/voice/test_recognition`, `/api/whisper/status`, `/api/whisper/download`, `/api/tts/status`, `/api/tts/download`, `/api/tts/test`.
  - Автоматизация и интеграции: `/api/protocols/*`, `/api/steam/*`, `/api/websites/*`, `/api/vpn/*`, `/api/network/*`, `/api/telegram/*`, `/api/aliases`, `/api/workspace/*`, `/api/tools/*`, `/api/rofl/*`, `/api/apps/*`.
  - Обновления: `/api/updates`, `/api/updates/check`, `/api/updates/apply`.
* **WebSocket (`/ws`):** полнодуплексный канал связи (`assistantSocket.js`), передающий в React UI:
  - чанки ответов LLM в реальном времени;
  - бегущую строку промежуточного распознавания Vosk;
  - статусы ядра (`idle`, `listen`, `think`, `speak`);
  - телеметрию ПК (опрос раз в 2.5 сек).
* **Фоновый жизненный цикл и трей:**
  - Нативный системный трей Windows реализован в Tauri v2 на Rust (`ui/src-tauri/src/lib.rs`), там же поддерживается отдельное окно плавающего виджета **Dynamic Island** (`island`) с управлением видимостью и click-through. При выходе из трея Tauri отправляет защищённый запрос `POST /api/shutdown` на шлюз с сессионным токеном, корректно останавливая фоновый бэкенд.
  - Headless-бэкенд `start/main.py` полностью отвязан от PySide6/Qt и работает на чистом цикле `asyncio / threading`. Аварийный режим PySide6 запускается только через явный ключ `--legacy-gui` или `--pyside`.
  - При закрытии окна интерфейса крестиком окно скрывается в трей, а ядро продолжает работать и принимать события.
  - Полное завершение работы подтверждается через диалоговое окно (`ConfirmModal.jsx`), меню системного трея или голосовую команду `закрой себя`.
  - Python-контроллер трея (`presentation/tray_icon.py`) сохранен как fallback при наличии PySide6 в окружении.
* **Слой совместимости:** контроллеры старого интерфейса PySide6 перенесены в `presentation/legacy/` и сохранены только для поддержки аварийного интерфейса `ui_archive/`. В коде действует прозрачный мета-путь импорта `presentation.*` с выдачей `DeprecationWarning`.

### 2.2. Command Router, Steam и Протоколы Старка
* **Модульный Command Router (`services/command_router.py` и `services/router/`):**
  - Фасад `CommandRouter` делегирует обработку команд специализированным диспетчерам:
    - `app_dispatcher.py` - запуск, закрытие и проверка запущенных приложений;
    - `media_dispatcher.py` - системная громкость, выключение звука, управление плеером;
    - `protocols_dispatcher.py` - сценарии протоколов Старка;
    - `site_dispatcher.py` - переход по сайтам и веб-алиасам;
    - `system_dispatcher.py` - телеметрия, скриншоты, папки Windows, дата/время, блокировка, очистка корзины и чата.
  - `services/command_catalog.py`: централизованные списки триггеров и шаблонов сопоставления.
* **Индексатор приложений Windows (`core/app_indexer.py`):**
  - Автоматическое сканирование ярлыков меню «Пуск» и реестра Windows `App Paths`.
  - Формирование голосовых и текстовых алиасов на лету.
  - Подмешивание найденных названий софта в контекстный промпт Whisper (`voice/prompt_builder.py`).
* **Интеграция со Steam (`core/steam_manager.py`):** парсинг манифестов установленных игр и запуск через безопасный системный протокол `steam://rungameid/<appid>`.
* **Протоколы автоматизации (`services/stark_protocols.py`, `core/protocols_manager.py`):** цепочки команд (утренний брифинг, кино, защита, игры, очистка) с поддержкой персонализированных профилей.
* **Каталог веб-ресурсов (`core/website_manager.py`):** умные алиасы со стеммингом и транслитерацией для мгновенного перехода на сайты.
* **Сеть и обход блокировок (`core/vpn_manager.py`, пакет `core/vpn/`):**
  - `core/vpn/discovery.py` - поиск VPN-клиентов (Happ, FlClashX) и `service.bat` от Запрета без жестких путей (реестр, меню «Пуск», процессы, типовые каталоги).
  - `core/vpn/uia_driver.py` - автоматизация нажатия кнопок подключения FlClashX через UI Automation.
  - `core/vpn/zapret_controller.py` - управление жизненным циклом службы и процесса Запрета (winws).
  - `core/vpn/manager.py` - координатор статусов и переключений режимов.
* **Безопасность и подтверждения:** критические операции (закрытие приложений `close_application`, удаление/перезапись файлов) требуют подтверждения пользователя (`requires_confirmation=True`).
* **Tool Calling:** `GenerationWorker` поддерживает до 5 раундов последовательного вызова инструментов нейросетью.

### 2.3. Голосовая подсистема (Voice)
* **STT (Распознавание речи):** `faster-whisper` (модель `small` на CPU, `int8`, язык `ru`). Ленивая загрузка при первом запросе. Текст проходит нормализацию через `voice.command_normalizer` (знаки препинания, расширения «точка txt»).
* **Wake Word:** фоновый детектор ключевой фразы на `vosk`. Временно блокируется во время воспроизведения речи, чтобы предотвратить самосрабатывание от динамиков.
* **TTS (Синтез речи):** модульный движок `Piper TTS` (ONNX на CPU) в изолированном потоке `jarvis-tts-worker`.
  * Шина `speech.requested` принимает реплики чата и рофлы.
  * `AudioAssetManager` поддерживает подготовленные WAV-записи и LRU-кэш на 256 МБ.
  * Каталог профилей голосов хранится в `%APPDATA%/Jarvis/tts/voice_profiles.json`, аудио-кэш - в `%APPDATA%/Jarvis/tts/assets/`, а файлы весов моделей Piper (ONNX) скачиваются в `%LOCALAPPDATA%/Jarvis/models/tts/voices/` (с поддержкой legacy-каталога при наличии).

### 2.4. Workspace и файловая безопасность
* **Песочница:** `security/sandbox.py` строго ограничивает файловые операции границами папки `workspace/`. Выход за пределы каталога блокируется.
* **WorkspaceIndex:** живой индекс фактического содержимого рабочего каталога (`core/workspace_index.py`).
* **TargetResolver:** единый резолвер путей (`tools.paths.resolve_workspace_path`) с нормализацией регистра, поддержкой автоматических и пользовательских алиасов со стеммингом (`core/alias_manager.py`) и контролируемым нечётким поиском (порог `0.78` в `tools/paths.py`; базовый порог `0.72` в `alias_manager.py` и `workspace_index.py`).

### 2.5. Телеметрия и медиа-контроль
* **Системный звук и плеер (`tools/media_control.py`):** прямое управление громкостью, переключение Mute/Unmute через Windows CoreAudio API (`pycaw`) и отправка виртуальных мультимедиа-кодов Windows для плеера (пауза, плей, треки).
* **Телеметрия железа (`tools/system_info.py`):** мониторинг CPU (общий и по ядрам), RAM, дисков, GPU (с автоматическим фоллбэком NVIDIA NVML → AMD → WMI → DXGI) и времени аптайма системы.

### 2.6. Пользовательский интерфейс (Tauri v2 + React)
* **Фронтенд-стек:** React 19, Vite 7, Tauri 2 (`ui/src/`).
* **Оформление:** темная тема с акцентами neon cyan, emerald green и purple violet, CSS Custom Properties (`src/index.css`).
* **Модульная структура настроек (`ui/src/components/settings/`):**
  - Экран `Settings.jsx` декомпозирован на независимые тематические секции: `GeneralSettings`, `VoiceSettings`, `NeuralSettings`, `RoflSettings`, `SecuritySettings`, `TelegramSettings`, `DangerZone`, `UpdatesBanner` и вспомогательные компоненты `common.jsx`.
* **Визуальные компоненты и анимации:**
  - Hero Orb (`Home.jsx`): морфинг формы (`@keyframes morph`), дыхание (`breathe`), вращение при размышлении (`spin`) и интерполяция цвета через `@property --c`.
  - Звуковая волна: 36 динамических полос с анимацией амплитуды.
  - Кастомный TitleBar: перетаскивание окна, кнопки управления окном, переключатель режима **Dynamic Island** (`IslandApp.jsx`) и компактного HUD-виджета (390x620).
  - Выдвижная шторка HistoryModal: вкладка бенчмарка реального времени и история вызовов.
  - Подвкладка «Программы ПК» в Aliases (`AppsSubtab.jsx`): поиск, запуск и добавление алиасов установленных в Windows программ.
  - Скользящий индикатор активной вкладки сайдбара (`.ind` с `translateY`).
  - Индикация телеметрии CPU и RAM с динамическим обновлением по WebSocket.

### 2.7. Шуточный сервис (RoflService)
* `services/rofl_service.py` добавляет вероятностные реплики на успешные действия ассистента.
* Цитаты и списки фраз вынесены в модуль `services/rofl_phrases.py`.
* Поддерживает два уровня реплик: стандартные и «демонические» (вероятности настраиваются через API `/api/rofl`).
* Содержит тематические фразы на команды мультимедиа (`media_volume_up`, `media_volume_down`, `media_sound_off`, `media_sound_on`, `media_play_pause`, `media_stop`), телеметрию и запуск приложений.
* Все реплики транслируются в шину `speech.requested` и озвучиваются тем же локальным голосом Piper TTS.

### 2.8. Модули расширения (modules/)
* **Telegram-бот удалённого управления (`modules/telegram_bot.py`, пакет `modules/telegram/`):**
  - Модульная архитектура: `service.py` (жизненный цикл и поллинг), `client.py` (HTTP-клиент и реверс-прокси), `handlers.py` (команды и роутер), `keyboards.py` (инлайн-кнопки).
  - Работает в выделенном фоновом потоке со своим `asyncio` event loop.
  - Сессионная изоляция (`session_id`) и сброс накопившихся апдейтов (`drop_pending_updates=True`) предотвращают конфликты 409 и повторное исполнение команд после простоя.
  - Поддерживает переопределение `api_base_url` на пользовательский Cloudflare Worker, позволяя боту работать в РФ без VPN при блокировке IP-подсетей Telegram.
  - Доступ строго ограничен белым списком `allowed_chat_ids`.
  - Приём обычного текста маршрутизируется в `Command Router` ассистента.
* **Монитор доступности сервисов и DPI (`modules/network_checker.py`):**
  - Асинхронное тестирование доступности ключевых игровых и системных шлюзов (Discord Gateway, YouTube, Steam Store, Telegram API, GitHub).
  - Разделение статусов: норма (ok), деградация (slow) и блокировка/таймаут (blocked).
  - Встроенное TTL-кэширование (15 секунд) для мгновенного отклика UI.
* **Эндпоинты Gateway:** `/api/network/services`, `/api/telegram/status`, `/api/telegram/test`, `/api/telegram/restart`.

---

## 3. Логирование (`logs/`)

Логи ведутся строго под текущую сессию и изолированы по файлам:
* `logs/jarvis.log` - жизненный цикл приложения, инициализация и системные события.
* `logs/errors.log` - агрегированный журнал всех ошибок уровня `ERROR` и выше.
* `logs/commands.log` - маршрутизация Command Router, вызовы инструментов и подтверждения.
* `logs/voice.log` - аудиопоток, микрофон, Vosk и Whisper.
* `logs/tts.log` - синтез речи Piper TTS.
* `logs/ollama.log` - состояние сервера Ollama, загрузка/выгрузка моделей, токены и промпты.
* `logs/dependencies.log` - проверка и установка зависимостей.
* `logs/update.log` - сервисы автообновления и проверки релизов.
* `logs/events.log` - структурированный журнал шины событий EventBus в формате JSON.
* `logs/startup.log` / `logs/fatal.log` - ранний запуск и дампы `faulthandler`.

При каждом новом старте приложения через `start/bootstrap.py` устаревшие логи очищаются, создавая чистую диагностическую среду.

---

## 4. Портативность и пути

* В кодовой базе запрещены абсолютные хардкод-пути (`C:\...`).
* Все внутренние пути разрешаются через модуль `core/app_paths.py` относительно расположения приложения:
  - Пользовательские конфигурации (Roaming): `%APPDATA%\Jarvis` (`settings.json`, `aliases.json`, `websites.json`, `protocols.json`).
  - Локальные данные машины (Local): `%LOCALAPPDATA%\Jarvis` (`logs/`, кэш нейромоделей `models/`, токен безопасности `session.token`).
  - Портативный режим: при отсутствии переменных окружения автоматически используются каталоги `<APP_ROOT>\user_data` и `<APP_ROOT>\local_data`.
* Запуск через `start.bat` использует динамический `%~dp0`.
