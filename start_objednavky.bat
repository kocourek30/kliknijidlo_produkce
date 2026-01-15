@echo off
chcp 65001 >nul
cls
title kliknijidlo - Development Server
color 0A

echo 🚀 Spouštím kliknijidlo (RFID + Django + venv)...
echo.

REM Přejdi do složky projektu
cd /d "%~dp0"

REM 1. Spustí Node.js RFID čtečku v novém okně
echo 📡 Spouštím RFID čtečku (COM3)...
start "RFID Reader" cmd /k "cd /d %CD% && node rfid_websocket.js"

REM Počká 3 sekundy na Node
timeout /t 3 /nobreak >nul

REM 2. Aktivuje venv v TOMTOM okně
echo 🐍 Aktivuji venv...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ venv neexistuje! Spusť: python -m venv venv
    pause
    exit /b 1
)

REM 3. Spustí Django (zůstane běžet)
echo 🌐 Django server: http://localhost:8000
echo 📡 RFID čtečka běží na pozadí
echo.
echo ⏹️ Ukonči: Ctrl+C
echo ========================================
python manage.py runserver 8000
