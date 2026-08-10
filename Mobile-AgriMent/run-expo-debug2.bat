@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
set DEBUG=expo:*
set EXPO_SERVE_LOG_LEVEL=debug
echo === Starting Expo with debug ===
node node_modules\@expo\cli\build\bin\cli start --host lan --port 8081 2>&1 | findstr /R "."
echo === Exit ===
