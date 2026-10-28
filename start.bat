@echo off
chcp 65001 >nul
setlocal
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

set "PROJECT_ROOT=%~dp0"
set "START_DIR=%PROJECT_ROOT%start"

rem Support both the current layout and the future start\ layout.
if not exist "%START_DIR%\" set "START_DIR=%PROJECT_ROOT%"

rem Free port 8765 if held by an orphaned session before touching logs
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

call "%START_DIR%\install_dependencies.bat"
if errorlevel 1 exit /b 1

rem Start backend in headless mode
start "" pythonw "%START_DIR%\bootstrap.py" --headless %*

rem Wait for backend to be ready
ping 127.0.0.1 -n 3 >nul

rem Launch Tauri frontend in development mode
echo Starting Tauri desktop UI...
cd /d "%PROJECT_ROOT%ui"
call npx.cmd tauri dev

exit /b 0
