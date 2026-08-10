@echo off
title AgriMent - Backend (FastAPI)
set SCRIPT_DIR=%~dp0

echo.
echo ============================================
echo  AgriMent - Starting Backend Server
echo ============================================
echo.

cd /d "%SCRIPT_DIR%backend"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080
pause
