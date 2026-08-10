@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\Program Files\nodejs;%PATH%
set DEBUG=metro,*expo
echo Starting expo at %DATE% %TIME%
npx expo start --host lan --port 8081
