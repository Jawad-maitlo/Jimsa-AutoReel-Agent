@echo off
setlocal
title Jimsa Autoreel Agent - Stop
echo Stopping Jimsa terminal processes...
taskkill /FI "WINDOWTITLE eq Jimsa API*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Jimsa UI*" /T /F >nul 2>nul
echo Stop commands sent. If a terminal remains open, close it manually.
pause
