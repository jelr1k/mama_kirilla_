@echo off
chcp 65001 >nul
setlocal
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "UI_DIR=%PROJECT_ROOT%\ui"

if not exist "%UI_DIR%\package.json" (
    echo [ERROR] Не найдена папка ui: "%UI_DIR%"
    pause
    exit /b 1
)

title Kirieshcka v2 UI Only Dev Launcher
echo ========================================================
echo          Kirieshcka v2 - UI Only (without backend)
echo ========================================================

rem Free up Vite dev port 5174 and stale Tauri dev binary if left running
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5174 ^| findstr LISTENING') do (
    powershell -NoProfile -Command "try { $p = Get-Process -Id %%a -ErrorAction Stop; if ($p.ProcessName -match 'node|tauri') { Stop-Process -Id %%a -Force } } catch {}" >nul 2>&1
)
powershell -NoProfile -Command "Get-Process -Name 'app' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq '%UI_DIR%\src-tauri\target\debug\app.exe' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

where npx >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js / npx не найден в системе.
    echo [INFO] Установите Node.js LTS: https://nodejs.org/
    pause
    exit /b 1
)

if not exist "%UI_DIR%\node_modules" (
    echo [INFO] Папка node_modules не найдена, ставлю зависимости UI...
    cd /d "%UI_DIR%"
    call npm.cmd install
    if errorlevel 1 (
        echo [ERROR] Не удалось выполнить npm install.
        pause
        exit /b 1
    )
)

if /i "%~1"=="--browser" goto :vite_only
if /i "%~1"=="--vite" goto :vite_only

where cargo >nul 2>&1
if errorlevel 1 (
    if not exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
        echo [ERROR] Rust / Cargo не найден в системе.
        echo [INFO] Установите Rust с https://rustup.rs/ или запускайте с флагом --browser
        pause
        exit /b 1
    )
)

echo Запуск десктопного UI (Tauri v2 + Vite HMR, без Python-бэкенда)...
cd /d "%UI_DIR%"
call npx.cmd tauri dev
exit /b %errorlevel%

:vite_only
echo Запуск UI в режиме браузера (Vite HMR на http://127.0.0.1:5174)...
cd /d "%UI_DIR%"
call npm.cmd run dev
exit /b %errorlevel%
