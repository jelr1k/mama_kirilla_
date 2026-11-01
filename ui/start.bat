@echo off
cd /d "%~dp0"
echo Starting Kirieshcka UI via Tauri dev...
if not exist node_modules (
    echo Installing node dependencies...
    call npm.cmd install
)
call npx.cmd tauri dev
