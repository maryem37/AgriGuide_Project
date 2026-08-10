@echo off
title Install Packages
set "PATH=C:\Program Files\nodejs;%PATH%"
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
echo.
echo Installing expo-location and react-native-maps...
echo.
node node_modules\expo\bin\cli install expo-location react-native-maps
echo.
echo ---- Done ----
pause
