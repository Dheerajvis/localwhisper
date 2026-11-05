import os
import sys
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Audio Settings
SAMPLE_RATE = 16000  # Whisper native rate
CHANNELS = 1         # Mono
DTYPE = "float32"

# Speech-to-Text Model Settings
# Options: "tiny.en", "base.en", "small.en", "medium.en", "large-v3-turbo"
DEFAULT_WHISPER_MODEL = "base.en"
WHISPER_COMPUTE_TYPE = "int8" if sys.platform == "darwin" else "float16"

# Post-processing / Smart Flow (WhisperFlow parity)
# Modes: "smart" (removes filler words, formats punct), "developer", "email", "raw"
DEFAULT_FLOW_MODE = "smart"

# Local LLaMA Settings (Optional local GGUF)
LLAMA_MODEL_PATH = str(MODELS_DIR / "llama-3.2-1b-instruct.Q4_K_M.gguf")

# System & Keyboard Hotkeys
IS_MACOS = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

# Hotkey settings:
# Mode: "toggle" (press once to start, press again to stop) or "push_to_talk" (hold to speak)
HOTKEY_MODE = "toggle"

# Key combo:
# On macOS: Cmd+Shift+Space or Alt+Space
# On Windows: Ctrl+Shift+Space or Alt+Space
DEFAULT_HOTKEY_DISPLAY = "Cmd + Shift + Space" if IS_MACOS else "Ctrl + Shift + Space"

# Auto-Paste into active window
AUTO_PASTE_ENABLED = True
RESTORE_CLIPBOARD_DELAY = 0.35  # seconds before restoring previous clipboard
