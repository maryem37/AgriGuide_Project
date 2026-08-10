@echo off
echo ============================================
echo  FarMinds - Fix Firewall (Run as Admin!)
echo ============================================
echo.
netsh advfirewall firewall add rule name="FarMinds Backend" dir=in action=allow protocol=TCP localport=8080
echo.
echo Done! Firewall port 8080 is now open.
echo Your phone can now reach the backend.
echo.
pause
