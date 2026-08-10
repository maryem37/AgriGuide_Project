@echo off
title FarMinds - Start All (Auto)
set SCRIPT_DIR=%~dp0

echo.
echo ============================================
echo  FarMinds - Starting Backend & Frontend
echo ============================================
echo.

REM Kill any existing processes on ports 8080 and 8081
echo Cleaning up any existing processes...
taskkill /F /IM uvicorn.exe >nul 2>&1
for /F "tokens=5" %%P in ('netstat -a -n -o ^| findstr ":8080 " 2^>nul') do (
    taskkill /PID %%P /F >nul 2>&1
)
for /F "tokens=5" %%P in ('netstat -a -n -o ^| findstr ":8081 " 2^>nul') do (
    taskkill /PID %%P /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM Start backend using the virtual environment
echo Starting backend on port 8080...
start "FarMinds Backend" cmd /k "cd /d "%SCRIPT_DIR%backend" && venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080"

timeout /t 5 /nobreak >nul

REM Start Expo with --clear to avoid stale cache
echo Starting Expo on port 8081...
start "FarMinds Frontend" cmd /k "cd /d "%SCRIPT_DIR%frontend" && set PATH=C:\Program Files\nodejs;%PATH% && set EXPO_USE_DEV_CACHE=1 && npx expo start --host lan --port 8081"

echo.
echo ============================================
echo  Both servers started!
echo  Backend:  http://localhost:8080
echo  Expo:     http://localhost:8081
echo  Health:   http://localhost:8080/health
echo ============================================
echo.
echo  On your phone (same WiFi network):
for /F "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /R "IPv4.*10\.\|IPv4.*192\.168\.\|IPv4.*172\."') do (
    echo  Expo:     http://%%I:8081
    echo  Backend:  http://%%I:8080
)
echo.
echo  If the QR code doesn't load on your phone:
echo   1. Ensure phone and computer are on the SAME WiFi network
echo   2. Add Firewall rules (admin): netsh advfirewall firewall add rule name="AgriMent Backend (8080)" dir=in action=allow protocol=TCP localport=8080 profile=private
echo   3. Add Firewall rules (admin): netsh advfirewall firewall add rule name="AgriMent Expo (8081)" dir=in action=allow protocol=TCP localport=8081 profile=private
echo.
pause
