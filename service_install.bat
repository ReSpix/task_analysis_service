@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ==== ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ====
fltmc >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ИНФО] Требуются права администратора. Перезапуск...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)


REM ==== ПЕРЕЙТИ В ДИРЕКТОРИЮ СКРИПТА ====
cd /d "%~dp0"


REM ==== НАСТРОЙКИ ====
call settings.bat
set SERVICE_NAME=AsanaIntegrationService
set SERVICE_DISPLAY_NAME=Asana Integration Service
set SERVICE_DESCRIPTION=Сервис для интеграции челленджей: Asana, Яндекс Формы, уведомления Телеграм и отчеты
set VENV_DIR=.venv
set PYTHON_EXE=%~dp0%VENV_DIR%\Scripts\python.exe
set PROJECT_DIR=%~dp0\src
set MAIN_MODULE=main:app
set LOG_DIR=%~dp0data
set NSSM_EXE=%~dp0nssm-2.24\win64\nssm.exe
set REQUIREMENTS_FILE=src\requirements.txt

REM ==== Проверка существования службы ====
sc query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel%==0 (
    echo ============================================
    echo [ОШИБКА] Служба "%SERVICE_NAME%" уже существует.
    echo Удаите ее с помощью:
    echo service_remove.bat
    echo После чего этот файл можно будет запустить снова
    echo ============================================
    pause
    exit /b 1
)

echo ============================================
echo [1/5] Проверка Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не установлен или не в PATH
    pause
    exit /b 1
)

echo ============================================
echo [2/5] Создание виртуального окружения
if not exist "%VENV_DIR%" (
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
) else (
    echo [ИНФО] Виртуальное окружение уже существует
)

echo ============================================
echo [3/5] Установка зависимостей
if exist "%REQUIREMENTS_FILE%" (
    "%PYTHON_EXE%" -m pip install --upgrade pip
    "%PYTHON_EXE%" -m pip install -r "%REQUIREMENTS_FILE%"
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить зависимости
        pause
        exit /b 1
    )
) else (
    echo [ОШИБКА] Файл requirements.txt не найден
    pause
    exit /b 1
)

echo ============================================
echo [4/5] Установка службы через NSSM

if not exist "%NSSM_EXE%" (
    echo [ОШИБКА] NSSM не найден по пути: %NSSM_EXE%
    pause
    exit /b 1
)

REM Удаление старой службы (если есть)
"%NSSM_EXE%" remove %SERVICE_NAME% confirm >nul 2>&1

REM Установка новой службы
"%NSSM_EXE%" install %SERVICE_NAME% "%PYTHON_EXE%"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить службу
    pause
    exit /b 1
)

"%NSSM_EXE%" set %SERVICE_NAME% AppDirectory "%PROJECT_DIR%"
"%NSSM_EXE%" set %SERVICE_NAME% AppParameters "-m uvicorn %MAIN_MODULE% --host %HOST% --port %PORT%"
"%NSSM_EXE%" set %SERVICE_NAME% DisplayName "%DISPLAY_NAME%"
"%NSSM_EXE%" set %SERVICE_NAME% Description "%DESCRIPTION%"
"%NSSM_EXE%" set %SERVICE_NAME% Start SERVICE_AUTO_START

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
"%NSSM_EXE%" set %SERVICE_NAME% AppStdout "%LOG_DIR%\additional_1.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppStderr "%LOG_DIR%\additional_2.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppRestartDelay 5000

echo ============================================
echo [5/5] Запуск службы
sc start %SERVICE_NAME%

echo ============================================
echo ✅ FastAPI служба установлена и запущена
echo 📂 Логи: %LOG_DIR%

if "%HOST%" == "0.0.0.0" (
    set HOST=127.0.0.1
)

echo 🌐 URL: http://%HOST%:%PORT%
echo ============================================
pause
