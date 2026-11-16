@echo off
chcp 65001 >nul
title Sherlock Web UI Server

echo ========================================================
echo          Sherlock OSINT Web - Server Launcher
echo ========================================================
echo.
echo [*] Starting web server on http://127.0.0.1:8000 ...
echo [*] The browser will open automatically.
echo [*] To stop the server, press Ctrl+C or close this window.
echo.

python web_app.py
pause
