@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
echo === Node ===
node -v
echo === Starting expo (no clear, max-workers 1) ===
node node_modules\@expo\cli\build\bin\cli start --host lan --port 8081 --max-workers 1 2>&1
echo === done ===
