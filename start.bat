@echo off
chcp 65001 >nul
setlocal
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "START_DIR=%PROJECT_ROOT%\start"

if not exist "%START_DIR%\" set "START_DIR=%PROJECT_ROOT%"

title Kirieshcka v2 Launcher
echo ========================================================
echo               Kirieshcka v2 Startup (Tauri)
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
call npx.cmd tauri dev

rem Backend stays alive in system tray after window close until user explicitly exits via tray or UI shutdown button.

exit /b 0
