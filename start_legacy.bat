@echo off
chcp 65001 >nul
echo [ERROR] Legacy PySide6 GUI has been archived in ui_archive/ and is no longer supported. Use start.bat (Tauri v2).
if not "%ASSISTANT_NO_PAUSE%"=="1" pause
exit /b 1
