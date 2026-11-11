@echo off
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"
python -m pytest
if errorlevel 1 goto :error
call npm test
if errorlevel 1 goto :error
call npm run build
if errorlevel 1 goto :error
echo All tests and the frontend build passed.
pause
exit /b 0
:error
echo Tests failed. Review the output above.
pause
exit /b 1
