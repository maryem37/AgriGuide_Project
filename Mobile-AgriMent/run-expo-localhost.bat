@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
echo === Starting expo with localhost ===
node node_modules\@expo\cli\build\bin\cli start --localhost --port 8081
echo === Exit code: %ERRORLEVEL% ===
