#!/usr/bin/env bash
# LocalWhisper Launch Script (macOS / Linux)
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[LocalWhisper] Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

echo "[LocalWhisper] Starting LocalWhisper (iOS 27 Liquid Glass UI)..."
.venv/bin/python app.py
