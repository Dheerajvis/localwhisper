@echo off
REM LocalWhisper Launch Script (Windows)
cd /d "%~dp0"

if not exist ".venv" (
    echo [LocalWhisper] Creating virtual environment...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\pip.exe install -r requirements.txt
)

echo [LocalWhisper] Starting LocalWhisper (iOS 27 Liquid Glass UI)...
.venv\Scripts\python.exe app.py
pause
