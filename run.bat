@echo off
REM Console Task Manager Launcher
REM This script ensures the application runs in a proper terminal

python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while running the task manager.
    echo Please ensure Python and all dependencies are installed.
    echo.
    pause
)

