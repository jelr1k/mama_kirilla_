# Карта соответствия документации и кода (JARVIS / Kirieshka v2)

Используй эту таблицу при чтении и синхронизации активных документов. Архив `docs/archive/` не синхронизируется.

## 1. Таблица «Документ ↔ Кодовая база»

| Документ | Что описывает | С чем сверять в коде |
|---|---|---|
| `README.md` | Обзор, версия, стек, реализованные фичи, запуск | `core/version.py`, `start.bat`, `start_ui.bat`, `ui/package.json`, `services/gateway/routers/`, `core/`, `modules/` |
| `AGENTS.md` | Табу, архитектура, команды тестов | Актуальность путей (`security/sandbox.py`, `core/logging_config.py`, `services/gateway_service.py`, `ui/`, `ui_archive/`), `.venv\Scripts\pytest tests/` |
| `.gemini/rules.md` и `docs/GEMINI.md` | Короткие входные указатели для ИИ | Ссылки на `AGENTS.md`, `docs/AI_GUIDE.md`, `docs/ARCHITECTURE.md`, `docs/INDEX.md` |
| `docs/INDEX.md` | Оглавление всей документации | Наличие и краткое содержание всех файлов `docs/*.md` и `docs/archive/` |
| `docs/AI_GUIDE.md` | Стек, структура папок, карта ключевых файлов | Дерево каталогов репозитория, ключевые файлы `core/`, `services/`, `tools/`, `modules/`, `voice/`, `ui/src/`, число тестов |
| `docs/ARCHITECTURE.md` | Поток данных, Gateway REST/WS, TTS, логи, пути | `services/command_router.py`, `services/chat_service.py`, `services/gateway_service.py`, `services/gateway/routers/*.py`, `services/gateway/hub.py`, `ui/src/services/assistantSocket.js`, `voice/tts/`, `core/logging_config.py`, `core/app_paths.py` |
| `docs/COMPONENTS_MAP.md` | Полная матрица «подсистема ↔ файлы кода ↔ тесты» | Все файлы в `core/`, `services/`, `tools/`, `modules/`, `voice/`, `security/`, `presentation/`, `start/`, `config/`, `ui/src/`, `tests/` |
| `docs/COMMANDS.md` | Справочник голосовых/текстовых команд | `services/command_catalog.py`, `services/command_router.py`, `services/router/*.py`, `tools/registry.py`, `tools/system_actions.py`, `tools/media_control.py`, `tools/applications.py`, `tools/files.py` |
| `docs/APP_DISCOVERY.md` | Поиск программ, TargetResolver, алиасы, RapidFuzz | `core/app_indexer.py`, `core/target_resolver.py`, `core/alias_manager.py`, `core/website_manager.py`, `core/workspace_index.py`, `tools/paths.py` |
| `docs/PROTOCOLS_V2_SPEC.md` | Спецификация глубокой автоматизации протоколов | Сверять терминологию и статус реализации с `core/protocols_manager.py` и `services/stark_protocols.py` (если документ остаётся спецификацией — помечать нереализованное явно) |
| `docs/SCENARIO_RUNTIME.md` | Практический рантайм сценариев рабочего места | `core/protocols_manager.py`, `services/stark_protocols.py`, `core/vpn/uia_driver.py`, `tools/applications.py`, `tools/application_closer.py` |
| `docs/INSTALLATION.md` | Установка с нуля и dev-запуск | `config/requirements.txt`, `config/requirements-dev.txt`, `start.bat`, `start_ui.bat`, `start/install_dependencies.bat`, `start/check_dependencies.py`, `ui/package.json` |
| `docs/STORAGE_LAYOUT.md` | Где хранятся настройки, кэши, логи, токен | `core/app_paths.py`, `core/config_manager.py`, `config/settings.json`, `config/models.json`, `core/logging_config.py`, `services/gateway/deps.py` |
| `docs/PROJECT_STATUS.md` | Чеклист готового, задачи в работе, Roadmap | Фактическое наличие модулей в репо, `ui/src/App.jsx`, `ui/src/components/`, `services/`, `core/`, `tests/` |

## 2. Типичные места расхождений в этом проекте

- **Роутеры шлюза и клиенты API:** при добавлении или переименовании эндпоинтов в `services/gateway/routers/*.py` часто забывают обновить список в `docs/ARCHITECTURE.md` и `docs/PROJECT_STATUS.md`.
- **Декомпозиция монолитов:** модули выносятся в подпакеты (`services/gateway/`, `services/router/`, `services/update_*.py`, `core/vpn/`, `modules/telegram/`, `ui/src/components/settings/`), а старые описания в `PROJECT_STATUS.md` или `COMPONENTS_MAP.md` могут ссылаться на плоскую структуру или старый PySide6-код.
- **Скрипты запуска и фронтенд:** `start.bat`, `start_ui.bat`, `start/splash.py` vs `ui/src/components/IslandApp.jsx` — всегда проверяй, что реально запускается сейчас.
- **Пороги и лимиты:** пороги fuzzy-поиска (`tools/paths.py`, `core/alias_manager.py`, `core/workspace_index.py`), лимит раундов Tool Calling (`services/chat_service.py`), интервал телеметрии WS (`services/gateway/hub.py`) — при сверке читать точные константы в коде.
- **Счётчик тестов:** в `AI_GUIDE.md` и `PROJECT_STATUS.md` зашиты числа тестов — при любой синхронизации сверять их фактической командой pytest.
