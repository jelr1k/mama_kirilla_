@echo off
chcp 65001 >nul
setlocal
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "START_DIR=%PROJECT_ROOT%\start"

if not exist "%START_DIR%\" set "START_DIR=%PROJECT_ROOT%"

rem Parse arguments for legacy mode
if /i "%~1"=="--legacy" goto :legacy_startup
if /i "%~1"=="--legacy-gui" goto :legacy_startup
if /i "%~1"=="--pyside" goto :legacy_startup
if /i "%~1"=="-legacy" goto :legacy_startup

title Assistant Dev Launcher
echo ========================================================
echo               Assistant Dev Launcher
echo ========================================================

rem Free up dev ports if held by previous Assistant instances (python/node/tauri)
for /f "tokens=5" %%a in ('netstat -aon -p TCP ^| findstr :8765 ^| findstr LISTENING') do (
    powershell -NoProfile -Command "$f = Join-Path $env:LOCALAPPDATA 'Assistant\session.token'; if (-not (Test-Path $f)) { $f = Join-Path $env:LOCALAPPDATA 'Jarvis\session.token' }; $h = @{}; if (Test-Path $f) { $t = (Get-Content $f -Raw -ErrorAction SilentlyContinue); if ($t) { $h.Authorization = 'Bearer ' + $t.Trim() } }; try { Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/shutdown' -Method Post -Headers $h -TimeoutSec 1 -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 300 } catch {}; try { $p = Get-Process -Id %%a -ErrorAction Stop; if ($p.ProcessName -match 'python') { Stop-Process -Id %%a -Force; Write-Host '[INFO] Stopped stale Assistant backend PID %%a' } } catch {}" >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon -p TCP ^| findstr :5174 ^| findstr LISTENING') do (
    powershell -NoProfile -Command "try { $p = Get-Process -Id %%a -ErrorAction Stop; if ($p.ProcessName -match 'node|tauri') { Stop-Process -Id %%a -Force; Write-Host '[INFO] Stopped stale Vite dev PID %%a' } } catch {}" >nul 2>&1
)
tasklist /FI "IMAGENAME eq app.exe" 2>nul | find /I "app.exe" >nul
if not errorlevel 1 (
    powershell -NoProfile -Command "Get-Process -Name 'app' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq (Join-Path $env:PROJECT_ROOT 'ui\src-tauri\target\debug\app.exe') } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1
)

call "%START_DIR%\install_dependencies.bat"
if errorlevel 1 (
    echo [ERROR] Dependencies check failed.
    if not "%ASSISTANT_NO_PAUSE%"=="1" pause
    exit /b 1
)

set "PYTHON_EXE=pythonw"
set "PYTHON_CLI=python"
set "VENV_PYTHONW=%PROJECT_ROOT%\.venv\Scripts\pythonw.exe"
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if exist "%VENV_PYTHONW%" set "PYTHON_EXE=%VENV_PYTHONW%"
if exist "%VENV_PYTHON%" set "PYTHON_CLI=%VENV_PYTHON%"

rem Verify Node.js and Rust are available for dev build
where npx >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js / npx не найден в системе.
    echo [INFO] Для разработки интерфейса требуется Node.js.
    echo        Установите Node.js LTS с сайта https://nodejs.org/
    if not "%ASSISTANT_NO_PAUSE%"=="1" pause
    exit /b 1
)

where cargo >nul 2>&1
if errorlevel 1 (
    if not exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        echo [ERROR] Rust / Cargo не найден в системе.
        echo [INFO] Для сборки десктопной оболочки Tauri v2 требуется Rust.
        echo        Установите Rust с сайта https://rustup.rs/
        if not "%ASSISTANT_NO_PAUSE%"=="1" pause
        exit /b 1
    )
)

echo [1/2] Запуск ядра Assistant (Headless Python backend)...
start "" "%PYTHON_EXE%" "%START_DIR%\bootstrap.py" --headless %*

rem UI (Vite + cargo + WebView2) стартует параллельно с ядром: сокет UI сам переподключается к шлюзу.
rem Локальный бинарь tauri вместо npx экономит ~1 с на резолве пакета.
set "TAURI_CMD=npx.cmd tauri dev"
if exist "%PROJECT_ROOT%\ui\node_modules\.bin\tauri.cmd" set "TAURI_CMD=node_modules\.bin\tauri.cmd dev"
echo Запуск десктопного интерфейса Tauri v2...
start "" /B cmd /c "cd /d "%PROJECT_ROOT%\ui" && %TAURI_CMD% >nul 2>&1"

echo [2/2] Ожидание готовности API шлюза...
"%PYTHON_CLI%" "%START_DIR%\splash.py" %*
if errorlevel 1 (
    echo [ERROR] Не удалось подключиться к шлюзу API [127.0.0.1:8765].
    if not "%ASSISTANT_NO_PAUSE%"=="1" pause
    exit /b 1
)

echo Шлюз ядра активен.
exit /b 0

:legacy_startup
echo [ERROR] Legacy PySide6 GUI has been archived in ui_archive/ and is no longer supported. Use start.bat (Tauri v2).
if not "%ASSISTANT_NO_PAUSE%"=="1" pause
exit /b 1
