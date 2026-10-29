# Руководство для ИИ по работе над кодовой базой JARVIS (Kirieshka v2)

Краткий архитектурный контекст и обязательные принципы для нейросетей-разработчиков при внесении правок в репозиторий `jelr1k/mama_kirilla_` (активная рабочая ветка `osnova`).

---

## 1. Главные принципы разработки

1. **Хирургическая точность правок:**
   Менять только те строки и файлы, которые прямо относятся к запросу. Никакого попутного рефакторинга, форматирования чужого кода или удаления комментариев.
2. **Простота без избыточных абстракций:**
   Не городить паттерны «на будущее». Если задачу можно надёжно решить в 30-50 строк без потери читаемости - пиши 50, а не 200.
3. **Приоритет детерминированного роутера (Command Router):**
   Любые однозначные команды (запуск приложений, громкость, телеметрия, скриншоты, блокировка, папки, время, файлы, Steam, протоколы) должны отсекаться в `services/command_router.py` и выполняться мгновенно без обращения к LLM.
4. **Неблокирующий UI:**
   Фронтенд Tauri v2 (React) общается с бэкендом через REST API и WebSocket шлюз (`services/gateway_service.py`). Все тяжелые задачи выполняются в отдельных потоках бэкенда (`TaskRunner`) и не тормозят рендеринг окна.
5. **Безопасность и песочница:**
   - Файловые операции строго изолированы внутри `workspace/` через `security/sandbox.py`.
   - Запрещено создание произвольных шелл-раннеров без строгой валидации.
   - Деструктивные операции требуют подтверждения (`requires_confirmation=True`).
6. **Портативность путей:**
   Никаких абсолютных путей (`C:\...`). Все пути строятся через `core/app_paths.py`, настройки хранятся в `%APPDATA%\Jarvis`.
7. **Обязательная проверка:**
   Перед сдачей задачи всегда проверять работоспособность тестами:
   ```bash
   python -m pytest -q
   ```

---

## 2. Структура проекта

```text
├── config/             # Конфигурации settings.json, models.json, requirements.txt
├── core/               # Ядро: app_paths, config_manager, events, ollama_manager, steam_manager, protocols_manager
├── services/           # Бизнес-логика: command_router, chat_service, gateway_service, stark_protocols, updater
├── tools/              # Исполнители инструментов: system_actions, media_control, system_info, applications, files
├── security/           # Песочница sandbox.py и валидация аргументов
├── voice/              # Микрофон, Whisper STT, Vosk wake-word и Piper TTS (voice/tts/)
├── ui/                 # Десктопный фронтенд Tauri v2: React/Vite (src/) + Rust (src-tauri/)
├── ui_archive/         # Архивный интерфейс PySide6
├── start/              # Точки входа: bootstrap.py, check_dependencies.py, main.py
├── tests/              # Набор тестов pytest (610 тестов)
└── docs/               # Актуальная проектная документация
```

---

## 3. Карта ключевых файлов

- **Маршрутизация команд:** `services/command_router.py` (паттерны, регулярки, сопоставление).
- **Связка чата и роутера:** `services/chat_service.py` (асинхронный запуск, передача в LLM, стриминг).
- **Шлюз для фронтенда:** `services/gateway_service.py` (FastAPI эндпоинты и трансляция WebSocket-событий).
- **Протоколы Старка и Стим:** `services/stark_protocols.py`, `core/protocols_manager.py`, `core/steam_manager.py`.
- **Системные действия:** `tools/system_actions.py` (скриншоты, папки, блокировка ПК, дата/время).
- **Звук и телеметрия:** `tools/media_control.py`, `tools/system_info.py`.
- **Реестр инструментов:** `tools/registry.py` (декларации и права тулов).
- **Шутки и реплики:** `services/rofl_service.py` (реакции на события, цитаты).
- **Фронтенд:** `ui/src/App.jsx`, `ui/src/components/`, `ui/src-tauri/tauri.conf.json`.
