@echo off
setlocal enabledelayedexpansion
REM ==========================================================
REM LocalWhisper - Windows Launch & Auto-Setup Script
REM ==========================================================
title LocalWhisper Launcher

cd /d "%~dp0"

echo ==========================================================
echo        LocalWhisper - Offline Dictation for Windows
echo ==========================================================

REM 1. Detect Python command
set PYTHON_CMD=
where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=py -3
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM 2. Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo [LocalWhisper] Setting up isolated Python virtual environment...
    %PYTHON_CMD% -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [LocalWhisper] Upgrading pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    echo [LocalWhisper] Installing dependencies (this only happens once)...
    .venv\Scripts\pip.exe install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies! Please check your internet connection.
        pause
        exit /b 1
    )
    echo [LocalWhisper] Setup complete!
)

REM 3. Launch the application
echo [LocalWhisper] Launching LocalWhisper...
echo [LocalWhisper] Global Hotkey: Right Alt (or Ctrl + Shift + Space)
.venv\Scripts\python.exe app.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [LocalWhisper] Application terminated with an error code.
    pause
)
