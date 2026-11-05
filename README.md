# LocalWhisper 🎙️⚡
> **100% Offline Local Voice-to-Text Desktop App with Real-Time Live Dictation, Floating Capsule UI & Smart Flow AI**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)]()
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)]()
[![Faster-Whisper](https://img.shields.io/badge/Whisper-faster--whisper-orange.svg)]()
[![Offline](https://img.shields.io/badge/Privacy-100%25%20Offline-success.svg)]()

LocalWhisper is a privacy-first, completely local speech-to-text application inspired by **Wispr Flow / WhisperFlow** and the **Gemini voice typing** experience. Built with a signature **Kree8 Studio** aesthetic, it features a minimal floating capsule pill with audio-reactive spectrum waveforms and a comprehensive Obsidian & Mint Green Settings Dashboard.

It runs entirely on-device with **zero external API calls**, zero telemetry, and zero latency overhead.

---

## ✨ Features

- 🔒 **100% Offline & Private**: Audio is recorded and processed locally on your machine. No cloud, no subscription, no telemetry.
- ⚡ **Real-Time Live Dictation**: Words stream and type directly at your active text cursor in real time as you speak—no waiting for silence or hitting stop.
- 🎯 **Continuous Hands-Free Mode (Gemini Style)**: Intelligent Voice Activity Detection (VAD) monitors your speech passively and automatically types when you talk.
- 🛡️ **Hardware Fault-Tolerance & Auto-Fallback**: Automatically senses your active microphone and seamlessly cascades from disconnected Bluetooth earbuds (e.g. AirPods, realme Buds) to the built-in MacBook microphone without interrupting your session.
- 💊 **Minimalist Floating Capsule Pill**:
  - Ultra-sleek glassmorphic capsule that floats on top of all applications.
  - 6-dot drag grip to position anywhere on screen.
  - Idle state with ambient mint logo glow.
  - Active state expands into a 12-bar dynamic rainbow spectrum waveform.
- 🎛️ **Obsidian & Mint Dashboard & Settings**:
  - Manage and switch Whisper models on the fly (`tiny.en`, `base.en`, `small.en`, `medium.en`, `large-v3-turbo`).
  - Real-time audio VU meter and microphone sensitivity threshold controls.
  - Audio device selector with active system default detection.
- 🧠 **Smart Flow Text Processing**:
  - Automatically cleans verbal fillers (*"um", "uh", "you know"*).
  - Intelligently converts spoken punctuation (*"comma", "new line", "bullet point"*).
  - Specialized formatting modes: **Smart Dictation**, **Developer/Code**, **Email**, and **Raw**.
- ⌨️ **Global Hotkey & Direct Active Cursor Injection**:
  - Press `Cmd + Shift + Space` (macOS) or `Ctrl + Shift + Space` (Windows) to dictate anywhere (Slack, VS Code, Browser, Notes, Terminal).
  - Supports both **Toggle** and **Push-to-Talk** modes.

---

## 🚀 Quick Start

### Prerequisites
- **macOS** (macOS 11+ Big Sur, Monterey, Ventura, Sonoma, Sequoia) or **Windows 10/11**
- **Python 3.9+**

### macOS / Linux
```bash
# Clone the repository
git clone https://github.com/yourusername/localwhisper.git
cd localwhisper

# Launch LocalWhisper (automatically sets up .venv & installs dependencies on first run)
chmod +x run.sh
./run.sh
```

### Windows
Double-click `run.bat` or run in terminal:
```cmd
run.bat
```

---

## 🍏 Building the Native macOS Application Bundle

To install LocalWhisper as a standalone native macOS `.app` in `~/Applications`:

```bash
# Compile and codesign the native Mach-O app bundle
.venv/bin/python build_macos_app.py
```
This compiles a native Mach-O binary (`Contents/MacOS/LocalWhisper`) with standard entitlements and registers it with macOS LaunchServices. You can launch it directly from **Spotlight** (`⌘ Space -> LocalWhisper`) or **Finder**.

---

## 🎛️ Flow Modes

| Mode | Purpose | Spoken Input | Injected Output |
| :--- | :--- | :--- | :--- |
| **⚡ Smart** | Clean dictation, removes fillers & formats punctuation | *"um so basically we should test this comma new line bullet point one"* | *So basically we should test this, • one* |
| **💻 Developer** | Formats code constructs, symbols, and camelCase | *"create a function compute hash taking input string"* | *Create a def compute_hash(): taking input string* |
| **✉️ Email** | Formats professional emails with greetings & sign-offs | *"hello team hope you are well please review the pr thanks"* | *Hello team,\n\nHope you are well please review the pr\n\nThanks,* |
| **🎙️ Raw** | Verbatim raw transcription without post-processing | *"um test test"* | *um test test* |

---

## 🧠 Local Models

LocalWhisper uses [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) for maximum speed and minimal memory footprint:

| Model | Download Size | RAM Usage | Speed | Recommended For |
| :--- | :--- | :--- | :--- | :--- |
| **`tiny.en`** | ~75 MB | ~390 MB | ⚡⚡⚡ (~180ms) | Ultra-fast notes, low-power machines |
| **`base.en`** *(Default)* | ~142 MB | ~500 MB | ⚡⚡ (~450ms) | Optimal balance of speed and accuracy |
| **`small.en`** | ~480 MB | ~1.0 GB | ⚡ (~1.1s) | Accents, technical & developer terms |
| **`medium.en`** | ~1.5 GB | ~2.6 GB | 🎯 (~2.8s) | Complex dictation & studio-level accuracy |
| **`large-v3-turbo`** | ~1.6 GB | ~2.8 GB | 🌐 (~1.8s) | Multilingual transcription champion |

*Models are saved in `models/whisper/` and load entirely from disk.*

---

## 📁 Repository Structure

```
localwhisper/
├── app.py                   # Master app coordinator & pywebview native bridge
├── config.py                # Core configuration & defaults
├── build_macos_app.py       # Compiles self-contained macOS .app bundle
├── launcher.m               # Native Mach-O launcher with permission pre-warming
├── entitlements.plist       # macOS hardened runtime entitlements
├── requirements.txt         # Production dependencies
├── run.sh                   # macOS/Linux launcher script
├── run.bat                  # Windows launcher script
├── settings.example.json    # Default settings template
├── assets/
│   └── logo.png             # Official Mint Green brand emblem
├── engine/
│   ├── audio_recorder.py    # Resilient audio capture with auto-device fallback
│   ├── transcriber.py       # Offline faster-whisper engine
│   ├── live_streamer.py     # Real-time incremental delta typing engine
│   ├── hands_free.py        # Continuous hands-free VAD dictation engine
│   ├── llama_formatter.py   # Smart Flow punctuation & filler cleaner
│   ├── injector.py          # Quartz / CGEvent active cursor text injector
│   ├── hotkey_manager.py    # Cross-platform global hotkey listener
│   ├── settings_manager.py  # Persistent preferences & model discovery
│   └── permissions.py       # System permission auditing
├── ui/
│   ├── index.html           # Floating capsule pill interface
│   ├── styles.css           # Pill styling & 12-bar spectrum animation
│   ├── app.js               # Capsule event handling & audio reactivity
│   ├── settings.html        # Obsidian & Mint Settings Dashboard
│   ├── settings.css         # Kree8 design tokens & dashboard styling
│   ├── settings.js          # Dynamic model management & hardware controls
│   └── refraction.js        # Interactive caustic dispersion background
└── tests/
    ├── fixtures/            # Test audio samples
    ├── test_system.py       # Component integrity suite
    ├── test_no_duplicates.py# Zero-duplicate streaming verification
    └── verify_end_to_end.py # 8-step end-to-end headless audit
```

---

## 🧪 Testing

Run the test suite headlessly from the repository root:

```bash
# Verify all components
.venv/bin/python tests/test_system.py

# Verify zero-duplicate live streaming
.venv/bin/python tests/test_no_duplicates.py

# Run complete 8-step end-to-end system audit
.venv/bin/python tests/verify_end_to_end.py
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
