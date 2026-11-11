@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Jimsa Autoreel Agent - Launcher

if not exist ".venv\Scripts\python.exe" (
  echo Setup has not been run. Run setup_windows.bat first.
  pause & exit /b 1
)
if not exist "node_modules" (
  echo Frontend dependencies are missing. Run setup_windows.bat first.
  pause & exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg is required but was not found. See docs\SETUP.md
  pause & exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul

echo Starting local API at http://127.0.0.1:8000 ...
start "Jimsa API" cmd /k "cd /d "%~dp0backend" && call "%~dp0.venv\Scripts\activate.bat" && python run.py"
echo Starting local interface at http://127.0.0.1:5173 ...
start "Jimsa UI" cmd /k "cd /d "%~dp0" && npm run dev -- --host 127.0.0.1"

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo.
echo Jimsa is starting. Two terminal windows keep the local services running.
echo Close those windows or run stop_windows.bat when finished.
pause
