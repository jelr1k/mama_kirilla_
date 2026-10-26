# Сквозной индекс документации и кодовой базы JARVIS

**Дата обновления:** 2026-10-23  
**Ветка разработки:** `experimental` (активная разработка / UI), `osnova` (базовая)  
**Назначение:** Полный реестр документации, исходных файлов, тестов и архитектурных связей для ускорения навигации агентов и разработчиков.

---

## 1. Карта документации (`docs/`)

Вся проектная документация структурирована по назначению в каталоге [`docs/`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs). Единственный документ вне `docs/` — корневой [`README.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/README.md).

| Документ | Назначение | Ключевые темы |
| :--- | :--- | :--- |
| [`00_INDEX.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/00_INDEX.md) | Общий указатель структуры `docs/` | Иерархия источников истины, правила добавления документов |
| [`INDEX.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/INDEX.md) *(этот файл)* | Сквозное индексирование «код ↔ доки ↔ тесты» | Полная матрица трассируемости компонентов и тестов |
| [`GEMINI.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/GEMINI.md) | Контекст архитектуры, стек и правила | Стек, структура папок, потоки данных, жесткие правила |
| [`01_REQUIREMENTS/PROJECT_SPEC.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/01_REQUIREMENTS/PROJECT_SPEC.md) | Актуальное техническое задание (v3.2) | Требования к роутеру, Tool Calling, Workspace, STT/TTS, мультимедиа |
| [`01_REQUIREMENTS/ROADMAP.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/01_REQUIREMENTS/ROADMAP.md) | Дорожная карта будущего развития | Workspace 2.0, streaming TTS, Model Router, память |
| [`02_ARCHITECTURE/AI_WORK_GUIDE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/AI_WORK_GUIDE.md) | Подробнейшее руководство для ИИ | Порядок изучения кода, границы компонентов, аудит |
| [`02_ARCHITECTURE/LOGGING_SYSTEM.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/LOGGING_SYSTEM.md) | Архитектура системы логирования | Специализированные логи, errors.log, очистка при старте |
| [`02_ARCHITECTURE/PATH_PORTABILITY.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/PATH_PORTABILITY.md) | Портативность путей | Отказ от хардкода дисков, `app_paths.py`, `start.bat` |
| [`02_ARCHITECTURE/TTS_ARCHITECTURE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/TTS_ARCHITECTURE.md) | Архитектура синтеза речи (TTS) | Piper TTS, EventBus `speech.requested`, ассеты, кэш |
| [`03_FEATURES/AUTO_ALIASES.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/AUTO_ALIASES.md) | Автоматические алиасы и WorkspaceIndex | Стемминг, русские имена, идемпотентная регистрация |
| [`03_FEATURES/COMMAND_REFERENCE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/COMMAND_REFERENCE.md) | Справочник команд Command Router | Шаблоны фраз, прямые тулы, медиа, звук, телеметрия |
| [`03_FEATURES/WORKSPACE_UI.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/WORKSPACE_UI.md) | Пользовательский интерфейс Workspace | Drag-and-drop, QFileDialog, запуск объектов |
| [`04_STATUS/IMPLEMENTATION_STATUS.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/04_STATUS/IMPLEMENTATION_STATUS.md) | Фактический статус реализации | Что готово, что частично, актуальные ограничения |
| [`05_INSTALLATION/INSTALL_REQUIREMENTS.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/05_INSTALLATION/INSTALL_REQUIREMENTS.md) | Требования к окружению и установке | Python 3.11+, Ollama, faster-whisper, Piper, Vosk |
| [`07_REVIEWS/CRITICAL_ISSUES_REVIEW_2026-10-23.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/07_REVIEWS/CRITICAL_ISSUES_REVIEW_2026-10-23.md) | Критический аудит от 23.10.2026 | Точки отказа: перезапись файлов, фризы UI, утечки COM, диски |
| [`07_REVIEWS/OPUS_AUDIT_2026-10-20.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/07_REVIEWS/OPUS_AUDIT_2026-10-20.md) | Контрольный аудит от 20.10.2026 | Статусы исправления закрытия приложений и shutdown |
| [`07_REVIEWS/TECHNICAL_AUDIT_2026-10-16.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/07_REVIEWS/TECHNICAL_AUDIT_2026-10-16.md) | Технический аудит от 16.10.2026 | Архитектурные риски (A-01...A-07) и их решения |
| [`07_REVIEWS/CODE_REVIEW_2026-09-19.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/07_REVIEWS/CODE_REVIEW_2026-09-19.md) | Раннее ревью от 19.09.2026 | Исторический контекст формирования Command Router |
| [`presentation/README.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/README.md) | Документация слоя контроллеров | Описание всех 11 контроллеров, их сигналов и методов |
| [`voice/tts/README.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/README.md) | Документация пакета TTS | Сервис, движки, проигрыватель, ассеты |

---

## 2. Матрица трассируемости подсистем: Документы ↔ Исходники ↔ Тесты

### 2.1. Жизненный цикл, Запуск и Базовая инфраструктура
- **Назначение:** Определение путей приложения, проверка зависимостей без лишнего pip, ранний bootstrap, шина событий `EventBus`, асинхронный `TaskRunner`.
- **Документация:**
  - [`docs/02_ARCHITECTURE/AI_WORK_GUIDE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/AI_WORK_GUIDE.md)
  - [`docs/02_ARCHITECTURE/PATH_PORTABILITY.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/PATH_PORTABILITY.md)
  - [`docs/05_INSTALLATION/INSTALL_REQUIREMENTS.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/05_INSTALLATION/INSTALL_REQUIREMENTS.md)
- **Исходный код:**
  - Точка входа: [`start/bootstrap.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/start/bootstrap.py)
  - Сборка приложения: [`start/main.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/start/main.py)
  - Предстартовая проверка: [`start/check_dependencies.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/start/check_dependencies.py)
  - Скрипты запуска: [`start.bat`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/start.bat), [`start/install_dependencies.bat`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/start/install_dependencies.bat)
  - Координатор ядра: [`core/application.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/application.py)
  - Портативные пути: [`core/app_paths.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/app_paths.py)
  - События: [`core/events.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/events.py)
  - Фоновые задачи: [`core/task_runner.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/task_runner.py)
  - Версия: [`core/version.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/version.py)
  - Контроллер: [`presentation/application_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/application_controller.py)
- **Тесты:**
  - [`tests/test_start_main_smoke.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_start_main_smoke.py)
  - [`tests/test_start_and_paths_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_start_and_paths_layers.py)
  - [`tests/test_check_dependencies.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_check_dependencies.py)
  - [`tests/test_core_infrastructure.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_core_infrastructure.py)

---

### 2.2. Система логирования
- **Назначение:** Раздельные журналы по подсистемам (`jarvis.log`, `voice.log`, `ollama.log`, `commands.log`, `startup.log`, `events.log`), единый `errors.log`, очистка старых логов при запуске.
- **Документация:**
  - [`docs/02_ARCHITECTURE/LOGGING_SYSTEM.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/LOGGING_SYSTEM.md)
- **Исходный код:**
  - Настройка логирования: [`core/logging_config.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/logging_config.py)
- **Тесты:**
  - [`tests/test_core_infrastructure.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_core_infrastructure.py)

---

### 2.3. Конфигурация и пользовательские настройки
- **Назначение:** Deep-merge шаблона с настройками пользователя в `%APPDATA%\Jarvis\settings.json`, атомарная запись через временные файлы.
- **Документация:**
  - [`docs/02_ARCHITECTURE/AI_WORK_GUIDE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/AI_WORK_GUIDE.md)
- **Исходный код:**
  - Менеджер настроек: [`core/config_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/config_manager.py)
  - Шаблон настроек: [`config/settings.json`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/config/settings.json)
  - Каталог моделей: [`config/models.json`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/config/models.json)
  - Контроллер настроек: [`presentation/settings_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/settings_controller.py)
  - Страница настроек: [`ui/settings_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/settings_page.py)
- **Тесты:**
  - [`tests/test_settings_controller_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_settings_controller_layers.py)
  - [`tests/test_core_infrastructure.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_core_infrastructure.py)

---

### 2.4. Чат, Command Router и Интеграция с LLM (Ollama)
- **Назначение:** Центральный сервис общения `ChatService`, Command Router для мгновенного выполнения команд, Tool Calling (до 5 раундов), безопасный shutdown с отменой ожидания подтверждений, потоковая генерация ответа, управление Ollama Server и жизненным циклом моделей.
- **Документация:**
  - [`docs/01_REQUIREMENTS/PROJECT_SPEC.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/01_REQUIREMENTS/PROJECT_SPEC.md)
  - [`docs/03_FEATURES/COMMAND_REFERENCE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/COMMAND_REFERENCE.md)
- **Исходный код:**
  - Центральный сервис чата: [`services/chat_service.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/chat_service.py)
  - Маршрутизатор команд: [`services/command_router.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/command_router.py)
  - Сообщения и история: [`chat/conversation.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/chat/conversation.py), [`chat/history.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/chat/history.py)
  - Провайдеры LLM: [`llm/provider.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/llm/provider.py), [`llm/ollama.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/llm/ollama.py)
  - Менеджер сервера Ollama: [`core/ollama_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/ollama_manager.py)
  - Контроллеры: [`presentation/chat_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/chat_controller.py), [`presentation/ollama_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/ollama_controller.py)
  - UI чата: [`ui/chat_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/chat_page.py), UI Ollama: [`ui/ollama_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/ollama_page.py)
- **Тесты:**
  - [`tests/test_chat_router_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_chat_router_layers.py) *(тестирует подтверждение close_application, таймаут подтверждения, shutdown)*
  - [`tests/test_command_router_intent.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_command_router_intent.py)
  - [`tests/test_router_smart_matching.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_router_smart_matching.py)
  - [`tests/test_llm_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_llm_layers.py)
  - [`tests/test_ollama_manager_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_ollama_manager_layers.py)
  - [`tests/test_chat_tool_scope.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_chat_tool_scope.py)

---

### 2.5. Файловая подсистема, Sandbox и Workspace
- **Назначение:** Полная изоляция файловых операций внутри `workspace/`, проверка `is_relative_to`, защита от перезаписи файлов (`overwrite=False`), живой `WorkspaceIndex`, разрешение целей через `TargetResolver` и контролируемый fuzzy-поиск (`tools/paths.py`).
- **Документация:**
  - [`docs/01_REQUIREMENTS/PROJECT_SPEC.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/01_REQUIREMENTS/PROJECT_SPEC.md)
  - [`docs/03_FEATURES/WORKSPACE_UI.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/WORKSPACE_UI.md)
  - [`docs/03_FEATURES/AUTO_ALIASES.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/AUTO_ALIASES.md)
- **Исходный код:**
  - Файловые инструменты: [`tools/files.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/files.py)
  - Резолвер путей и fuzzy-поиск: [`tools/paths.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/paths.py)
  - Песочница безопасности: [`security/sandbox.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/security/sandbox.py)
  - Проверка разрешений: [`security/permission_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/security/permission_manager.py)
  - Индексация Workspace: [`core/workspace_index.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/workspace_index.py)
  - Менеджер алиасов: [`core/alias_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/alias_manager.py)
  - Единый TargetResolver: [`core/target_resolver.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/core/target_resolver.py)
  - Контроллеры: [`presentation/workspace_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/workspace_controller.py), [`presentation/alias_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/alias_controller.py)
  - UI страниц: [`ui/workspace_tab.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/workspace_tab.py), [`ui/alias_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/alias_page.py)
- **Тесты:**
  - [`tests/test_file_tools.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_file_tools.py)
  - [`tests/test_file_tools_extended.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_file_tools_extended.py)
  - [`tests/test_filename_search.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_filename_search.py)
  - [`tests/test_paths.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_paths.py)
  - [`tests/test_sandbox.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_sandbox.py)
  - [`tests/test_target_resolver_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_target_resolver_layers.py)
  - [`tests/test_workspace_index.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_workspace_index.py)
  - [`tests/test_alias_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_alias_manager.py)

---

### 2.6. Реестр инструментов (Tools), Процессы, Мультимедиа и Телеметрия
- **Назначение:** Регистрация доступных инструментов в `ToolRegistry`, исполнение через `ToolExecutor` с проверкой прав и подтверждением, запуск и безопасное закрытие приложений Windows с обязательным запросом подтверждения пользователя, системное управление мультимедиа (громкость, mute, плеер), динамическая телеметрия системы (CPU, GPU, RAM, диски, аптайм без хардкода).
- **Документация:**
  - [`docs/03_FEATURES/COMMAND_REFERENCE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/03_FEATURES/COMMAND_REFERENCE.md)
  - [`docs/07_REVIEWS/OPUS_AUDIT_2026-10-20.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/07_REVIEWS/OPUS_AUDIT_2026-10-20.md)
- **Исходный код:**
  - Реестр: [`tools/registry.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/registry.py)
  - Исполнитель: [`tools/executor.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/executor.py)
  - Управление приложениями: [`tools/applications.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/applications.py)
  - Корректное закрытие: [`tools/application_closer.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/application_closer.py)
  - Мультимедиа и звук: [`tools/media_control.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/media_control.py)
  - Телеметрия железа: [`tools/system_info.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/system_info.py)
  - Системные действия: [`tools/system.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tools/system.py)
  - Контроллер: [`presentation/tools_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/tools_controller.py)
  - UI инструментов: [`ui/tools_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/tools_page.py)
- **Тесты:**
  - [`tests/test_applications.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_applications.py)
  - [`tests/test_application_closer.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_application_closer.py)
  - [`tests/test_application_helpers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_application_helpers.py)
  - [`tests/test_application_lifecycle_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_application_lifecycle_layers.py)
  - [`tests/test_media_control.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_media_control.py)
  - [`tests/test_system_telemetry.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_system_telemetry.py)
  - [`tests/test_tool_calling.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_tool_calling.py)
  - [`tests/test_tool_executor.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_tool_executor.py)
  - [`tests/test_tool_executor_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_tool_executor_layers.py)

---

### 2.7. Голосовой ввод (STT) и Ключевая фраза (Wake Word)
- **Назначение:** Захват микрофона (`sounddevice`), локальное распознавание речи в текст через `faster-whisper`, обнаружение wake word через `vosk`, нормализация голосовых команд (`CommandNormalizer`), подавление wake word во время проигрывания TTS.
- **Документация:**
  - [`docs/01_REQUIREMENTS/PROJECT_SPEC.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/01_REQUIREMENTS/PROJECT_SPEC.md)
  - [`docs/05_INSTALLATION/INSTALL_REQUIREMENTS.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/05_INSTALLATION/INSTALL_REQUIREMENTS.md)
- **Исходный код:**
  - Распознавание речи: [`voice/speech_recognizer.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/speech_recognizer.py)
  - Детекция Wake Word: [`voice/wake_word.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/wake_word.py)
  - Нормализатор речи: [`voice/command_normalizer.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/command_normalizer.py)
  - Контроллер голоса: [`voice/controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/controller.py)
  - Микрофон и устройства: [`voice/microphone.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/microphone.py), [`voice/devices.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/devices.py)
  - Контроллеры Presentation: [`presentation/voice_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/voice_controller.py), [`presentation/wake_word_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/wake_word_controller.py), [`presentation/dependency_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/dependency_controller.py)
- **Тесты:**
  - [`tests/test_voice.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_voice.py)
  - [`tests/test_voice_service_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_voice_service_layers.py)
  - [`tests/test_voice_wake_word_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_voice_wake_word_layers.py)
  - [`tests/test_voice_normalizer.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_voice_normalizer.py)
  - [`tests/test_voice_devices.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_voice_devices.py)
  - [`tests/test_voice_device_resolution_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_voice_device_resolution_layers.py)
  - [`tests/test_microphone_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_microphone_layers.py)
  - [`tests/test_speech_recognizer_layers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_speech_recognizer_layers.py)
  - [`tests/test_wake_word_controller.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_wake_word_controller.py)

---

### 2.8. Синтез речи (TTS / Voice Output)
- **Назначение:** Локальный голосовой вывод через Piper TTS на CPU, асинхронный поток `jarvis-tts-worker`, очередь воспроизведения, двухуровневый кэш (готовые WAV-ассеты + LRU-кэш генераций), подписка на `speech.requested`.
- **Документация:**
  - [`docs/02_ARCHITECTURE/TTS_ARCHITECTURE.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/02_ARCHITECTURE/TTS_ARCHITECTURE.md)
  - [`voice/tts/README.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/README.md)
- **Исходный код:**
  - Сервис TTS: [`voice/tts/service.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/service.py)
  - Интерфейс движка: [`voice/tts/engine.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/engine.py)
  - Движок Piper: [`voice/tts/engines/piper.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/engines/piper.py)
  - Профили голосов: [`voice/tts/voice_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/voice_manager.py)
  - Аудио-ассеты и кэш: [`voice/tts/asset_manager.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/asset_manager.py)
  - Воспроизведение звука: [`voice/tts/audio_player.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/audio_player.py)
  - Очистка текста: [`voice/tts/text.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/text.py)
  - Метрики: [`voice/tts/metrics.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/voice/tts/metrics.py)
  - Диалог ассетов TTS: [`ui/tts_assets_dialog.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/tts_assets_dialog.py)
- **Тесты:**
  - [`tests/test_tts_service.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_tts_service.py)
  - [`tests/test_tts_architecture_components.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_tts_architecture_components.py)

---

### 2.9. Шуточные реакции (RoflService)
- **Назначение:** Вероятностные рофл-ответы при запуске приложений, прямых командах (включая громкость, звук, телеметрию) и системных событиях, поддержка редких и «демонических» реплик.
- **Исходный код:**
  - Сервис рофлов: [`services/rofl_service.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/rofl_service.py)
  - Диалог настройки вероятностей: [`ui/rofl_settings_dialog.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/rofl_settings_dialog.py)
- **Тесты:**
  - [`tests/test_rofl_service.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_rofl_service.py)

---

### 2.10. Автоматическое обновление приложения (Update System)
- **Назначение:** Проверка релизов на GitHub, безопасное скачивание архива, staging, создание резервной копии, вызов отдельного процесса updater, откат при сбое.
- **Документация:**
  - Раздел «Проверка и установка обновлений» в [`README.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/README.md)
- **Исходный код:**
  - Проверка релизов: [`services/update_checker.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_checker.py)
  - Загрузчик: [`services/update_downloader.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_downloader.py)
  - Установщик: [`services/update_installer.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_installer.py)
  - Бэкап: [`services/update_backup.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_backup.py)
  - Откат: [`services/update_rollback.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_rollback.py)
  - Перезапуск: [`services/update_relauncher.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_relauncher.py)
  - Политика установки: [`services/update_install_policy.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/services/update_install_policy.py)
  - Процесс updater: [`start/updater.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/start/updater.py)
- **Тесты:**
  - [`tests/test_update_checker_fallback.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_update_checker_fallback.py)

---

### 2.11. Слой Presentation (Контроллеры) и Графический интерфейс Kirieshka v2 (UI)
- **Назначение:** Полное разделение интерфейса и бизнес-логики через паттерн Controller и шину событий. 11 специализированных контроллеров. Модульный пакет кинематических анимаций, неоновый кибер-стиль оформления, анимированный сплэш-скрин, динамические бейджи загрузки ресурсов в шапке.
- **Документация:**
  - [`presentation/README.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation/README.md)
  - [`docs/GEMINI.md`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/docs/GEMINI.md)
- **Исходный код:**
  - Главное окно: [`ui/main_window.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/main_window.py)
  - Заставка (Splash Screen): [`ui/splash_screen.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/splash_screen.py)
  - Страницы: [`ui/chat_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/chat_page.py), [`ui/settings_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/settings_page.py), [`ui/statistics_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/statistics_page.py), [`ui/workspace_tab.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/workspace_tab.py), [`ui/alias_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/alias_page.py), [`ui/tools_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/tools_page.py), [`ui/ollama_page.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/ollama_page.py)
  - Диалоги: [`ui/commands_window.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/commands_window.py), [`ui/rofl_settings_dialog.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/rofl_settings_dialog.py), [`ui/tts_assets_dialog.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/tts_assets_dialog.py)
  - Пакет анимаций UI: [`ui/animations/`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/animations) (`tab_animations.py`, `button_animations.py`, `toggle.py`, `effects.py`, `splash_screen.py`)
  - Темы оформления: [`ui/theme.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/ui/theme.py)
  - Контроллеры: [`presentation/`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/presentation)
- **Тесты:**
  - [`tests/test_presentation_controllers.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_presentation_controllers.py)
  - [`tests/test_ui_animations.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_ui_animations.py)
  - [`tests/test_ui_smoke.py`](file:///d:/putin/kirieshkav2/mama_kirilla_-osnova/tests/test_ui_smoke.py)

---

## 3. Реестр решённых багов и архитектурных проблем

| Проблема / Задача | Где была проблема | Как решена в коде | Подтверждающие тесты |
| :--- | :--- | :--- | :--- |
| **Скачок скролла в чате** | `ui/chat_page.py` | Сохранение `was_at_bottom = previous_value >= maximum - 2`, автоскролл только если пользователь внизу | Ручная проверка UI, `test_ui_smoke.py` |
| **Разрешение имён файлов после STT** | `voice/command_normalizer.py`, `tools/paths.py` | Нормализация в `voice/command_normalizer.py`, fuzzy-поиск в `tools/paths.py` с порогом 0.72 по реальному `WorkspaceIndex` | `tests/test_filename_search.py`, `tests/test_voice_normalizer.py` |
| **Подтверждение `close_application`** | `tools/registry.py` | Установлен `requires_confirmation: True`, в `CommandRouter` добавлена обработка ожидания подтверждения | `tests/test_chat_router_layers.py` |
| **Зависание shutdown при ожидании подтверждения** | `services/chat_service.py` | Добавлен таймаут (60с), флаг `_shutting_down`, пробуждение потока в `shutdown()` через `event.set()` | `tests/test_chat_router_layers.py` |
| **Повторный медленный `pip install` на каждом старте** | `start/install_dependencies.bat` | Создан скрипт `start/check_dependencies.py`, быстро проверяющий установленные модули без pip | `tests/test_check_dependencies.py` |
| **Случайная перезапись файлов при copy/move** | `tools/files.py` | Добавлена проверка существования целевого файла и параметр `overwrite=False` | `tests/test_file_tools_extended.py` |
| **Остановка внешних процессов Ollama** | `core/ollama_manager.py` | Добавлено отслеживание управляемого процесса `_managed_process` | `tests/test_ollama_manager_layers.py` |
| **Управление медиа и системной громкостью** | `tools/media_control.py` | Интеграция Windows CoreAudio API с fallback на `pycaw`, отслеживание mute state, детекция команд в `CommandRouter` | `tests/test_media_control.py` |
| **Мониторинг железа без жесткого зашивания** | `tools/system_info.py` | Динамический сбор телеметрии CPU, GPU (NVIDIA/AMD/WMI/PowerShell), RAM, дисков и аптайма | `tests/test_system_telemetry.py` |
| **Сброс состояния анимации вкладок** | `ui/animations/tab_animations.py` | Метод `reset_animation_state` при повторных/быстрых переключениях вкладок | `tests/test_ui_animations.py` |
