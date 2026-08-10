@echo off
title AgriMent - Restart Backend (safe)
set SCRIPT_DIR=%~dp0

echo Stopping backend servers (matching uvicorn processes)...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
timeout /t 2 /nobreak >nul
echo Starting backend...
start "AgriMent Backend" cmd /k "cd /d "%SCRIPT_DIR%backend" && venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080"
echo Backend restart initiated!
timeout /t 3
