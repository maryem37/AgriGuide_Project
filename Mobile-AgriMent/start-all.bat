@echo off
title AgriMent - Start All
set SCRIPT_DIR=%~dp0
set "PATH=C:\Program Files\nodejs;C:\Users\azizb\AppData\Local\Programs\Python\Python313;%PATH%"

echo.
echo ============================================
echo  AgriMent - Starting All Services
echo ============================================
echo.

echo [1/2] Starting backend on port 8080 ...
start "AgriMent Backend" cmd /k "cd /d %SCRIPT_DIR%backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080"

timeout /t 4 /nobreak >nul

echo [2/2] Starting Expo dev server ...
start "AgriMent Frontend" cmd /k "cd /d %SCRIPT_DIR%frontend && npx expo start --lan"

echo.
echo Both servers started!
echo   Backend:  http://0.0.0.0:8080
echo   Frontend: Expo dev server (scan QR from phone)
echo.
pause
