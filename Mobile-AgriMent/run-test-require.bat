@echo off
cd /d "C:\Users\azizb\Downloads\Mobile\frontend"
set PATH=C:\nodejs22\node-v22.19.0-win-x64;%PATH%
echo === Testing require chain ===
node -e "try { const m = require('@expo/metro/metro'); console.log('OK:', Object.keys(m).slice(0,10)); } catch(e) { console.error('ERROR:', e.message); }"
echo === Testing runServer fork ===
node -e "try { const {runServer} = require('@expo/cli/build/src/start/server/metro/runServer-fork'); console.log('OK runServer loaded'); } catch(e) { console.error('ERROR:', e.message); }"
echo === done ===
