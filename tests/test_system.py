import sys
from pathlib import Path
import numpy as np
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=== LOCALWHISPER COMPONENT VERIFICATION ===")

# 1. Config Test
import config
print(f"[OK] Config loaded. Model dir: {config.MODELS_DIR}")

# 2. LLaMA / Smart Flow Formatter Test
from engine.llama_formatter import LlamaFormatter
formatter = LlamaFormatter(mode="smart")

test_raw = "um so like basically we should go ahead and check the status comma new line bullet point first item new line bullet point second item"
formatted = formatter.format_text(test_raw)
print(f"\n[Raw Speech Input]:\n{test_raw}")
print(f"[Smart Flow Output]:\n{formatted}")

# Verify code mode
formatter.mode = "developer"
code_raw = "create a function compute hash taking input string and returning hex digest"
code_formatted = formatter.format_text(code_raw)
print(f"\n[Developer Mode Input]:\n{code_raw}")
print(f"[Developer Mode Output]:\n{code_formatted}")

# Verify email mode
formatter.mode = "email"
email_raw = "hello team hope you are doing well please review the attached pr thanks"
email_formatted = formatter.format_text(email_raw)
print(f"\n[Email Mode Input]:\n{email_raw}")
print(f"[Email Mode Output]:\n{email_formatted}")

# 3. Audio Recorder Test
from engine.audio_recorder import AudioRecorder
recorder = AudioRecorder()
dev_idx, dev_name = recorder.get_best_input_device()
print(f"\n[OK] Sensed audio input device: '{dev_name}' (ID: {dev_idx})")

# 4. Settings Manager Test
from engine.settings_manager import SettingsManager
mgr = SettingsManager()
models = mgr.get_models_metadata()
print(f"[OK] Settings Manager loaded. Available models: {len(models['models'])}, Installed: {models['installed_count']}")

print("\n=== ALL COMPONENT CHECKS PASSED ===")
