@echo off
chcp 65001 >nul
setlocal
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

set "PROJECT_ROOT=%~dp0"
set "START_DIR=%PROJECT_ROOT%start"

if not exist "%START_DIR%\" set "START_DIR=%PROJECT_ROOT%"

title Kirieshcka v2 Launcher
echo ========================================================
echo               Kirieshcka v2 Startup (Tauri)
echo ========================================================

rem Check if port 8765 is in use
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo [INFO] Port 8765 is held by PID %%a. Verifying health...
    powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 1; if ($r.status -eq 'ok') { exit 0 } } catch {}; exit 1" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Terminating orphaned process on port 8765 (PID %%a)...
        taskkill /f /pid %%a >nul 2>&1
    )
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

echo [2/2] Waiting for backend gateway health (http://127.0.0.1:8765/health)...
powershell -NoProfile -Command "$ready = $false; for ($i=0; $i -lt 30; $i++) { try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health' -TimeoutSec 1; if ($r.status -eq 'ok') { $ready = $true; break } } catch {}; Start-Sleep -Milliseconds 500 }; if (-not $ready) { exit 1 }"
if errorlevel 1 (
    echo [ERROR] Python backend gateway failed to become ready on port 8765.
    pause
    exit /b 1
)

echo Backend is ready. Launching Tauri desktop UI...
cd /d "%PROJECT_ROOT%ui"
call npx.cmd tauri dev

rem Clean up backend on window exit if running
powershell -NoProfile -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/shutdown' -Method Post -TimeoutSec 2 } catch {}" >nul 2>&1

exit /b 0
