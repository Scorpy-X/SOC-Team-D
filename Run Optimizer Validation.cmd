@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo The Python virtual environment is missing.
    echo Run: Setup Dev.cmd
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\run_optimizer_validation.py"
if errorlevel 1 pause
