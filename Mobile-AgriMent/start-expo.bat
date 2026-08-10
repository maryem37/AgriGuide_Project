@echo off
set SCRIPT_DIR=%~dp0
set "PATH=C:\Program Files\nodejs;%PATH%"
cd /d "%SCRIPT_DIR%frontend"
start "Expo" cmd /k "cd /d "%SCRIPT_DIR%frontend" && npx expo start --host lan --clear"
exit /b
