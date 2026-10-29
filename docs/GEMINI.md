# GEMINI.md — Контекст и архитектурный гайд для LLM (Kirieshka v2 / mama_kirilla_)

Выжимка архитектуры, актуального стека и правил для LLM при работе с репозиторием `jelr1k/mama_kirilla_` (целевая рабочая ветка `osnova`).

Подробное руководство см. в [`AI_GUIDE.md`](AI_GUIDE.md) и [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## 1. Стек и технологии

**Kirieshka v2 (Jarvis)** — модульный локальный голосовой и текстовый ассистент под Windows 11 с акцентом на приватность, быстродействие и автономную работу без облаков.

* **Репозиторий:** `jelr1k/mama_kirilla_` (рабочая ветка: `osnova`)
* **Язык и среда:** Python 3.11+, Windows 11
* **Целевой UI:** Tauri v2 + React / Vite (`ui/`), единый шлюз FastAPI/WebSocket (`services/gateway_service.py`)
* **Архивный UI:** PySide6 (`ui_archive/`) сохранен для справочных целей и режима обслуживания
* **Шина событий:** Кастомный `EventBus` (`core/events.py`) для слабой связности компонентов
* **Слой Presentation:** Контроллеры для изоляции UI от бизнес-логики (`presentation/`)
* **LLM бэкенд:** Локальная Ollama (легкие модели с Tool Calling)
* **STT (распознавание):** faster-whisper
* **Wake-word:** Vosk (детекция активационной фразы)
* **TTS (синтез речи):** Piper TTS (локальные ONNX-голоса через `voice/tts/`)
* **Steam & Протоколы:** `SteamManager` (`core/steam_manager.py`), `ProtocolsManager` (`core/protocols_manager.py`), `StarkProtocols` (`services/stark_protocols.py`)
* **Тесты:** pytest (610 тестов: 607 passed, 3 skipped)

---

## 2. Архитектурный поток (Data Flow)

```text
[Пользователь (Tauri v2 UI / Голосовой ввод)]
                   ↓
       services/command_router.py
          /                 \
(Четкий паттерн / алиас)   (Сложный / разговорный запрос)
         ↓                                 ↓
  Прямой Tool (без LLM)           Ollama Manager (LLM)
         ↓                                 ↓
   Мгновенный ответ                 Tool Calling
                                           ↓
                                      ToolExecutor
                                           ↓
                                      EventBus / Gateway / UI
```

**Критический принцип:** `CommandRouter` обязан отсекать простые команды (запуск/закрытие софта, Steam игры, протоколы Старка, управление медиа и звуком, телеметрия ПК, системные папки, скриншоты, файлы) и выполнять их напрямую через `tools/` без обращения к LLM.

---

## 3. Структура каталогов

- `start/` — входные точки приложения: `bootstrap.py`, `main.py`, `check_dependencies.py`, `updater.py`.
- `core/` — фундамент системы: `application.py`, `config_manager.py`, `ollama_manager.py`, `alias_manager.py`, `event_bus.py`, `tool_executor.py`, `app_paths.py`, `target_resolver.py`, `steam_manager.py`, `protocols_manager.py`.
- `services/` — бизнес-логика: `command_router.py`, `chat_service.py`, `gateway_service.py`, `stark_protocols.py`, `rofl_service.py`, `statistics_service.py`, `model_service.py`, сервисы автообновления.
- `tools/` — исполняемые инструменты:
  - `applications.py`, `application_closer.py` — запуск и закрытие приложений
  - `media_control.py` — системная громкость, выключение/включение звука через Windows CoreAudio API, управление плеером
  - `system_info.py` — динамическая телеметрия железа (CPU, GPU без хардкода, RAM, диски, аптайм)
  - `files.py`, `paths.py` — безопасная работа с файлами
  - `registry.py` — реестр и декларации Tool Calling
- `ui/` — графический интерфейс Tauri v2 + React/Vite:
  - `src/` — React-компоненты (Chat, Commands, Settings, Aliases, Workspace, Ollama, Protocols)
  - `src-tauri/` — Rust/Tauri v2 бэкенд окна
- `ui_archive/` — архивный PySide6 интерфейс и анимации `animations/`.
- `voice/` — голосовой пайплайн: `microphone.py`, `speech_recognizer.py`, `wake_word.py`, `command_normalizer.py`, `devices.py`, `statistics.py`, подсистема синтеза `voice/tts/` (Piper TTS).
- `config/` — конфигурация JSON, алиасы, схемы настроек.
- `docs/` — документация: `INDEX.md`, `ARCHITECTURE.md`, `COMMANDS.md`, `SPEC_AND_STATUS.md`, `INSTALLATION.md`, `AI_GUIDE.md`, архивные материалы.
- `tests/` — тестовый набор `pytest`.

---

## 4. Жесткие правила разработки

1. **Хирургическая точность:** менять только относящиеся к задаче строки, без попутного переформатирования и удаления чужих комментариев.
2. **Простота кода:** не создавать абстракций «на будущее». 50 читаемых строк всегда лучше 200 строк с переусложнёнными фабриками.
3. **Безопасность:** файловые операции изолированы в `workspace/` через `security/sandbox.py`.
4. **Портативность:** все пути строятся через `core/app_paths.py`, никаких `C:\...`.
5. **Проверка перед коммитом:** обязательный прогон тестов `python -m pytest -q`.
6. **Работа с Git:** не трогать ветки и гитхаб без явного запроса пользователя.
