import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import config

# Path to persistent settings
SETTINGS_FILE = config.BASE_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "active_model": config.DEFAULT_WHISPER_MODEL,
    "active_mode": config.DEFAULT_FLOW_MODE,
    "auto_paste": config.AUTO_PASTE_ENABLED,
    "hands_free_mode": False,
    "hands_free_muted": False,
    "remove_fillers": True,
    "format_punctuation": True,
    "auto_capitalize": True,
    "microphone_device_id": None,
    "hotkey_combo": "cmd+shift+space" if config.IS_MACOS else "ctrl+shift+space",
    "hotkey_mode": "toggle",
    "silence_threshold": 0.0028
}

AVAILABLE_MODELS = [
    {
        "id": "tiny.en",
        "name": "Whisper Tiny (English)",
        "tag": "⚡⚡⚡ Ultra Fast",
        "description": "Blazing fast inference (~180ms). Minimal RAM & battery usage. Best for short notes.",
        "download_size": "~75 MB",
        "vram_ram": "~390 MB RAM",
        "speed_rating": "5/5",
        "accuracy_rating": "3/5",
        "folder_name": "models--Systran--faster-whisper-tiny.en"
    },
    {
        "id": "base.en",
        "name": "Whisper Base (English)",
        "tag": "⚡⚡ Fast • Default",
        "description": "Recommended default (~450ms). Perfect balance between ultra-fast speed and high accuracy.",
        "download_size": "~142 MB",
        "vram_ram": "~500 MB RAM",
        "speed_rating": "4/5",
        "accuracy_rating": "4/5",
        "folder_name": "models--Systran--faster-whisper-base.en"
    },
    {
        "id": "small.en",
        "name": "Whisper Small (English)",
        "tag": "⚡ High Accuracy",
        "description": "Superior accuracy for technical terminology, developer terms, and varied accents (~1.1s).",
        "download_size": "~480 MB",
        "vram_ram": "~1.0 GB RAM",
        "speed_rating": "3/5",
        "accuracy_rating": "4.5/5",
        "folder_name": "models--Systran--faster-whisper-small.en"
    },
    {
        "id": "medium.en",
        "name": "Whisper Medium (English)",
        "tag": "🎯 Studio Grade",
        "description": "Studio-level accuracy (~2.8s). Handles complex dictation, specialized jargon, and fast speech.",
        "download_size": "~1.5 GB",
        "vram_ram": "~2.6 GB RAM",
        "speed_rating": "2/5",
        "accuracy_rating": "5/5",
        "folder_name": "models--Systran--faster-whisper-medium.en"
    },
    {
        "id": "large-v3-turbo",
        "name": "Whisper Large V3 Turbo",
        "tag": "🌐 Multilingual Champion",
        "description": "State-of-the-art multilingual model with optimized turbo decoding (~1.8s).",
        "download_size": "~1.6 GB",
        "vram_ram": "~2.8 GB RAM",
        "speed_rating": "3/5",
        "accuracy_rating": "5/5",
        "folder_name": "models--Systran--faster-whisper-large-v3-turbo"
    }
]

class SettingsManager:
    def __init__(self):
        self.models_dir = config.MODELS_DIR / "whisper"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()

    def _load(self) -> Dict[str, Any]:
        """Loads persistent settings or initializes defaults."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with defaults
                    merged = dict(DEFAULT_SETTINGS)
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"[SettingsManager] Error loading settings: {e}", flush=True)
        return dict(DEFAULT_SETTINGS)

    def save(self, new_settings: Dict[str, Any]) -> bool:
        """Saves settings to disk."""
        try:
            self.settings.update(new_settings)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"[SettingsManager] Error saving settings: {e}", flush=True)
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        return dict(self.settings)

    def get_models_metadata(self) -> Dict[str, Any]:
        """Computes live storage and installation status for all models."""
        models_list = []
        total_bytes = 0

        for m in AVAILABLE_MODELS:
            folder_path = self.models_dir / m["folder_name"]
            is_installed = False
            actual_size_str = "Not installed"
            size_bytes = 0

            if folder_path.exists() and folder_path.is_dir():
                try:
                    for f in folder_path.glob("**/*"):
                        if f.is_file():
                            size_bytes += f.stat().st_size
                    if size_bytes > 5 * 1024 * 1024:  # > 5MB means weights downloaded
                        is_installed = True
                        total_bytes += size_bytes
                        if size_bytes > 1024 * 1024 * 1024:
                            actual_size_str = f"{size_bytes / (1024**3):.1f} GB"
                        else:
                            actual_size_str = f"{size_bytes / (1024**2):.1f} MB"
                except Exception:
                    pass

            item = dict(m)
            item["is_installed"] = is_installed
            item["actual_size"] = actual_size_str
            item["size_bytes"] = size_bytes
            item["is_active"] = (m["id"] == self.settings.get("active_model", config.DEFAULT_WHISPER_MODEL))
            item["folder_path"] = str(folder_path)
            models_list.append(item)

        if total_bytes > 1024 * 1024 * 1024:
            total_size_str = f"{total_bytes / (1024**3):.2f} GB"
        else:
            total_size_str = f"{total_bytes / (1024**2):.1f} MB"

        return {
            "models_dir": str(self.models_dir),
            "total_size": total_size_str,
            "total_bytes": total_bytes,
            "installed_count": sum(1 for m in models_list if m["is_installed"]),
            "models": models_list
        }

    def reveal_in_finder(self) -> bool:
        """Opens macOS Finder to the local models folder."""
        try:
            if config.IS_MACOS:
                subprocess.run(["open", str(self.models_dir)], check=True)
                return True
            elif config.IS_WINDOWS:
                os.startfile(str(self.models_dir))
                return True
            else:
                subprocess.run(["xdg-open", str(self.models_dir)], check=True)
                return True
        except Exception as e:
            print(f"[SettingsManager] Reveal in Finder error: {e}", flush=True)
            return False

    def get_audio_devices(self) -> List[Dict[str, Any]]:
        """Queries sounddevice for available input devices, highlighting the active system default."""
        device_list = []
        try:
            import sounddevice as sd
            try:
                sd._terminate()
                sd._initialize()
            except Exception:
                pass
            devices = sd.query_devices()
            default_id = sd.default.device[0]
            current_active_id = self.settings.get("microphone_device_id")

            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    name = dev.get("name", f"Microphone {idx}")
                    name_lower = name.lower()
                    is_system_default = (idx == default_id)
                    is_recommended = is_system_default or (("macbook" in name_lower or "built-in" in name_lower) and "iphone" not in name_lower)
                    is_selected = (idx == current_active_id) if current_active_id is not None else is_system_default
                    device_list.append({
                        "id": idx,
                        "name": f"{name} (Active System Default)" if is_system_default else name,
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": int(dev.get("default_samplerate", 16000)),
                        "is_recommended": is_recommended,
                        "is_selected": is_selected
                    })
        except Exception as e:
            print(f"[SettingsManager] Audio devices query error: {e}", flush=True)
        return device_list

    def get_permissions_status(self) -> Dict[str, Any]:
        """Returns macOS Microphone and Accessibility permission states."""
        status = {
            "microphone_granted": True,
            "accessibility_granted": True
        }
        if config.IS_MACOS:
            try:
                from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
                mic = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
                status["microphone_granted"] = (mic == 3)
            except Exception:
                pass
            try:
                from ApplicationServices import AXIsProcessTrusted
                status["accessibility_granted"] = bool(AXIsProcessTrusted())
            except Exception:
                pass
        return status
