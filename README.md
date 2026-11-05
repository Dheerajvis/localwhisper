# LocalWhisper 🎙️⚡
> **100% Offline Local Voice-to-Text Desktop App with Real-Time Live Dictation, Floating Capsule UI & Smart Flow AI**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)]()
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)]()
[![Faster-Whisper](https://img.shields.io/badge/Whisper-faster--whisper-orange.svg)]()
[![Offline](https://img.shields.io/badge/Privacy-100%25%20Offline-success.svg)]()
[![GitHub Release](https://img.shields.io/github/v/release/Dheerajvis/localwhisper)](https://github.com/Dheerajvis/localwhisper/releases)

LocalWhisper is a privacy-first, completely local speech-to-text desktop application featuring real-time live voice dictation. Built with a modern obsidian and mint aesthetic, it features a minimal floating capsule pill with audio-reactive spectrum waveforms and a comprehensive offline Settings Dashboard.

It runs entirely on-device with **zero external API calls**, zero telemetry, and zero latency overhead.

---

## 📦 Direct App Download (Ready to Run)

Skip setup and download the pre-compiled builds directly from [**GitHub Releases**](https://github.com/Dheerajvis/localwhisper/releases):

| Operating System | Download Link | Quick Instructions |
| :--- | :--- | :--- |
| **🍎 macOS (Apple Silicon M1/M2/M3/M4)** | [**LocalWhisper-v1.0.0-macOS-arm64.zip**](https://github.com/Dheerajvis/localwhisper/releases/download/v1.0.0/LocalWhisper-v1.0.0-macOS-arm64.zip) | Extract `.zip`, drag `LocalWhisper.app` to Applications, and double-click to launch. |
| **🪟 Windows (10 / 11 64-bit)** | [**GitHub Releases**](https://github.com/Dheerajvis/localwhisper/releases) *(or 1-Click `run.bat` below)* | Download from Releases, or download repository zip and double-click `run.bat`. |

---

## ✨ Features

- 🔒 **100% Offline & Private**: Audio is recorded and transcribed in-memory on your machine. No cloud, no subscriptions, no telemetry.
- ⚡ **Real-Time Live Dictation**: Words stream and type directly at your active text cursor in real time as you speak—no waiting for silence or hitting stop.
- 🎯 **Continuous Hands-Free Mode**: Intelligent Voice Activity Detection (VAD) monitors your speech passively and automatically types when you speak.
- 🛡️ **Hardware Fault-Tolerance & Auto-Fallback**: Automatically senses your active microphone and seamlessly cascades from disconnected Bluetooth earbuds (AirPods, Galaxy Buds, realme Buds) to the built-in microphone without interrupting your dictation.
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
  - Press `Cmd + Shift + Space` (macOS) or `Ctrl + Shift + Space` (Windows) to dictate anywhere (Slack, VS Code, Browser, Word, Notepad, Terminal).
  - Supports both **Toggle** and **Push-to-Talk** modes.

---

## 💻 Running on Windows

LocalWhisper is fully optimized for Windows 10 and Windows 11 with native active window tracking and text typing.

### Option 1: 1-Click Auto-Setup (`run.bat`)
1. Download or clone this repository:
   ```cmd
   git clone https://github.com/Dheerajvis/localwhisper.git
   cd localwhisper
   ```
2. Double-click `run.bat` (or run `run.bat` in Command Prompt / PowerShell).
   - `run.bat` automatically checks Python 3.9+, creates an isolated `.venv`, installs requirements, and launches LocalWhisper.
3. Start dictating with `Ctrl + Shift + Space` or `Ctrl + Alt + Space`.

### Windows Tips & Settings:
- **Default Hotkey**: `Ctrl + Shift + Space` (toggle recording) or `Ctrl + Alt + Space`.
- **Text Typing**: Automatically injects text directly into the focused window (Word, Notepad, Browser, Discord, VS Code, Slack).
- **Microphone Access**: If prompted, ensure **Settings > Privacy & security > Microphone** is toggled ON for desktop apps.
- **Acceleration**: Runs with 8-bit quantization (`int8`) on CPU out of the box for instantaneous inference with low RAM.

---

## 🍏 Running on macOS

### Option 1: Pre-Built Standalone App
1. Download [**LocalWhisper-v1.0.0-macOS-arm64.zip**](https://github.com/Dheerajvis/localwhisper/releases/download/v1.0.0/LocalWhisper-v1.0.0-macOS-arm64.zip).
2. Unzip and move `LocalWhisper.app` to your `/Applications` or `~/Applications` folder.
3. Double-click to launch.

*Note on macOS Permissions:*
On first launch, macOS will prompt for:
1. **Microphone**: Required to capture audio offline.
2. **Accessibility**: Required to type text directly at the cursor in your active applications. (If not prompted automatically, open **System Settings > Privacy & Security > Accessibility** and enable LocalWhisper).

### Option 2: Run from Source (`run.sh`)
```bash
git clone https://github.com/Dheerajvis/localwhisper.git
cd localwhisper
chmod +x run.sh
./run.sh
```

---

## 🎛️ Flow Modes

| Mode | Purpose | Spoken Input | Injected Output |
| :--- | :--- | :--- | :--- |
| **⚡ Smart** | Clean dictation, removes fillers & formats punctuation | *"um so basically we should test this comma new line bullet point one"* | *So basically we should test this, • one* |
| **💻 Developer** | Formats code constructs, symbols, and camelCase | *"create a function compute hash taking input string"* | *Create a def compute_hash(): taking input string* |
| **✉️ Email** | Formats professional emails with greetings & sign-offs | *"hello team hope you are well please review the pr thanks"* | *Hello team,\n\nHope you are well please review the pr\n\nThanks,* |
| **🎙️ Raw** | Verbatim raw transcription without post-processing | *"um test test"* | *um test test* |

---

## 🧠 Local Whisper Models

LocalWhisper uses [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) with optimized 8-bit quantization for maximum speed and minimal memory footprint:

| Model | Download Size | RAM Usage | Speed | Recommended For |
| :--- | :--- | :--- | :--- | :--- |
| **`tiny.en`** | ~75 MB | ~390 MB | ⚡⚡⚡ (~180ms) | Ultra-fast notes, low-power machines |
| **`base.en`** *(Default)* | ~142 MB | ~500 MB | ⚡⚡ (~450ms) | Optimal balance of speed and accuracy |
| **`small.en`** | ~480 MB | ~1.0 GB | ⚡ (~1.1s) | Accents, technical & developer terms |
| **`medium.en`** | ~1.5 GB | ~2.6 GB | 🎯 (~2.8s) | Complex dictation & studio-level accuracy |
| **`large-v3-turbo`** | ~1.6 GB | ~2.8 GB | 🌐 (~1.8s) | Multilingual transcription champion |

*Models are downloaded once to your local user application directory and run 100% offline.*

---

## 📁 Repository Structure

```
localwhisper/
├── .github/workflows/
│   └── build-and-release.yml# Multi-platform CI/CD for Windows & macOS builds
├── app.py                   # Master app coordinator & pywebview native bridge
├── config.py                # Cross-platform configuration & defaults
├── localwhisper.spec        # Standalone PyInstaller build specification
├── build_macos_app.py       # Compiles self-contained macOS .app bundle
├── launcher.m               # Native Mach-O launcher with permission pre-warming
├── entitlements.plist       # macOS hardened runtime entitlements
├── requirements.txt         # Production dependencies with platform markers
├── run.sh                   # macOS/Linux launcher script
├── run.bat                  # Windows launcher & auto-setup script
├── settings.example.json    # Default settings template
├── assets/
│   └── logo.png             # Official Mint Green brand emblem
├── engine/
│   ├── audio_recorder.py    # Resilient audio capture with auto-device fallback
│   ├── transcriber.py       # Offline faster-whisper engine
│   ├── live_streamer.py     # Real-time incremental delta typing engine
│   ├── hands_free.py        # Continuous hands-free VAD dictation engine
│   ├── llama_formatter.py   # Smart Flow punctuation & filler cleaner
│   ├── injector.py          # Native cursor text injector (Quartz on Mac, user32 on Windows)
│   ├── hotkey_manager.py    # Cross-platform global hotkey listener
│   ├── settings_manager.py  # Persistent preferences & model discovery
│   └── permissions.py       # System permission auditing
├── ui/
│   ├── index.html           # Floating capsule pill interface
│   ├── styles.css           # Pill styling & 12-bar spectrum animation
│   ├── app.js               # Capsule event handling & audio reactivity
│   ├── settings.html        # Obsidian & Mint Settings Dashboard
│   ├── settings.css         # Modern design tokens & dashboard styling
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
python tests/test_system.py

# Verify zero-duplicate live streaming
python tests/test_no_duplicates.py

# Run complete 8-step end-to-end system audit
python tests/verify_end_to_end.py
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
