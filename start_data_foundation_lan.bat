@echo off
cd /d "%~dp0"
set INTRANET_HOST=0.0.0.0
set INTRANET_PORT=8789
echo.
echo Data Foundation LAN mode
echo URL: http://10.32.53.129:8789/data-foundation
echo.
echo Please enter a temporary admin password, at least 10 characters.
set /p INTRANET_ADMIN_PASSWORD=Admin password:
python -m intranet_app.app
