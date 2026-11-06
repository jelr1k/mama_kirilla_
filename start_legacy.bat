@echo off
chcp 65001 >nul
setlocal

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "START_DIR=%PROJECT_ROOT%\start"

if not exist "%START_DIR%\" set "START_DIR=%PROJECT_ROOT%"

title Kirieshka v2 Launcher (Classic PySide6)
echo ========================================================
echo       Kirieshka v2 Startup (Classic PySide6 GUI)
echo ========================================================

rem Освобождаем порты, если остались висеть от прошлых сессий
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo [INFO] Завершение процесса на порту 8765, PID %%a
    taskkill /f /pid %%a >nul 2>&1
)

call "%START_DIR%\install_dependencies.bat"
if errorlevel 1 (
    echo [ERROR] Ошибка проверки или установки зависимостей.
    pause
    exit /b 1
)

set "PYTHON_EXE=python"
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" set "PYTHON_EXE=%VENV_PYTHON%"

echo [1/1] Запуск JARVIS (PySide6 GUI)...
"%PYTHON_EXE%" "%START_DIR%\main.py" --legacy-gui %*
if errorlevel 1 (
    echo [ERROR] Ошибка при работе Jarvis.
    pause
    exit /b 1
)
