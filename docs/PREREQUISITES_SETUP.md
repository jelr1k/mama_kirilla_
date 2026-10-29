# Полное руководство: Системные зависимости и настройка окружения на новом ПК

В этом руководстве собраны все внешние инструменты, компиляторы и рантаймы, которые **нельзя** установить через обычный `pip install -r requirements.txt`, но без которых проект **Kirieshcka v2 (Tauri v2 + Python Backend)** не соберется и не запустится на чистой Windows.

---

## 1. Сводная таблица зависимостей

| Компонент | Зачем нужен проекту | Минимальная версия |
| :--- | :--- | :--- |
| **Visual Studio C++ Build Tools** | Линкер `link.exe` для Rust, сборка нативных Windows API компонентов Tauri v2, компиляция C-расширений Python (`psutil`, `sounddevice`, `rapidfuzz`) | MSVC v143 (VS 2022) + Windows 10/11 SDK |
| **Rust & Cargo (`rustup`)** | Компиляция нативной оболочки окна Tauri v2 (`ui/src-tauri`) | Rust 1.85+ (stable-x86_64-pc-windows-msvc) |
| **Node.js & npm** | Сборка React/Vite фронтенда и запуск Tauri CLI (`npx tauri dev`) | Node.js LTS (v20.x или v22.x) |
| **Python** | Основной бэкенд ассистента: FastAPI, голосовые модули (Whisper, Vosk, Piper TTS), роутинг команд | Python 3.11 или 3.12 (64-bit). *Важно: 3.12 рекомендуется, 3.13+ пока не ставить из-за отсутствия предсобранных колес нейросетей* |
| **Ollama for Windows** | Локальный сервер LLM для общения, вызова инструментов и протоколов | Актуальная версия |
| **Microsoft Edge WebView2** | Движок рендеринга веб-интерфейса внутри окна Tauri | Evergreen Runtime (в чистых Win 10/11 уже есть, нужен для LTSC/сборок) |
| **Git for Windows** | Клонирование репозитория, переключение веток, автообновления | 2.40+ |

---

## 2. Способ 1: Быстрая установка через терминал (CMD / PowerShell / Winget)

Штатный пакетный менеджер Windows `winget` позволяет поставить всё необходимое одной пачкой без ручного скачивания установщиков.

### Шаг 1. Открой PowerShell или CMD от имени Администратора и выполни:

```powershell
# 1. Git, Python 3.12, Node.js LTS, Rustup и Ollama
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
winget install --id Rustlang.Rustup -e --accept-source-agreements --accept-package-agreements
winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
winget install --id Microsoft.EdgeWebView2Runtime -e --accept-source-agreements --accept-package-agreements

# 2. Visual Studio 2022 Build Tools (с обязательным пакетом C++ и Windows SDK)
winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

> **Важно:** После завершения установки **перезапусти терминал** (или перезагрузи ПК), чтобы обновились системные пути `PATH`.

### Шаг 2. Инициализация Rust toolchain (в обычном терминале):

```powershell
rustup default stable-x86_64-pc-windows-msvc
```

### Шаг 3. Разрешение на запуск скриптов npm в PowerShell (если ругается на `npm.ps1`):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

---

## 3. Способ 2: Ручная установка через официальные сайты (GUI)

Если нет `winget` или предпочитаешь ставить через классические `.exe` инсталлеры.

### 1. Visual Studio C++ Build Tools
* **Откуда качать:** [Официальный сайт Visual Studio (Раздел «Инструменты сборки»)](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
* **Что нажимать в инсталлере:**
  1. Запусти скачанный `vs_BuildTools.exe`.
  2. Во вкладке **«Рабочие нагрузки» (Workloads)** обязательно поставь галочку напротив **«Разработка классических приложений на C++»** (*Desktop development with C++*).
  3. В панели справа проверь, что выбраны:
     - *MSVC v143 — средства сборки C++ для VS 2022 (x64/x86)*
     - *Пакет SDK для Windows 10 или 11 (Windows SDK)*
     - *Основные компоненты C++ для классических приложений*
  4. Нажми «Установить» в правом нижнем углу и дождитесь окончания.

### 2. Rust (rustup)
* **Откуда качать:** [rust-lang.org/tools/install](https://www.rust-lang.org/tools/install)
* **Установка:**
  1. Скачай `rustup-init.exe` (64-bit).
  2. Запусти его. В консоли появится вопрос по умолчанию:
     ```text
     1) Proceed with standard installation (default - recommended)
     ```
  3. Нажми `1` и `Enter`. Установщик сам подтянет `cargo`, `rustc` и свяжет их с установленным ранее компилятором MSVC C++.

### 3. Node.js (версия LTS)
* **Откуда качать:** [nodejs.org](https://nodejs.org/en) (выбирай зеленую кнопку **LTS**, например 20.x или 22.x).
* **Установка:**
  1. Запусти `.msi` инсталлер, жми `Next`.
  2. Галочку *«Automatically install the necessary tools»* можно не ставить (мы их уже поставили через шаг 1).
  3. Убедись, что выбрана опция добавления в `PATH` (по умолчанию включена).

### 4. Python 3.12 (64-bit)
* **Откуда качать:** [python.org/downloads/windows](https://www.python.org/downloads/windows/) (ищи стабильный релиз 3.12.x).
* **Установка:**
  > [!IMPORTANT]
  > На самом первом экране установщика **ОБЯЗАТЕЛЬНО** поставь галочку внизу:  
  > **☑ Add python.exe to PATH**  
  > Без нее батники и система не увидят команду `python`.
  1. Выбери *«Install Now»*.
  2. В конце нажми *«Disable path length limit»*, если установщик предложит.

### 5. Ollama for Windows
* **Откуда качать:** [ollama.com/download/windows](https://ollama.com/download/windows)
* **Установка:**
  1. Скачай `OllamaSetup.exe` и запусти.
  2. Установка полностью автоматическая. По завершении в системном трее (возле часов) появится значок ламы.
  3. Открой терминал и скачай нужную модель:
     ```powershell
     ollama pull qwen2.5:7b
     # или более легкую модель для скромных видеокарт:
     ollama pull qwen2.5:3b
     ```

### 6. Microsoft Edge WebView2 (если Windows урезанная)
* **Откуда качать:** [Microsoft Edge WebView2 Evergreen Bootstrapper](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
* **Установка:**
  - Скачай и запусти *Evergreen Standalone Installer* или *Bootstrapper*. Если WebView2 уже есть в системе, установщик сам сообщит об этом.

### 7. Git for Windows
* **Откуда качать:** [git-scm.com/download/win](https://git-scm.com/download/win)
* **Установка:**
  - Запусти установщик, можно оставлять дефолтные параметры (главное, чтобы была выбрана опция *«Git from the command line and also from 3rd-party software»*).

---

## 4. Пошаговый запуск проекта с нуля на новом компе

Когда все инструменты установлены и терминал перезапущен:

### 1. Клонирование репозитория
```powershell
git clone https://github.com/jelr1k/mama_kirilla_.git
cd mama_kirilla_
git checkout osnova
```

### 2. Установка зависимостей фронтенда (React / Vite)
```powershell
cd ui
npm install
cd ..
```
*(Этот шаг обязателен перед первым запуском, чтобы в папке `ui/node_modules` появились `@tauri-apps/api`, `vite` и `react`).*

### 3. Проверка запуска через лаунчер
Просто дважды кликни на файл:
```bat
start.bat
```
Что сделает `start.bat` сам:
1. Создаст локальное виртуальное окружение `.venv` (если его нет).
2. Автоматически установит все Python библиотеки из `config/requirements.txt` (FastAPI, uvicorn, faster-whisper, sounddevice, vosk, piper-tts и др.).
3. Запустит headless бэкенд на порту 8765 и дождется ответа `/health`.
4. Запустит `npx tauri dev`, который скомпилирует Rust-часть и откроет приложение на рабочем столе.

---

## 5. Типичные грабли и их решение (FAQ)

### Грабли 1: `error: linker 'link.exe' not found` при сборке Tauri
* **Причина:** Не установлены Visual Studio C++ Build Tools или забыли отметить галочку «Разработка классических приложений на C++».
* **Решение:** Доставить Build Tools (Способ 1 или Способ 2), убедиться, что Windows SDK установлен, и перезапустить терминал.

### Грабли 2: `npm : File ... npm.ps1 cannot be loaded because running scripts is disabled`
* **Причина:** Политика безопасности PowerShell по умолчанию блокирует запуск внешних скриптов `.ps1`.
* **Решение:** Выполни в PowerShell от администратора:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  ```
  Или запускай команды через классическую командную строку `cmd.exe`.

### Грабли 3: Ошибка при установке Python колес (`pip install failed`)
* **Причина:** Попытка использовать слишком новый Python (например 3.13 или 3.14), для которого нейросетевые библиотеки `faster-whisper`, `piper-tts`, `sounddevice` еще не выложили готовые бинарные сборки для Windows.
* **Решение:** Использовать строго **Python 3.12 (64-bit)**.

### Грабли 4: Белое окно или ошибка WebView2
* **Причина:** Кастомная сборка Windows (ReviOS, AtlasOS, Tiny11), из которой вырезали компоненты Edge.
* **Решение:** Скачать и установить [Microsoft Edge WebView2 Evergreen Bootstrapper](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

### Грабли 5: Окно открылось, но чат пишет «Не удалось подключиться к Ollama»
* **Причина:** Сервер Ollama не запущен или выгружен из трея.
* **Решение:** Запустить Ollama из меню «Пуск» или выполнить в консоли `ollama serve`. Проверить доступность по адресу: `http://localhost:11434`.
