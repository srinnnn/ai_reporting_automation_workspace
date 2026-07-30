@echo off
cd /d %~dp0
python tools\meituan_download_assistant_sync.py
pause
