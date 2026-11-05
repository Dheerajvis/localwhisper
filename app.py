import os
import sys
import time
import threading
from pathlib import Path
import numpy as np
import webview
import config
from engine.audio_recorder import AudioRecorder
from engine.transcriber import Transcriber
from engine.llama_formatter import LlamaFormatter
from engine.injector import TextInjector
from engine.hotkey_manager import HotkeyManager
from engine.settings_manager import SettingsManager
from engine.hands_free import HandsFreeEngine
from engine.live_streamer import LiveStreamer

class LocalWhisperBridge:
    """Clean JavaScript API Bridge for the floating pill UI."""
    def __init__(self, app):
        self._app = app

    def toggle_recording(self):
        self._app.toggle_recording()

    def set_mode(self, mode):
        self._app.set_mode(mode)

    def set_model(self, model_name):
        self._app.set_model(model_name)

    def toggle_hands_free(self):
        current = self._app.settings_mgr.settings.get("hands_free_mode", False)
        self._app.update_setting("hands_free_mode", not current)

    def open_settings(self):
        self._app.open_settings_window()

    def open_accessibility_settings(self):
        self._app.injector.open_accessibility_settings()

    def quit(self):
        self._app.quit()

class SettingsBridge:
    """API Bridge specifically for the dedicated Settings & Models window."""
    def __init__(self, app):
        self._app = app

    def get_models_info(self):
        return self._app.settings_mgr.get_models_metadata()

    def get_settings(self):
        return self._app.settings_mgr.get_all_settings()

    def save_setting(self, key, value):
        return self._app.update_setting(key, value)

    def reveal_in_finder(self):
        return self._app.settings_mgr.reveal_in_finder()

    def switch_model(self, model_id):
        return self._app.switch_model(model_id)

    def get_audio_devices(self):
        return self._app.settings_mgr.get_audio_devices()

    def test_microphone(self):
        return self._app.test_mic_sample()

    def get_permissions(self):
        return self._app.settings_mgr.get_permissions_status()

    def open_accessibility_settings(self):
        self._app.injector.open_accessibility_settings()

class LocalWhisperApp:
    def __init__(self):
        self.settings_mgr = SettingsManager()
        saved = self.settings_mgr.get_all_settings()

        self.window = None
        self.settings_window = None
        
        self.recorder = AudioRecorder()
        saved_device = saved.get("microphone_device_id")
        if saved_device is not None:
            self.recorder.active_device_id = saved_device

        active_model = saved.get("active_model", config.DEFAULT_WHISPER_MODEL)
        self.transcriber = Transcriber(model_size=active_model)

        active_mode = saved.get("active_mode", config.DEFAULT_FLOW_MODE)
        self.formatter = LlamaFormatter(mode=active_mode)

        self.injector = TextInjector()
        self.auto_paste = saved.get("auto_paste", True)

        self.live_streamer = LiveStreamer(
            recorder=self.recorder,
            transcriber=self.transcriber,
            injector=self.injector,
            formatter=self.formatter,
            on_partial_text=self._on_live_stream_partial
        )

        self.hands_free = HandsFreeEngine(
            transcriber=self.transcriber,
            formatter=self.formatter,
            injector=self.injector,
            settings_mgr=self.settings_mgr,
            on_status_change=self._on_hands_free_status,
            on_transcript=self._on_hands_free_transcript
        )

        self.hotkey_mgr = None
        self._is_processing = False
        self._lock = threading.Lock()

    def _on_live_stream_partial(self, text: str):
        if self.window:
            try:
                escaped = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                self.window.evaluate_js(f'window.setTranscript("{escaped}");')
            except Exception:
                pass

    def _on_hands_free_status(self, state: str, details: str = ""):
        if self.window:
            try:
                self.window.evaluate_js(f"window.updateState('{state}', '{details}');")
            except Exception:
                pass

    def _on_hands_free_transcript(self, text: str, latency_ms: float = 0.0):
        if self.window:
            try:
                escaped = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                self.window.evaluate_js(f'window.setTranscript("{escaped}", {latency_ms:.1f});')
            except Exception:
                pass

    def start_recording(self):
        """Starts real-time live recording and typing."""
        with self._lock:
            if self._is_processing or self.recorder.is_recording:
                return

            print("[LocalWhisperApp] Starting new recording session with real-time live typing...", flush=True)
            self.injector.capture_target_app()
            self.injector.reset()
            self.live_streamer.reset()
            
            # Temporarily pause hands-free background listener so there is no microphone contention
            if self.hands_free and self.hands_free.is_running:
                self.hands_free.is_muted = True

            # Check for customized microphone device
            dev_id = self.settings_mgr.settings.get("microphone_device_id")
            success = self.recorder.start(device_id=dev_id)
            if success:
                self.live_streamer.start()
                if self.window:
                    self.window.evaluate_js("window.updateState('listening');")
                threading.Thread(target=self._meter_audio_loop, daemon=True).start()
            else:
                print("[LocalWhisperApp] Failed to start audio recorder on any candidate device.", flush=True)
                if self.window:
                    self.window.evaluate_js("window.updateState('idle');")

    def stop_recording(self):
        """Stops audio recording and finalizes transcribed text."""
        with self._lock:
            if not self.recorder.is_recording or self._is_processing:
                return

            print("[LocalWhisperApp] Stopping recording session and finalizing stream...", flush=True)
            self._is_processing = True
            if self.window:
                self.window.evaluate_js("window.updateState('transcribing');")
            
            # Asynchronously stop the recorder and process the audio in a worker thread
            threading.Thread(target=self._stop_and_process, daemon=True).start()

    def toggle_recording(self):
        """Toggles recording and types transcribed text directly into the active cursor in real-time."""
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _stop_and_process(self):
        """Worker thread: Stops audio recording, finalizes live streaming, and updates UI."""
        try:
            audio = self.recorder.stop()
            final_text = self.live_streamer.stop_and_finalize(audio)
            print(f"[LocalWhisperApp] Live dictation complete: \"{final_text}\"", flush=True)

            if self.window:
                escaped = final_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                if final_text.strip():
                    self.window.evaluate_js(f'window.setTranscript("{escaped}");')
                    self.window.evaluate_js("window.updateState('pasted');")
                else:
                    self.window.evaluate_js("window.setTranscript('No speech detected');")
                    time.sleep(0.8)
                    self.window.evaluate_js("window.updateState('idle');")
        except Exception as e:
            print(f"[LocalWhisperApp] Error in stop and process: {e}", flush=True)
            if self.window:
                self.window.evaluate_js("window.updateState('idle');")
        finally:
            with self._lock:
                self._is_processing = False
                # Restore hands-free state if enabled
                if self.hands_free and self.hands_free.is_enabled:
                    self.hands_free.is_muted = self.settings_mgr.settings.get("hands_free_muted", False)

    def _meter_audio_loop(self):
        """Pushes real-time microphone volume to UI while recording."""
        while self.recorder.is_recording:
            try:
                lvl = self.recorder.get_level()
                if self.window:
                    self.window.evaluate_js(f"window.updateAudioLevel({lvl:.3f});")
            except Exception:
                pass
            time.sleep(0.06)

    def _process_audio(self, audio):
        """Transcribes, polishes, and directly types text into active cursor window."""
        try:
            start_time = time.time()
            print(f"[LocalWhisperApp] Transcribing {len(audio)} audio samples...", flush=True)
            raw_text = self.transcriber.transcribe(audio)

            if not raw_text or not raw_text.strip():
                print("[LocalWhisperApp] No speech detected in audio.", flush=True)
                if self.window:
                    self.window.evaluate_js("window.setTranscript('No speech detected');")
                    time.sleep(0.8)
                    self.window.evaluate_js("window.updateState('idle');")
                return

            if self.window:
                self.window.evaluate_js("window.updateState('formatting');")

            # Stage 2: Smart Flow post-processing
            formatted_text = self.formatter.format_text(raw_text)
            total_latency_ms = (time.time() - start_time) * 1000
            print(f"[LocalWhisperApp] Polished text: \"{formatted_text}\" (took {total_latency_ms:.1f}ms)", flush=True)

            # Stage 3: Refocus target window and type directly into the cursor
            print(f"[LocalWhisperApp] Typing directly into active cursor: \"{formatted_text}\"", flush=True)
            if self.injector.last_target_app is not None:
                try:
                    self.injector.last_target_app.activateWithOptions_(3)
                    time.sleep(0.04)
                except Exception:
                    pass

            success, reason = self.injector.type_text_at_cursor(formatted_text)
            if not success and reason != "needs_accessibility":
                # Fallback to clipboard Cmd+V paste if Quartz direct keystroke failed
                auto_paste_active = self.settings_mgr.settings.get("auto_paste", True)
                success, reason = self.injector.inject_text(formatted_text, auto_paste=auto_paste_active)

            # Stage 4: UI feedback
            if self.window:
                escaped = formatted_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
                if success:
                    self.window.evaluate_js(f'window.setTranscript("{escaped}", {total_latency_ms:.1f});')
                    self.window.evaluate_js("window.updateState('pasted');")
                elif reason == "needs_accessibility":
                    self.window.evaluate_js('window.setTranscript("Copied! Press ⌘V (Enable Accessibility to auto-type)");')
                    self.window.evaluate_js("window.updateState('needs_accessibility');")
                else:
                    self.window.evaluate_js(f'window.setTranscript("{escaped}", {total_latency_ms:.1f});')
                    self.window.evaluate_js("window.updateState('pasted');")

        except Exception as e:
            print(f"[LocalWhisperApp] Audio processing error: {e}", flush=True)
            if self.window:
                self.window.evaluate_js("window.updateState('idle');")

    def open_settings_window(self):
        """Opens or brings the dedicated Settings window forward."""
        if self.settings_window:
            try:
                self.settings_window.show()
                self.settings_window.restore()
                return
            except Exception:
                self.settings_window = None

        settings_html = Path(__file__).resolve().parent / "ui" / "settings.html"
        bridge = SettingsBridge(self)

        self.settings_window = webview.create_window(
            title="LocalWhisper Dashboard & Settings",
            url=f"file://{settings_html}",
            js_api=bridge,
            width=920,
            height=640,
            min_size=(840, 560),
            resizable=True
        )

        def on_closed():
            self.settings_window = None

        self.settings_window.events.closed += on_closed

    def switch_model(self, model_id: str) -> bool:
        """Loads a different Whisper model and persists preference."""
        print(f"[LocalWhisperApp] Switching active Whisper model to: '{model_id}'...", flush=True)
        self.settings_mgr.save({"active_model": model_id})
        success = self.transcriber.load_model(model_id)
        if self.window:
            self.window.evaluate_js(f"window.updateState('idle');")
        return success

    def update_setting(self, key: str, value: any) -> bool:
        """Saves a setting and updates runtime state."""
        self.settings_mgr.save({key: value})
        if key == "active_mode":
            self.formatter.mode = value
            print(f"[LocalWhisperApp] Active mode updated to: {value}", flush=True)
        elif key == "auto_paste":
            self.auto_paste = bool(value)
        elif key == "hands_free_mode":
            is_enabled = bool(value)
            if self.hands_free:
                self.hands_free.set_enabled(is_enabled)
                if is_enabled and not self.hands_free.is_running:
                    self.hands_free.start()
                elif not is_enabled and self.hands_free.is_running:
                    self.hands_free.stop()
            print(f"[LocalWhisperApp] Hands-free mode updated to: {is_enabled}", flush=True)
        elif key == "microphone_device_id":
            self.recorder.active_device_id = value
            if self.hands_free:
                self.hands_free.active_device_id = value
                if self.hands_free.is_running:
                    self.hands_free.stop()
                    self.hands_free.start(device_id=value)
            print(f"[LocalWhisperApp] Microphone input changed to device: {value}", flush=True)
        elif key == "silence_threshold":
            if self.hands_free:
                self.hands_free.silence_threshold = float(value)
        return True

    def test_mic_sample(self) -> float:
        """Captures a 1.2s live audio sample from selected mic and returns peak RMS."""
        try:
            import sounddevice as sd
            dev_id = self.settings_mgr.settings.get("microphone_device_id")
            if dev_id is None:
                dev_id, _ = self.recorder.get_best_input_device()
            
            samples = sd.rec(int(16000 * 1.2), samplerate=16000, channels=1, dtype='float32', device=dev_id)
            sd.wait()
            rms = float(np.sqrt(np.mean(samples ** 2)))
            return rms
        except Exception as e:
            print(f"[LocalWhisperApp] Test mic sample error: {e}", flush=True)
            return 0.0

    def set_mode(self, mode: str):
        self.formatter.mode = mode
        self.settings_mgr.save({"active_mode": mode})
        print(f"[LocalWhisperApp] Mode changed to: {mode}", flush=True)

    def set_model(self, model_name: str):
        self.switch_model(model_name)

    def quit(self):
        """Cleanly terminates the application."""
        print("[LocalWhisperApp] Quitting LocalWhisper cleanly...", flush=True)
        if self.hands_free:
            self.hands_free.stop()
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        if self.settings_window:
            try:
                self.settings_window.destroy()
            except Exception:
                pass
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        os._exit(0)

    def run(self):
        # 1. Pre-warm Whisper in background so first dictation runs at full speed
        threading.Thread(target=self.transcriber.load_model, daemon=True).start()

        # 2. Start Continuous Hands-Free Engine if enabled
        if self.hands_free.is_enabled:
            threading.Thread(target=self.hands_free.start, daemon=True).start()

        # 3. Start Global Hotkey Listener safely
        try:
            saved_mode = self.settings_mgr.settings.get("hotkey_mode", config.HOTKEY_MODE)
            self.hotkey_mgr = HotkeyManager(
                on_toggle=self.toggle_recording,
                on_press_down=self.start_recording,
                on_release=self.stop_recording,
                mode=saved_mode
            )
            self.hotkey_mgr.start()
        except Exception as e:
            print(f"[LocalWhisperApp] Hotkey manager note: {e}", flush=True)

        # 3. Create Sleek Tiny Liquid Glass Pill Window
        ui_path = Path(__file__).resolve().parent / "ui" / "index.html"
        bridge = LocalWhisperBridge(self)

        # Compact floating pill window (380x160 transparent container with complete shadow clearance)
        self.window = webview.create_window(
            title="LocalWhisper",
            url=f"file://{ui_path}",
            js_api=bridge,
            width=380,
            height=160,
            frameless=True,
            easy_drag=True,
            on_top=True,
            transparent=True,
            resizable=False
        )

        try:
            webview.start(debug=False)
        finally:
            if self.hotkey_mgr:
                self.hotkey_mgr.stop()

if __name__ == "__main__":
    app = LocalWhisperApp()
    app.run()
