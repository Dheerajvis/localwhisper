import time
import queue
import threading
from collections import deque
from typing import Optional, Callable, Tuple
import numpy as np
import sounddevice as sd
import config
from engine.live_streamer import LiveStreamer

class HandsFreeEngine:
    """
    Continuous Hands-Free Dictation Engine with Real-Time VAD.
    Passively monitors the auto-sensed microphone in real-time, detects voice activity,
    streams audio to Whisper, and types recognized words into the active cursor position
    in real time as the user speaks.
    """

    def __init__(
        self,
        transcriber,
        formatter,
        injector,
        settings_mgr,
        on_status_change: Optional[Callable[[str, str], None]] = None,
        on_transcript: Optional[Callable[[str, float], None]] = None
    ):
        self.transcriber = transcriber
        self.formatter = formatter
        self.injector = injector
        self.settings_mgr = settings_mgr
        self.on_status_change = on_status_change
        self.on_transcript = on_transcript

        self.sample_rate = config.SAMPLE_RATE
        self.channels = config.CHANNELS
        self.blocksize = 1024  # 64ms per block at 16kHz

        # Settings
        settings = self.settings_mgr.get_all_settings()
        self.is_enabled = settings.get("hands_free_mode", True)
        self.is_muted = settings.get("hands_free_muted", False)
        self.silence_threshold = float(settings.get("silence_threshold", 0.0028))

        # Runtime State
        self.is_running = False
        self.is_speaking = False
        self.noise_floor = 0.0020
        self.active_device_id = settings.get("microphone_device_id", None)
        self.active_device_name = "Auto-Sensed"

        # Thresholds tuned for real human voice vs ambient room noise
        self.consecutive_speech_needed = 2    # ~128ms of speech to trigger onset
        self.silence_pause_needed = 7         # ~448ms of silence to conclude utterance
        self.min_speech_samples = 3200        # At least 0.20s to filter short mic clicks

        # Real-time streaming typing engine
        self.streamer = LiveStreamer(
            recorder=None,
            transcriber=self.transcriber,
            injector=self.injector,
            formatter=self.formatter,
            on_partial_text=self._on_stream_partial
        )

        # Threading Queues
        self._raw_queue = queue.Queue(maxsize=100)
        self._streaming_queue = queue.Queue(maxsize=2)
        self._stream: Optional[sd.InputStream] = None

        self._process_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None

    def _refresh_portaudio(self):
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            pass

    def _get_candidate_devices(self, preferred_id: Optional[int] = None) -> list:
        self._refresh_portaudio()
        candidates = []
        seen = set()

        try:
            devices = sd.query_devices()
        except Exception:
            devices = []

        def add_candidate(dev_idx: Optional[int]):
            if dev_idx in seen:
                return
            if dev_idx is None:
                seen.add(None)
                candidates.append((None, "System Default"))
                return
            if 0 <= dev_idx < len(devices):
                d = devices[dev_idx]
                if d.get("max_input_channels", 0) > 0:
                    seen.add(dev_idx)
                    candidates.append((dev_idx, d.get("name", f"Device {dev_idx}")))

        if preferred_id is not None:
            add_candidate(preferred_id)

        try:
            def_in = sd.default.device[0]
            if def_in is not None:
                add_candidate(def_in)
        except Exception:
            pass

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                name_l = dev.get("name", "").lower()
                if ("macbook" in name_l or "built-in" in name_l or "internal" in name_l) and "iphone" not in name_l:
                    add_candidate(idx)

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                name_l = dev.get("name", "").lower()
                if "blackhole" not in name_l and "virtual" not in name_l and "iphone" not in name_l:
                    add_candidate(idx)

        add_candidate(None)
        return candidates

    def start(self, device_id: Optional[int] = None) -> bool:
        """Starts the continuous hands-free stream and worker threads with resilient device fallback."""
        if self.is_running:
            return True

        self.is_running = True

        # Start audio consumer and live streaming worker
        self._process_thread = threading.Thread(target=self._process_audio_loop, daemon=True)
        self._worker_thread = threading.Thread(target=self._streaming_worker_loop, daemon=True)
        self._process_thread.start()
        self._worker_thread.start()

        candidates = self._get_candidate_devices(device_id)

        for cand_id, cand_name in candidates:
            try:
                stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=config.DTYPE,
                    callback=self._audio_callback,
                    device=cand_id,
                    blocksize=self.blocksize
                )
                stream.start()
                self._stream = stream
                self.active_device_id = cand_id
                self.active_device_name = cand_name
                print(f"[HandsFreeEngine] Listening on device: '{cand_name}' (ID: {cand_id})...", flush=True)
                self._notify_status("idle", "Hands-Free Active")
                return True
            except Exception as e:
                print(f"[HandsFreeEngine] Could not start on '{cand_name}' (ID: {cand_id}): {e}", flush=True)
                self._refresh_portaudio()

        print("[HandsFreeEngine] Error: All candidate devices failed.", flush=True)
        self.is_running = False
        return False

    def stop(self):
        """Stops hands-free engine cleanly."""
        self.is_running = False
        if self._stream:
            try:
                self._stream.abort()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._notify_status("idle", "Hands-Free Off")

    def toggle_mute(self) -> bool:
        """Toggles temporary mute on/off for privacy without stopping stream."""
        self.is_muted = not self.is_muted
        self.settings_mgr.save({"hands_free_muted": self.is_muted})
        state = "muted" if self.is_muted else "idle"
        details = "Muted (Paused)" if self.is_muted else "Hands-Free Active"
        print(f"[HandsFreeEngine] Mute toggled: is_muted={self.is_muted}", flush=True)
        self._notify_status(state, details)
        return self.is_muted

    def set_enabled(self, enabled: bool):
        """Enables or disables hands-free dictation."""
        self.is_enabled = enabled
        self.settings_mgr.save({"hands_free_mode": enabled})
        if not enabled:
            self.is_speaking = False
            self._notify_status("idle", "Manual Mode")
        else:
            self._notify_status("idle", "Hands-Free Active")

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice streaming callback (lock-free queue push)."""
        if not self.is_running:
            return
        audio_chunk = indata[:, 0].copy()
        try:
            self._raw_queue.put_nowait(audio_chunk)
        except queue.Full:
            pass

    def _on_stream_partial(self, partial_text: str):
        """Forward live streaming partials to UI callback."""
        if self.on_transcript and partial_text:
            self.on_transcript(partial_text, 0.0)

    def _process_audio_loop(self):
        """Continuous VAD processor: segments speech and feeds real-time streaming worker."""
        pre_speech_ring = deque(maxlen=4)  # ~250ms pre-speech audio buffer
        current_speech_chunks = []
        speech_counter = 0
        silence_counter = 0
        last_stream_time = 0.0

        while self.is_running:
            try:
                chunk = self._raw_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if not self.is_enabled or self.is_muted:
                pre_speech_ring.clear()
                current_speech_chunks.clear()
                self.is_speaking = False
                continue

            # Calculate RMS Energy
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            # Update adaptive background noise floor during silence
            if not self.is_speaking:
                self.noise_floor = 0.98 * self.noise_floor + 0.02 * rms

            # Sensitive speech threshold tuned for Bluetooth earbuds & laptop mics
            effective_threshold = max(self.silence_threshold, self.noise_floor * 1.8, 0.0025)
            is_speech = (rms >= effective_threshold)

            if is_speech:
                speech_counter += 1
                silence_counter = 0

                if not self.is_speaking and speech_counter >= self.consecutive_speech_needed:
                    self.is_speaking = True
                    self.streamer.reset()
                    last_stream_time = time.time()
                    self._notify_status("listening", "Listening...")
                    current_speech_chunks = list(pre_speech_ring) + [chunk]
                elif self.is_speaking:
                    current_speech_chunks.append(chunk)

                    # Stream incremental audio snapshot to live typing worker every ~360ms
                    now = time.time()
                    if len(current_speech_chunks) >= 5 and (now - last_stream_time) >= 0.36:
                        last_stream_time = now
                        snapshot = np.concatenate(current_speech_chunks)
                        # Put to worker; if worker is busy, drop older partial so it stays real-time
                        try:
                            if self._streaming_queue.full():
                                try:
                                    self._streaming_queue.get_nowait()
                                except queue.Empty:
                                    pass
                            self._streaming_queue.put_nowait((snapshot, False))
                        except Exception:
                            pass
            else:
                speech_counter = 0

                if self.is_speaking:
                    silence_counter += 1
                    current_speech_chunks.append(chunk)

                    # When silence reaches pause threshold, conclude this utterance
                    if silence_counter >= self.silence_pause_needed:
                        self.is_speaking = False
                        if current_speech_chunks:
                            final_segment = np.concatenate(current_speech_chunks)
                            if len(final_segment) >= self.min_speech_samples:
                                try:
                                    self._streaming_queue.put((final_segment, True), timeout=0.5)
                                except queue.Full:
                                    pass
                        current_speech_chunks = []
                        silence_counter = 0
                        self._notify_status("transcribing", "Finalizing...")
                else:
                    pre_speech_ring.append(chunk)

    def _streaming_worker_loop(self):
        """Worker thread: decodes partial/final audio and types words into cursor live as you speak."""
        while self.is_running:
            try:
                item = self._streaming_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            audio_segment, is_final = item
            t0 = time.time()

            try:
                # Process audio and type new words directly at active cursor
                delta = self.streamer.process_audio(audio_segment, is_final=is_final)
                latency_ms = (time.time() - t0) * 1000

                if is_final:
                    full_text = " ".join(self.streamer.typed_words).strip()
                    if full_text:
                        print(f"[HandsFreeEngine] Phrase complete: \"{full_text}\" ({latency_ms:.1f}ms)", flush=True)
                        if self.on_transcript:
                            self.on_transcript(full_text, latency_ms)
                        self._notify_status("pasted", f"Typed {len(full_text)} chars")
                    else:
                        self._notify_status("idle", "Hands-Free Active")
                    # Reset streamer for next spoken phrase
                    self.streamer.reset()
                    time.sleep(0.3)
                    self._notify_status("idle", "Hands-Free Active")

            except Exception as e:
                print(f"[HandsFreeEngine] Live streaming worker error: {e}", flush=True)
                if is_final:
                    self.streamer.reset()
                    self._notify_status("idle", "Hands-Free Active")

    def _transcription_worker_loop(self):
        """Compatibility alias for streaming worker loop."""
        return self._streaming_worker_loop()

    def _notify_status(self, state: str, details: str = ""):
        """Sends UI status update via callback."""
        if self.on_status_change:
            try:
                self.on_status_change(state, details)
            except Exception as e:
                print(f"[HandsFreeEngine] Status notify error: {e}", flush=True)
