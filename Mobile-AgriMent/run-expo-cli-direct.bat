@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
set NODE_OPTIONS=
echo === Node ===
node -v
echo === Running expo start ===
node node_modules\@expo\cli\build\bin\cli start --host lan --port 8081
echo === Exit code: %ERRORLEVEL% ===
