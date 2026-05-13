@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Could not find .venv\Scripts\python.exe.
  echo Run Setup Dev.cmd first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "scripts\generate_sample_investor_reports.py"
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Sample report generation failed with exit code %EXIT_CODE%.
  pause
  exit /b %EXIT_CODE%
)

echo.
echo Sample reports are in data\reports\samples\latest.
echo Open data\reports\samples\latest\index.html to review them.
pause
