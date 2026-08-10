@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\Program Files\nodejs;%PATH%
set NODE_OPTIONS=--max-old-space-size=4096
echo === Starting metro single-threaded ===
node node_modules\metro\src\cli.js start --port 8081 --max-workers 1 --resetCache 2>&1
echo === Exit code: %ERRORLEVEL% ===
timeout /t 5
