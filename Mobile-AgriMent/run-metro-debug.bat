@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
set DEBUG=metro:*
echo === Node ===
node -v
echo === Starting metro direct ===
node node_modules\metro\src\cli.js start --port 8081 --verbose 2>&1 | findstr /R "." 
echo === done ===
