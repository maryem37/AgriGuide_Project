@echo off
title AgriMent - Frontend (Expo)
set SCRIPT_DIR=%~dp0

echo.
echo ============================================
echo  AgriMent - Starting Expo Dev Server
echo ============================================
echo.
echo (Scan the QR code with Expo Go on your phone)
echo.

set "PATH=C:\Program Files\nodejs;%PATH%"

cd /d "%SCRIPT_DIR%frontend"
npx expo start --lan
pause
