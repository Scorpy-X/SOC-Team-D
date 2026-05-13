@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" "scripts\run_optimizer_developer_check.py"
if errorlevel 1 pause
