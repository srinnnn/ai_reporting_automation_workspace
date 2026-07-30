@echo off
echo This script must be run as Administrator.
netsh advfirewall firewall add rule name="Intranet Workbench 8789" dir=in action=allow protocol=TCP localport=8789 profile=domain,private
echo.
echo If the command succeeded, coworkers can try:
echo http://10.32.53.129:8789/data-foundation
pause
