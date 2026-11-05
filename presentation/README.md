# Слой Presentation

Слой `presentation` исторически выступал мостом (адаптером) между десктопным интерфейсом и ядром/сервисами Jarvis.

## Текущая архитектура (Tauri v2)

В современном стеке приложения графический интерфейс реализован на **Tauri v2 + React** (`ui/`). Общение с бэкендом происходит не через Qt-сигналы, а через **WebSocket & REST Gateway API** (`services/gateway/`).

Из слоя `presentation` в проде используется исключительно:
- [`tray_icon.py`](presentation/tray_icon.py) - управление иконкой в системном трее Windows, контекстным меню (развернуть UI, перезагрузить, открыть документацию, завершить работу).

---

## Легаси контроллеры (`presentation/legacy/`)

Контроллеры старого графического интерфейса PySide6 (архивированного в `ui_archive/`) изолированы в пакет [`presentation/legacy/`](presentation/legacy/):

> [!NOTE]
> При прямом импорте из `presentation.legacy` или через shim обратной совместимости в корне `presentation` генерируется `DeprecationWarning`.

| Файл | Класс | Назначение в старом GUI |
| :--- | :--- | :--- |
| [`alias_controller.py`](presentation/legacy/alias_controller.py) | `AliasController` | Управление голосовыми и текстовыми алиасами |
| [`application_controller.py`](presentation/legacy/application_controller.py) | `ApplicationController` | Жизненный цикл приложения (применение настроек, закрытие) |
| [`chat_controller.py`](presentation/legacy/chat_controller.py) | `ChatController` | Чат, стриминг ответов LLM, подтверждение тулов |
| [`dependency_controller.py`](presentation/legacy/dependency_controller.py) | `DependencyController` | Проверка и скачивание весов моделей Whisper |
| [`ollama_controller.py`](presentation/legacy/ollama_controller.py) | `OllamaController` | Статус, запуск/остановка и выгрузка моделей Ollama |
| [`protocols_controller.py`](presentation/legacy/protocols_controller.py) | `ProtocolsController` | Управление игровыми сценариями и протоколами Stark |
| [`settings_controller.py`](presentation/legacy/settings_controller.py) | `SettingsController` | Настройки аудио, STT/TTS, автообновлений |
| [`statistics_controller.py`](presentation/legacy/statistics_controller.py) | `StatisticsController` | Мониторинг CPU, RAM и телеметрии Whisper/Ollama |
| [`tools_controller.py`](presentation/legacy/tools_controller.py) | `ToolsController` | Управление доступом к инструментам песочницы |
| [`voice_controller.py`](presentation/legacy/voice_controller.py) | `VoiceController` | Голосовой ввод и распознавание речи Whisper |
| [`wake_word_controller.py`](presentation/legacy/wake_word_controller.py) | `WakeWordController` | Прослушивание ключевого слова активации Vosk |
| [`websites_controller.py`](presentation/legacy/websites_controller.py) | `WebsitesController` | Открытие и управление веб-ресурсами |
| [`workspace_controller.py`](presentation/legacy/workspace_controller.py) | `WorkspaceController` | Индексация рабочей директории |

---

## Обратная совместимость

Корневой пакет `presentation` сохраняет прозрачную обратную совместимость через `sys.meta_path` finder:
- Код, импортирующий `from presentation.<controller> import ...`, продолжает работать корректно, перенаправляясь в `presentation.legacy.<controller>` с выдачей `DeprecationWarning`.
