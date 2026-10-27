@echo off
cd /d "%~dp0"
echo Starting Jarvis Claude UI...
if not exist node_modules (
    echo Installing dependencies...
    call npm.cmd install
)
call npm.cmd run app
