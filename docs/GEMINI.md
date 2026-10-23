# Контекст проекта JARVIS

**Проект:** Jarvis - локальный настольный ассистент для Windows 11
**Стек:** Python 3.12+, PySide6, Ollama, faster-whisper, Vosk, Piper TTS
**Репозиторий:** `jelr1k/localjarvisgolos`, ветка `osnova`
**Версия:** 0.1.3

## Архитектура

```text
Пользователь → UI / голосовой ввод → Command Router
  ├── простая команда → прямой Tool
  └── сложная команда → LLM (Ollama) → Tool Calling (до 5 раундов) → ToolExecutor → permissions/sandbox → действие → ответ
```

### Структура каталогов

- `core/` - lifecycle приложения, `ConfigManager`, `EventBus`, `WorkspaceIndex`, `AliasManager`, `OllamaManager`, пути
- `llm/` - абстрактный `LLMProvider` + `OllamaProvider` (потоковая генерация через `requests`)
- `services/` - `ChatService` (центральный), `CommandRouter`, `RoflService`, система обновлений (checker, downloader, installer, backup, rollback)
- `tools/` - `ToolRegistry`, `ToolExecutor`, файловые операции (`files.py`), управление приложениями (`applications.py`, `application_closer.py`), пути (`paths.py`)
- `security/` - `Sandbox` (файловая песочница, `resolve()` + `is_relative_to`), `PermissionManager`, `Validator`
- `voice/` - `SpeechRecognizer` (faster-whisper), `WakeWord` (Vosk), `CommandNormalizer`, `VoiceController`, `Microphone`, `Devices`
- `voice/tts/` - Piper TTS: `TTSService` (очередь + worker-поток), `PiperEngine`, `AssetManager` (скачивание моделей), `VoiceManager`
- `presentation/` - контроллеры между backend и PySide6 UI
- `ui/` - страницы: Чат, Генерация/статистика, Настройки, Алиасы, Workspace, Инструменты, Ollama
- `start/` - `bootstrap.py` (точка входа), `main.py`, `updater.py`
- `config/` - `settings.json` (шаблон), `models.json`, `requirements.txt`
- `tests/` - 40+ тестовых файлов (unit, integration, regression, smoke)
- `docs/` - структурированная документация (requirements, architecture, features, status, installation, issues, reviews)

### Ключевые компоненты

**EventBus** (`core/events.py`) - межкомпонентное общение. Backend не знает про PySide6.

**ConfigManager** (`core/config_manager.py`) - deep merge шаблона с пользовательскими настройками из `%APPDATA%\Jarvis\settings.json`. Атомарная запись через temp + `os.replace`.

**WorkspaceIndex** (`core/workspace_index.py`) - живой индекс `workspace/` с fuzzy search, нормализацией кириллицы, алиасами.

**Sandbox** (`security/sandbox.py`) - все файловые пути резолвятся через `Path.resolve()` и проверяются `is_relative_to(workspace_root)`. Выход за workspace невозможен.

**ToolExecutor** (`tools/executor.py`) - единая точка выполнения инструментов. Двойная проверка разрешений: при формировании набора tools для запроса + перед выполнением.

**ChatService** (`services/chat_service.py`) - центральный сервис: Command Router → если не распознано → LLM с ограниченным набором tools → до 5 раундов tool calling.

## Правила работы

### Безопасность

- Файловые операции ТОЛЬКО через sandbox
- Нет произвольного shell exec (`cmd.exe`, PowerShell, `shell=True`) - сознательное архитектурное ограничение
- Новые инструменты обязаны проходить через `ToolExecutor` и `PermissionManager`
- Деструктивные операции (удаление, перезапись, перемещение) требуют подтверждения пользователя

### Архитектурные принципы

- Не создавать дублирующих механизмов (второй sandbox, второй executor и т.д.)
- Минимальные изменения: не переписывать большие файлы целиком ради мелкой правки
- Перед изменением изучить существующую реализацию, тесты и связанные компоненты
- Код - главный источник истины. Если документация противоречит коду, ориентироваться на код
- Backend не должен зависеть от PySide6 напрямую - связь через EventBus

### Git

- Рабочая ветка: `osnova`. Не переключаться на `main` и не создавать новые ветки без запроса
- Не делать merge/PR в `main` без явного запроса
- Коммиты: `fix: ...`, `feat: ...`, `docs: ...` - конкретное описание, не "update" или "changes"

### Порядок перед изменениями

```text
1. README.md → docs/AI_WORK_GUIDE.md → PROJECT_SPEC.md
2. Структура каталогов
3. Связанные исходные файлы
4. Тесты
5. Только потом менять код
```

### Модули по задачам

- Ollama → `core/ollama_manager.py`, `llm/ollama.py`
- Приложения → `tools/applications.py`, `tools/application_closer.py`
- Файлы/пути → `tools/files.py`, `tools/paths.py`, `security/sandbox.py`
- Маршрутизация → `services/command_router.py`, `services/chat_service.py`
- Голос STT → `voice/speech_recognizer.py`, `voice/controller.py`, `voice/command_normalizer.py`
- Wake word → `voice/wake_word.py`
- TTS → `voice/tts/service.py`, `voice/tts/engines/piper.py`
- Настройки → `core/config_manager.py`, `config/settings.json`
- Алиасы → `core/alias_manager.py`
- UI → `ui/`, `presentation/`

## Известные проблемы и заметки

- `docs/` синхронизированы с кодовой базой ветки `osnova` (wake word, TTS, безопасный shutdown и подтверждение close_application реализованы).
- `command_router.py` (32KB) перегружен - кандидат на рефакторинг в будущем, но работает стабильно и покрыт тестами.
- `rofl_service.py` (27KB) - шуточные фразы захардкожены, стоит вынести в data-файл при развитии сервиса.
- `_PENDING_LAUNCH_CHOICES` в `tools/applications.py` — глобальное состояние выбора приложений.

## Что НЕ делать

- Не заменять стек (PySide6 → Electron, Ollama → другой сервер)
- Не отключать sandbox
- Не давать инструментам shell-доступ
- Не встраивать абсолютные пути Windows
- Не хранить пользовательские настройки в исходниках
- Не считать документацию более правильной, чем код
