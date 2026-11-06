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

title Kirieshcka v2 Dev Launcher
echo ========================================================
echo               Kirieshcka v2 Dev Launcher
echo ========================================================

rem Free up dev ports if held by previous Jarvis instances (python/node/tauri)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    powershell -NoProfile -Command "try { $p = Get-Process -Id %%a -ErrorAction Stop; if ($p.ProcessName -match 'python') { Stop-Process -Id %%a -Force; Write-Host '[INFO] Stopped stale Jarvis backend PID %%a' } } catch {}" >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5174 ^| findstr LISTENING') do (
    powershell -NoProfile -Command "try { $p = Get-Process -Id %%a -ErrorAction Stop; if ($p.ProcessName -match 'node|tauri') { Stop-Process -Id %%a -Force; Write-Host '[INFO] Stopped stale Vite dev PID %%a' } } catch {}" >nul 2>&1
)

call "%START_DIR%\install_dependencies.bat"
if errorlevel 1 (
    echo [ERROR] Dependencies check failed.
    pause
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
    echo [INFO] Для разработки интерфейса Kirieshcka v2 требуется Node.js.
    echo        Установите Node.js LTS с сайта https://nodejs.org/
    pause
    exit /b 1
)

where cargo >nul 2>&1
if errorlevel 1 (
    if not exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        echo [ERROR] Rust / Cargo не найден в системе.
        echo [INFO] Для сборки десктопной оболочки Tauri v2 требуется Rust.
        echo        Установите Rust с сайта https://rustup.rs/
        pause
        exit /b 1
    )
)

echo [1/2] Запуск ядра Jarvis (Headless Python backend)...
start "" "%PYTHON_EXE%" "%START_DIR%\bootstrap.py" --headless %*

echo [2/2] Ожидание готовности API шлюза...
"%PYTHON_CLI%" "%START_DIR%\splash.py" %*
if errorlevel 1 (
    echo [ERROR] Не удалось подключиться к шлюзу API [127.0.0.1:8765].
    pause
    exit /b 1
)

echo Шлюз ядра активен. Запуск десктопного интерфейса Tauri v2...
cd /d "%PROJECT_ROOT%\ui"
start "" powershell -WindowStyle Hidden -Command "Start-Process cmd -ArgumentList '/c npx.cmd tauri dev' -WindowStyle Hidden -WorkingDirectory '%PROJECT_ROOT%\ui'"

timeout /t 1 >nul 2>&1
exit /b 0

:legacy_startup
title Kirieshcka v2 Launcher (Classic PySide6 GUI)
echo ========================================================
echo       Kirieshka v2 Startup (Classic PySide6 GUI)
echo ========================================================

set "PYTHON_EXE=python"
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" set "PYTHON_EXE=%VENV_PYTHON%"

echo Запуск классического интерфейса Jarvis (PySide6)...
"%PYTHON_EXE%" "%START_DIR%\main.py" --legacy-gui %*
exit /b %errorlevel%
