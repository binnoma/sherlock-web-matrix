@echo off
chcp 65001 >nul
title Sherlock Username Scanner

set USERNAME_ARG=%~1

if "%USERNAME_ARG%"=="" (
    echo ========================================================
    echo             Sherlock OSINT Username Hunter
    echo ========================================================
    echo.
    set /p USERNAME_ARG="Enter username to search (ادخل اسم المستخدم): "
)

if "%USERNAME_ARG%"=="" (
    echo [!] No username entered. Exiting...
    pause
    exit /b 1
)

if not exist "results" mkdir results

echo.
echo [*] Scanning for "%USERNAME_ARG%"... Please wait.
echo [*] Output will be saved to: results\result.csv / .xlsx
echo.

sherlock --csv --xlsx --output "results\result_%USERNAME_ARG%" --print-found %USERNAME_ARG%

echo.
echo ========================================================
echo [*] Scan completed! Results saved in "results" folder.
echo ========================================================
echo.
pause
