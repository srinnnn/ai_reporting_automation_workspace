@echo off
cd /d "%~dp0"
set ANTA_RETAIL_HOST=127.0.0.1
set ANTA_RETAIL_PORT=8766
python -m intranet_app.anta_retail_launcher
