# План декомпозиции монолитов (God Objects) | Jarvis (Kirieshka v2)

Целевая ветка: `osnova`  
Стек: Python 3.11+, FastAPI, React + Vite (Tauri v2), PyTest, OpenCode CLI

---

## 0. Принципы декомпозиции и правила тандема

1. **Хирургическая точность:** Никакого попутного переписывания сигнатур и типов. Перенос кода "as-is" с сохранением всех публичных методов и точек входа.
2. **Обратная совместимость:** Все оригинальные модули (`services/gateway_service.py`, `services/command_router.py`, `modules/telegram_bot.py` и др.) обязаны реэкспортировать классы и функции, чтобы не ломать тесты и импорты сторонних подсистем.
3. **Отказ от циклов:** Все зависимости от `core.events.EventBus` и синглтонов прокидываются через аргументы конструкторов или канонические импорты.
4. **Контроль тестов:** После каждого этапа обязательный прогон:
   ```powershell
   & ".venv\Scripts\python.exe" -m pytest tests/
   ```
5. **OpenCode Tandem:** После каждого шага запускается Read-Only аудит:
   ```powershell
   python "C:\Users\Jelr1k1\.gemini\config\skills\opencode-tandem\scripts\review.py" --task "<описание этапа>" --files <список_файлов> --dir "d:\putin\kirieshkav2\mama_kirilla_-osnova" --timeout 300
   ```

---

## Этап 1: `services/gateway_service.py` (1508 -> 432 строки) [ВЫПОЛНЕНО НА 100%]

**Проблема:** В одном файле смешаны FastAPI-сервер, WebSocketHub, обработка событий шины и 56 эндпоинтов всех категорий.

### Шаги реализации:
1. Создать структуру пакета:
   - `services/gateway/__init__.py`
   - `services/gateway/hub.py` -> класс `WebSocketHub` (управление подключениями, пинги, бродкаст).
   - `services/gateway/routers/chat.py` -> эндпоинты чата (`/api/chat/message`, `/api/chat/stop`, подтверждения действий).
   - `services/gateway/routers/settings.py` -> чтение, запись и сброс конфигураций.
   - `services/gateway/routers/system.py` -> статус системы, телеметрия, автозапуск, рестарт/завершение.
   - `services/gateway/routers/voice.py` -> выбор устройств, STT/TTS генерация, кэш аудио.
   - `services/gateway/routers/integrations.py` -> роуты Steam, VPN, Stark Protocols, Workspace.
2. В каждом роутере использовать `fastapi.APIRouter(prefix="/api/...", tags=[...])`. Зависимости передавать через FastAPI `Depends` или `request.app.state`.
3. В `services/gateway_service.py`:
   - Оставить сборщик приложения FastAPI: подключение роутеров через `app.include_router(...)`.
   - Оставить жизненный цикл `GatewayService` (старт uvicorn в потоке, graceful stop).
   - Для обратной совместимости сохранить импорты `from services.gateway_service import GatewayService, WebSocketHub`.
4. **Верификация:**
   - `& ".venv\Scripts\python.exe" -m pytest tests/test_gateway_service.py tests/test_ui_smoke.py`
   - OpenCode Tandem ревью.

---

## Этап 2: `services/command_router.py` (1213 -> 395 строк) [ВЫПОЛНЕНО НА 100%]

**Проблема:** Свыше 400 строк захардкоженного словаря `ROUTER_COMMANDS` с регулярками и метод `_route_extended_tools` на 260 строк с каскадом `if/elif`.

### Шаги реализации:
1. Вынесена конфигурация определений и шаблонов:
   - `services/command_catalog.py`: `ROUTER_COMMANDS`, `ASYNC_SYSTEM_COMMANDS`, `ACTION_META`, `KEYWORD_TOOLS`, маппинги и хелперы матчинга.
2. Вынесены специализированные обработчики категорий в пакет `services/router/`:
   - `media_dispatcher.py` -> регулировка громкости, mute, управление плеером.
   - `site_dispatcher.py` -> веб-поиск (Google, YouTube, Яндекс), открытие URL.
   - `protocols_dispatcher.py` -> протоколы Jarvis (StarkProtocols).
   - `system_dispatcher.py` -> ПК-утилиты (мышь, vpn, zapret, скриншот, корзина, блокировка, папки) + управление окном Jarvis.
   - `app_dispatcher.py` -> явные файлы (create, write, rename, copy, move, file_info), поиск софта, сворачивание и управление Ollama.
   - `__init__.py` -> чистый экспорт диспетчеров.
3. В `services/command_router.py`:
   - Оставлена чистая координация маршрутизации, intent recognition и интеграция с `ToolExecutor`.
   - Сокращен с 1213 до 395 строк (-818 строк). Сохранена 100% обратная совместимость.
4. **Верификация:**
   - Все профильные тесты (55) и полный сьют (654 passed, 3 skipped) успешно пройдены.
   - OpenCode Tandem ревью пройдено (блокирующих проблем нет, замечания [WARN] по регулярке `create_folder` и очередности оконных действий устранены).

---

## Этап 3: `modules/telegram_bot.py` (1004 строки) [ВЫПОЛНЕНО НА 100%]

**Проблема:** В одном модуле был реализован HTTP-клиент к Bot API, polling цикл, сборка inline-клавиатур и бизнес-логика ответов.

### Шаги реализации:
1. Создан пакет `modules/telegram/`:
   - `client.py` -> HTTP-транспорт `TelegramClientMixin` (отправка текста, фото, чат-экшенов, ответов на колбэки через `httpx`, разбиение текста `chunk_text`).
   - `keyboards.py` -> генерация инлайн- и реплай-кнопок (главное меню, управление VPN, питание, отмена выключения).
   - `handlers.py` -> `TelegramCommandHandlerMixin` (обработка команд `/start`, `/status`, `/screen`, `/vpn`, `/ping`, `/sleep`, `/shutdown`, `/reboot`, `/lock`, защита Pending Choices, роутер команд и fallback на LLM).
   - `service.py` -> класс `TelegramBotService` (жизненный цикл, сессии, polling loop `getUpdates`, дроп устаревших апдейтов, graceful cancellation).
   - `__init__.py` -> чистый экспорт модулей и псевдонимов.
2. В `modules/telegram_bot.py`:
   - Сделана тонкая фасадная обертка (48 строк вместо 1004).
   - Сохранены все экспорты: `TelegramBotModule`, `TelegramBotService`, `get_telegram_bot`, `_global_telegram_bot`, `_global_telegram_bot_lock`, `_router_route_lock` и клавиатуры.
3. **Верификация:**
   - Профильные тесты `tests/test_telegram_bot_ux.py` и `tests/test_modules.py` пройдены (15 passed).
   - Полный сьют тестов пройден: 654 passed, 3 skipped.
   - OpenCode Tandem ревью: проведено.

---

## Этап 4: `core/vpn_manager.py` (980 строк) [ВЫПОЛНЕНО НА 100%]

**Проблема:** В одном классе смешаны эвристики реестра, парсинг zip/батников Zapret и автоматизация GUI через Windows UIAutomation.

### Шаги реализации:
1. Создан пакет `core/vpn/`:
   - `constants.py` -> конфигурации клиентов (Happ, FlClashX), алиасы, стоп-слова, эвристики UIA.
   - `discovery.py` -> поиск процессов, сканирование реестра Windows, ярлыков Start Menu, типовых путей и корней дисков.
   - `zapret_controller.py` -> валидация маркеров Zapret, поиск service.bat/архивов, безопасная распаковка с защитой от traversal, запуск батника.
   - `uia_driver.py` -> поиск UIA-окон клиентов, обход элементов управления, клики по кнопкам подключения, эвристика largest unlabeled button.
   - `manager.py` -> фасадный класс `VpnManager` с кэшированием статусов (TTL), управлением жизненным циклом и синглтоном `get_vpn_manager()`.
   - `__init__.py` -> чистый экспорт интерфейсов.
2. В `core/vpn_manager.py`:
   - Сделан фасадный модуль (112 строк вместо 980, сокращение на 88%).
   - Обеспечена 100% обратная совместимость: реэкспорты констант, динамический модуль-проперти `_manager`, перенаправление `_process_running` и модулей `os`, `psutil` для monkeypatch в тестах.
3. **Верификация:**
   - Профильные тесты `tests/test_vpn_manager.py` пройдены (10 passed).
   - Полный сьют тестов пройден: 659 passed, 3 skipped, 0 failed.
   - OpenCode Tandem ревью: проведено, замечания [WARN] по monkeypatch и совместимости устранены.

---

## Этап 5: Фронтенд `ui/src/components/Settings.jsx` (1497 строк) [ВЫПОЛНЕНО НА 100%]

**Проблема:** Монолитный React-компонент, где в одну кучу сброшены стейты микрофона, моделей TTS/STT, токена телеграма, обновлений и сетевых портов.

### Шаги реализации:
1. Создана директория `ui/src/components/settings/`:
   - `common.jsx` -> общие переиспользуемые UI-компоненты `Tip` и `Toggle`.
   - `UpdatesBanner.jsx` -> баннер обновлений с GitHub-ссылкой, кнопкой 1-click update и индикатором прогресса.
   - `GeneralSettings.jsx` -> именование приложения, имя ассистента, автозапуск с Windows.
   - `NeuralSettings.jsx` -> эндпоинт Ollama, селектор моделей, ползунки температуры/токенов/контекста, режим роутера.
   - `VoiceSettings.jsx` -> выбор и тестирование микрофона, wake word, загрузка Whisper, тест распознавания речи, движок TTS (голоса, скорость, громкость).
   - `SecuritySettings.jsx` -> переключатель запуска приложений вне Workspace.
   - `TelegramSettings.jsx` -> токен бота, проверка через Telegram API, список Chat ID, уведомления о старте, статус службы.
   - `RoflSettings.jsx` -> служебное слово, ползунки вероятностей рофлов, сохранение и сброс.
   - `DangerZone.jsx` -> кнопка корректного завершения работы приложения.
   - `index.js` -> единый реэкспорт компонентов.
2. В `ui/src/components/Settings.jsx`:
   - Сокращен вдвое (с 1497 до 751 строк, чистый контейнер состояния и обработчиков).
   - Сохранена полная обратная совместимость структуры DOM, стилей и обработчиков.
3. **Верификация:**
   - Сборка фронтенда: `npm --prefix ui run build` завершена успешно за 1.25s (66 трансформированных модулей).
   - Тесты бэкенд-интеграции: `pytest tests/test_ui_smoke.py` пройдены (4 passed).
   - OpenCode Tandem ревью: `[BLOCKER]: 0`. Отмечено полное совпадение разметки, стилей и props.

---

## Этап 6: Легаси слой `presentation/` (13 контроллеров PySide6) [ВЫПОЛНЕНО НА 100%]

**Проблема:** В проде (Tauri v2) из `presentation/` используется исключительно `tray_icon.py`. Остальные 13 контроллеров висят мертвым грузом старого Qt GUI.

### Шаги реализации:
1. Выделен реально используемый системный трей `presentation/tray_icon.py`.
2. Создан пакет `presentation/legacy/`:
   - Перемещены все 13 устаревших Qt-контроллеров: `alias_controller.py`, `application_controller.py`, `chat_controller.py`, `dependency_controller.py`, `ollama_controller.py`, `protocols_controller.py`, `settings_controller.py`, `statistics_controller.py`, `tools_controller.py`, `voice_controller.py`, `wake_word_controller.py`, `websites_controller.py`, `workspace_controller.py`.
   - В `presentation/legacy/__init__.py` реализован ленивый экспорт контроллеров через `__getattr__` и вызов `DeprecationWarning`.
3. В корневом `presentation/__init__.py` создана прозрачная обратная совместимость:
   - Экспортируются методы системного трея (`create_system_tray`, `create_tray_pixmap`).
   - Реализован `_LegacyPresentationFinder` (`sys.meta_path`) и `_LegacyProxyModule`, прозрачно перенаправляющие старые импорты `from presentation.<controller> import ...` в `presentation.legacy.<controller>` с сохранением идентичности классов (`is`), выдачей `DeprecationWarning` и поддержкой monkeypatching в тестах.
4. Обновлены прямые импорты в проекте (`start/main.py`, `ui_archive/main_window.py`, `ui_archive/protocols_page.py`) и тестах.
5. Актуализирована документация `presentation/README.md`.
6. **Верификация:**
   - Таргетные тесты: 39 passed in 45s.
   - Полный сьют тестов: 661 passed, 3 skipped, 0 failed.
   - OpenCode Tandem ревью: `[BLOCKER]: 0`. Замечания ревьюера по ленивому импорту и поддержке monkeypatching учтены и реализованы.

---

# Итоги выполнения плана декомпозиции монолитов

Все 6 этапов комплексного плана успешно завершены:
1. **Gateway Service** (`services/gateway_service.py`): монолит 1508 строк разбит на чистый модульный хаб и 5 роутеров (`services/gateway/`).
2. **Command Router** (`services/command_router.py`): монолит 1213 строк разбит на каталог (`services/command_catalog.py`) и диспетчеры (`services/router/`).
3. **Telegram Bot Module** (`modules/telegram_bot.py`): монолит 960 строк разбит на модули аутентификации, команд, клавиатур и оповещений (`modules/telegram/`).
4. **VPN Manager** (`core/vpn_manager.py`): монолит 980 строк разбит на сканер маркеров, Zapret-контроллер, UIA-драйвер и синглтон-менеджер (`core/vpn/`).
5. **Settings UI** (`ui/src/components/Settings.jsx`): монолит 1497 строк разбит на 9 модульных вкладок и карточек настроек (`ui/src/components/settings/`).
6. **Legacy Presentation Layer** (`presentation/`): 13 контроллеров PySide6 изолированы в `presentation/legacy/`, в корне оставлен чистый системный трей `tray_icon.py` с сохранением 100% обратной совместимости.
