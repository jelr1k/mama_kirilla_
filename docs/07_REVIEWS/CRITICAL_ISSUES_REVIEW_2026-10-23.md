# Критический аудит кодовой базы JARVIS (Kirieshka v2)

**Дата:** 2026-10-23  
**Статус:** КРИТИЧЕСКИЕ ДЕФЕКТЫ («ИСПРАВИТЬ ПРЯМ СЕЙЧАС, ИНАЧЕ ПИЗДА ВСЕМУ»)  
**Область:** безопасность данных, зависания UI, системные вызовы Windows, блокировки потоков, утечки ресурсов.

---

## 1. Тихая перезапись файлов пользователя при `copy_file` и `move_file` (Потеря данных)

- **Где этот код:**  
  [`tools/files.py`](tools/files.py#L139-L176) (функции `copy_file` строки 139–155 и `move_file` строки 158–176).

- **Почему он спорный и опасный:**  
  В документации (`INDEX.md`, `IMPLEMENTATION_STATUS.md`) чёрным по белому написано, что реализована защита от случайной перезаписи файлов (`overwrite=False`).  
  **В реальности в коде никакой проверки нет вообще!**  
  ```python
  # tools/files.py
  copied = Path(shutil.copy2(source, target))
  # и в move_file:
  moved = Path(shutil.move(str(source), str(target)))
  ```
  Код вычисляет `expected = target / source.name` или `expected = target`, но перед вызовом `shutil.copy2` или `shutil.move` **не проверяет** `if expected.exists()`. `shutil.copy2` и `shutil.move` в Python на уровне ОС молча затирают существующий целевой файл.

- **На что повлияет:**  
  Если в целевой папке уже лежит файл с таким же именем (например, важный отчёт или конфиг), а пользователь или LLM командует скопировать или переместить файл — **старый файл уничтожается безвозвратно и без предупреждений**. Никакого отката нет.

- **Как исправить прямо сейчас:**  
  Перед вызовом `shutil.copy2` / `shutil.move` добавить явную проверку:
  ```python
  if expected.exists():
      return _result(False, path=expected, error=f"Целевой файл уже существует: {expected.name}. Перезапись заблокирована.")
  ```

---

## 2. Невозможность удалить директорию и ложный `PermissionError` при удалении папок

- **Где этот код:**  
  [`tools/files.py`](tools/files.py#L104-L121) (функция `delete_file`).

- **Почему он спорный и опасный:**  
  В `CommandRouter` команда «удали папку X» отправляется в тул `delete_file`. Тул выполняет:
  ```python
  file_path.unlink()
  ```
  В Python метод `Path.unlink()` предназначен **только для файлов**. Если `file_path` — это директория, на Windows вылетает `PermissionError: [WinError 5] Отказано в доступе`, а на Linux/macOS — `IsADirectoryError: [Errno 21] Is a directory`.  
  При этом отдельного инструмента `delete_folder` в `tools/files.py` и `tools/registry.py` вообще не существует!

- **На что повлияет:**  
  Любая попытка удалить папку через ассистента терпит крах, а пользователю выводится ложное сообщение: *«Нет прав на удаление: Отказано в доступе»*, заставляя думать, что слетели права доступа Windows или UAC, хотя это грубый баг вызова системного API.

- **Как исправить прямо сейчас:**  
  В `delete_file` проверять тип объекта:
  ```python
  if file_path.is_dir():
      shutil.rmtree(file_path)
  else:
      file_path.unlink()
  ```

---

## 3. Намертво виснущий интерфейс при закрытии приложений (`close_application`)

- **Где этот код:**  
  [`tools/application_closer.py`](tools/application_closer.py#L90-L105) (строки 90 и 103), вызываемый через [`services/command_router.py`](services/command_router.py#L213-L223).

- **Почему он спорный и опасный:**  
  В `close_application` прописано:
  ```python
  gone, alive = psutil.wait_procs(processes, timeout=5)
  ...
  if alive:
      ...
      gone_after_kill, alive_after_kill = psutil.wait_procs(alive, timeout=3)
  ```
  Суммарный таймаут ожидания составляет **до 8 секунд**.  
  Команда «закрой Steam» после подтверждения пользователем («да») исполняется в методе `execute_confirmed()` **синхронно прямо в главном GUI-потоке Qt** (потому что вызов идёт из обработчика UI `chat_controller.send()`).

- **На что повлияет:**  
  Главное окно Jarvis на 5–8 секунд превращается в «белый экран» со статусом Windows *«Jarvis (Не отвечает)»*. Пользователь кликает, система думает, что приложение упало, и предлагает принудительно его завершить.

- **Как исправить прямо сейчас:**  
  Вынести выполнение `execute_confirmed` (или как минимум тяжёлых системных тулов вроде `close_application`, `media`, `telemetry`) в `TaskRunner` (фоновый пул потоков), а результат возвращать через сигнал/колбэк, не блокируя UI-поток Qt.

---

## 4. Утечка COM-интерфейсов Windows и задержки в главном потоке в `media_control.py`

- **Где этот код:**  
  [`tools/media_control.py`](tools/media_control.py#L39-L80) (`_get_audio_endpoint_volume`) и строки 122–132 (`_send_key`).

- **Почему он спорный и опасный:**  
  1. **Утечка COM-объектов:** `_get_audio_endpoint_volume()` вызывает `ole32.CoInitialize(None)`, создаёт COM-объекты `p_enum`, `p_device`, `p_endpoint_vol` через `CoCreateInstance` и `get_default_endpoint`. **Ни для одного из них не вызывается метод `Release()` (vtable[2])!** Также никогда не вызывается `CoUninitialize()`. При каждом опросе состояния звука (`get_master_mute()`) или изменении громкости в памяти процесса текут COM-указатели и удерживаются открытые дескрипторы службы `audiosrv` Windows.
  2. **Синхронный `sleep` на 1 секунду:** В `_send_key` при шагах регулировки звука (до 25 шагов из роутера) стоит:
     ```python
     for _ in range(repeat):
         user32.keybd_event(vk, 0, 0, 0)
         user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
         if repeat > 1:
             time.sleep(0.04)
     ```
     `25 * 0.04 = 1.0` секунда блокирующего сна. И это снова вызывается из `CommandRouter` синхронно на UI-потоке!

- **На что повлияет:**  
  Деградация стабильности работы с аудиоустройствами Windows при длительной работе, фризы интерфейса на секунду при любой голосовой или текстовой команде «сделай громче 50».

- **Как исправить прямо сейчас:**  
  1. Вызывать `Release()` для интерфейсов `p_device` и `p_enum` сразу после извлечения конечной точки громкости.
  2. Убрать задержку `time.sleep(0.04)` или свести её к минимуму (`0.005`), либо выполнять отправку медиа-событий асинхронно.

---

## 5. Зависание закрытия программы (`closeEvent` freeze) из-за ожидания Ollama

- **Где этот код:**  
  [`ui/main_window.py`](ui/main_window.py#L117-L121) (`closeEvent`), [`core/application.py`](core/application.py#L165) (`shutdown()`) и [`core/ollama_manager.py`](core/ollama_manager.py#L132-L144) (`unload_model`).

- **Почему он спорный и опасный:**  
  При нажатии на крестик окна срабатывает `closeEvent`:
  ```python
  self.hide()
  self.application_controller.shutdown()
  ```
  Внутри `shutdown()` синхронно вызывается `ollama_manager.shutdown_for_app()` -> `unload_models()`. Внутри `unload_model` крутится цикл с сетевыми запросами к Ollama:
  ```python
  deadline = time.monotonic() + 5
  status = self.get_model_status(model)
  while status is not None and time.monotonic() < deadline:
      time.sleep(0.25)
      status = self.get_model_status(model)
  ```
  Если сервер Ollama перегружен или выгружаются 2 модели, этот цикл спит до 5–10 секунд прямо в обработчике закрытия окна.

- **На что повлияет:**  
  Окно визуально исчезает (`self.hide()`), но процесс `python.exe` продолжает висеть в фоне до 10-15 секунд, держа заблокированными лог-файлы в `logs/`. Если пользователь сразу кликает `start.bat`, чтобы запустить Jarvis заново, запуск ломается с ошибкой доступа к файлам или плодит конфликтные зомби-процессы.

- **Как исправить прямо сейчас:**  
  В `shutdown()` отправлять асинхронный запрос на выгрузку модели с коротким сетевым таймаутом (1 сек), не блокируя выход процесса жестким `while sleep`.

---

## 6. Зависание на 30+ секунд при опросе телеметрии с сетевыми или спящими дисками

- **Где этот код:**  
  [`tools/system_info.py`](tools/system_info.py#L88-L96).

- **Почему он спорный и опасный:**  
  ```python
  for partition in psutil.disk_partitions(all=False):
      try:
          usage = psutil.disk_usage(partition.mountpoint)
  ```
  На Windows `psutil.disk_partitions(all=False)` возвращает все смонтированные буквы дисков, включая отключенные сетевые шары (SMB/диски `Z:\`), виртуальные приводы и кардридеры.  
  Вызов `psutil.disk_usage()` к сетевому диску, сервер которого недоступен, вызывает блокировку потока на полный таймаут Windows SMB (от 20 до 45 секунд!). А на пустом CD/DVD приводе Windows может выплюнуть модальное системное окно с ошибкой устройства.

- **На что повлияет:**  
  При команде «нагрузка пк» или «телеметрия» Jarvis намертво виснет на полминуты, если у пользователя подключен хотя бы один неактивный сетевой диск или спящий внешний накопитель.

- **Как исправить прямо сейчас:**  
  Фильтровать разделы по типу файловой системы или `opts`: пропускать `cdrom`, сетевые пути и проверять флаг `removable` перед вызовом `disk_usage`, либо опрашивать только диск с установленной ОС (`C:\`) и корень проекта.

---

## 7. Фоновая генерация LLM не останавливается при выходе (`_shutting_down`)

- **Где этот код:**  
  [`services/chat_service.py`](services/chat_service.py#L153-L194) (`_run_generation`) и строки 378–391 (`shutdown`).

- **Почему он спорный и опасный:**  
  В `shutdown()` вызывается `self._generation_future.cancel()`. В стандартной библиотеке Python `concurrent.futures` вызов `Future.cancel()` **не прерывает уже выполняющийся поток**, если задача уже стартовала.  
  При этом внутри цикла генерации `_run_generation`:
  ```python
  for round_number in range(1, 6):
      ...
      for item in self.provider.stream_chat(request):
          ...
      for tool_call in tool_calls:
          ...
          result = executor.execute(tool_name, arguments, self._confirm_tool)
  ```
  **Нигде не проверяется `if self._shutting_down: break`!**

- **На что повлияет:**  
  Пользователь закрыл приложение, а генератор в фоне продолжает делать запросы к Ollama, выполнять последующие раунды Tool Calling, читать и писать файлы на диске.

- **Как исправить прямо сейчас:**  
  Внутри генератора `_run_generation` на каждой итерации чанков и перед каждым вызовом `executor.execute()` проверять:
  ```python
  if self._shutting_down:
      logger.info("generation_aborted_due_to_shutdown")
      return None
  ```

---

## 8. Несоответствие схемы инструмента `control_media` в `ToolRegistry`

- **Где этот код:**  
  [`tools/registry.py`](tools/registry.py#L127-L142).

- **Почему он спорный и опасный:**  
  В схеме тула для LLM прописано:
  ```json
  "action": {
      "type": "string",
      "enum": ["volume_up", "volume_down", "volume_mute", "play_pause", "next_track", "prev_track"]
  }
  ```
  При этом реальные действия включения и выключения звука, которые реализованы в `media_control.py` и передаются роутером, называются:
  `sound_off`, `sound_on`, `mute`, `unmute`, `toggle_mute`.  
  Их в схеме для LLM **нет вообще**.

- **На что повлияет:**  
  Если запрос «выключи звук на компьютере» попадёт в LLM (например, сложная фраза «допиши файл и заглуши звук»), модель не сможет выбрать `sound_off`, выберет `volume_mute` (который вместо выключения может включить звук, если он уже был заглушен) либо выдаст ошибку валидации схемы аргументов `Validator`.

- **Как исправить прямо сейчас:**  
  Добавить `sound_off`, `sound_on`, `mute`, `unmute`, `toggle_mute` в `enum` схемы `control_media` в `tools/registry.py`.

---

## 9. Потенциальный Zip Slip в загрузчике Vosk

- **Где этот код:**  
  [`voice/wake_word.py`](voice/wake_word.py#L137-L138) (`_download_model`).

- **Почему он спорный и опасный:**  
  ```python
  with zipfile.ZipFile(archive) as archive_file:
      archive_file.extractall(model_dir.parent)
  ```
  Использование `extractall()` без фильтрации членов архива классифицируется как уязвимость пути (Zip Slip). Если сетевой трафик перехвачен или ссылка на модель подменена, архив может содержать относительные пути вроде `../../`, перезаписывая системные файлы или файлы проекта.

- **На что повлияет:**  
  Риск выхода за пределы папки кэша при распаковке внешнего zip-архива.

- **Как исправить прямо сейчас:**  
  В Python 3.12+ использовать `archive_file.extractall(model_dir.parent, filter='data')` либо явно валидировать пути перед распаковкой каждого файла.

---

## Сводная таблица приоритетов исправления

| № | Проблема | Файл | Риск | Критичность |
|---|---|---|---|---|
| **1** | Тихая перезапись файлов при `copy_file`/`move_file` | `tools/files.py` | Потеря данных пользователя | **БЛОКЕР (КРИТИЧНО)** |
| **2** | Падение `delete_file` на папках (`unlink`) | `tools/files.py` | Сбой удаления папок, ложный `PermissionError` | **ВЫСОКАЯ** |
| **3** | Зависание интерфейса на 8с при закрытии софта | `tools/application_closer.py` | Зависание окна (Not Responding) | **ВЫСОКАЯ** |
| **4** | Утечка COM-памяти и лаги в `media_control.py` | `tools/media_control.py` | Утечка дескрипторов аудио, лаги UI | **ВЫСОКАЯ** |
| **5** | Зависание выхода из программы на выгрузке Ollama | `core/application.py`, `ui/main_window.py` | Зомби-процесс Python после закрытия | **ВЫСОКАЯ** |
| **6** | Блокировка на сетевых дисках в телеметрии | `tools/system_info.py` | Фриз ассистента на 30 секунд | **СРЕДНЯЯ** |
| **7** | Неубиваемая фоновая генерация после shutdown | `services/chat_service.py` | Скрытая фоновая активность после выхода | **СРЕДНЯЯ** |
| **8** | Обрезанный enum в реестре тулов `control_media` | `tools/registry.py` | Невозможность модели управлять звуком | **СРЕДНЯЯ** |
