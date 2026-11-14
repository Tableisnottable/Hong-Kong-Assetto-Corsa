@echo off
cd /d "%~dp0.."
python tools/set_kmb_bus_display.py %*
pause
