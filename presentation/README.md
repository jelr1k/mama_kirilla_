# Слой Presentation (Контроллеры)

Слой `presentation` выступает мостом (адаптером) между UI (PySide6) и ядром/сервисами Jarvis. 

Backend приложения спроектирован так, чтобы не знать о существовании графического интерфейса. Общение между ними происходит через **EventBus** и паттерн **Controller**:
- Сервисы шлют события в шину событий (`EventBus`)
- Контроллеры слушают `EventBus` и транслируют события в сигналы Qt (`Signal`) для виджетов
- UI вызывает методы контроллеров, а те дергают backend-сервисы или запускают асинхронные задачи через `TaskRunner`

---

## Обзор контроллеров

| Файл | Класс | Назначение |
| :--- | :--- | :--- |
| [`alias_controller.py`](presentation/alias_controller.py) | [`AliasController`](presentation/alias_controller.py#L7) | Управление голосовыми и текстовыми алиасами (псевдонимами) |
| [`application_controller.py`](presentation/application_controller.py) | [`ApplicationController`](presentation/application_controller.py#L6) | Жизненный цикл приложения (запуск, выключение, применение настроек) |
| [`chat_controller.py`](presentation/chat_controller.py) | [`ChatController`](presentation/chat_controller.py#L6) | Управление чатом, стримингом ответов LLM, подтверждением вызова тулов и ROFL-ответами |
| [`dependency_controller.py`](presentation/dependency_controller.py) | [`DependencyController`](presentation/dependency_controller.py#L6) | Загрузка и проверка зависимостей моделей Whisper (STT) |
| [`ollama_controller.py`](presentation/ollama_controller.py) | [`OllamaController`](presentation/ollama_controller.py#L6) | Управление сервером Ollama (старт/стоп, загрузка/выгрузка моделей в память) |
| [`settings_controller.py`](presentation/settings_controller.py) | [`SettingsController`](presentation/settings_controller.py#L14) | Самый крупный контроллер: настройки, микрофоны, TTS/Whisper ассеты, автообновления и бэкапы |
| [`statistics_controller.py`](presentation/statistics_controller.py) | [`StatisticsController`](presentation/statistics_controller.py#L7) | Мониторинг системных ресурсов (CPU, RAM) и метрик Whisper / Ollama |
| [`tools_controller.py`](presentation/tools_controller.py) | [`ToolsController`](presentation/tools_controller.py#L6) | Включение/отключение инструментов и разрешений песочницы |
| [`voice_controller.py`](presentation/voice_controller.py) | [`VoiceController`](presentation/voice_controller.py#L6) | Запись голоса и распознавание речи через Whisper |
| [`wake_word_controller.py`](presentation/wake_word_controller.py) | [`WakeWordController`](presentation/wake_word_controller.py#L6) | Фоновое отслеживание слова активации (Vosk) |
| [`workspace_controller.py`](presentation/workspace_controller.py) | [`WorkspaceController`](presentation/workspace_controller.py#L8) | Индексация рабочей директории (workspace), добавление файлов и привязка алиасов к файлам |

---

## Детальное описание компонентов

### 1. [`AliasController`](presentation/alias_controller.py)
Работает с менеджером алиасов [`AliasManager`](core/alias_manager.py).
- **Сигналы**:
  - `changed`: срабатывает при изменении или удалении алиасов.
- **Методы**:
  - `list_objects()`: возвращает список всех сущностей, у которых есть алиасы.
  - `get_aliases(category, target)` / `default_aliases(category, target)`: чтение пользовательских и дефолтных алиасов.
  - `set_aliases(category, target, aliases)`: установка списка псевдонимов с отправкой сигнала `changed`.
  - `remove_object(category, target)`: удаление кастомных настроек алиаса.

---

### 2. [`ApplicationController`](presentation/application_controller.py)
Связывает UI с главным классом приложения.
- **Подписки**: `application.settings_applied`
- **Сигналы**:
  - `settings_applied(str, str)`: сообщает UI об успешном применении настроек.
- **Методы**:
  - `apply_settings()`: триггерит переприменение конфигурации в сервисах.
  - `start()` / `shutdown()`: управление жизненным циклом.
  - `config_value(key, default)`: быстрое получение значения из конфига.
  - `close()`: отписка от шины событий.

---

### 3. [`ChatController`](presentation/chat_controller.py)
Ключевой контроллер для диалогового интерфейса.
- **Подписки**: `chat.chunk`, `chat.generation_started`, `chat.generation_finished`, `chat.direct_response`, `chat.error`, `chat.rofl_response`, `chat.confirmation_requested`, `chat.tool_confirmation_requested`.
- **Сигналы**:
  - `chunk_received(object)`: порция стримингового текста от LLM.
  - `generation_started(object)` / `generation_finished(object)`: границы генерации.
  - `direct_response(str)`: прямой ответ (без LLM, например от CommandRouter).
  - `rofl_response(str)`: пасхалки и подколы Jarvis.
  - `confirmation_requested(str, object)`: запрос подтверждения деструктивного действия у пользователя.
  - `error(str)`: ошибка генерации или выполнения команды.
- **Методы**:
  - `send(text, thinking=False)`: отправка сообщения в [`ChatService`](services/chat_service.py).
  - `refresh_tools()`: обновление списка доступных для LLM тулов.
  - `command_catalog()`: каталог поддерживаемых прямых команд.
  - `set_ui_actions(actions)`: проброс UI-хэндлеров (например, открытие окон).

---

### 4. [`DependencyController`](presentation/dependency_controller.py)
Управляет загрузкой внешних моделей Whisper для распознавания речи.
- **Подписки**: `dependency.progress`, `dependency.state_changed`, `dependency.finished`.
- **Сигналы**:
  - `progress(str, int, int, float)`: статус скачивания весов (имя, скачано, всего, процент).
  - `state_changed(str, str)`: изменение состояния загрузки.
  - `finished(str, bool, str)`: завершение скачивания с флагом успеха.
- **Методы**: `whisper_status(model_name)`, `ensure_whisper_model(model_name)`, `whisper_download_size(model_name)`, `cancel()`.

---

### 5. [`OllamaController`](presentation/ollama_controller.py)
Асинхронный контроллер локального LLM-сервера Ollama. Все тяжелые операции выполняются через пул потоков `TaskRunner`.
- **Сигналы**:
  - `operation_finished(str, object)`: завершение фоновой операции (`start`, `stop`, `load`, `unload`, `status`).
  - `status_changed(object)`: обновление текущего состояния сервера и загруженных моделей.
- **Методы**:
  - `run(action, model=None)`: отправка задачи в фоновый воркер.
  - `model_status(model)`: проверка, загружена ли конкретная модель в память.
  - `started_by_jarvis()`: флаг, был ли процесс Ollama запущен самим Jarvis.

---

### 6. [`SettingsController`](presentation/settings_controller.py)
Центральный пульт управления настройками приложения.
- **Функционал**:
  - Чтение, валидация и сохранение конфигурации (`settings.json`).
  - Обнаружение и тестирование микрофонов.
  - Загрузка моделей голоса Piper TTS и моделей Whisper.
  - Полный цикл автообновлений: проверка обновлений на GitHub, скачивание релиза, проверка контрольных сумм / целостности, создание резервной копии (`backup`) и перезапуск через `UpdateRelauncher`.
- **Сигналы**: огромный набор сигналов прогресса для UI (`microphones_refreshed`, `tts_asset_finished`, `update_download_progress`, `update_restart_requested` и др.).

---

### 7. [`StatisticsController`](presentation/statistics_controller.py)
Сбор телеметрии и отображение нагрузки на вкладке статистики.
- **Подписки**: `voice.whisper_stats`
- **Сигналы**:
  - `system_status(object)`: снимок потребления CPU (%), RAM (всего / занято / процент) и статуса модели.
  - `whisper_updated(object)`: метрики времени распознавания голоса.
- **Методы**:
  - `update_system_status(model)`: асинхронный замер нагрузки через `psutil`.

---

### 8. [`ToolsController`](presentation/tools_controller.py)
Управление реестром инструментов ([`ToolRegistry`](tools/executor.py)) и правами доступа ([`PermissionManager`](security/permissions.py)).
- **Сигналы**:
  - `changed`: испускается при переключении активности инструмента.
- **Методы**:
  - `tools()`: список зарегистрированных инструментов.
  - `is_enabled(name)` / `set_enabled(name, enabled)`: чтение и переключение прав на выполнение конкретного тула.
  - `workspace`: путь к рабочей директории.

---

### 9. [`VoiceController`](presentation/voice_controller.py)
Контроллер голосового ввода через Whisper.
- **Подписки**: `voice.listening_changed`, `voice.transcribing_changed`, `voice.transcript_ready`, `voice.error`.
- **Сигналы**:
  - `listening_changed(bool)`: состояние записи с микрофона.
  - `transcribing_changed(bool)`: индикатор того, что модель расшифровывает аудио.
  - `transcript_ready(str)`: готовый распознанный текст.
  - `error(str)`: ошибка аудиопотока или модели.
- **Методы**: `start()`, `stop()`, `apply_config(config)`.

---

### 10. [`WakeWordController`](presentation/wake_word_controller.py)
Контроллер постоянного прослушивания ключевого слова активации ("Джарвис") на базе легковесной Vosk.
- **Подписки**: `wake_word.detected`, `wake_word.recognized`, `wake_word.listening_changed`, `wake_word.status`, `wake_word.error`.
- **Сигналы**:
  - `detected(str)` / `recognized(str)`: обнаружение триггер-фразы.
  - `listening_changed(bool)`: активность фонового потока.
- **Методы**: `start()`, `stop()`, `restart()`, `apply_config(config)`, `is_running()`.

---

### 11. [`WorkspaceController`](presentation/workspace_controller.py)
Управление файловым пространством пользователя.
- Работает через [`WorkspaceViewModel`](core/workspace_view_model.py).
- **Методы**:
  - `refresh()`: пересканирование директории `workspace/` и обновление индексов.
  - `add_file(source)`: безопасное добавление файла в изолированную рабочую область.
  - `set_aliases(entry, aliases)`: назначение алиасов файлам в песочнице.
