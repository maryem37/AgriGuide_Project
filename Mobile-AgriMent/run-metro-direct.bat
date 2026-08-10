@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\Program Files\nodejs;%PATH%
echo === Starting metro via cli.js ===
node node_modules\metro\src\cli.js start --port 8081 --resetCache 2>&1
echo === Exit code: %ERRORLEVEL% ===
timeout /t 5
