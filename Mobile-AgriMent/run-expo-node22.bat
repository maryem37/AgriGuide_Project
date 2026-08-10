@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
echo === Node version ===
node -v
echo === Starting Expo CLI ===
call node node_modules\expo\bin\cli start --host lan --port 8081
