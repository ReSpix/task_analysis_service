@echo off
chcp 65001 >nul
setlocal

:: Проверка и перезапуск с правами администратора
fltmc >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ИНФО] Требуются права администратора. Перезапуск...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)


REM ==== NSSM путь ====
set NSSM_EXE=%~dp0nssm-2.24\win64\nssm.exe

"%NSSM_EXE%" stop AsanaIntegrationService
"%NSSM_EXE%" remove AsanaIntegrationService confirm

pause
