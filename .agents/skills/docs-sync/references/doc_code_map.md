# Карта соответствия документации и кода (JARVIS / Kirieshka v2)

Используй эту карту как ориентир по ролям документов и источникам истины в коде. Конкретные списки файлов, роутов, событий и компонентов всегда бери из живого вывода `audit_docs.py --facts`, а не из памяти.

Архив `docs/archive/` хранит исторические планы и аудиты — он не синхронизируется с текущим кодом.

## 1. Доменные роли документов

| Документ / группа | Роль документа | Источник истины в коде |
|---|---|---|
| `README.md` | Витрина проекта: обзор, текущая версия, стек, ключевые фичи, быстрый старт | `core/version.py`, `ui/package.json`, `start.bat`, `start_ui.bat`, роутеры шлюза, верхнеуровневые пакеты кода |
| `AGENTS.md` | Жёсткие табу, активная ветка (`osnova`), архитектурные границы, кладбище фич, команда тестов | Реальная структура репозитория (`security/sandbox.py`, `core/logging_config.py`, `services/gateway_service.py`, `ui/`, `ui_archive/`) |
| `.gemini/rules.md`, `docs/GEMINI.md`, `docs/AI_GUIDE.md` | Входные точки и контекст для ИИ-ассистентов: стек, дерево каталогов, правила правок | `AGENTS.md`, `docs/INDEX.md`, фактическое дерево директорий верхнего уровня, реальное число тестов |
| `docs/INDEX.md` | Центральный навигационный реестр всей активной документации | Все файлы `docs/*.md` (каждый новый документ обязан быть зарегистрирован здесь) |
| `docs/ARCHITECTURE.md` | Потоки данных, `EventBus` → `Gateway` (REST/WS), TTS, логирование, жизненный цикл | `core/application.py`, `core/events.py`, `services/gateway_service.py`, `services/gateway/routers/*.py`, `services/gateway/hub.py`, `ui/src/services/*`, `voice/tts/`, `core/logging_config.py`, `core/app_paths.py` |
| `docs/COMPONENTS_MAP.md` | Полная матрица «подсистема ↔ файлы кода ↔ тесты» | Все авто-обнаруженные исходники и конфиги из `audit_docs.py` + `tests/` + `ui/src/**/*.test.*` |
| `docs/COMMANDS.md` | Справочник голосовых/текстовых команд и режимов обработки | `services/command_catalog.py`, `services/command_router.py`, `services/router/*.py`, `tools/*.py` |
| `docs/APP_DISCOVERY.md` | Поиск программ, сайтов, алиасов, `TargetResolver` и пороги fuzzy-поиска | `core/app_indexer.py`, `core/target_resolver.py`, `core/alias_manager.py`, `core/website_manager.py`, `core/workspace_index.py`, `tools/paths.py` |
| `docs/PROTOCOLS_V2_SPEC.md` и `docs/SCENARIO_RUNTIME.md` | Спецификация и фактический рантайм сценариев/протоколов | `core/protocols_manager.py`, `services/stark_protocols.py`, `core/vpn/uia_driver.py`, `tools/applications.py`, `tools/application_closer.py` (нереализованное в спецификации помечать явно) |
| `docs/INSTALLATION.md` | Установка с нуля и dev-запуск | `config/requirements*.txt`, `start.bat`, `start_ui.bat`, `start/*`, `ui/package.json`, `ui/src-tauri/` |
| `docs/STORAGE_LAYOUT.md` | Хранение настроек, кэшей моделей, логов и токена сессии | `core/app_paths.py`, `core/config_manager.py`, `config/settings.json`, `config/models.json`, `core/logging_config.py`, `services/gateway/deps.py` |
| `docs/PROJECT_STATUS.md` | Текущий статус, реализованные возможности, чеклист задач, Roadmap | Реальное наличие модулей, `ui/src/App.jsx`, `ui/src/components/`, `ui/src/motion/`, `services/`, `core/`, факт тестов |
| Любые новые/концептные `docs/*.md` (напр. `docs/MOTION_UI_CONCEPT.md`) | Дизайн-концепты, прототипы, RFC и локальные спецификации | Соответствующая подсистема в коде (напр. `ui/src/motion/`), регистрация в `docs/INDEX.md`, относительные ссылки вместо локальных `file://` |

## 2. Инварианты проверки при любых правках кода

1. **Новые пакеты и подмодули:** при декомпозиции или добавлении директорий (как `chat/`, `llm/`, `ui/src/motion/`, `services/gateway/routers/`, `services/router/`) сверяй, чтобы они попали в `COMPONENTS_MAP.md`, а новые документы — в `docs/INDEX.md`.
2. **Контракт бэкенд ↔ фронт:** при изменении эндпоинтов в `services/gateway/routers/*.py` или событий в `services/gateway_service.py` обновляй `docs/ARCHITECTURE.md` (и `PROJECT_STATUS.md`, если меняется функционал).
3. **Магические числа и пороги:** любые пороги fuzzy-поиска, лимиты раундов Tool Calling, таймауты и интервалы телеметрии перед записью в доки читай напрямую из кода.
4. **Счётчики тестов:** либо снимай точное число через `.venv\Scripts\python.exe -m pytest tests/ --collect-only -q` (и `npm --prefix ui test -- --run` при необходимости), либо заменяй жёсткое число на ссылку на каталог тестов, чтобы счётчик не протухал при каждом коммите.
5. **Единая версия:** `core/version.py` (`APP_VERSION`), `ui/package.json`, `ui/src-tauri/tauri.conf.json` и `README.md` должны совпадать.
