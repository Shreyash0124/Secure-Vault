@echo off
setlocal
title SecureVault Cloud - Plan 2

REM Always run from this project's root folder, regardless of where this file is launched.
cd /d "%~dp0"

echo.
echo  ==========================================
echo        SecureVault Cloud - Plan 2
echo  ==========================================
echo.

if not exist "src\main.py" (
    echo [ERROR] Could not find src\main.py.
    echo Keep this launcher in the Plan-2-Local-CLI project root.
    echo.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    echo Install Python or make sure the Python command works in CMD.
    echo.
    pause
    exit /b 1
)

python src\main.py
set "APP_EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%APP_EXIT_CODE%"=="0" (
    echo [INFO] SecureVault exited with code %APP_EXIT_CODE%.
)
pause
exit /b %APP_EXIT_CODE%
