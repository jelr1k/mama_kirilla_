# Руководство для ИИ по работе над кодовой базой JARVIS (Kirieshka v2)

Краткий архитектурный контекст и обязательные принципы для нейросетей-разработчиков при внесении правок в репозиторий `jelr1k/mama_kirilla_` (активная рабочая ветка `osnova`).

**Стек:** Python 3.12 (FastAPI-шлюз REST + WebSocket на `127.0.0.1:8765`), Tauri v2 (Rust + React 19 / Vite 7), Ollama, faster-whisper, Vosk, Piper TTS. Архивный GUI — PySide6 в `ui_archive/`.

---

## 1. Главные принципы разработки

1. **Хирургическая точность правок:**
   Менять только те строки и файлы, которые прямо относятся к запросу. Никакого попутного рефакторинга, форматирования чужого кода или удаления комментариев.
2. **Простота без избыточных абстракций:**
   Не городить паттерны «на будущее». Если задачу можно надёжно решить в 30-50 строк без потери читаемости - пиши 50, а не 200.
3. **Zero-LLM Core и приоритет детерминированного роутера:**
   LLM практически не используется для жизнедеятельности и базовой работы приложения. Языковая модель — это лишь опциональный текстовый собеседник и фоллбэк. Все прикладные системные действия (запуск приложений, громкость, мониторинг железа, скриншоты, управление питанием/окнами, файлы, Steam, протоколы Старка, сетевая диагностика, VPN/Zapret, Telegram-бот) работают на 100% автономно через детерминированный Command Router и прямое Windows API без вызова LLM и без обязательного наличия Ollama.
   Любые однозначные команды (запуск приложений, громкость, телеметрия, скриншоты, блокировка, папки, время, файлы, Steam, протоколы) должны отсекаться в `services/command_router.py` и выполняться мгновенно без обращения к LLM.
4. **Неблокирующий UI:**
   Фронтенд Tauri v2 (React) общается с бэкендом через REST API и WebSocket шлюз (`services/gateway_service.py`). Все тяжелые задачи выполняются в отдельных потоках бэкенда (`TaskRunner`) и не тормозят рендеринг окна.
5. **Безопасность и песочница:**
   - Файловые операции строго изолированы внутри `workspace/` через `security/sandbox.py`.
   - Запрещено создание произвольных шелл-раннеров без строгой валидации.
   - Деструктивные операции требуют подтверждения (`requires_confirmation=True`).
6. **Портативность путей:**
   Никаких абсолютных путей (`C:\...`). Все пути строятся через `core/app_paths.py`, настройки хранятся в `%APPDATA%\Jarvis`, локальные кэши/логи/токен - в `%LOCALAPPDATA%\Jarvis`.
7. **Проверка тестами:**
   Тесты обязательны только после правок программного кода (перед коммитом чисто документации запускать не требуется):
   ```bash
   python -m pytest -q
   ```

---

## 2. Структура проекта

```text
├── config/             # Конфигурации settings.json, models.json, requirements.txt
├── core/               # Ядро: app_paths, config_manager, events, ollama_manager, steam_manager, protocols_manager, vpn_manager, vpn/, app_indexer
├── modules/            # Опциональные модули: telegram_bot, telegram/, network_checker
├── services/           # Бизнес-логика: command_router, router/, chat_service, gateway_service, gateway/, stark_protocols, updater
├── tools/              # Исполнители инструментов: system_actions, media_control, system_info, applications, files
├── security/           # Песочница sandbox.py и валидация аргументов
├── voice/              # Микрофон, Whisper STT, Vosk wake-word и Piper TTS (voice/tts/)
├── ui/                 # Десктопный фронтенд Tauri v2: React/Vite (src/) + Rust (src-tauri/)
├── presentation/       # Системный трей Windows (tray_icon.py) и легаси контроллеры (legacy/)
├── ui_archive/         # Архивный интерфейс PySide6
├── start/              # Точки входа: bootstrap.py, check_dependencies.py, main.py
├── tests/              # Набор тестов pytest (680 тестов: 677 passed, 3 skipped))
└── docs/               # Актуальная проектная документация и архивы (docs/archive/)
```

---

## 3. Карта ключевых файлов

- **Маршрутизация команд:** фасад `services/command_router.py`, специализированные диспетчеры `services/router/` (`app`, `media`, `protocols`, `site`, `system`), каталог команд `services/command_catalog.py`.
- **Индексация программ Windows:** `core/app_indexer.py` (скан меню «Пуск» и реестра App Paths, генерация алиасов на лету).
- **Связка чата и роутера:** `services/chat_service.py` (асинхронный запуск, передача в LLM, стриминг).
- **Шлюз для фронтенда:** фасад `services/gateway_service.py`, модульные роутеры `services/gateway/routers/`, WebSocket-хаб `services/gateway/hub.py`.
- **Протоколы Старка и Стим:** `services/stark_protocols.py`, `core/protocols_manager.py`, `core/steam_manager.py`.
- **Системные действия:** `tools/system_actions.py` (скриншоты, папки, блокировка ПК, дата/время).
- **Звук и телеметрия:** `tools/media_control.py`, `tools/system_info.py`.
- **Реестр инструментов:** `tools/registry.py` (декларации и права тулов).
- **Шутки и реплики:** `services/rofl_service.py`, фразы `services/rofl_phrases.py`.
- **Сетевой монитор и VPN:** фасад `core/vpn_manager.py`, пакет `core/vpn/` (discovery, uia_driver, zapret_controller), монитор `modules/network_checker.py`.
- **Удалённый бот:** фасад `modules/telegram_bot.py`, пакет `modules/telegram/` (service, client, handlers, keyboards, Cloudflare Worker прокси).
- **Системный трей и окно:** `presentation/tray_icon.py`, `ui/src/components/ConfirmModal.jsx`.
- **Фронтенд:** `ui/src/App.jsx`, вкладки `ui/src/components/`, декомпозированные настройки `ui/src/components/settings/`.
