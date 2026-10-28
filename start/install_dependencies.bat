@echo off
chcp 65001 >nul
setlocal

set "SCRIPT_DIR=%~dp0"

rem Support both the current root layout and the future start\ layout.
if exist "%SCRIPT_DIR%core" (
    set "PROJECT_ROOT=%SCRIPT_DIR%"
) else (
    set "PROJECT_ROOT=%SCRIPT_DIR%.."
)

set "LOG_DIR=%PROJECT_ROOT%\logs"
set "LOG_FILE=%LOG_DIR%\startup.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

rem Защита от блокировки файла лога другим запущенным процессом
(>>"%LOG_FILE%" echo off) 2>nul
if errorlevel 1 set "LOG_FILE=%LOG_DIR%\startup_installer.log"

(>>"%LOG_FILE%" echo off) 2>nul
if errorlevel 1 set "LOG_FILE=%LOG_DIR%\startup_%RANDOM%.log"

set "VENV_DIR=%PROJECT_ROOT%\.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

if exist "%PYTHON_EXE%" goto :venv_ready

python --version >nul 2>&1
if errorlevel 1 goto :python_missing

echo [Jarvis] Создание локального окружения .venv...
python -m venv --system-site-packages "%VENV_DIR%"

if exist "%PYTHON_EXE%" (
    echo [Jarvis] Локальное окружение успешно создано.
    goto :venv_ready
)

echo [Jarvis] Внимание: не удалось создать .venv, используется системный Python.
set "PYTHON_EXE=python"

:venv_ready
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\config\requirements.txt"
if not exist "%REQUIREMENTS_FILE%" set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"

set "FORCE_INSTALL=0"
if /i "%~1"=="--force" set "FORCE_INSTALL=1"
if /i "%~1"=="-f" set "FORCE_INSTALL=1"
if /i "%~1"=="/f" set "FORCE_INSTALL=1"
if /i "%~1"=="--repair" set "FORCE_INSTALL=1"

rem Быстрая проверка
if "%FORCE_INSTALL%"=="0" (
    "%PYTHON_EXE%" "%SCRIPT_DIR%check_dependencies.py" "%REQUIREMENTS_FILE%" --quiet >nul 2>&1
    if not errorlevel 1 exit /b 0
)

echo.>>"%LOG_FILE%"
echo ==================================================>>"%LOG_FILE%"
echo [%date% %time%] Проверка зависимостей Jarvis>>"%LOG_FILE%"

if "%FORCE_INSTALL%"=="0" (
    "%PYTHON_EXE%" "%SCRIPT_DIR%check_dependencies.py" "%REQUIREMENTS_FILE%" >>"%LOG_FILE%" 2>&1
    if not errorlevel 1 (
        echo [%date% %time%] Все зависимости уже установлены.>>"%LOG_FILE%"
        exit /b 0
    )
    echo [%date% %time%] Обнаружены отсутствующие зависимости. Запуск установки...>>"%LOG_FILE%"
)

echo Проверка и установка зависимостей Jarvis в локальную папку .venv...
"%PYTHON_EXE%" -m pip install -r "%REQUIREMENTS_FILE%" >>"%LOG_FILE%" 2>&1

if errorlevel 1 (
    echo [%date% %time%] ОШИБКА: не удалось установить зависимости Jarvis.>>"%LOG_FILE%"
    echo.>>"%LOG_FILE%"
    echo.
    echo Не удалось установить зависимости Jarvis.
    echo Подробности сохранены в:
    echo %LOG_FILE%
    echo Проверьте подключение к интернету и доступность pip.
    pause
    exit /b 1
)

echo [%date% %time%] Зависимости успешно проверены/установлены.>>"%LOG_FILE%"
exit /b 0

:python_missing
echo ОШИБКА: Python не найден в системе.
echo Пожалуйста, установите Python 3.10+ и добавьте его в переменную PATH.
pause
exit /b 1
