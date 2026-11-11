# Сценарии рабочего места (Scenario Runtime)

**Статус:** спецификация и план внедрения (не реализовано)
**Область:** `core/scenarios/`, `services/router/`, `services/gateway/`, `core/vpn/`, `tools/`
**Связанные документы:** [`ARCHITECTURE.md`](ARCHITECTURE.md), [`PROTOCOLS_V2_SPEC.md`](PROTOCOLS_V2_SPEC.md), [`APP_DISCOVERY.md`](APP_DISCOVERY.md), [`COMMANDS.md`](COMMANDS.md)

---

## 1. Задача

JARVIS должен по одной команде приводить компьютер в нужное **рабочее состояние**, а не просто запускать одно приложение.

Типовой сценарий «Работа»:

1. Запустить unlocker `ag_*.exe` **от администратора**.
2. Дождаться, пока он реально поднимется и применит настройки обхода.
3. Запустить Antigravity и дождаться готовности окна/входа.
4. Запустить Discord.
5. Открыть папку проекта.
6. Пока сценарий активен — периодически проверять здоровье unlocker и чинить известные проблемы.
7. При переключении на другой сценарий — закрыть приложения и **выключить все функции** unlocker, а не просто убить процесс.

Ключевая метрика: **сколько ручных кликов и секунд ожидания убрано**. Если сценарий не экономит действия — он не нужен.

---

## 2. Ключевые понятия

| Понятие | Определение |
|---|---|
| **Scenario** | Именованное желаемое состояние рабочего места + правила настройки приложений. |
| **Desired state** | Что должно быть запущено, какие громкость/медиа/сеть, какие приложения закрыты. |
| **AppAdapter** | Адаптер конкретного приложения: обнаружение, запуск, ожидание готовности, настройка, проверка, деактивация. |
| **Readiness gate** | Условие «приложение реально готово»: процесс → окно → UIA-элемент → сеть/туннель. |
| **Ownership** | Сценарий владеет только тем, что запустил сам. Чужие процессы не закрываются. |
| **Operation** | Единица работы с id, шагами, прогрессом, отменой и результатом. Сценарий — родительская операция, шаги — дочерние. |
| **Deactivate** | Обратное приведение приложения в нейтральное состояние: выключить функции, затем закрыть. |

### 2.1. Главный принцип

Сценарий — это **не список шагов**, а **декларация конечного состояния**. Движок сам считает разницу между «как сейчас» и «как надо» и выполняет только недостающие действия.

Почему так:

- повторный запуск идемпотентен;
- переключение сценариев — это diff, а не второй скрипт;
- частичный сбой не отменяет остальные шаги;
- отчёт показывает, что именно было изменено.

---

## 3. Модель данных

### 3.1. Файл сценариев

Новый файл: `%APPDATA%\Jarvis\scenarios.json` (рядом с `protocols.json`).

В `core/app_paths.py` добавить:

```python
SCENARIOS_FILE = APP_DATA_DIR / "scenarios.json"
```

Схема:

```json
{
  "version": 1,
  "active": null,
  "scenarios": {
    "work": { "...": "см. ниже" }
  }
}
```

### 3.2. Сценарий «Работа»

```json
{
  "id": "work",
  "name": "Работа",
  "phrases": ["работа", "на работу", "рабочий режим", "протокол работа"],
  "desired": {
    "volume": 40,
    "media": "pause",
    "apps": {
      "unlocker": {
        "running": true,
        "elevated": true,
        "keep_running": true,
        "wait": "ready",
        "config": {
          "account": true,
          "error_400": true,
          "group_proxy": false,
          "autopatch": true,
          "dns_bypass": true,
          "local_proxy": true,
          "builtin_exits": true,
          "custom_proxy": true
        }
      },
      "antigravity": {
        "running": true,
        "wait": "window",
        "depends_on": ["unlocker"]
      },
      "discord": {
        "running": true,
        "wait": "window"
      },
      "project_folder": {
        "running": true,
        "type": "folder",
        "path": "D:\\putin\\kirieshkav2\\mama_kirilla_-osnova",
        "wait": "window"
      }
    }
  },
  "configure": {},
  "close": ["steam", "game"],
  "health": {
    "interval_seconds": 30,
    "apps": ["unlocker"]
  }
}
```

### 3.3. Семантика полей

| Поле | Смысл |
|---|---|
| `phrases` | Голосовые/текстовые триггеры. |
| `desired.apps.*.running` | `true` — ensure running, `false` — ensure stopped. |
| `elevated` | Запуск с повышением прав (UAC). Только для явно разрешённых приложений. |
| `keep_running` | Не закрывать приложение после завершения сценария. Закрытие — только при переключении или явной деактивации. |
| `depends_on` | DAG-зависимости: приложение запускается после готовности указанных. |
| `wait` | Гейт готовности: `process`, `window`, `uia`, `tunnel`, `none`. |
| `type` | `app` (по умолчанию) или `folder`. |
| `config` | Желаемое состояние внутренних функций приложения (для unlocker — тумблеры и режимы). |
| `configure` | Дополнительные хуки после запуска. `optional:` — сбой не валит сценарий. |
| `close` | Что закрыть явно. Только перечисленное; остальное не трогать. |
| `health` | Какие приложения и как часто проверять, пока сценарий активен. |

### 3.4. Совместимость с `protocols.json`

`protocols.json` остаётся рабочим. `ScenarioManager` при первом запуске:

1. читает `protocols.json`;
2. конвертирует `open_apps`, `close_mode`, `close_apps`, `volume_mode`, `pause_media`, `lock_screen`, `clean_recycle_bin` в `scenarios.json`;
3. **не удаляет** старый файл.

Роутер сначала ищет сценарий, затем — старый протокол. Это позволяет мигрировать по одному сценарию без большого взрыва.

---

## 4. Исполнение

### 4.1. Фазы `ScenarioRunner`

```
run(scenario_id)
├─ 1. resolve       — загрузить сценарий, проверить схему
├─ 2. snapshot      — снять текущее состояние (процессы, окна, громкость, медиа)
├─ 3. plan          — diff desired vs actual, топологическая сортировка по depends_on
├─ 4. deactivate    — если активен другой сценарий, сначала деактивировать его
├─ 5. stop          — закрыть явно перечисленное в close (с подтверждением, если необратимо)
├─ 6. activate      — по фазам DAG:
│      ├─ ensure_running(app)
│      ├─ wait_ready(app)
│      └─ configure(app)
├─ 7. global        — громкость, медиа, блокировка и т.п.
├─ 8. verify        — проверить, что desired достигнут
├─ 9. report        — вернуть структурированный отчёт и опубликовать события
└─ 10. health loop  — если включён, запустить периодические проверки
```

### 4.2. Diff и идемпотентность

Для каждого приложения:

| Сейчас | Надо | Действие |
|---|---|---|
| не запущено | `running: true` | launch + wait_ready + configure |
| запущено | `running: true` | wait_ready (если нужно) + configure только при `force_configure` |
| запущено | `running: false` | deactivate + close (если owned или в `close`) |
| не запущено | `running: false` | ничего |

`configure` по умолчанию выполняется только для приложений, которые сценарий запустил сам. Для уже запущенных — только если явно указано `force_configure: true`.

### 4.3. Зависимости

`depends_on` образует DAG. Движок:

1. строит граф;
2. находит циклы → ошибка конфигурации, сценарий не запускается;
3. выполняет топологическими слоями: слой N+1 стартует после готовности всех зависимостей слоя N.

Пример: `unlocker` → (`antigravity`, `discord`) → `project_folder`.

### 4.4. Ожидание готовности (`core/scenarios/wait.py`)

```python
def wait_until(predicate, timeout: float, interval: float = 0.5, description: str = "") -> bool: ...
def wait_process(names: Iterable[str], timeout: float) -> bool: ...
def wait_window(pid: int, title_re: str | None, timeout: float) -> bool: ...
def wait_uia(pid: int, locator: UiaLocator, timeout: float) -> bool: ...
def wait_tcp(host: str, port: int, timeout: float) -> bool: ...
```

Правила:

- Всегда есть таймаут. Бесконечных ожиданий нет.
- Ожидание прерываемое: проверять `operation.cancelled`.
- Ошибка ожидания — это результат шага, а не исключение наружу.
- Для окон использовать `win32gui.EnumWindows`/UIA по PID, а не поиск по заголовку целиком.

### 4.5. Операции и события

Сценарий — родительская операция. Каждый шаг — дочерняя. События в `EventBus`:

```
scenario.started    {scenario_id, operation_id}
scenario.step       {operation_id, app_id, step, status, detail}
scenario.health     {scenario_id, items: [...]}
scenario.finished   {scenario_id, success, report, duration_ms}
scenario.failed     {scenario_id, step, error}
scenario.deactivated{scenario_id}
```

Fast lane не затрагивается: «громкость +10», «скриншот», «время» остаются прямыми вызовами без операций.

### 4.6. Отчёт

```json
{
  "scenario": "work",
  "success": true,
  "duration_ms": 8420,
  "started": ["unlocker", "antigravity", "discord"],
  "configured": ["unlocker", "antigravity"],
  "closed": ["steam"],
  "skipped": ["project_folder"],
  "steps": [
    {"app": "unlocker", "step": "launch", "status": "ok", "ms": 1200},
    {"app": "unlocker", "step": "wait_ready", "status": "ok", "ms": 2400},
    {"app": "antigravity", "step": "wait_window", "status": "ok", "ms": 3100}
  ],
  "warnings": []
}
```

Отчёт — обязательная часть. Он же показывается в UI, отправляется в Telegram и озвучивается.

---

## 5. Адаптеры приложений

### 5.1. Контракт

```python
class AppAdapter(Protocol):
    app_id: str

    def detect(self) -> AppState: ...
    def launch(self) -> None: ...
    def wait_ready(self, timeout: float) -> bool: ...
    def configure(self, config: dict) -> list[StepResult]: ...
    def verify(self) -> bool: ...
    def health_check(self) -> list[HealthItem]: ...
    def remediate(self, item: HealthItem) -> bool: ...
    def deactivate(self) -> list[StepResult]: ...
```

`AppState`:

```python
@dataclass
class AppState:
    running: bool
    elevated: bool | None
    pid: int | None
    window_ready: bool
    owned: bool
    detail: dict
```

`HealthItem`:

```python
@dataclass
class HealthItem:
    id: str
    state: Literal["ok", "needs_fix", "unknown", "needs_user"]
    detail: str
    fixable: bool
```

### 5.2. Generic-адаптер

Покрывает большинство приложений:

- `detect` — `tools.applications.get_process_status` / `psutil`;
- `launch` — `tools.applications.launch_application(target, allow_outside_workspace=True)` или `os.startfile`;
- `wait_ready` — процесс + окно по PID;
- `configure` — no-op;
- `deactivate` — `tools.application_closer.close_application`, только если owned.

### 5.3. Реестр и разрешение путей

```python
ADAPTERS: dict[str, type[AppAdapter]] = {
    "unlocker": UnlockerAdapter,
    "antigravity": AntigravityAdapter,
    "discord": GenericAdapter,
    "project_folder": FolderAdapter,
}
```

Разрешение исполняемого файла:

1. явный `path` в конфиге приложения;
2. `AppIndexer.resolve_app(query)`;
3. `find_application(query)`;
4. glob по `install_dir` (`ag_*.exe`) с выбором старшей версии.

**Запрещено** хардкодить `C:\...` и версию `2.29.0`. Версия меняется — путь должен находиться динамически.

### 5.4. `UnlockerAdapter` (`ag_*.exe`)

Самый сложный адаптер. Управляет не только процессом, но и внутренними функциями.

#### 5.4.1. Запуск

- Найти `ag_*.exe` (см. 5.3).
- Запустить с повышением прав:

```python
ctypes.windll.shell32.ShellExecuteW(
    None, "runas", str(exe), None, str(exe.parent), 1
)
```

- Это единственное разрешённое место повышения прав. Никаких shell-строк.
- Если UAC отклонён — шаг `needs_user`, сценарий не валится целиком, но `unlocker` помечается как неготовый, а зависимые приложения не запускаются.

#### 5.4.2. Готовность

`wait_ready` = процесс + главное окно + наличие ключевых элементов управления (не просто «процесс жив»).

Перед чтением настроек развернуть секцию «Настройки для опытных», если она свёрнута: найти элемент с именем «Настройки для опытных» и проверить `ExpandCollapsePattern`; если `Collapsed` — развернуть.

#### 5.4.3. Карта UI и проверки здоровья

Окно: **Antigravity Unlocker 2 v2.29.0** (версия в заголовке меняется).

Сверху вниз:

| # | Элемент | Тип | Желаемое |
|---|---|---|---|
| 1 | Баннер статуса «Работает» / «Модель ответила только что · путь: ...» | Text | только чтение |
| 2 | «Вход в аккаунт из-под санкций» | Toggle | ON |
| 3 | «Снять ошибку 400 в чате с ИИ» | Toggle | ON |
| 4 | «Прокси из группы» (+ «Скопировать команду», «Открыть группу», поле кода) | Toggle + кнопки | OFF |
| 5 | «Автопатч» | Toggle | ON |
| 6 | «Настройки для опытных» | Expander | развернуть |
| 7 | «Обход через DNS» (+ поле «Свой DNS для обхода», «Применить») | Toggle + Edit | ON |
| 8 | «Локальный прокси» | Toggle | ON |
| 9 | «Встроенные выходы» | Toggle | ON |
| 10 | «Свой HTTP-прокси» (+ поле прокси, «Применить») | Toggle + Edit | ON |

Проверки здоровья:

| id | Элемент UI (Name) | Желаемое | Автоисправление |
|---|---|---|---|
| `account` | «Вход в аккаунт из-под санкций» | ON | Переключить в ON. Пароли не вводить. |
| `error_400` | «Снять ошибку 400 в чате с ИИ» | ON | Переключить в ON. Если поверх открыт диалог 400 — закрыть, не более 3 раз. |
| `group_proxy` | «Прокси из группы» | OFF | Переключить в OFF. |
| `autopatch` | «Автопатч» | ON | Переключить в ON. |
| `dns_bypass` | «Обход через DNS» | ON | Переключить в ON. |
| `local_proxy` | «Локальный прокси» | ON | Переключить в ON. |
| `builtin_exits` | «Встроенные выходы» | ON | Переключить в ON. |
| `custom_proxy` | «Свой HTTP-прокси» | ON | Переключить в ON. Значение поля не перезаписывать без явного запроса. |

Дополнительно, только для отчёта (не исправлять):

| id | Источник | Что читаем |
|---|---|---|
| `status` | верхний баннер | «Работает» или текст ошибки |
| `active_path` | строка «Первый путь сейчас: ...» | `свой прокси`, `VPN`, `встроенные выходы` |

Правила:

- **Никогда не кликать вслепую.** Если элемент не найден однозначно — `unknown`, а не «нажмём самую большую кнопку».
- Искать по `Name` (подпись секции), а не по координатам. Тип переключателя уточнить через UIA-дамп: вероятно `ButtonControl` с `TogglePattern` или `CheckBoxControl`.
- Состояние читать через `TogglePattern.ToggleState`. Если паттерн недоступен — `unknown`, не угадывать.
- Переключение: `TogglePattern.Toggle()`; fallback — `InvokePattern.Invoke()`, затем `Click(simulateMove=False)`.
- После переключения — повторная проверка состояния. Если не изменилось, `needs_fix`, не циклить.
- Все действия логируются: `unlocker.health`, `unlocker.remediate`, что нашли, что нажали.
- Поле «Свой HTTP-прокси» не логировать и не коммитить: там могут быть credentials.

#### 5.4.4. Деактивация

При переключении сценария:

1. выключить `dns_bypass`, `local_proxy`, `exit_mode` → прямой режим;
2. вернуть `group_proxy` в исходное состояние, если сценарий его менял;
3. закрыть процесс;
4. проверить, что процесс завершён.

Порядок важен: сначала выключить функции, потом закрывать. Иначе можно оставить систему в состоянии «VPN выключен, но маршруты остались».

#### 5.4.5. Что нельзя делать

- Не хранить и не вводить логины/пароли.
- Не обходить UAC молча.
- Не нажимать кнопки, смысл которых не подтверждён UIA-локтором.
- Не пытаться «починить» аккаунт автоматически.

### 5.5. `AntigravityAdapter`

- `detect` — процесс `antigravity*.exe`, окно по PID.
- `launch` — `find_application`/`AppIndexer`, без хардкода.
- `wait_ready` — окно + признак загрузки IDE (например, наличие главного тулбара).
- `configure` — `ensure_signed_in`: проверить, что вход выполнен; если нет — `needs_user`, не вводить credentials.
- `deactivate` — закрыть окно/процесс, только если owned.

### 5.6. `DiscordAdapter`

Наследует generic. Опциональные хуки:

- `mute_mic` — через UIA или горячую клавишу, если настроено;
- `join_channel` — только если пользователь явно указал канал.

По умолчанию — просто запуск и ожидание окна.

### 5.7. `FolderAdapter`

- `type: "folder"`, `path` обязателен.
- `launch` — `os.startfile(path)` (без shell).
- `wait_ready` — окно Проводника с этим путём в заголовке (best effort).
- `deactivate` — закрыть именно это окно, не все Проводники. Если не удалось однозначно определить — свернуть/оставить, записать warning.
- Путь проходит проверку допустимых директорий (см. раздел 8).

---

## 6. Переключение сценариев

```python
def switch_to(target_id: str) -> Report:
    if active == target_id:
        return no_op()
    if active:
        deactivate(active)      # обратный порядок активации
    report = run(target_id)
    active = target_id
    return report
```

Правила:

1. **Обратный порядок.** Деактивация идёт от последнего запущенного к первому: папка → Discord → Antigravity → unlocker. Сеть выключается последней.
2. **Ownership.** Закрывается только то, что сценарий запустил сам. Если приложение было открыто до сценария — оно `external`, не закрывается.
3. **Явный `close`.** Приложения из `close` закрываются, но с подтверждением, если действие необратимо (например, есть несохранённые данные — определить нельзя, поэтому подтверждаем закрытие сторонних приложений).
4. **Идемпотентность.** Повторный `switch_to` в тот же сценарий — no-op.
5. **Частичный сбой деактивации.** Если unlocker не удалось выключить, `active` не меняется, событие `scenario.failed`, пользователю показывается, что именно осталось включённым.

---

## 7. Интеграция с существующим кодом

### 7.1. Новые модули

```
core/scenarios/
  __init__.py
  models.py          # Scenario, DesiredState, AppSpec, StepResult, HealthItem
  store.py           # scenarios.json: load/save/validate, миграция protocols.json
  registry.py        # AppAdapter registry
  runner.py          # ScenarioRunner
  wait.py            # WaitEngine
  adapters/
    __init__.py
    generic.py
    unlocker.py
    antigravity.py
    discord.py
    folder.py
```

### 7.2. Что переиспользовать, а не писать заново

| Существующее | Как использовать |
|---|---|
| `core/vpn/uia_driver.py` | Вынести общие функции в `core/uia/`: `find_window_by_pids`, `iter_controls`, `find_control`, `invoke`, `set_toggle`. `core.vpn.uia_driver` оставить тонким re-export для совместимости. |
| `core/vpn/discovery.py` | Шаблоны поиска процессов и путей. |
| `tools/applications.py` | `find_application`, `launch_application(allow_outside_workspace=True)`, `get_process_status`. |
| `tools/application_closer.py` | `close_application` для деактивации. |
| `core/app_indexer.py` | `resolve_app` для динамического поиска. |
| `core/target_resolver.py`, `core/alias_manager.py` | Алиасы и человеческие имена. |
| `core/app_paths.py` | `SCENARIOS_FILE`. |
| `core/events.py`, `core/task_runner.py` | События и фоновое исполнение. |
| `security/permissions.py` | Права на запуск/закрытие/повышение. |

### 7.3. Роутер и голос

В `services/router/protocols_dispatcher.py`:

```python
def dispatch_protocol_command(text, protocols_manager, config, scenario_manager=None):
    if scenario_manager:
        scenario = scenario_manager.find_by_phrase(text)
        if scenario:
            return scenario_manager.run_blocking(scenario.id)
    # старый путь — fallback
    ...
```

`CommandRouter` получает `scenario_manager` так же, как сейчас получает `protocols_manager`. Голосовых фраз достаточно из `phrases`.

### 7.4. Gateway API

Новый роутер `services/gateway/routers/scenarios.py`:

```
GET  /api/scenarios
GET  /api/scenarios/active
GET  /api/scenarios/{id}
POST /api/scenarios/{id}/run
POST /api/scenarios/{id}/switch
POST /api/scenarios/deactivate
GET  /api/scenarios/{id}/health
```

Ответы — те же структуры, что в отчёте. Все действия требуют авторизации шлюза, как остальные маршруты.

### 7.5. UI

В v1 UI не обязателен. Достаточно событий и отчёта. Позже:

- панель «Активный сценарий» с прогрессом шагов;
- список health-проверок unlocker с кнопкой «Починить»;
- кнопка «Переключить» между сценариями.

### 7.6. Совместимость

- `protocols.json` и `StarkProtocols` не удаляются до паритета.
- `StarkProtocols.execute_protocol("work")` (жёстко зашитый `opera`/`antigravity`/`unlocker`) заменяется сценарием `work` только после приёмки.
- `PROTOCOLS_V2_SPEC.md` остаётся теоретической базой; этот документ — практическая реализация.

---

## 8. Безопасность и права

1. **Повышение прав** — только через `ShellExecuteW(..., "runas", ...)` и только для приложений из белого списка (`unlocker`). UAC-отказ — штатная ситуация, не ошибка.
2. **Никаких shell-строк.** Запуск — только по проверенному пути. Никаких `cmd /c`, `powershell -Command` и склейки аргументов.
3. **Пути папок** — проверять по списку разрешённых корней из конфига. Не открывать произвольный путь из голосовой команды.
4. **Закрытие процессов** — только owned или явно перечисленные в `close`. Системные процессы и процессы JARVIS/Ollama не трогать (см. `PROTECTED_PROCESS_NAMES`).
5. **Credentials** — не хранить, не вводить, не логировать.
6. **UIA** — не кликать по координатам и не нажимать «самую большую кнопку». Только однозначные локаторы.
7. **Права** — добавить `scenario.run`, `scenario.switch`, `scenario.elevate`, `scenario.close_external` в `PermissionManager`.

---

## 9. Ошибки и восстановление

| Ситуация | Поведение |
|---|---|
| UIA не установлен | `unlocker` → `needs_user`, остальные приложения запускаются, если не зависят от unlocker. |
| Окно не появилось за таймаут | Шаг `failed`, зависимые пропускаются, отчёт с причиной. |
| Ошибка 400 повторяется | До 3 попыток закрыть, затем `needs_user`, health loop не циклится. |
| Приложение уже запущено | Не перезапускать, помечать `external` или `owned` по факту запуска. |
| Unlocker не выключился | `switch` отменяется, `active` не меняется, событие `scenario.failed`. |
| Папка не найдена | `warning`, сценарий продолжается. |
| Отменён пользователем | Все шаги проверяют `cancelled`, деактивация уже запущенного выполняется. |

---

## 10. Наблюдаемость

- Каждый шаг: `app_id`, `step`, `status`, `duration_ms`, `detail`.
- Health loop: `scenario.health` раз в интервал, с списком `HealthItem`.
- Лог: `logs/commands.log` для запусков, `logs/jarvis.log` для ошибок, отдельный `logs/scenarios.log` — по желанию.
- Отчёт доступен через `GET /api/scenarios/{id}` и последний — через `GET /api/scenarios/active`.

---

## 11. Тестирование

1. **Unit** — `models`, `store`, diff, топологическая сортировка, ownership, switch. Без Windows и без реальных приложений.
2. **Fake adapters** — сценарные состояния (`not_running` → `running` → `ready` → `failed`), проверка отчёта и событий.
3. **Dry-run** — `dry_run=True`: адаптеры не выполняют side effects, только логируют план. Обязателен для отладки.
4. **UIA smoke** — отдельный маркер `@pytest.mark.uia`, только Windows, запускается вручную. Для безопасного теста — Notepad как generic adapter.
5. **Ручной приёмочный прогон** — реальный сценарий «Работа» на машине пользователя.

---

## 12. План внедрения

| Этап | Что делаем | Результат |
|---|---|---|
| **P0** | Вынести `core/uia/`, добавить `wait.py`, тесты | Общая база UIA и ожиданий |
| **P1** | `models`, `store`, `registry`, `runner`, generic adapter | Сценарий запускает/закрывает приложения |
| **P2** | Сценарий `work` без настройки: unlocker, antigravity, discord, папка | Вертикальный срез, экономит клики |
| **P3** | `UnlockerAdapter`: health-проверки и автоисправления | Unlocker реально настроен |
| **P4** | Переключение, деактивация, ownership | `work` ↔ `game` без ручных действий |
| **P5** | Роутер, голос, Gateway API | Управление из UI/Telegram |
| **P6** | Перенос остальных протоколов | `protocols.json` можно архивировать |
| **P7** | Триггеры (`app.launched` → сценарий) | Автоматизация без команды |

Каждый этап шипается отдельно. P2 — главный: если он не экономит время, дальше идти не надо.

---

## 13. Критерии приёмки

1. Команда «работа» запускает unlocker (с UAC), Antigravity, Discord и папку проекта в правильном порядке.
2. Повторная команда «работа» не перезапускает уже открытое и не ломает состояние.
3. Unlocker проверяет 6 пунктов и умеет автоматически: закрыть 400, включить DNS-обход, включить локальный прокси, выбрать режим выходов, отключить групповой прокси.
4. Если аккаунт не залогинен — сценарий сообщает об этом и не пытается вводить пароль.
5. Переключение на другой сценарий выключает функции unlocker и закрывает Antigravity, Discord и папку.
6. Чужие приложения не закрываются.
7. В отчёте видно, что запустилось, что настроилось, что не удалось и сколько это заняло.
8. Нет хардкода `C:\...` и версии `ag_2.29.0`; путь находится динамически.
9. `pytest tests/` зелёный; UIA-тесты — отдельным маркером.

---

## 14. Не-цели

- Универсальный workflow engine.
- LLM-планировщик, который «сам решает», что запускать.
- Хранение операций в базе данных.
- Автоматический ввод паролей и обход UAC.
- Поддержка не-Windows платформ.
- Полный UI-конструктор сценариев в первой версии.

---

## 15. Открытые вопросы

1. Точные UIA-локаторы (Name/AutomationId) для переключателей unlocker: DNS-обход, локальный прокси, групповой прокси, режим выходов. Нужен UIA-дамп окна.
2. «Вход в акк из-под санкций» — это вход в Antigravity или в unlocker? От этого зависит, какой адаптер проверяет `account`.
3. «Отрублен ли прокси из группы» — желаемое состояние `false` (выключен) или `true`? В спецификации принято `false`; подтвердить.
4. Discord: нужно ли автоматически мьютить микрофон/заходить в канал, или достаточно запуска?
5. Путь папки проекта — фиксированный или выбирается в настройках сценария?
6. Unlocker должен оставаться открытым после запуска «Работы» (для health loop) или его можно закрыть? По текущей модели — остаётся, health loop работает.
7. UAC-подтверждение при каждом запуске — приемлемо? Если нет, нужен другой механизм (служба/планировщик), это отдельная задача.
8. Что считать «готовностью» Antigravity: окно, тулбар, отсутствие сплэша, вход в аккаунт?
