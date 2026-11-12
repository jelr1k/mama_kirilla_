# Установка, системные зависимости и запуск dev-билда JARVIS

Единое руководство по развёртыванию ассистента из исходников на Windows 10/11 для разработчиков.

Стек проекта:
* **Бэкенд:** Python 3.12 (FastAPI шлюз на `127.0.0.1:8765`, WebSocket, Vosk wake word / faster-whisper STT, Piper TTS, Ollama LLM, EventBus).
* **Фронтенд:** Tauri v2 + React / Vite (`ui/`), трей, нативные системные горячие клавиши, защищённый межпроцессный обмен токенами сессий.

---

## 1. Системные требования и зависимости (Prerequisites)

Для сборки нативной оболочки Rust и запуска бэкенда на чистом ПК требуются системные инструменты, которые **нельзя** поставить через обычный `pip`:

| Компонент | Зачем нужен проекту | Минимальная версия | Проверка в терминале |
| :--- | :--- | :--- | :--- |
| **Python** | Основной бэкенд: FastAPI, Command Router, Vosk, Whisper, Piper TTS | Python 3.12 (64-bit) | `python --version` |
| **Node.js & npm** | Сборка React/Vite фронтенда и запуск Tauri CLI | Node.js LTS (v20+ или v22+) | `node -v` и `npm -v` |
| **Rust & Cargo (`rustup`)** | Компиляция нативной оболочки окна Tauri v2 (`ui/src-tauri`) | Rust 1.85+ (stable-x86_64-pc-windows-msvc) | `rustc --version` |
| **Visual Studio C++ Build Tools** | Линкер `link.exe` для Rust, компиляция C-расширений (`psutil`, `sounddevice`, `rapidfuzz`) | MSVC v143 (VS 2022) + Windows 10/11 SDK | Наличие `cl.exe` |
| **Ollama for Windows** | Локальная языковая модель (опциональный модуль чата) | Актуальная версия | `ollama --version` |
| **Microsoft Edge WebView2** | Движок рендеринга веб-интерфейса Tauri | Evergreen Runtime | Встроен в Win 10/11 |
| **Git for Windows** | Клонирование репозитория и управление ветками | 2.40+ | `git --version` |

---

## 2. Быстрая установка окружения на чистый ПК через Winget

Штатный пакетный менеджер Windows `winget` ставит всё одной пачкой без ручного скачивания установщиков.

### Шаг 1. Открой PowerShell от имени Администратора:

```powershell
# 1. Базовые утилиты и рантаймы
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
winget install --id Rustlang.Rustup -e --accept-source-agreements --accept-package-agreements
winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
winget install --id Microsoft.EdgeWebView2Runtime -e --accept-source-agreements --accept-package-agreements

# 2. Visual Studio 2022 Build Tools (с обязательным пакетом C++ и Windows SDK)
winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

> **Важно:** После установки перезапусти терминал (или ПК), чтобы обновились системные переменные `PATH`.

### Шаг 2. Инициализация Rust и разрешений скриптов:

```powershell
rustup default stable-x86_64-pc-windows-msvc
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

---

## 3. Быстрый запуск в один клик (`start.bat`)

После клонирования репозитория (`git clone https://github.com/jelr1k/mama_kirilla_.git` ветка `osnova`):

1. Установи зависимости фронтенда:
   ```cmd
   cd ui
   npm install
   cd ..
   ```
2. Запусти лаунчер:
   ```cmd
   start.bat
   ```

### Что делает `start.bat` автоматически:
1. Проверяет наличие Python 3.12 в `PATH`.
2. Создает виртуальное окружение `.venv` (если отсутствует).
3. Обновляет пакеты из `config/requirements.txt` без лишней переустановки.
4. Очищает зависшие процессы порта `8765` от прошлых сессий.
5. Запускает бэкенд в фоне (`pythonw.exe start/bootstrap.py --headless`).
6. Запускает скрипт ожидания готовности ядра (`start/splash.py`), опрашивающий `http://127.0.0.1:8765/health`.
7. После старта ядра поднимает dev-интерфейс Tauri v2 (`npx tauri dev` в `ui/`). Для отладки только фронтенда без бэкенда доступен скрипт `start_ui.bat` (или `start_ui.bat --browser`).

---

## 4. Ручной запуск и отладка (для разработки)

Если нужно видеть логи бэкенда в живом времени или запускать фронтенд с горячей перезагрузкой (HMR):

### Шаг 1. Настройка виртуального окружения Python
```cmd
py -3.12 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r config\requirements.txt
```

### Шаг 2. Запуск бэкенда с выводом логов в консоль
```cmd
python start\main.py
```
Бэкенд запустит FastAPI шлюз на `http://127.0.0.1:8765`, WebSocket на `ws://127.0.0.1:8765/ws` и инициализирует сервисы.

### Шаг 3. Запуск dev-сервера фронтенда в отдельном терминале
```cmd
cd ui
npm run tauri dev
```

---

## 5. Типичные проблемы и решения (FAQ)

### `error: linker 'link.exe' not found` при сборке Tauri
* **Причина:** Не установлены Visual Studio C++ Build Tools или пропущена галочка «Разработка классических приложений на C++».
* **Решение:** Доставить Build Tools через winget или VS Installer, убедиться в наличии Windows SDK и перезапустить терминал.

### `npm : File npm.ps1 cannot be loaded because running scripts is disabled`
* **Причина:** Политика безопасности PowerShell блокирует скрипты.
* **Решение:** Выполнить в PowerShell от администратора: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force` или использовать `cmd.exe`.

### Сбой при установке Python библиотек (`pip install failed`)
* **Причина:** Использование неподдерживаемой версии Python (3.13 / 3.14).
* **Решение:** Использовать строго **Python 3.12 (64-bit)**.
