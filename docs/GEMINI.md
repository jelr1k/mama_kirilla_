# GEMINI.md — Контекст и архитектурный гайд для LLM (Kirieshka v2 / mama_kirilla_)

Краткая выжимка архитектуры, актуального стека и правил для LLM/агентов при работе с репозиторием `jelr1k/mama_kirilla_` (ветки `experimental`, `osnova`).

---

## 1. О проекте и стек

**Kirieshka v2 (Jarvis)** — модульный локальный голосовой и текстовый ассистент под Windows 11 с акцентом на приватность, быстродействие и автономную работу без облаков.

- **Репозиторий:** `jelr1k/mama_kirilla_` (ветки `experimental` — активная разработка/UI, `osnova` — базовая)
- **Язык и среда:** Python 3.11+, Windows 11
- **GUI:** PySide6 (Qt) с модульным пакетом кинематических анимаций `ui/animations/`
- **Шина событий:** Кастомный `EventBus` (`core/event_bus.py`) для слабой связности компонентов
- **Слой Presentation:** 11 специализированных контроллеров для изоляции UI от бизнес-логики
- **LLM бэкенд:** Локальная Ollama (легкие модели с Tool Calling)
- **STT (распознавание):** faster-whisper
- **Wake-word:** Vosk (детекция активационной фразы)
- **TTS (синтез речи):** Piper TTS (локальные ONNX-голоса через `voice/tts/`)
- **Тесты:** pytest

---

## 2. Архитектурный поток (Data Flow)

```text
[Пользователь (UI чат / Голосовой ввод)]
                   ↓
      services/command_router.py
         /                 \
(Четкий паттерн / алиас)   (Сложный / разговорный запрос)
        ↓                                 ↓
 Прямой Tool (без LLM)           Ollama Manager (LLM)
        ↓                                 ↓
  Мгновенный ответ                 Tool Calling
                                         ↓
                                    ToolExecutor
                                         ↓
                                    EventBus / UI
```

**Критический принцип:** `CommandRouter` обязан отсекать простые команды (запуск/закрытие софта, управление медиа и звуком, телеметрия ПК, файловые операции, системные алиасы) и выполнять их напрямую через `tools/` без обращения к LLM. Запрос отправляется в Ollama только тогда, когда это свободный диалог, формулировка неоднозначна или требуется сложная композиция тулов.

---

## 3. Актуальная структура проекта

- `start/` — входные точки приложения: `bootstrap.py`, `main.py`, `check_dependencies.py`, `updater.py`.
- `core/` — фундамент системы: `application.py`, `config_manager.py`, `ollama_manager.py`, `alias_manager.py`, `event_bus.py`, `tool_executor.py`, `app_paths.py`, `target_resolver.py`.
- `presentation/` — слой контроллеров (Presenter/Controller):
  - `application_controller.py`, `chat_controller.py`, `voice_controller.py`, `wake_word_controller.py`
  - `settings_controller.py`, `statistics_controller.py`, `tools_controller.py`, `alias_controller.py`
  - `workspace_controller.py`, `dependency_controller.py`, `ollama_controller.py`
- `services/` — бизнес-логика: `command_router.py`, `chat_service.py`, `rofl_service.py`, `statistics_service.py`, `model_service.py`, сервисы автообновления (`update_service.py`, `update_checker.py`, `update_downloader.py`, `update_validator.py`, `update_backup.py`).
- `tools/` — исполняемые инструменты:
  - `applications.py`, `application_closer.py` — запуск и закрытие приложений
  - `media_control.py` — системная громкость, выключение/включение звука через Windows CoreAudio API, управление плеером
  - `system_info.py` — динамическая телеметрия железа (CPU, GPU без хардкода, RAM, диски, аптайм)
  - `file_tools.py`, `paths.py`, `security.py` — безопасная работа с файлами
  - `registry.py` — реестр и декларации Tool Calling
- `ui/` — графический интерфейс PySide6:
  - `main_window.py` — главное окно с бейджами CPU/RAM и переключением вкладок
  - Страницы: `chat_page.py`, `settings_page.py`, `statistics_page.py`, `workspace_tab.py`, `alias_page.py`, `tools_page.py`, `ollama_page.py`
  - Диалоги: `commands_window.py`, `rofl_settings_dialog.py`, `tts_assets_dialog.py`
  - Пакет `ui/animations/` — модульная система кинематических анимаций
  - `theme.py` — темная кибер-тема (deep slate, neon cyan, emerald green)
- `voice/` — голосовой пайплайн: `microphone.py`, `speech_recognizer.py`, `wake_word.py`, `command_normalizer.py`, `devices.py`, `statistics.py`, подсистема синтеза `voice/tts/` (Piper TTS).
- `config/` — конфигурация JSON, алиасы, схемы настроек.
- `docs/` — документация: `00_INDEX.md` (путеводитель), `INDEX.md` (сквозная матрица трассируемости), `01_REQUIREMENTS/`, `02_ARCHITECTURE/`.
- `tests/` — тестовый набор `pytest`.

---

## 4. Графика и анимации (`ui/animations/`)

Все анимации изолированы в пакете `ui/animations/`:

- `tab_animations.py` — `AnimatedTabBar` (hover glow при наведении на вкладки, скользящий индикатор активной вкладки) и `AnimatedTabWidget` (`SlidingStackedWidget` со скольжением страниц и централизованным сбросом состояния при быстром переключении).
- `button_animations.py` — `ButtonHoverFilter` (плавное неоновое свечение рамки/фона при наведении и тактильный прожим клика), `install_button_micro_interactions`.
- `toggle.py` — `AnimatedToggle` (неоновый свитч с плавно скользящим круглым бегунком взамен стандартных чекбоксов).
- `effects.py` — `PulsingEffect` (циклическая пульсация записи/распознавания), `SmoothScroller` (плавный скролл чата), `ThinkingIndicator` (полоса раздумий LLM), `animate_cards_entrance` (каскадное появление блоков), `fade_in_window`.
- `splash_screen.py` — `SplashScreen` (заставка Kirieshka v2 в стиле Discord со статусами и прогресс-баром при старте).

---

## 5. Жесткие правила разработки

1. **Иерархия истины:**
   - Фактический код текущей рабочей ветки (`experimental` / `osnova`) > Тесты (`pytest`) > Документация в `docs/` > Предположения.
   - Если код расходится с документацией — сначала выясняем поведение кода, а не слепо верим тексту.

2. **GUI и асинхронность:**
   - Никогда не блокировать главный поток Qt (UI). Любые тяжелые вызовы (Ollama, Piper TTS, Whisper, файловые операции) выполняются в отдельных воркерах (`QThread` / `threading`), результат возвращается через сигналы Qt или `EventBus`.

3. **Портативность путей:**
   - Никаких захардкоженных абсолютных путей (`C:\...`, `D:\...`).
   - Использовать `app_paths.py` и относительные пути от корня проекта.

4. **Система логирования:**
   - Не ломать существующую структуру логов. Ошибки обязаны попадать в специализированные логгеры и `logs/errors.log`.

5. **Безопасность и валидация:**
   - Все пути к файлам и запуск процессов проверять через правила безопасности и валидаторы проекта.

6. **Тестирование перед сдачей:**
   - Любое изменение в коде валидировать прогоном тестов (`pytest tests/`). Если затронут Command Router или Tools — запуск соответствующих тест-сьютов обязателен.

7. **Работа с Git и GitHub:**
   - Не трогать гит и гитхаб без запроса, если нужен для цели для начала спросить, а потом выполнять.
