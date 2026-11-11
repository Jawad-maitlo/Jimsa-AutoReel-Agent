@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause & exit /b 1
)
if not exist "dist\index.html" (
  echo Building production interface...
  call npm run build
  if errorlevel 1 pause & exit /b 1
)
echo Starting Jimsa at http://127.0.0.1:8000
start "" "http://127.0.0.1:8000"
cd backend
call "..\.venv\Scripts\activate.bat"
python run.py
