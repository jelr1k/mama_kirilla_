@echo off
chcp 65001 >nul
setlocal
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "START_DIR=%PROJECT_ROOT%\start"

if not exist "%START_DIR%\" set "START_DIR=%PROJECT_ROOT%"

rem Parse arguments for legacy / PySide mode
if /i "%~1"=="--legacy" goto :legacy_startup
if /i "%~1"=="--legacy-gui" goto :legacy_startup
if /i "%~1"=="--pyside" goto :legacy_startup
if /i "%~1"=="-legacy" goto :legacy_startup

title Kirieshcka v2 Launcher
echo ========================================================
echo               Kirieshcka v2 Startup
echo ========================================================

rem Check if port 8765 or 5174 is in use by orphaned processes
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo [INFO] Terminating stale process on port 8765, PID %%a
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5174 ^| findstr LISTENING') do (
    echo [INFO] Terminating stale process on port 5174, PID %%a
    taskkill /f /pid %%a >nul 2>&1
)

call "%START_DIR%\install_dependencies.bat"
if errorlevel 1 (
    echo [ERROR] Dependencies check failed.
    pause
    exit /b 1
)

set "PYTHON_EXE=pythonw"
set "VENV_PYTHONW=%PROJECT_ROOT%\.venv\Scripts\pythonw.exe"
if exist "%VENV_PYTHONW%" set "PYTHON_EXE=%VENV_PYTHONW%"

rem Check if Node/Rust are available for Tauri
set "HAS_NODE=1"
where npx >nul 2>&1
if errorlevel 1 set "HAS_NODE=0"

set "HAS_CARGO=1"
where cargo >nul 2>&1
if errorlevel 1 (
    if not exist "%USERPROFILE%\.cargo\bin\cargo.exe" set "HAS_CARGO=0"
)

if "%HAS_NODE%"=="0" (
    echo [WARN] Node.js / npx не найден в системе.
    echo [INFO] Сборка Tauri недоступна. Запуск классического интерфейса PySide6...
    goto :run_legacy
)

if "%HAS_CARGO%"=="0" (
    echo [WARN] Rust / Cargo не найден в системе.
    echo [INFO] Сборка Tauri недоступна. Запуск классического интерфейса PySide6...
    goto :run_legacy
)

echo [1/2] Starting Python headless backend...
start "" "%PYTHON_EXE%" "%START_DIR%\bootstrap.py" --headless %*

echo [2/2] Waiting for backend gateway health (Discord-style splash)...
start /wait "" "%PYTHON_EXE%" "%START_DIR%\splash.py" %*
if errorlevel 1 (
    echo [ERROR] Python backend gateway failed to become ready on port 8765.
    pause
    exit /b 1
)

echo Backend is ready. Launching Tauri desktop UI...
cd /d "%PROJECT_ROOT%\ui"
start "" powershell -WindowStyle Hidden -Command "Start-Process cmd -ArgumentList '/c npx.cmd tauri dev' -WindowStyle Hidden -WorkingDirectory '%PROJECT_ROOT%\ui'"

rem Backend and UI stay alive in system tray after window close until user explicitly exits via tray or UI shutdown button.
timeout /t 1 >nul 2>&1
exit /b 0

:legacy_startup
title Kirieshcka v2 Launcher (Classic PySide6)
echo ========================================================
echo       Kirieshka v2 Startup (Classic PySide6 GUI)
echo ========================================================

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo [INFO] Terminating stale process on port 8765, PID %%a
    taskkill /f /pid %%a >nul 2>&1
)

call "%START_DIR%\install_dependencies.bat"
if errorlevel 1 (
    echo [ERROR] Dependencies check failed.
    pause
    exit /b 1
)

:run_legacy
set "PYTHON_EXE=python"
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" set "PYTHON_EXE=%VENV_PYTHON%"

echo Запуск классического интерфейса Jarvis (PySide6)...
"%PYTHON_EXE%" "%START_DIR%\main.py" --legacy-gui %*
exit /b %errorlevel%
