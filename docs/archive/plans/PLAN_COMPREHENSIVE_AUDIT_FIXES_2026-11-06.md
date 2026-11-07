# План реализации исправлений по итогам комплексного аудита

## Описание цели
Привести архитектуру JARVIS (Kirieshka v2) на ветке `osnova` к состоянию переносимого, безопасного, надежного и автономно развертываемого десктопного приложения для Windows 10/11 без зависимости от окружения разработчика.

Детальный отчет об аудите сохранен в [`docs/reviews/DEPLOYABILITY_SECURITY_ARCHITECTURE_AUDIT.md`](file:///d:/putin/kirieshkav2/mama_kirilla_/docs/reviews/DEPLOYABILITY_SECURITY_ARCHITECTURE_AUDIT.md).

---

## Требуется согласование с пользователем (User Review Required)

> [!IMPORTANT]
> **1. Отвязка бэкенда от PySide6 (ARCH-01):**
> Для облегчения бэкенда и создания легкого дистрибутива предлагается полностью убрать `QApplication` из `start/main.py`, а системный трей реализовать нативно в Tauri v2 (Rust). Классический аварийный GUI `ui_archive` останется доступен только при явном запуске `start_legacy.bat` со своим отдельным скриптом.

> [!WARNING]
> **2. Сессионный токен Gateway API (SEC-01):**
> Все REST-ручки и WebSocket потребуют заголовок `Authorization: Bearer <session_token>`. Токен будет генерироваться бэкендом при старте и передаваться в Tauri UI при инициализации. Это полностью защитит от несанкционированного управления из браузера (CSRF), но сделает невозможным дергать API голым `curl` без передачи токена.

> [!NOTE]
> **3. Разделение путей на Roaming и Local (PORT-01):**
> Модели Vosk, Whisper, Piper TTS и логи будут перенесены из `%APPDATA%\Jarvis` в `%LOCALAPPDATA%\Jarvis`. При первом запуске будет выполнен автоматический перенос существующих файлов, чтобы не скачивать модели заново.

---

## Предлагаемые изменения по этапам

### Этап 1: Критическая безопасность (P0)

#### [MODIFY] `services/gateway/deps.py` & `services/gateway_service.py`
- Внедрить генерацию криптографического токена сессии `secrets.token_urlsafe(32)`.
- Реализовать FastAPI dependency `verify_session_token` для проверки `Authorization: Bearer <token>`.
- Реализовать проверку токена в query-параметре при подключении к WebSocket (`/ws?token=...`).

#### [MODIFY] `ui/src/services/api.js` & `ui/src/services/assistantSocket.js`
- Добавить передачу сессионного токена в заголовки HTTP-запросов и WebSocket URL.

#### [MODIFY] `tools/applications.py`
- Заблокировать запуск исполняемых расширений (`.exe`, `.bat`, `.cmd`, `.vbs`, `.ps1`) из каталога Workspace через `launch_application` без явного подтверждения пользователя.

---

### Этап 2: Переносимость и сохранение данных (P1)

#### [MODIFY] `core/app_paths.py`
- Ввести раздельные константы:
  - `LOCAL_DATA_DIR = Path(os.environ.get("LOCALAPPDATA")) / "Jarvis"`
  - `LOG_DIR = LOCAL_DATA_DIR / "logs"`
  - `MODELS_DIR = LOCAL_DATA_DIR / "models"`
  - `TTS_CACHE_DIR = LOCAL_DATA_DIR / "tts"`
  - `WORKSPACE_DIR` перенести в каталог профиля пользователя по умолчанию с поддержкой переопределения.
- Реализовать мягкую миграцию старых каталогов из `%APPDATA%`.

#### [MODIFY] `core/config_manager.py`
- При обнаружении невалидного JSON в `settings.json` создавать аварийную копию `settings.json.corrupted_<timestamp>` перед сбросом к значениям по умолчанию.

---

### Этап 3: Отвязка от PySide6 и нативный трей (P1)

#### [MODIFY] `start/main.py`
- Удалить импорт `PySide6.QtWidgets.QApplication` из headless-режима.
- Запуск headless-бэкенда перевести на чистый цикл `asyncio / threading` без Qt event loop.

#### [MODIFY] `ui/src-tauri/src/lib.rs` & `ui/src-tauri/Cargo.toml`
- Подключить модуль `tauri::tray::TrayIconBuilder` в Rust для создания нативного системного трея Windows.
- Реализовать меню трея: "Показать окно", "Статус", "Выход".

---

### Этап 4: Развертывание и упаковка (DEPLOY-01)

#### [MODIFY] `config/requirements.txt`
- Вынести `pytest` и `pytest-cov` в `config/requirements-dev.txt`.
- Оставить в `requirements.txt` только чистые runtime-зависимости.

#### [MODIFY] `ui/src-tauri/tauri.conf.json`
- Настроить конфигурацию `bundle` для создания автономного инсталлятора (NSIS / MSI).
- Настроить sidecar для запуска предсобранного Python-рантайма.

---

## План верификации

### Автоматические тесты
```bash
# 1. Запуск полного набора существующих unit и integration тестов
pytest -q

# 2. Запуск новых тестов безопасности API и токенов
pytest tests/test_gateway_security.py -v

# 3. Запуск тестов песочницы и путей
pytest tests/test_start_and_paths_layers.py tests/test_security_sandbox.py -v
```

### Ручная верификация
1. Запуск бэкенда без прав администратора на чистой папке.
2. Проверка недоступности REST-эндпоинтов без заголовка авторизации (`curl -I http://127.0.0.1:8765/api/status` -> 401).
3. Проверка работы системного трея при закрытии и восстановлении окна Tauri.
