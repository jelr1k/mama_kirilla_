# Комплексный аудит кодовой базы и детальный план улучшений

> **Дата аудита:** 15 ноября 2026 г.  
> **Целевая кодовая база:** `mama_kirilla_-osnova` (ветка `osnova`)  
> **Статус аудита:** Аналитический (Read-Only), без изменения исходных файлов репозитория  
> **Базовое состояние тестов:**  
> - Python pytest: **707 тестов** (704 passed, 3 skipped, 12 warnings за 17.32с)  
> - Frontend Vitest: **77 тестов** (12 suites passed, 77 passed)

---

## 1. Executive Summary (Общий обзор системы и архитектуры)

### 1.1. Назначение и концепция системы
**Ассистент** — это персональный локальный десктопный ассистент для Windows 11, спроектированный по парадигме **Zero-LLM Core**. Вся базовая автоматизация, распознавание команд, запуск приложений, системный мониторинг, мультимедиа-контроль, выполнение сценариев (протоколов) и синтез речи работают **на 100% локально, автономно и детерминированно** без обязательного наличия нейросетей или подключения к интернету.

Интеграция с локальной языковой моделью (Ollama) спроектирована исключительно как изолированный опциональный режим «поболтать» (свободный текстовый диалог), не влияющий на базовые сценарии управления компьютером.

### 1.2. Архитектурная топология системы

```
+----------------------------------------------------------------------------------------------------+
|                                    ПОЛЬЗОВАТЕЛЬСКИЙ ВВОД                                           |
|       Голос (Микрофон)         Горячие клавиши        Клавиатура / Мышь         Telegram Bot       |
+--------------+------------------------+----------------------+-----------------------+-------------+
               |                        |                      |                       |
               v                        |                      v                       v
+-----------------------------+         |       +-----------------------------+ +--------------------+
|       ГОЛОСОВОЙ ПАКЕТ       |         |       |       ТАУРИ v2 + REACT      | |    МОДУЛЬ ТГ       |
| Vosk (Wake-Word)             |         |       |      ui/src/App.jsx         | | modules/telegram/  |
| faster-whisper (STT)        |         |       |  Dynamic Island (IslandApp) | | (Удаленный статус, |
| Piper (Локальный TTS)       |         |       |    REST / WebSocket Client  | |  скриншоты, команды|
+--------------+--------------+         |       +--------------+--------------+ +---------+----------+
               |                        |                      | Bearer Token (43 chars)  |
               v                        v                      v                          v
+----------------------------------------------------------------------------------------------------+
|                   ШЛЮЗ СВЯЗИ И СЕТЕВОЙ СЛОЙ (services/gateway_service.py)                         |
|   FastAPI REST API (127.0.0.1:8765)  |  WebSocket Hub (services/gateway/hub.py)                    |
|   Маршрутизаторы: /api/chat, /api/system, /api/apps, /api/protocols, /api/websites, /api/settings  |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                        ЯДРО ПРИЛОЖЕНИЯ (core/application.py: JarvisApplication)                    |
|                                                                                                    |
|  +-------------------------+  +--------------------------+  +-----------------------------------+  |
|  |       EventBus          |  |       TaskRunner         |  |        Менеджеры состояния        |  |
|  |    (core/events.py)     |  |   (core/task_runner.py)  |  | ConfigManager, AliasManager,      |  |
|  | In-process thread-safe  |  | ThreadPoolExecutor       |  | AppIndexer, WebsiteManager,       |  |
|  | publish/subscribe hub   |  | (4 фоновых воркера)      |  | SteamManager, VpnManager          |  |
|  +------------+------------+  +--------------------------+  +-----------------------------------+  |
+---------------|------------------------------------------------------------------------------------+
                |
                +---------------------------------+----------------------------------+
                v                                 v                                  v
+-------------------------------+ +--------------------------------+ +-------------------------------+
|     МАРШРУТИЗАТОР КОМАНД      | |      СЦЕНАРИИ И ПРОТОКОЛЫ      | |      ИЗОЛИРОВАННЫЙ ЧАТ        |
|  services/command_router.py   | |  services/stark_protocols.py   | |   services/chat_service.py    |
|  - Детерминированные regex    | |  - "Режим игры", "Кино",       | |  - Опциональная Ollama        |
|  - services/command_catalog.py| |    "Работа", "Разгон"          | |  - Стриминг токенов           |
|  - 100% оффлайн роутинг       | |  - Запуск/закрытие процессов   | |  - Изолирован от ядра         |
+---------------+---------------+ +---------------+----------------+ +-------------------------------+
                |                                 |
                +---------------------------------+
                v
+----------------------------------------------------------------------------------------------------+
|                    СИСТЕМНЫЕ ИНСТРУМЕНТЫ И ИСПОЛНИТЕЛЬ (tools/, security/)                         |
|  - tools/executor.py & PermissionManager: Проверка прав доступа и песочницы                        |
|  - security/sandbox.py: Строгая изоляция файловой системы (WORKSPACE_DIR)                         |
|  - tools/system_actions.py: Скриншоты, очистка корзины, блокировка, аптайм                         |
|  - tools/media_control.py: Windows Core Audio (IAudioEndpointVolume - мастер-громкость)           |
|  - tools/mouse_driver.py: Драйвер Fury / ZET Gaming                                                |
|  - core/steam_manager.py: Парсинг VDF, запуск steam://rungameid/                                   |
|  - core/vpn/: Zapret (winws), Happ, FlClash (ручной запуск по требованию)                          |
+----------------------------------------------------------------------------------------------------+
```

### 1.3. Оценка общего состояния здоровья кодовой базы
Система обладает зрелой компонентной архитектурой с четким разделением фронтенда (Tauri v2 + React) и бэкенда (Python 3), развитым каталогом детерминированных команд, качественной реализацией синтеза речи на базе Piper и высокой скоростью выполнения модульных тестов (17.3 секунд на 707 тестов).

Тем не менее, детальный сквозной аудит выявил ряд **критических дефектов, архитектурных нарушений и скрытых багов**:
1. **Эрозия принципа Zero-LLM Core**: Проникновение сетевых вызовов к Ollama HTTP API внутрь выполнения протоколов автоматизации (`stark_protocols.py:311-393`), фоновый автозапуск сервера Ollama при старте программы (`application.py:141, 156`), и дефолтный фоллбэк с исполнением инструментов через LLM (`config_manager.py:29`, `chat_service.py:129-160`).
2. **Нарушение стандартов синхронизации процессов**: Использование 7 слепых вызовов `time.sleep()` и жестко зашитых координат в драйвере мыши (`mouse_driver.py:126-172`), а также запуск и завершение процессов через неконтролируемые вызовы `os.startfile` и `proc.terminate()` без ожидания хэндлов WinAPI (`stark_protocols.py:82-120, 218, 244, 271`).
3. **Критические функциональные ошибки в проде**:
   - `NameError: name 're' is not defined` в `tools/system_actions.py:65` при попытке сделать скриншот с кастомным именем файла (скрывалось пустым ассертом в тестах).
   - `AttributeError: 'EventBus' object has no attribute 'publish'` в `core/website_manager.py:204`, крашащий сохранение сайтов/закладок.
   - Несоответствие схемы телеметрии в `modules/telegram/handlers.py:38-51`, из-за чего бот Telegram рапортует `RAM: 0.0 / 0.0 GB (0%)` и не выводит GPU.
   - Логическая инверсия миграции AppData в `core/app_paths.py:38, 47, 78-81`, навсегда блокирующая перенос пользовательских файлов из старой папки `Jarvis` в `Assistant`.
   - Полное удаление файла `errors.log` при каждом перезапуске приложения через `start/bootstrap.py:47-59`, уничтожающее историю крашей.
4. **Уязвимость обхода песочницы**: Эндпоинт шлюза `/api/apps/launch` (`services/gateway/routers/integrations.py:287-300`) вызывает запуск программ на хосте напрямую в обход `PermissionManager` и настроек `allow_outside_workspace`.
5. **Скрытое урезание прогона тестов**: Батник `tests/run_tests.bat:57` запускает только 19 файлов тестов из подкаталогов `tests\unit` и `tests\integration`, полностью игнорируя 66 файлов тестов в корне `tests/` (78% тестов не прогоняется разработчиком).

---

## 2. Аудит архитектурного соответствия AGENTS.md

| Правило AGENTS.md | Статус | Основные локации | Характер соблюдения / нарушения |
|---|---|---|---|
| **Zero-LLM Core** | ⚠️ **Нарушение** | `stark_protocols.py:311-393`<br>`config_manager.py:29`<br>`chat_service.py:129-160`<br>`application.py:141, 156` | Сценарии обращаются к HTTP API Ollama; роутер по умолчанию сбрасывает неопознанные команды на LLM с исполнением системных тулов; Ollama автостартует при запуске бэкенда. |
| **Синхронизация WinAPI vs Blind Sleeps** | ❌ **Нарушение** | `mouse_driver.py:126-172`<br>`stark_protocols.py:82-120, 218`<br>`updater.py:74, 135` | 7 слепых слипов в драйвере мыши; отсутствие `WaitForInputIdle` и `psutil.wait_procs` в протоколах; цикл опроса процесса в апдейтере. |
| **Динамический поиск путей (No Hardcode)** | ⚠️ **Нарушение** | `stark_protocols.py:134-190`<br>`paths.py:162-178` | Жестко прописаны пути к Opera GX, Discord, Antigravity и папке Downloads пользователя; обход файлов сканирует корень репозитория. |
| **Изоляция песочницы (Sandbox)** | ⚠️ **Нарушение** | `gateway/routers/integrations.py:287-300`<br>`stark_protocols.py:108` | Эндпоинт `/api/apps/launch` запускает произвольные исполняемые файлы мимо `PermissionManager`; фоллбэк `os.startfile(app_key)`. |
| **Кладбище запрещенных фич** | ✅ **Соблюдено** | `tools/media_control.py`<br>`core/steam_manager.py`<br>`core/vpn/`<br>`tools/system_info.py` | Поканальный микшер отсутствует (только мастер-громкость); бэкапы сейвов отсутствуют; сторожи авто-VPN отсутствуют; алерты перегрева железа отсутствуют. |
| **Сохранность логов и errors.log** | ❌ **Нарушение** | `start/bootstrap.py:47-59` | При старте вызывается `_clear_previous_logs()`, удаляющий все файлы `*.log*` (включая `errors.log`), стирая диагностику падений. |
| **Интерфейс: Только Tauri v2 + React** | ⚠️ **Частично** | `presentation/tray_icon.py:10-14`<br>`presentation/legacy/`<br>`start/main.py:165`<br>`start.bat:12-16` | UI работает на Tauri v2, но 13 файлов контроллеров PySide6 не изолированы в `ui_archive/`, трей импортирует PySide, сохранены флаги запуска устаревшего GUI. |

### 2.1. Детальный разбор Zero-LLM Core
- **Суть требования:** «Вся логика, автоматизация, протоколы и роутер команд работают на 100% оффлайн и детерминированно. Приложение полностью автономно без нейросетей. Локальная модель — только как опциональный изолированный режим "поболтать"».
- **Фактическое состояние:**
  1. В `services/stark_protocols.py:311-393` метод `_try_generate_llm_response()` во время отработки сценария шлет синхронный HTTP GET на `http://localhost:11434/api/ps` и POST на `http://localhost:11434/api/chat` для генерации реплики ассистента («Ты только что активировал сценарий...»). Это вносит задержку от 0.5 до 3 секунд и делает поведение протокола зависимым от внешнего демона.
  2. В `core/config_manager.py:29` значение `"router_only_mode": False` выставлено по умолчанию. Если пользователь произносит фразу, которую регулярные выражения `CommandRouter` не распознали, `ChatService._process_message` (`services/chat_service.py:129-160`) передает запрос в Ollama, снабжая ее набором схем функций (`tools=ollama_tools(...)`) и объектом `ToolExecutor`. В итоге нейросеть получает возможность вызывать функции файловой системы и запуска программ в недетерминированном режиме.
  3. В `core/application.py:141, 156-160` при старте приложения задача `start_ollama` ставится в пул потоков автоматически, запуская процесс `ollama serve`.

### 2.2. Детальный разбор стандартов синхронизации процессов
- **Суть требования:** «Протоколы: Никаких слепых `time.sleep()` для синхронизации с окнами. Только проверка хэндлов через WinAPI, ожидание процессов и отчет пользователю через голос (Piper) / EventBus».
- **Фактическое состояние:**
  1. В `tools/mouse_driver.py:126-172` реализована жесткая цепочка из 7 слепых пауз: `time.sleep(0.2)`, `time.sleep(0.15)`, `time.sleep(0.04)`, `time.sleep(0.06)`, `time.sleep(0.04)`, `time.sleep(0.02)`, `time.sleep(0.2)`. В совокупности с хардкодом координат `BUTTON_APPLY_CLIENT_X = 648`, `BUTTON_APPLY_CLIENT_Y = 512` (и в другой ветке `192, 520`), драйвер гарантированно ломается при изменении DPI масштабирования экрана Windows.
  2. В `services/stark_protocols.py:82-120` запуск приложений производится через неблокирующий `os.startfile(str(path))`. Сразу же возвращается `(True, "запущено")` без проверки создания окна и без вызова `WaitForInputIdle`.
  3. При закрытии процессов (`services/stark_protocols.py:218, 244, 271`) вызывается `proc.terminate()` в цикле без последующего ожидания `psutil.wait_procs()`. Если сценарий сначала закрывает программы, а затем запускает новые, возникает конфликт блокировок файлов и графических ресурсов.

### 2.3. Детальный разбор структуры логов и сохранности ошибок
- **Суть требования:** «Логи: Структуру `core/logging_config.py` и файл `errors.log` не трогать без конкретной аварии».
- **Фактическое состояние:**
  - Сама структура `core/logging_config.py` сконфигурирована корректно: ошибки уровня `ERROR` дублируются в `errors.log`, а подсистемы пишут в отдельные файлы (`jarvis.log`, `commands.log`, `voice.log`).
  - Однако в `start/bootstrap.py:47-59` функция `_clear_previous_logs()` при запуске программы ищет все файлы `LOG_DIR.glob("*.log*")` и производит `path.unlink()`. Это приводит к тому, что при перезапуске ассистента после сбоя файл `errors.log` полностью затирается.

### 2.4. Детальный разбор кладбища запрещенных фич
Аудит подтвердил строгое и бескомпромиссное соблюдение запретов:
1. **Поканальный микшер звука**: Отсутствует. В `tools/media_control.py:51-182` и роутере управление звуком реализовано строго через интерфейс Windows Core Audio `IAudioEndpointVolume` (мастер-громкость конечной точки вывода звука и общий Mute). Никаких обращений к `IAudioSessionManager` и регулировки звука отдельных процессов в коде нет.
2. **Бэкап сохранений игр**: Отсутствует. Класс `SteamManager` (`core/steam_manager.py`) выполняет только парсинг VDF-манифестов для построения списка игр и запуск по URI `steam://rungameid/<id>`.
3. **Автовосстановление VPN и сторожевые таймеры**: Отсутствует. Все компоненты в `core/vpn/` (`zapret_controller.py`, `discovery.py`, `uia_driver.py` для клиентов Happ и FlClash) являются пассивными исполнителями, запускаемыми строго по явному вызову пользователя. Фоновые демоны перезапуска отсутствуют.
4. **Фоновые алерты и мониторинг перегрева железа**: Отсутствует. В `tools/system_info.py:75-132` опрос параметров системы происходит исключительно on-demand при запросе статуса.

---

## 3. Комплексный аудит компонентов кодовой базы

### 3.1. Ядро приложения (Backend Core)
- `core/application.py`:
  - `JarvisApplication` служит главным координатором. Инициализация подсистем разделена четко.
  - **Проблема:** Строки 141, 156-160 запускают `self.ollama_manager.start()` безусловно в фоновом пуле при старте приложения, нарушая автономность Zero-LLM Core.
- `core/events.py`:
  - `EventBus` обеспечивает потокобезопасную доставку событий через блокировку `threading.Lock()`.
  - **Проблема:** Метод отправки событий называется `emit(event, data)`. В классе отсутствует алиас `publish()`, что приводит к падению в смежных сервисах.
- `core/task_runner.py`:
  - Базируется на `ThreadPoolExecutor(max_workers=4)`.
  - **Риск истощения пула (Starvation):** 4 потока легко блокируются долгими операциями: распознавание Whisper STT на процессоре (1 поток), генерация ответа Ollama (1 поток), ожидание подтверждения действия в чате с таймаутом 60с (`chat_service.py:368`, 1 поток), запуск сервера Ollama (1 поток). В этот момент выполнение быстрых задач (команды роутера, проверки статуса) полностью парализуется.
- `core/config_manager.py` и `core/alias_manager.py`:
  - Сохранение настроек (`config_manager.py:169-171`) и псевдонимов (`alias_manager.py:242-244`) использует статические пути временных файлов:
    `temp_path = self.path.with_suffix(self.path.suffix + ".tmp")`.
  - **Гонка записи:** При параллельном обращении из нескольких потоков (например, одновременное изменение настроек через веб-интерфейс и роутер) возникает коллизия `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process`, либо повреждение JSON файла при вызове `replace()`.
- `core/app_paths.py`:
  - Содержит критическую логическую инверсию в строках 38, 47, 78-81:
    ```python
    LOCAL_DATA_DIR = _PRIMARY_LOCAL if (_PRIMARY_LOCAL.exists() or not _LEGACY_LOCAL.exists()) else _LEGACY_LOCAL
    APP_DATA_DIR = _PRIMARY_ROAMING if (_PRIMARY_ROAMING.exists() or not _LEGACY_ROAMING.exists()) else _LEGACY_ROAMING
    ...
    if _LEGACY_ROAMING.is_dir() and APP_DATA_DIR == _PRIMARY_ROAMING:
        _migrate_legacy_files(_LEGACY_ROAMING, APP_DATA_DIR)
    ```
    Если существует папка `Jarvis`, а `Assistant` еще не создана, переменная `APP_DATA_DIR` инициализируется значением `_LEGACY_ROAMING`. Условие `APP_DATA_DIR == _PRIMARY_ROAMING` становится ложным, и миграция никогда не запускается. Приложение навсегда остается привязано к устаревшей папке.
- `core/website_manager.py`:
  - Строка 204: `self.event_bus.publish("websites.updated", {"count": len(self._websites)})`.
  - Вызывает немедленный `AttributeError: 'EventBus' object has no attribute 'publish'`, перехватываемый `except Exception:` со спамом в лог `failed_to_save_websites`.

### 3.2. Сервисы и протоколы (Services & Protocols)
- `services/command_router.py`:
  - Чистая, высокоэффективная детерминированная маршрутизация на регулярных выражениях. Поддерживает псевдонимы, нормализацию числительных и нечеткий поиск. Полностью соответствует требованиям.
- `services/stark_protocols.py`:
  - Реализует игровые и рабочие профили.
  - Содержит сетевые HTTP-запросы к Ollama (`line 311-393`), жестко прописанные пути к файлам (`line 134-190`), отсутствие проверки завершения процессов при вызове `proc.terminate()` (`line 218, 244, 271`), а также небезопасный запуск произвольных строк через `os.startfile(app_key)` (`line 108`).
- `services/chat_service.py`:
  - Состояние стриминга (`_current_answer`, `_generation_future`) не защищено мьютексом. При одновременном получении сообщения из веб-сокета и голосового распознавания фрагменты текста склеиваются в переменную `self._current_answer += item.text` (`line 250`), приводя к каше в ответе.
- `services/statistics_service.py`:
  - Списки `self.history = []` и `self.whisper_history = []` (`line 6-7`) ничем не ограничены по размеру. При непрерывной работе ассистента в течение нескольких дней они вызывают медленную утечку оперативной памяти.

### 3.3. Системные инструменты и аппаратура (Tools & Hardware)
- `tools/system_actions.py`:
  - Строка 65: `safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base_name)`.
  - **Критический краш:** В модуле отсутствует `import re`. При вызове функции `take_screenshot(filename="screen.png")` возникает `NameError: name 're' is not defined`.
- `tools/mouse_driver.py`:
  - Реализует взаимодействие с мышью ZET Gaming / Fury.
  - Нарушает запрет слепых пауз (7 вызовов `time.sleep()`), использует хрупкие координаты кликов (`648, 512` и `192, 520`), которые съезжают при масштабировании экрана Windows.
- `tools/media_control.py`:
  - Управление мастер-звуком через Win32 COM интерфейсы (`IAudioEndpointVolume`).
  - Низкое покрытие тестами (35%) из-за отсутствия эмуляции vtable COM-интерфейсов в тестах.
- `tools/applications.py`:
  - Строка 33: Глобальная переменная `_PENDING_LAUNCH_CHOICES: list[Path] = []`.
  - Используется для выбора программы при неоднозначном вводе («запусти хром» -> «1 или 2»). Является глобальным состоянием модуля, подвержена гонкам при одновременных запросах из UI, голоса или Telegram.
- `tools/system_info.py`:
  - Собирает параметры CPU, RAM, GPU, аптайма.
  - Возвращает плоский словарь с ключами `ram_used_gb`, `ram_total_gb`, `ram_percent`, `gpu_name`. Не согласуется со структурой, ожидаемой Telegram-ботом.

### 3.4. Пользовательский интерфейс и шлюз связи (UI & Gateway)
- `ui/src/App.jsx`:
  - Современный интерфейс на React 19 с 9 вкладками.
  - Строка 214: При подтверждении завершения работы из UI вызывается `getCurrentWindow().destroy()`. В Tauri v2 это уничтожает только окно `"main"`. Если в этот момент создано или скрыто окно Dynamic Island (`"island"`), процесс Tauri не завершается и зависает в диспетчере задач.
- `ui/src/components/IslandApp.jsx`:
  - Плавающий оверлей Dynamic Island с динамическим клик-сквозным поведением.
  - В тестах `IslandApp.test.jsx` асинхронные таймеры вызывают предупреждения React 19 `not wrapped in act(...)`.
- `ui/src-tauri/src/lib.rs`:
  - Rust-бэкенд для Tauri v2.
  - Корректно управляет регионами окон `HRGN` через WinAPI GDI (`SetWindowRgn`, `DeleteObject`).
  - Строка 386: В методе выключения `request_backend_shutdown()` синхронный вызов `TcpStream::connect("127.0.0.1:8765")` не имеет таймаута на установление соединения (`connect_timeout`), из-за чего при зависшем бэкенде поток UI Windows может заблокироваться на 20 секунд.
- `services/gateway/hub.py`:
  - Строка 81: `message = json.dumps(payload, ensure_ascii=False)`.
  - При передаче несериализуемых объектов (объекты ошибок, `datetime`, сложные структуры) вызов падает с необработанным `TypeError`, обрывая рассылку событий воркера.
- `services/gateway/routers/chat.py`:
  - Строка 31: HTTP эндпоинт `POST /api/chat` принимает текст, но полностью игнорирует флаг `"thinking"`, в отличие от обработчика веб-сокета.
- `services/gateway/routers/system.py`:
  - Строки 39-42: Поиск `start.bat` через `.parent.parent.parent` ошибочно проверяет несуществующий путь `services/start.bat`.
  - Строка 114: Жесткий вызов `os._exit(0)` через 0.5 секунды убивает процесс до того, как основной поток в `start/main.py` успеет освободить файловые блокировки `msvcrt` и сбросить состояние на диск.
- `services/gateway/routers/integrations.py`:
  - Строки 287-300: Эндпоинт `/api/apps/launch` напрямую дергает `indexer.launch_app(target)`, обходя проверку прав `PermissionManager` и границы рабочего каталога.

### 3.5. Интеграции и внешние модули (Integrations)
- `modules/telegram/handlers.py`:
  - Строки 38-51: Обработчик команды `/status` запрашивает `telemetry.get("ram", {})` и `telemetry.get("gpus", [])`. Так как `tools/system_info.py` возвращает плоские ключи, Telegram выводит нулевые значения: `RAM: 0.0 / 0.0 GB (0%)` и не показывает видеокарту.
- `core/steam_manager.py`:
  - Корректно находит Steam через реестр `HKCU/HKLM Software\Valve\Steam`, парсит `appmanifest_*.acf`, формирует библиотеку игр и запускает их через безопасный протокол `steam://rungameid/`. Никаких нарушений.
- `core/vpn/`:
  - Содержит чистые утилиты запуска Zapret (`winws.exe`), Happ и FlClash. Никаких фоновых сторожей автоподключения нет.

### 3.6. Аудит документации (docs-sync)
- Запуск аудита через `.agents/skills/docs-sync/scripts/audit_docs.py --json` показал отсутствие битых ссылок и полное покрытие компонентов.
- Число тестов в документации (`README.md`, `PROJECT_STATUS.md`, `COMPONENTS_MAP.md`) — **707 pytest и 77 Vitest** — в точности совпадает с реальными прогонами.
- **Выявленные расхождения:**
  1. `STORAGE_LAYOUT.md:72`: Указано, что сессионный токен состоит из «64 символов hex». В реальности `services/gateway_service.py:73` генерирует `secrets.token_urlsafe(32)`, что дает строку из **43 символов** base64url.
  2. `AI_GUIDE.md:25`: Указан путь `%APPDATA%\Jarvis` вместо первичного `%APPDATA%\Assistant`.
  3. `ui/src-tauri/Cargo.toml:3`: Версия указана как `0.1.0`, в то время как во всех остальных файлах (`package.json`, `version.py`, `tauri.conf.json`, `README.md`) зафиксирована версия `0.1.8`.
  4. `COMMANDS.md:85`: В качестве примера приводится фраза поиска документации по PySide6, хотя фреймворк признан устаревшим.

### 3.7. Состояние и скрытые проблемы тестового фреймворка
- В каталоге `tests/` находится **85 файлов тестов** (707 тест-кейсов).
- **Критический дефект `tests/run_tests.bat:57`**:
  Скрипт содержит команду:
  `python -m pytest tests\unit tests\integration -ra --tb=short`
  Это приводит к запуску только 19 файлов тестов и пропуску 66 файлов тестов в корне `tests/` (78% тестов не проверяются скриптом сборки).
- **Ложноположительный тест в `tests/test_new_system_tools.py:62`**:
  Тест скриншота проверял `assert "success" in res`. Поскольку упавшая функция вернула `{"success": False, "error": "name 're' is not defined"}`, тест прошел успешно и замаскировал критический баг.
- В `.venv\Scripts\` отсутствует файл `pytest.exe`, поэтому запуск должен осуществляться через `.venv\Scripts\python.exe -m pytest tests/`.

---

## 4. Каталог обнаруженных дефектов и уязвимостей

| ID | Уровень | Файл и строки | Краткое описание проблемы |
|---|---|---|---|
| **BUG-01** | **High** | `tools/system_actions.py:65` | `NameError: name 're' is not defined` при создании скриншота с именем. |
| **BUG-02** | **High** | `core/website_manager.py:204` | `AttributeError: 'EventBus' object has no attribute 'publish'` при сохранении сайтов. |
| **BUG-03** | **High** | `core/app_paths.py:38, 47, 78-81` | Инверсия условия миграции папки `Jarvis` в `Assistant`. |
| **BUG-04** | **Medium** | `modules/telegram/handlers.py:38-51` | Несоответствие ключей телеметрии RAM и GPU в команде `/status`. |
| **BUG-05** | **Medium** | `start/bootstrap.py:47-59` | Удаление файла `errors.log` при каждом запуске программы. |
| **BUG-06** | **High** (SEC-1) | `services/gateway/routers/integrations.py:287-300` | Эндпоинт `/api/apps/launch` запускает процессы мимо `PermissionManager`. |
| **BUG-07** | **Medium** (SEC-2) | `services/stark_protocols.py:108` | Небезопасный фоллбэк `os.startfile(app_key)`. |
| **BUG-08** | **Medium** (SEC-3) | `tools/paths.py:14, 31, 162-178` | `find_by_name` сканирует корень репозитория `APP_ROOT` мимо песочницы. |
| **BUG-09** | **Medium** | `services/gateway/hub.py:81` | `json.dumps` падает с `TypeError` при наличии несериализуемых объектов. |
| **BUG-10** | **Low** | `services/gateway/routers/chat.py:31` | `POST /api/chat` теряет флаг `"thinking"`. |
| **BUG-11** | **Low** | `services/gateway_service.py:348-358` | Действие `protocols.execute` в WS теряет параметр `profile_id`. |
| **BUG-12** | **Low** | `services/gateway/routers/system.py:39-42` | Ошибочный относительный путь к `start.bat` при настройке автозапуска. |
| **BUG-13** | **Medium** | `services/gateway/routers/system.py:114` | Грубое завершение процесса через `os._exit(0)` ломает graceful shutdown. |
| **BUG-14** | **Medium** | `services/chat_service.py:47, 83-102, 244-252` | Гонка склеивания токенов в `_current_answer` без мьютекса. |
| **BUG-15** | **Medium** | `core/config_manager.py:169-171`<br>`core/alias_manager.py:242-244` | Коллизия записи в статичный `.tmp` файл при параллельных запросах. |
| **BUG-16** | **Low** | `services/statistics_service.py:6-7, 13-16` | Утечка памяти в неограниченных списках истории телеметрии. |
| **BUG-17** | **Low** | `tools/applications.py:33, 486-516` | Гонка в глобальной переменной `_PENDING_LAUNCH_CHOICES`. |
| **BUG-18** | **Medium** | `core/task_runner.py:10-14` | Истощение пула из 4 потоков при параллельной работе STT и Ollama. |
| **BUG-19** | **Low** | `services/gateway_service.py:480-484` | Таймер перезапуска wake-word (300мс) обгоняет синтез речи TTS. |
| **BUG-20** | **Medium** | `ui/src/App.jsx:214-228` | Закрытие приложения уничтожает только `main` окно, оставляя фоновый процесс. |
| **BUG-21** | **Medium** | `ui/src-tauri/src/lib.rs:386-398` | Зависание UI потока Windows при TCP соединении без `connect_timeout`. |
| **BUG-22** | **High** | `tests/run_tests.bat:57` | Пропуск 66 файлов тестов (78% тестового покрытия) в batch-скрипте. |
| **BUG-23** | **Medium** | `tests/test_new_system_tools.py:62` | Пустая проверка `assert "success" in res`, скрывавшая NameError. |
| **BUG-24** | **Low** | `ui/src/components/Network.jsx:95` | Неочищенный таймер `setTimeout` при размонтировании вкладки Network. |
| **BUG-25** | **Info / False Positive** | `ui/src-tauri/capabilities/default.json:19, 21` | Оптический ложный дефект: строки 19 (`allow-unminimize`) и 21 (`allow-unmaximize`) задают разные права Tauri v2 core:window, оба обязательны к сохранению. |

---

### Детальные карточки ключевых дефектов

#### BUG-01: Отсутствие `import re` в `tools/system_actions.py`
- **Файл и строки:** `tools/system_actions.py:65`
- **Фрагмент кода:**
  ```python
  base_name = Path(str(filename).strip()).name
  safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base_name)
  ```
- **Корневая причина:** В строках импорта 1-14 модуль `re` не импортирован.
- **Способ воспроизведения:**
  Выполнить: `& .venv\Scripts\python.exe -c "from tools.system_actions import take_screenshot; print(take_screenshot(filename='test.png'))"`
- **Результат:** Функция падает с `NameError: name 're' is not defined`.
- **Серьезность:** High.

#### BUG-02: Несуществующий метод `publish` в `core/website_manager.py`
- **Файл и строки:** `core/website_manager.py:204`
- **Фрагмент кода:**
  ```python
  if self.event_bus:
      self.event_bus.publish("websites.updated", {"count": len(self._websites)})
  ```
- **Корневая причина:** Класс `EventBus` в `core/events.py` предоставляет только метод `emit()`.
- **Способ воспроизведения:**
  Выполнить: `& .venv\Scripts\python.exe -c "from core.events import EventBus; from core.website_manager import WebsiteManager; wm = WebsiteManager(event_bus=EventBus()); wm.save()"`
- **Результат:** `AttributeError: 'EventBus' object has no attribute 'publish'`.
- **Серьезность:** High.

#### BUG-03: Логическая инверсия миграции каталогов AppData
- **Файл и строки:** `core/app_paths.py:38, 47, 78-81`
- **Фрагмент кода:**
  ```python
  LOCAL_DATA_DIR = _PRIMARY_LOCAL if (_PRIMARY_LOCAL.exists() or not _LEGACY_LOCAL.exists()) else _LEGACY_LOCAL
  APP_DATA_DIR = _PRIMARY_ROAMING if (_PRIMARY_ROAMING.exists() or not _LEGACY_ROAMING.exists()) else _LEGACY_ROAMING
  ...
  if _LEGACY_ROAMING.is_dir() and APP_DATA_DIR == _PRIMARY_ROAMING:
      _migrate_legacy_files(_LEGACY_ROAMING, APP_DATA_DIR)
  ```
- **Корневая причина:** Если целевая папка `_PRIMARY_ROAMING` еще не создана, а `_LEGACY_ROAMING` существует, `APP_DATA_DIR` становится равной `_LEGACY_ROAMING`. Условие миграции не выполняется, папка `Assistant` не создается.
- **Способ воспроизведения:** Смоделировать наличие папки `%APPDATA%\Jarvis` при отсутствии `%APPDATA%\Assistant` и вызвать `ensure_application_dirs()`.
- **Серьезность:** High.

#### BUG-04: Несоответствие схемы телеметрии в Telegram-боте
- **Файл и строки:** `modules/telegram/handlers.py:38-51` vs `tools/system_info.py:114-126`
- **Фрагмент кода:**
  ```python
  ram = telemetry.get("ram", {})
  ram_pct = ram.get("percent", 0)
  ram_used = round(ram.get("used", 0) / (1024**3), 1)
  gpus = telemetry.get("gpus", [])
  ```
- **Корневая причина:** `tools/system_info.py` возвращает плоские ключи `ram_percent`, `ram_used_gb`, `ram_total_gb` и `gpu_name`.
- **Результат:** В Telegram выводится `RAM: 0.0 / 0.0 GB (0%)`, информация о видеокарте отсутствует.
- **Серьезность:** Medium.

#### BUG-05: Удаление `errors.log` при старте
- **Файл и строки:** `start/bootstrap.py:51-54`
- **Фрагмент кода:**
  ```python
  for path in LOG_DIR.glob("*.log*"):
      try:
          if path.is_file():
              path.unlink()
  ```
- **Корневая причина:** Функция чистит все лог-файлы без исключения для `errors.log` и `fatal.log`.
- **Результат:** При падении приложения повторный запуск удаляет следы аварии.
- **Серьезность:** Medium.

#### BUG-06 (SEC-1): Запуск приложений в обход `PermissionManager`
- **Файл и строки:** `services/gateway/routers/integrations.py:287-300`
- **Фрагмент кода:**
  ```python
  target = payload.get("app") or payload.get("name") or payload.get("path")
  return indexer.launch_app(target)
  ```
- **Корневая причина:** Метод `AppIndexer.launch_app` напрямую вызывает `os.startfile(target_path)`, минуя проверку `PermissionManager.is_enabled("launch_application")` и флага `allow_outside_workspace`.
- **Результат:** Любой клиент API может запустить произвольный софт на хосте без ограничений песочницы.
- **Серьезность:** High.

#### BUG-22: Урезание охвата тестов в `run_tests.bat`
- **Файл и строки:** `tests/run_tests.bat:57`
- **Фрагмент кода:**
  ```bat
  python -m pytest tests\unit tests\integration -ra --tb=short
  ```
- **Корневая причина:** В команду запуска переданы только две папки вместо `tests/`.
- **Результат:** 66 файлов тестов в корне `tests/` полностью игнорируются при запуске через батник.
- **Серьезность:** High.

---

## 5. Пошаговый план улучшений (/plan)

План выстроен строго по приоритетам: от критической корректности ядра и соответствия `AGENTS.md` к синхронизации WinAPI, безопасности, потокобезопасности и завершающей чистке устаревшего кода.

---

### Приоритет 1: Критическая корректность и соответствие AGENTS.md (Немедленно)

#### Задача 1.1. Исправление NameError в `tools/system_actions.py` и ужесточение тестов
- **Затрагиваемые файлы:**
  - `tools/system_actions.py:1-15`
  - `tests/test_new_system_tools.py:58-65`
- **Требуемые изменения:**
  1. В `tools/system_actions.py` добавить импорт стандартного модуля: `import re`.
  2. В `tests/test_new_system_tools.py` заменить пустую проверку `assert "success" in res` на строгие утверждения:
     ```python
     res = take_screenshot("test_screen.png")
     assert res.get("success") is True
     assert Path(res["path"]).is_file()
     ```
- **Критерий верификации:**
  Запуск команды:
  `& .venv\Scripts\python.exe -c "from tools.system_actions import take_screenshot; res = take_screenshot('test_verify.png'); assert res['success'] is True; print('SCREENSHOT OK:', res['path'])"`
  Прогон теста: `& .venv\Scripts\python.exe -m pytest tests/test_new_system_tools.py -k test_take_screenshot`.

#### Задача 1.2. Исправление вызова EventBus в `core/website_manager.py`
- **Затрагиваемые файлы:**
  - `core/website_manager.py:204`
- **Требуемые изменения:**
  Заменить обращение к несуществующему методу `publish`:
  ```python
  # Было:
  self.event_bus.publish("websites.updated", {"count": len(self._websites)})
  # Стало:
  self.event_bus.emit("websites.updated", {"count": len(self._websites)})
  ```
- **Критерий верификации:**
  Запуск команды:
  `& .venv\Scripts\python.exe -c "from core.events import EventBus; from core.website_manager import WebsiteManager; wm = WebsiteManager(event_bus=EventBus()); wm.save(); print('WEBSITES SAVE OK')"`
  Отсутствие исключений `AttributeError` и записей `failed_to_save_websites` в логе.

#### Задача 1.3. Исправление логики миграции путей в `core/app_paths.py` (с постоянным маркером)
- **Затрагиваемые файлы:**
  - `core/app_paths.py:38, 47, 78-81`
- **Требуемые изменения:**
  1. Переменные `LOCAL_DATA_DIR` и `APP_DATA_DIR` должны всегда указывать на целевые основные пути `_PRIMARY_LOCAL` (`%LOCALAPPDATA%\Assistant`) и `_PRIMARY_ROAMING` (`%APPDATA%\Assistant`).
  2. В функции `ensure_application_dirs()` исключить зависимость от эфемерных файлов (таких как `session.token`, который удаляется при завершении шлюза в `services/gateway_service.py:581-583` и отсутствует при холодном старте, что вызывало бы бесконечную повторную миграцию при каждом запуске).
  3. Использовать постоянный файл-маркер миграции (persistent migration marker), например `.migrated`:
     ```python
     roaming_marker = APP_DATA_DIR / ".migrated"
     if _LEGACY_ROAMING.is_dir() and not roaming_marker.exists():
         _migrate_legacy_files(_LEGACY_ROAMING, APP_DATA_DIR)
         roaming_marker.touch()

     local_marker = LOCAL_DATA_DIR / ".migrated"
     if _LEGACY_LOCAL.is_dir() and not local_marker.exists():
         _migrate_legacy_files(_LEGACY_LOCAL, LOCAL_DATA_DIR)
         local_marker.touch()
     ```
- **Критерий верификации:**
  Юнит-тест с изолированными временными каталогами: при первом вызове `ensure_application_dirs()` файлы из устаревшей директории копируются в новую и создается маркер `.migrated`; при повторных вызовах (и перезапусках процесса) миграция пропускается за 0 мс без холостых операций ввода-вывода.

#### Задача 1.4. Исправление схемы телеметрии в `modules/telegram/handlers.py`
- **Затрагиваемые файлы:**
  - `modules/telegram/handlers.py:38-52`
- **Требуемые изменения:**
  Считать плоские поля напрямую из словаря `telemetry`:
  ```python
  ram_pct = telemetry.get("ram_percent", 0)
  ram_used = telemetry.get("ram_used_gb", 0.0)
  ram_total = telemetry.get("ram_total_gb", 0.0)
  gpu_name = telemetry.get("gpu_name")
  gpu_info = f"\n🎮 <b>GPU:</b> {gpu_name}" if gpu_name else ""
  ```
- **Критерий верификации:**
  Запуск команды формирования текста статуса с реальным словарем `get_system_telemetry()`:
  `& .venv\Scripts\python.exe -c "from tools.system_info import get_system_telemetry; t = get_system_telemetry(); print(f'RAM: {t.get(\"ram_used_gb\")} / {t.get(\"ram_total_gb\")} GB ({t.get(\"ram_percent\")}%)')"`
  Вывод ненулевых реальных параметров памяти.

#### Задача 1.5. Сохранение файла аварийных логов `errors.log` при старте
- **Затрагиваемые файлы:**
  - `start/bootstrap.py:47-59`
- **Требуемые изменения:**
  Исключить `errors.log` и `fatal.log` из списка удаляемых файлов в `_clear_previous_logs()`:
  ```python
  for path in LOG_DIR.glob("*.log*"):
      if path.name in ("errors.log", "fatal.log"):
          continue
      try:
          if path.is_file():
              path.unlink()
      except OSError:
          pass
  ```
- **Критерий верификации:**
  Создать тестовый файл `errors.log`, вызвать `_clear_previous_logs()`, убедиться через `path.is_file()`, что файл сохранен.

#### Задача 1.6. Строгая фиксация границы Zero-LLM Core
- **Затрагиваемые файлы:**
  - `core/config_manager.py:29`
  - `services/chat_service.py:129-160`
  - `core/application.py:141, 156-160`
- **Требуемые изменения:**
  1. В `core/config_manager.py` установить значение по умолчанию `"router_only_mode": True`.
  2. В `services/chat_service.py` при активном `router_only_mode` возвращать детерминированный ответ («Команда не распознана») без передачи текста в Ollama и без вызова `ToolExecutor`.
  3. В `core/application.py` убрать безусловный вызов `self.ollama_manager.start()` из `start_ollama`. Запуск Ollama перевести строго в режим on-demand по запросу пользователя.
- **Критерий верификации:**
  Прогон тестов роутера при незапущенной Ollama: все команды выполняются оффлайн, фоновые запросы к портам отсутствуют.

#### Задача 1.7. Удаление вызовов Ollama из сценариев автоматизации
- **Затрагиваемые файлы:**
  - `services/stark_protocols.py:311-393, 473-478, 530`
  - `services/router/protocols_dispatcher.py:27-29`
- **Требуемые изменения:**
  1. Удалить метод `_try_generate_llm_response()` и использование `urllib.request`.
  2. Метод `generate_dynamic_response` должен использовать исключительно локальный мгновенный генератор фраз `_generate_stark_fallback()`.
  3. Удалить передачу параметров `ollama_url` и `model` из `protocols_dispatcher.py`.
- **Критерий верификации:**
  Запуск протокола (`stark_protocols.execute_protocol`) при отключенной сети и выключенной Ollama отрабатывает менее чем за 50 мс.

#### Задача 1.8. Устранение жестко зашитых путей к приложениям в `services/stark_protocols.py` (AGENTS.md No Hardcoded Paths)
- **Затрагиваемые файлы:**
  - `services/stark_protocols.py:107-195`
- **Требуемые изменения:**
  1. В методе `_resolve_app_path(app_key)` полностью устранить жестко закодированные пути ярлыков (`"Браузер Opera GX.lnk"`, `"Discord.lnk"`, `"Antigravity.lnk"`) и прямое обращение к пользовательской папке Downloads (`Path(os.environ["USERPROFILE"]) / "Downloads"` для `AG_*.exe`).
  2. Реализовать динамическое обнаружение исполняемых файлов через системный индекс приложений:
     ```python
     from core.app_indexer import AppIndexer
     from tools.applications import find_application

     indexer = AppIndexer.get_instance()
     resolved = indexer.resolve_app(app_key) or find_application(app_key)
     if resolved:
         return Path(resolved)
     ```
  3. В строке 108 удалить небезопасный фоллбэк `os.startfile(app_key)`: если приложение не найдено через динамический индекс, возвращать `(False, f"Приложение '{app_key}' не обнаружено в системе")` без слепого запуска непроверенной строки в командной оболочке Windows (устранение уязвимости SEC-2).
- **Критерий верификации:**
  Тест функции `_resolve_app_path` успешно находит установленные приложения через Start Menu и системный реестр независимо от имени пользователя Windows; передача незарегистрированного имени не приводит к вызову `os.startfile`.

---

### Приоритет 2: Синхронизация процессов и стандарты WinAPI

#### Задача 2.1. Устранение слепых пауз и хардкода координат в драйвере мыши (uiautomation + DPI fallback)
- **Затрагиваемые файлы:**
  - `tools/mouse_driver.py:126-172`
- **Требуемые изменения:**
  1. Заменить 7 слепых пауз `time.sleep()` на детерминированную синхронизацию WinAPI: вызов `WaitForInputIdle(hProcess, timeout)` и проверку готовности потока окна через `GetGUIThreadInfo` / `PeekMessageW`.
  2. Использовать библиотеку `uiautomation` (уже установлена в виртуальном окружении и зафиксирована в `config/requirements.txt:15` как `uiautomation>=2.0,<3`, в отличие от не установленной `pywinauto`) для поиска элементов интерфейса мыши по имени контрола или `AutomationId` (кнопка «Применить» / «Apply»).
  3. Поскольку кастомно отрисованное окно утилиты Fury / ZET Gaming может не экспортировать стандартные дочерние UIA элементы, реализовать надежный DPI-адаптивный фоллбэк: масштабирование базовых клиентских координат через системный WinAPI `GetDpiForWindow(hwnd)` (или `GetDeviceCaps` для HDC) и последующую трансляцию в экранные координаты через `ClientToScreen`, предотвращая смещение кликов при масштабных коэффициентах 125%, 150% и 175%.
- **Критерий верификации:**
  Проверка переключения профилей мыши без слепых пауз `time.sleep` и успешный клик при DPI масштабировании Windows 125% и 150%.

#### Задача 2.2. Синхронизация жизненного цикла процессов в протоколах (предотвращение WinError 193 для .lnk)
- **Затрагиваемые файлы:**
  - `services/stark_protocols.py:82-120, 218, 244, 271`
- **Требуемые изменения:**
  1. Предотвращение краша `[WinError 193]`: Вызов `subprocess.Popen([str(path)])` на Windows падает с фатальной ошибкой `OSError: [WinError 193] %1 не является приложением Win32`, если целевой путь является ярлыком `.lnk` (например, ярлыки Opera GX или Discord из меню Пуск). Для синхронного запуска и получения дескриптора процесса `hProcess` реализовать один из двух надежных подходов:
     - **Вариант А (резолвинг ярлыка):** Разрешать путь ярлыка `.lnk` к реальному исполняемому `.exe` файлу через WinAPI / COM `IShellLink` (или `wscript.shell` / `AppIndexer`) перед передачей в `subprocess.Popen(executable_path)`.
     - **Вариант Б (WinAPI ShellExecuteExW):** Вызывать `ctypes.windll.shell32.ShellExecuteExW` со структурой `SHELLEXECUTEINFOW`, передавая флаг `fMask = SEE_MASK_NOCLOSEPROCESS` (`0x00000040`). Это позволяет Windows Shell прозрачно обработать ярлык `.lnk` и вернуть реальный дескриптор `hProcess` процесса в поле `info.hProcess`.
  2. После получения `hProcess` ожидать создания оконного цикла ввода через `win32event.WaitForInputIdle(hProcess, 3000)` вместо слепого завершения функции.
  3. При закрытии приложений (`close_steam_games`, `close_user_apps_for_gaming`) обязательно вызывать `psutil.wait_procs(processes, timeout=2.0)` после `proc.terminate()`, как это реализовано в `tools/application_closer.py`, исключая конфликт блокировки файлов и дескрипторов при быстром перезапуске.
- **Критерий верификации:**
  Запуск приложения через ярлык `.lnk` в `launch_if_not_running()` отрабатывает без возникновения `WinError 193`, возвращает дескриптор созданного процесса и успешно ожидает `WaitForInputIdle`.

#### Задача 2.3. Замена поллинговых пауз в апдейтере на WinAPI события
- **Затрагиваемые файлы:**
  - `start/updater.py:74, 135`
- **Требуемые изменения:**
  Заменить опрос процесса в цикле со `sleep()` на открытие хэндла процесса через `win32api.OpenProcess(win32con.SYNCHRONIZE, False, pid)` и синхронное ожидание `win32event.WaitForSingleObject(handle, timeout_ms)`.
- **Критерий верификации:**
  Завершение ожидания происходит моментально по факту закрытия процесса без холостых задержек.

#### Задача 2.4. Замена жесткого `os._exit(0)` на событие плавного завершения
- **Затрагиваемые файлы:**
  - `services/gateway/routers/system.py:103-115`
  - `services/gateway_service.py:274, 371, 393`
- **Требуемые изменения:**
  1. Отправлять событие `application.shutdown` через `EventBus`.
  2. Управлять флагом `stop_event` в `start/main.py`, позволяя главному потоку корректно освободить мьютексы блокировки файлов и закрыть сетевые соединения.
  3. Сохранить вызов `os._exit(0)` только как аварийный сторожевой таймер с таймаутом не менее 3.0 секунд.
- **Критерий верификации:**
  Проверка корректного освобождения файлового замка экземпляра `assistant.lock` (создаваемого в `start/main.py:177`) при завершении работы через вызов `/api/shutdown`.

---

### Приоритет 3: Безопасность и контракты шлюза связи

#### Задача 3.1. Интеграция `PermissionManager` в эндпоинт `/api/apps/launch`
- **Затрагиваемые файлы:**
  - `services/gateway/routers/integrations.py:287-300`
- **Требуемые изменения:**
  Перед вызовом `indexer.launch_app(target)` валидировать права через `PermissionManager`:
  ```python
  pm = getattr(gateway.app_context, "permission_manager", None)
  if pm and not pm.is_enabled("launch_application"):
      return {"success": False, "error": "Запуск приложений запрещен настройками безопасности"}
  ```
- **Критерий верификации:**
  При отключенном разрешении `launch_application` запрос к эндпоинту возвращает отказ с кодом ошибки.

#### Задача 3.2. Валидация запуска и изоляция протоколов (SEC-2)
- **Затрагиваемые файлы:**
  - `services/stark_protocols.py:107-112`
- **Требуемые изменения:**
  В дополнение к динамическому поиску через `AppIndexer` (Задача 1.8), полностью изолировать точку запуска протоколов:
  1. Запретить передачу невалидированных строковых ключей в системную оболочку `os.startfile(app_key)`.
  2. Если приложение не найдено в индексе доверенных путей, немедленно возвращать структурированный ответ `(False, f"Запуск отклонен: приложение '{app_key}' не найдено в разрешенных путях")`.
- **Критерий верификации:**
  Передача произвольного или вредоносного ключа `app_key` возвращает структурированный отказ и не создает системных процессов в обход проверок.

#### Задача 3.3. Изоляция области поиска в `tools/paths.py`
- **Затрагиваемые файлы:**
  - `tools/paths.py:14, 31, 162-178`
- **Требуемые изменения:**
  Ограничить `SEARCH_ROOTS` исключительно рабочей областью `(TOOL_WORKSPACE,)`. Запретить поиск по `APP_ROOT` для предотвращения утечки исходного кода через файловые команды.
- **Критерий верификации:**
  Поиск файла `settings.json` через инструмент поиска файлов не должен возвращать пути внутри репозитория.

#### Задача 3.4. Защита сериализации в WebSocket Hub
- **Затрагиваемые файлы:**
  - `services/gateway/hub.py:76-85`
- **Требуемые изменения:**
  Обернуть сериализацию сообщений в блок `try/except` и добавить параметр `default=str`:
  ```python
  try:
      message = json.dumps(payload, default=str, ensure_ascii=False)
  except Exception as exc:
      logger.warning("websocket_json_encode_error: %s", exc)
      return
  ```
- **Критерий верификации:**
  Отправка объекта `{"error": Exception("test"), "time": datetime.now()}` в `hub.broadcast()` не вызывает падения воркера.

#### Задача 3.5. Синхронизация параметров REST и WebSocket контрактов
- **Затрагиваемые файлы:**
  - `services/gateway/routers/chat.py:24-32`
  - `services/gateway_service.py:348-358`
- **Требуемые изменения:**
  1. В `services/gateway/routers/chat.py` передавать флаг `thinking`:
     `chat_service.send(text, thinking=bool(payload.get("thinking", False)))`.
  2. В `services/gateway_service.py` для действия `protocols.execute` принимать `profile_id` и передавать его в `get_protocol_by_id(proto_id, profile_id=profile_id)`.
- **Критерий верификации:**
  Прогон запросов через REST и WebSocket с флагом `thinking` и кастомным `profile_id` демонстрирует эквивалентное поведение.

#### Задача 3.6. Исправление определения пути `start.bat` в `services/gateway/routers/system.py`
- **Затрагиваемые файлы:**
  - `services/gateway/routers/system.py:39-42`
- **Требуемые изменения:**
  Использовать канонический путь через `core.app_paths`:
  ```python
  from core.app_paths import APP_ROOT
  launcher = APP_ROOT / "start.bat"
  ```
- **Критерий верификации:**
  Проверка существования файла `launcher.is_file()` возвращает `True` с первой попытки без холостых обращений.

---

### Приоритет 4: Потокобезопасность, утечки памяти и жизненный цикл UI

#### Задача 4.1. Потокобезопасная синхронизация состояния в `ChatService`
- **Затрагиваемые файлы:**
  - `services/chat_service.py:47-55, 83-102, 244-252`
- **Требуемые изменения:**
  Ввести `threading.RLock()` для синхронизации доступа к атрибутам `_current_answer`, `_generation_future` и списку ожидающих сообщений. Исключить параллельное исполнение нескольких генераций в одном контексте.
- **Критерий верификации:**
  Тест на одновременный вызов `send()` из 5 параллельных потоков: ответы ставятся в очередь без взаимного повреждения текста.

#### Задача 4.2. Атомарное сохранение конфигураций с уникальными именами `.tmp`
- **Затрагиваемые файлы:**
  - `core/config_manager.py:167-185`
  - `core/alias_manager.py:240-248`
- **Требуемые изменения:**
  Добавить `threading.Lock()` на операции записи. Генерировать уникальные временные файлы вида:
  `temp_path = self.pathlib_path.with_name(f".{self.pathlib_path.name}.{uuid.uuid4().hex}.tmp")`.
- **Критерий верификации:**
  Стресс-тест на 50 параллельных записей настроек из разных потоков завершается без ошибок `PermissionError` и повреждения JSON.

#### Задача 4.3. Ограничение размера списков телеметрии в `StatisticsService`
- **Затрагиваемые файлы:**
  - `services/statistics_service.py:1-20`
- **Требуемые изменения:**
  Заменить стандартные списки на кольцевые буферы:
  ```python
  from collections import deque
  self.history = deque(maxlen=500)
  self.whisper_history = deque(maxlen=500)
  ```
- **Критерий верификации:**
  Добавление 10 000 записей через `add()` оставляет длину очереди равной строго 500 элементам.

#### Задача 4.4. Изоляция состояния множественного выбора в `tools/applications.py`
- **Затрагиваемые файлы:**
  - `tools/applications.py:33, 486-516`
- **Требуемые изменения:**
  Перенести список `_PENDING_LAUNCH_CHOICES` из глобальной области видимости модуля в контекст сессии или связать его с идентификатором клиента.
- **Критерий верификации:**
  Параллельные запросы выбора приложений от двух независимых сессий не перетирают списки вариантов друг друга.

#### Задача 4.5. Надежное завершение процесса из интерфейса Tauri
- **Затрагиваемые файлы:**
  - `ui/src-tauri/src/lib.rs:440-497`
  - `ui/src/App.jsx:214-228`
  - `ui/src/services/assistantSocket.js:279-290`
- **Требуемые изменения:**
  1. В `ui/src-tauri/src/lib.rs` зарегистрировать Tauri команду:
     ```rust
     #[tauri::command]
     fn exit_application(app: tauri::AppHandle) {
         app.exit(0);
     }
     ```
  2. В `App.jsx` и `assistantSocket.js` при закрытии вызывать `invoke('exit_application')`, гарантируя завершение всех окон вебвью (включая `"island"`).
  3. В `lib.rs:386` добавить таймаут на установку TCP соединения:
     `TcpStream::connect_timeout(&addr, std::time::Duration::from_millis(800))`.
- **Критерий верификации:**
  Нажатие кнопки выключения в UI полностью завершает процесс Tauri в диспетчере задач Windows даже при открытом Dynamic Island.

#### Задача 4.6. Разделение пулов потоков в `core/task_runner.py` для предотвращения Thread Pool Starvation (BUG-18)
- **Затрагиваемые файлы:**
  - `core/task_runner.py:10-14`
  - `core/application.py:140-165`
  - `services/chat_service.py:365-375`
- **Требуемые изменения:**
  1. В `core/task_runner.py` устранить риск паралича быстрых операций при одновременном запуске тяжелых блокирующих задач:
     - Создать выделенный пул `fast_executor` (`ThreadPoolExecutor(max_workers=4)`) исключительно для быстрых системных задач (команды маршрутизатора, опрос телеметрии, уведомления EventBus, обработчики WebSocket).
     - Создать изолированный пул `heavy_executor` (`ThreadPoolExecutor(max_workers=2)`) для длительных операций: обработка аудио через Whisper STT на CPU, стриминг ответов от Ollama и ожидание подтверждения опасных действий в чате с таймаутом 60с (`chat_service.py:368`).
  2. Предоставить явные методы планирования `submit_fast(fn, *args, **kwargs)` и `submit_heavy(fn, *args, **kwargs)`.
- **Критерий верификации:**
  Подача длительной 10-секундной блокирующей задачи в `heavy_executor` не препятствует моментальному выполнению команд быстрой очереди (время отклика роутера в `fast_executor` остается < 15 мс).

#### Задача 4.7. Устранение гонки таймера перезапуска Wake-Word и синтеза речи Piper TTS (BUG-19)
- **Затрагиваемые файлы:**
  - `services/gateway_service.py:480-484`
- **Требуемые изменения:**
  1. В `services/gateway_service.py:480-484` устранить слепой статический таймер `threading.Timer(0.3, wake_word_detector.start).start()`, который принудительно включает распознавание микрофона через 300 мс, в то время как движок Piper TTS продолжает озвучивать ответ ассистента через динамики (провоцируя самосрабатывание детектора Vosk на голос ассистента).
  2. Перевести управление жизненным циклом микрофона на детерминированные сигналы:
     - Ожидать завершения синтеза и воспроизведения аудиопотока через подписку на событие `tts.playback_finished` в `EventBus`.
     - Либо выполнять перезапуск детектора только при выполнении условия `tts_service.is_speaking() is False`.
- **Критерий верификации:**
  Синтез длинной реплики ассистента (> 2.0 секунд) не включает микрофон до момента полного завершения воспроизведения звука; ложные детекции wake-word от собственного голоса ассистента полностью исключены.

---

### Приоритет 5: Гигиена кода, изоляция устаревшего PySide6 и документация

#### Задача 5.1. Расширение охвата тестов в `tests/run_tests.bat`
- **Затрагиваемые файлы:**
  - `tests/run_tests.bat:57`
- **Требуемые изменения:**
  Заменить запуск подпапок на полный прогон:
  ```bat
  python -m pytest tests -ra --tb=short
  ```
- **Критерий верификации:**
  Запуск `tests\run_tests.bat` запускает все 85 файлов тестов (707 тест-кейсов).

#### Задача 5.2. Полная изоляция остатков PySide6 в архив
- **Затрагиваемые файлы:**
  - Перемещение `presentation/legacy/` в `ui_archive/presentation_legacy/`
  - `presentation/tray_icon.py:10-14` (удаление неиспользуемых импортов PySide6, так как трей нативно управляется Tauri Rust)
  - `start/main.py:32-75, 165-168` (удаление флагов `--legacy-gui`, `--pyside`)
  - `start.bat:12-16, 85-97` (удаление ветки `:legacy_startup`)
- **Критерий верификации:**
  В репозитории вне папки `ui_archive/` отсутствуют импорты `PySide6`. Прогон тестов не выдает `DeprecationWarning` по `presentation.legacy`.

#### Задача 5.3. Синхронизация версий, аудит разрешений Tauri и настройки безопасности (BUG-25 FP)
- **Затрагиваемые файлы:**
  - `ui/src-tauri/Cargo.toml:3`
  - `ui/src-tauri/capabilities/default.json:19-21`
  - `ui/src-tauri/tauri.conf.json:46-48`
- **Требуемые изменения:**
  1. В `Cargo.toml` синхронизировать версию с остальными компонентами экосистемы (`0.1.8` вместо `0.1.0`).
  2. **Аудит разрешений Tauri в `default.json` (BUG-25 / Оптический False Positive):**
     В строках 19-21 файла `default.json` указаны:
     - Строка 19: `"core:window:allow-unminimize"` (право на восстановление окна из свернутого состояния)
     - Строка 20: `"core:window:allow-maximize"` (право на разворачивание окна на весь экран)
     - Строка 21: `"core:window:allow-unmaximize"` (право на возврат окна из развернутого состояния в обычное)
     **Строка 19 (`allow-unminimize`) и строка 21 (`allow-unmaximize`) являются двумя принципиально разными разрешениями ядра Tauri v2!** Их внешняя текстовая схожесть является оптической иллюзией. **Оба разрешения обязательны к сохранению, удалять строку 21 категорически запрещено**, иначе окно потеряет возможность корректного восстановления из максимизированного состояния.
  3. Настроить локальную строгую политику безопасности (CSP) в `tauri.conf.json` для изоляции WebView от несанкционированных внешних скриптов.
- **Критерий верификации:**
  Валидация JSON-схемы `default.json` подтверждает сохранение обоих разрешений `allow-unminimize` и `allow-unmaximize`; успешный запуск проверки конфигурации `tauri.conf.json`.

#### Задача 5.4. Синхронизация документации (docs-sync)
- **Затрагиваемые файлы:**
  - `docs/STORAGE_LAYOUT.md:72` (исправление формата токена: 43 символа base64url)
  - `docs/AI_GUIDE.md:25` (исправление основного пути на `%APPDATA%\Assistant`)
  - `docs/COMMANDS.md:85` (замена примера поиска по PySide6 на современный стек)
- **Критерий верификации:**
  Повторный запуск аудита документации:
  `& .venv\Scripts\python.exe .agents/skills/docs-sync/scripts/audit_docs.py --json` с нулевым числом замечаний.

#### Задача 5.5. Очистка таймеров компонентов UI и предупреждений Vitest
- **Затрагиваемые файлы:**
  - `ui/src/components/Network.jsx:95`
  - `ui/src/components/IslandApp.test.jsx`
- **Требуемые изменения:**
  1. Сохранять `timerRef` для таймера в `Network.jsx` и вызывать `clearTimeout` в функции очистки `useEffect`.
  2. Обернуть асинхронные обновления состояния в `IslandApp.test.jsx` в `act(async () => { ... })`.
- **Критерий верификации:**
  Запуск `npm --prefix ui test` проходит без предупреждений React 19 `act(...)`.

---

### Приоритет 6: Независимость TTS и мульти-движковая архитектура

#### Задача 6.1. Реестр TTS-бэкендов и переключение моделей/движков (`Piper`, `Silero`, `Edge-TTS`, `SAPI5` и др.)
- **Затрагиваемые файлы:**
  - `voice/tts/engine.py`
  - `voice/tts/service.py`
  - `voice/tts/engines/` (новые адаптеры помимо `piper.py`)
  - `core/config_manager.py` (добавление `tts.engine` в `DEFAULTS`)
  - `services/gateway/routers/voice.py` и настройки TTS в UI (`ui/src/components/settings/`)
- **Требуемые изменения:**
  1. Расширить `TTSBackend` метаданными движка (список доступных голосов/моделей, требования к сети/оффлайну).
  2. Сделать фабрику/реестр движков в `voice/tts/engines/__init__.py`, чтобы `TTSService` не хардкодил `PiperTTSBackend()`, а подхватывал бэкенд по `config["tts"]["engine"]` с горячим переключением без перезапуска приложения.
  3. Добавить возможность пробовать альтернативные локальные и внешние движки (например, Silero, SAPI5, Edge-TTS, Coqui/XTTS) через единый интерфейс `synthesize(text) -> (np.ndarray, sample_rate)`.
- **Критерий верификации:**
  Переключение `tts.engine` в настройках меняет активный бэкенд `TTSService` в рантайме; тесты покрывают фабрику движков и fallback на Piper при отсутствии выбранного бэкенда.

---

## 6. Заключение

Проведенный комплексный аудит подтверждает, что архитектура ассистента обладает высоким потенциалом, модульностью и продуманным стеком (Tauri v2 + React 19 + локальный Python-бэкенд с быстрым Piper TTS). 

Реализация представленного плана улучшений позволит:
1. Полностью устранить отступления от манифеста `AGENTS.md`, вернув проекту 100% автономность и детерминированность **Zero-LLM Core** и устранив хардкод путей к приложениям в протоколах.
2. Ликвидировать критические runtime-баги (`import re` в скриншотах, `EventBus.publish` в закладках, застревание миграции AppData с фиксацией постоянного маркера `.migrated`, затирание лога крашей).
3. Привести механизмы синхронизации процессов и окон к профессиональным стандартам WinAPI, исключив хрупкие слепые паузы и жесткие координаты (с переходом на `uiautomation` и DPI-адаптивный фоллбэк), предотвратив сбои `WinError 193` при запуске ярлыков `.lnk` и исключив гонку перезапуска wake-word с синтезом речи TTS.
4. Устранить уязвимости обхода песочницы и закрыть риски истощения пула потоков через разделение быстрого и тяжелого исполнителей (`fast_executor` / `heavy_executor`).
5. Завершить изоляцию устаревшего кода PySide6 и синхронизировать тестовые сценарии и документацию с актуальным состоянием кодовой базы.
