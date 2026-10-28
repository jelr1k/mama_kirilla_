# Документация JARVIS (Kirieshka v2)

Центральный навигационный индекс актуальной проектной документации.

---

## Основные разделы

| Документ | Описание | Для кого |
|---|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Архитектура системы, подсистемы, EventBus, TTS, логирование и портативность | Разработчикам и архитекторам |
| [`COMMANDS.md`](COMMANDS.md) | Полный справочник поддерживаемых команд (приложения, звук, папки, скриншоты, файлы, Steam, протоколы) | Пользователям и разработчикам |
| [`SPEC_AND_STATUS.md`](SPEC_AND_STATUS.md) | Актуальный статус выполнения, решённые задачи, баги в работе и Roadmap | Для контроля прогресса |
| [`INSTALLATION.md`](INSTALLATION.md) | Требования, установка зависимостей, настройка Ollama/Whisper и запуск | Для развёртывания проекта |
| [`AI_GUIDE.md`](AI_GUIDE.md) | Архитектурный контекст и строгие правила внесения изменений для ИИ | Нейросетям-ассистентам |
| [`CODE_REVIEW_TAURI_V2_2026-10-27.md`](CODE_REVIEW_TAURI_V2_2026-10-27.md) | Аудит и план миграции на Tauri v2 | Разработчикам |
| [`GEMINI.md`](GEMINI.md) | Архитектурный контекст, стек и правила разработки | Для LLM и ассистентов |

---

## Архив документов

Исторические разовые аудиты кода и отчеты перенесены в каталог [`docs/archive/reviews/`](archive/reviews/):
* `CODE_REVIEW_2026-09-19.md`
* `TECHNICAL_AUDIT_2026-10-16.md`
* `OPUS_AUDIT_2026-10-20.md`
* `CRITICAL_ISSUES_REVIEW_2026-10-23.md`

Архивные версии технических спецификаций и гайдов: [`docs/archive/legacy_docs/`](archive/legacy_docs/).

---

## Структурная матрица подсистем (код ↔ тесты)

### 2.1. Жизненный цикл, Запуск и Базовая инфраструктура
- **Назначение:** Определение путей приложения, проверка зависимостей без лишнего pip, ранний bootstrap, шина событий `EventBus`, асинхронный `TaskRunner`.
- **Исходный код:**
  - Точка входа: [`start/bootstrap.py`](start/bootstrap.py)
  - Сборка приложения: [`start/main.py`](start/main.py)
  - Предстартовая проверка: [`start/check_dependencies.py`](start/check_dependencies.py)
  - Скрипты запуска: [`start.bat`](start.bat), [`start.vbs`](start.vbs), [`start/install_dependencies.bat`](start/install_dependencies.bat)
  - Координатор ядра: [`core/application.py`](core/application.py)
  - Портативные пути: [`core/app_paths.py`](core/app_paths.py)
  - События: [`core/events.py`](core/events.py)
  - Фоновые задачи: [`core/task_runner.py`](core/task_runner.py)
  - Версия: [`core/version.py`](core/version.py)
- **Тесты:**
  - [`tests/test_start_main_smoke.py`](tests/test_start_main_smoke.py)
  - [`tests/test_start_and_paths_layers.py`](tests/test_start_and_paths_layers.py)
  - [`tests/test_check_dependencies.py`](tests/test_check_dependencies.py)
  - [`tests/test_core_infrastructure.py`](tests/test_core_infrastructure.py)

---

### 2.2. Система логирования
- **Назначение:** Раздельные журналы по подсистемам (`jarvis.log`, `voice.log`, `ollama.log`, `commands.log`, `startup.log`, `events.log`), единый `errors.log`, очистка старых логов при запуске.
- **Исходный код:** [`core/logging_config.py`](core/logging_config.py)
- **Тесты:** [`tests/test_core_infrastructure.py`](tests/test_core_infrastructure.py)

---

### 2.3. Конфигурация и пользовательские настройки
- **Назначение:** Deep-merge шаблона с настройками пользователя в `%APPDATA%\Jarvis\settings.json`, атомарная запись через временные файлы.
- **Исходный код:**
  - Менеджер настроек: [`core/config_manager.py`](core/config_manager.py)
  - Шаблон настроек: [`config/settings.json`](config/settings.json)
  - Каталог моделей: [`config/models.json`](config/models.json)
- **Тесты:**
  - [`tests/test_settings_controller_layers.py`](tests/test_settings_controller_layers.py)
  - [`tests/test_core_infrastructure.py`](tests/test_core_infrastructure.py)

---

### 2.4. Чат, Command Router и Интеграция с LLM (Ollama)
- **Назначение:** Центральный сервис общения `ChatService`, Command Router для мгновенного выполнения команд, Tool Calling, потоковая генерация ответа, управление Ollama Server.
- **Исходный код:**
  - Центральный сервис чата: [`services/chat_service.py`](services/chat_service.py)
  - Маршрутизатор команд: [`services/command_router.py`](services/command_router.py)
  - Менеджер Steam игр: [`core/steam_manager.py`](core/steam_manager.py)
  - Менеджер протоколов Старка: [`core/protocols_manager.py`](core/protocols_manager.py), [`services/stark_protocols.py`](services/stark_protocols.py)
  - Сообщения и история: [`chat/conversation.py`](chat/conversation.py), [`chat/history.py`](chat/history.py)
  - Провайдеры LLM: [`llm/ollama.py`](llm/ollama.py)
  - Менеджер сервера Ollama: [`core/ollama_manager.py`](core/ollama_manager.py)
- **Тесты:**
  - [`tests/test_chat_router_layers.py`](tests/test_chat_router_layers.py)
  - [`tests/test_command_router_intent.py`](tests/test_command_router_intent.py)
  - [`tests/test_router_smart_matching.py`](tests/test_router_smart_matching.py)
  - [`tests/test_llm_layers.py`](tests/test_llm_layers.py)
  - [`tests/test_ollama_manager_layers.py`](tests/test_ollama_manager_layers.py)
  - [`tests/test_steam_manager.py`](tests/test_steam_manager.py)
  - [`tests/test_protocols_manager.py`](tests/test_protocols_manager.py)
  - [`tests/test_stark_protocols.py`](tests/test_stark_protocols.py)

---

### 2.5. Файловая подсистема, Sandbox и Workspace
- **Назначение:** Полная изоляция файловых операций внутри `workspace/`, проверка `is_relative_to`, защита от перезаписи файлов (`overwrite=False`), живой `WorkspaceIndex`, разрешение целей через `TargetResolver` и контролируемый fuzzy-поиск (`tools/paths.py`).
- **Исходный код:**
  - Файловые инструменты: [`tools/files.py`](tools/files.py)
  - Резолвер путей и fuzzy-поиск: [`tools/paths.py`](tools/paths.py)
  - Песочница безопасности: [`security/sandbox.py`](security/sandbox.py)
  - Индексация Workspace: [`core/workspace_index.py`](core/workspace_index.py)
  - Менеджер алиасов: [`core/alias_manager.py`](core/alias_manager.py)
  - Менеджер веб-сайтов: [`core/website_manager.py`](core/website_manager.py)
  - Единый TargetResolver: [`core/target_resolver.py`](core/target_resolver.py)
- **Тесты:**
  - [`tests/test_file_tools.py`](tests/test_file_tools.py)
  - [`tests/test_file_tools_extended.py`](tests/test_file_tools_extended.py)
  - [`tests/test_filename_search.py`](tests/test_filename_search.py)
  - [`tests/test_paths.py`](tests/test_paths.py)
  - [`tests/test_sandbox.py`](tests/test_sandbox.py)
  - [`tests/test_target_resolver_layers.py`](tests/test_target_resolver_layers.py)
  - [`tests/test_workspace_index.py`](tests/test_workspace_index.py)
  - [`tests/test_alias_manager.py`](tests/test_alias_manager.py)
  - [`tests/test_websites_and_system_commands.py`](tests/test_websites_and_system_commands.py)

---

### 2.6. Реестр инструментов (Tools), Процессы, Мультимедиа и Телеметрия
- **Назначение:** Регистрация доступных инструментов в `ToolRegistry`, исполнение через `ToolExecutor` с проверкой прав и подтверждением, запуск и безопасное закрытие приложений Windows с обязательным запросом подтверждения пользователя, системное управление мультимедиа, динамическая телеметрия системы.
- **Исходный код:**
  - Реестр: [`tools/registry.py`](tools/registry.py)
  - Исполнитель: [`tools/executor.py`](tools/executor.py)
  - Управление приложениями: [`tools/applications.py`](tools/applications.py)
  - Корректное закрытие: [`tools/application_closer.py`](tools/application_closer.py)
  - Мультимедиа и звук: [`tools/media_control.py`](tools/media_control.py)
  - Телеметрия железа: [`tools/system_info.py`](tools/system_info.py)
  - Системные действия: [`tools/system_actions.py`](tools/system_actions.py)
- **Тесты:**
  - [`tests/test_applications.py`](tests/test_applications.py)
  - [`tests/test_application_closer.py`](tests/test_application_closer.py)
  - [`tests/test_application_helpers.py`](tests/test_application_helpers.py)
  - [`tests/test_application_lifecycle_layers.py`](tests/test_application_lifecycle_layers.py)
  - [`tests/test_media_control.py`](tests/test_media_control.py)
  - [`tests/test_system_telemetry.py`](tests/test_system_telemetry.py)
  - [`tests/test_tool_calling.py`](tests/test_tool_calling.py)
  - [`tests/test_tool_executor.py`](tests/test_tool_executor.py)
  - [`tests/test_tool_executor_layers.py`](tests/test_tool_executor_layers.py)
  - [`tests/test_new_system_tools.py`](tests/test_new_system_tools.py)

---

### 2.7. Голосовой ввод (STT) и Ключевая фраза (Wake Word)
- **Назначение:** Захват микрофона, локальное распознавание речи в текст через `faster-whisper`, обнаружение wake word через `vosk`, нормализация голосовых команд, подавление wake word во время проигрывания TTS.
- **Исходный код:**
  - Распознавание речи: [`voice/speech_recognizer.py`](voice/speech_recognizer.py)
  - Детекция Wake Word: [`voice/wake_word.py`](voice/wake_word.py)
  - Нормализатор речи: [`voice/command_normalizer.py`](voice/command_normalizer.py)
  - Контроллер голоса: [`voice/controller.py`](voice/controller.py)
  - Микрофон и устройства: [`voice/microphone.py`](voice/microphone.py), [`voice/devices.py`](voice/devices.py)
- **Тесты:**
  - [`tests/test_voice.py`](tests/test_voice.py)
  - [`tests/test_voice_service_layers.py`](tests/test_voice_service_layers.py)
  - [`tests/test_voice_wake_word_layers.py`](tests/test_voice_wake_word_layers.py)
  - [`tests/test_voice_normalizer.py`](tests/test_voice_normalizer.py)
  - [`tests/test_voice_devices.py`](tests/test_voice_devices.py)
  - [`tests/test_microphone_layers.py`](tests/test_microphone_layers.py)
  - [`tests/test_speech_recognizer_layers.py`](tests/test_speech_recognizer_layers.py)
  - [`tests/test_wake_word_controller.py`](tests/test_wake_word_controller.py)

---

### 2.8. Синтез речи (TTS / Voice Output)
- **Назначение:** Локальный голосовой вывод через Piper TTS на CPU, асинхронный поток `jarvis-tts-worker`, очередь воспроизведения, двухуровневый кэш (готовые WAV-ассеты + LRU-кэш генераций), подписка на `speech.requested`.
- **Исходный код:**
  - Сервис TTS: [`voice/tts/service.py`](voice/tts/service.py)
  - Интерфейс движка: [`voice/tts/engine.py`](voice/tts/engine.py)
  - Движок Piper: [`voice/tts/engines/piper.py`](voice/tts/engines/piper.py)
  - Профили голосов: [`voice/tts/voice_manager.py`](voice/tts/voice_manager.py)
  - Аудио-ассеты и кэш: [`voice/tts/asset_manager.py`](voice/tts/asset_manager.py)
  - Воспроизведение звука: [`voice/tts/audio_player.py`](voice/tts/audio_player.py)
  - Очистка текста: [`voice/tts/text.py`](voice/tts/text.py)
  - Метрики: [`voice/tts/metrics.py`](voice/tts/metrics.py)
- **Тесты:**
  - [`tests/test_tts_service.py`](tests/test_tts_service.py)
  - [`tests/test_tts_architecture_components.py`](tests/test_tts_architecture_components.py)

---

### 2.9. Шуточные реакции (RoflService)
- **Назначение:** Вероятностные рофл-ответы при запуске приложений, прямых командах и системных событиях.
- **Исходный код:** [`services/rofl_service.py`](services/rofl_service.py)
- **Тесты:** [`tests/test_rofl_service.py`](tests/test_rofl_service.py)

---

### 2.10. Автоматическое обновление приложения (Update System)
- **Назначение:** Проверка релизов на GitHub, безопасное скачивание архива, staging, создание резервной копии, вызов отдельного процесса updater, откат при сбое.
- **Исходный код:**
  - Проверка релизов: [`services/update_checker.py`](services/update_checker.py)
  - Загрузчик: [`services/update_downloader.py`](services/update_downloader.py)
  - Установщик: [`services/update_installer.py`](services/update_installer.py)
  - Бэкап: [`services/update_backup.py`](services/update_backup.py)
  - Откат: [`services/update_rollback.py`](services/update_rollback.py)
  - Перезапуск: [`services/update_relauncher.py`](services/update_relauncher.py)
  - Политика установки: [`services/update_install_policy.py`](services/update_install_policy.py)
  - Процесс updater: [`start/updater.py`](start/updater.py)
- **Тесты:**
  - [`tests/test_update_checker_fallback.py`](tests/test_update_checker_fallback.py)
  - [`tests/unit/test_update_*.py`](tests/unit/)
  - [`tests/integration/test_update_*.py`](tests/integration/)

---

### 2.11. Графический интерфейс Tauri v2 (UI) и API Gateway
- **Назначение:** Целевой современный UI на Tauri v2 + React/Vite, связанный с ядром через FastAPI HTTP API и WebSocket Gateway (`GatewayService`).
- **Исходный код:**
  - API & WebSocket шлюз: [`services/gateway_service.py`](services/gateway_service.py)
  - React интерфейс: [`ui/src/`](ui/src/)
  - Tauri v2 конфигурация: [`ui/src-tauri/`](ui/src-tauri/)
  - Архивный PySide6 интерфейс: [`ui_archive/`](ui_archive/)
- **Тесты:**
  - [`tests/test_gateway_service.py`](tests/test_gateway_service.py)
  - [`tests/test_ui_smoke.py`](tests/test_ui_smoke.py)
  - [`tests/test_review_fixes.py`](tests/test_review_fixes.py)
