@echo off
cd /d "%~dp0"
set INTRANET_HOST=0.0.0.0
set INTRANET_PORT=8785
echo.
echo 请输入本次局域网共享使用的管理员密码，至少10位，不能使用 admin123。
set /p INTRANET_ADMIN_PASSWORD=管理员密码：
python -m intranet_app.app
