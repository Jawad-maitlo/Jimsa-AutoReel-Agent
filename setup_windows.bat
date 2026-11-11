@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Jimsa Autoreel Agent - Setup
echo.
echo === Jimsa Autoreel Agent setup ===
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found. Install Python 3.11 or 3.12 from python.org
  echo and enable "Add python.exe to PATH" during installation.
  pause & exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js was not found. Install Node.js 20 LTS from nodejs.org
  pause & exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo ERROR: FFmpeg was not found. See docs\SETUP.md for installation steps.
  pause & exit /b 1
)
where ffprobe >nul 2>nul
if errorlevel 1 (
  echo ERROR: FFprobe was not found. Install the full FFmpeg package.
  pause & exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :error
)
call ".venv\Scripts\activate.bat"
echo Installing pinned Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Installing locked frontend dependencies...
call npm ci
if errorlevel 1 goto :error
if not exist ".env" copy ".env.example" ".env" >nul
if not exist "storage" mkdir storage

echo Building frontend...
call npm run build
if errorlevel 1 goto :error

echo.
echo Setup complete. Run start_windows.bat to open the application.
echo Optional: install Ollama and run: ollama pull qwen2.5:7b
echo Social publishing requires your own developer credentials; see docs\SOCIAL_API.md
pause
exit /b 0
:error
echo.
echo Setup failed. Read the error above and see docs\TROUBLESHOOTING.md
pause
exit /b 1
