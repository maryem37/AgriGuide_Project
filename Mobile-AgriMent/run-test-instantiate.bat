@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
echo === Starting instantiateMetro test ===
node _test_instantiate.js
echo === Exit code: %ERRORLEVEL% ===
timeout /t 5
