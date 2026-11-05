import threading
import time
from typing import Optional, Callable, Tuple, List
import numpy as np
import sounddevice as sd
import config

def resample_to_16k(audio: np.ndarray, orig_sr: int) -> np.ndarray:
    """Downsamples audio array to 16000Hz cleanly and efficiently."""
    if len(audio) == 0 or orig_sr == 16000:
        return audio
    if orig_sr == 48000:
        return audio[::3].copy()
    if orig_sr == 32000:
        return audio[::2].copy()
    target_len = int(len(audio) * 16000 / orig_sr)
    if target_len <= 0:
        return np.array([], dtype=np.float32)
    return np.interp(
        np.linspace(0, len(audio), target_len, endpoint=False),
        np.arange(len(audio)),
        audio
    ).astype(np.float32)

class AudioRecorder:
    def __init__(self, sample_rate: int = config.SAMPLE_RATE, channels: int = config.CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._frames = []
        self._lock = threading.Lock()
        
        # Audio level metering (0.0 to 1.0)
        self.current_level: float = 0.0
        self.peak_level: float = 0.0
        self.active_device_id: Optional[int] = None
        self.active_device_name: str = "Default"
        self.stream_sample_rate: int = config.SAMPLE_RATE

    def _refresh_portaudio(self):
        """Re-initializes PortAudio so hardware changes (unplugged Bluetooth, new mics) are fresh."""
        try:
            sd._terminate()
            sd._initialize()
        except Exception as e:
            print(f"[AudioRecorder] PortAudio reinit notice: {e}", flush=True)

    def get_best_input_device(self) -> Tuple[Optional[int], str]:
        """
        Automatically senses and selects the active audio input device.
        Matches the macOS system default input device (e.g. connected Bluetooth earbuds,
        USB headset, or built-in mic if no external device is connected).
        """
        self._refresh_portaudio()
        try:
            devices = sd.query_devices()
            default_in = sd.default.device[0]

            # Primary: Follow active macOS system default input device
            if default_in is not None and 0 <= default_in < len(devices):
                dev = devices[default_in]
                if dev.get("max_input_channels", 0) > 0:
                    name = dev.get("name", "System Default")
                    return default_in, name

            # Fallback 1: Built-in MacBook Microphone
            for idx, dev in enumerate(devices):
                name = dev.get("name", "")
                channels = dev.get("max_input_channels", 0)
                if channels > 0:
                    name_lower = name.lower()
                    if ("macbook" in name_lower or "built-in" in name_lower or "internal" in name_lower) and "iphone" not in name_lower:
                        return idx, name

            # Fallback 2: Any physical input device (excluding virtual loopbacks and continuity iPhone)
            for idx, dev in enumerate(devices):
                name = dev.get("name", "")
                channels = dev.get("max_input_channels", 0)
                if channels > 0:
                    name_lower = name.lower()
                    if "blackhole" not in name_lower and "virtual" not in name_lower and "iphone" not in name_lower:
                        return idx, name

            return None, "System Default"
        except Exception as e:
            print(f"[AudioRecorder] Device sensing notice: {e}", flush=True)
            return None, "System Default"

    def _get_candidate_devices(self, preferred_id: Optional[int] = None) -> List[Tuple[Optional[int], str, int]]:
        """
        Builds a prioritized list of (device_id, name, default_samplerate) candidates.
        Ensures seamless fallback from disconnected Bluetooth headsets to built-in mic.
        """
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
                candidates.append((None, "System Default", self.sample_rate))
                return
            if 0 <= dev_idx < len(devices):
                d = devices[dev_idx]
                if d.get("max_input_channels", 0) > 0:
                    seen.add(dev_idx)
                    sr = int(d.get("default_samplerate", self.sample_rate))
                    candidates.append((dev_idx, d.get("name", f"Device {dev_idx}"), sr))

        # 1. Preferred configured device
        if preferred_id is not None:
            add_candidate(preferred_id)

        # 2. Current macOS system default input
        try:
            def_in = sd.default.device[0]
            if def_in is not None:
                add_candidate(def_in)
        except Exception:
            pass

        # 3. Built-in MacBook Microphone (most rock-solid fallback on macOS)
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                name_l = dev.get("name", "").lower()
                if ("macbook" in name_l or "built-in" in name_l or "internal" in name_l) and "iphone" not in name_l:
                    add_candidate(idx)

        # 4. Any other physical microphone (excluding virtual loopbacks and continuity iPhone)
        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                name_l = dev.get("name", "").lower()
                if "blackhole" not in name_l and "virtual" not in name_l and "iphone" not in name_l:
                    add_candidate(idx)

        # 5. System Default None fallback
        add_candidate(None)

        return candidates

    def _audio_callback(self, indata, frames, time_info, status):
        """Streaming callback invoked by sounddevice for each chunk."""
        if not self.is_recording:
            return
            
        audio_chunk = indata[:, 0].copy()
        with self._lock:
            self._frames.append(audio_chunk)

        # Compute RMS volume level (purely numeric calculation, NO Cocoa/WebKit calls)
        rms = float(np.sqrt(np.mean(audio_chunk ** 2)))
        if rms > self.peak_level:
            self.peak_level = rms
        level = float(np.clip(rms * 18.0, 0.0, 1.0))
        self.current_level = 0.4 * level + 0.6 * self.current_level

    def start(self, device_id: Optional[int] = None) -> bool:
        """
        Start capturing audio from microphone with automated multi-device resilient fallback.
        If a Bluetooth headset disconnected, it automatically falls back to the built-in mic.
        """
        with self._lock:
            if self.is_recording:
                return True
            self._frames.clear()
            self.current_level = 0.0
            self.peak_level = 0.0
            self.is_recording = True

        candidates = self._get_candidate_devices(device_id)

        for cand_id, cand_name, cand_sr in candidates:
            # Try configured sample rate (16000Hz) first, then native rate if needed
            rates_to_try = [self.sample_rate]
            if cand_sr != self.sample_rate and cand_sr > 0:
                rates_to_try.append(cand_sr)

            for rate in rates_to_try:
                try:
                    block_sz = 1024 if rate == self.sample_rate else int(1024 * rate / self.sample_rate)
                    stream = sd.InputStream(
                        samplerate=rate,
                        channels=self.channels,
                        dtype=config.DTYPE,
                        callback=self._audio_callback,
                        device=cand_id,
                        blocksize=block_sz
                    )
                    stream.start()
                    self._stream = stream
                    self.stream_sample_rate = rate
                    self.active_device_id = cand_id
                    self.active_device_name = cand_name
                    print(f"[AudioRecorder] Recording active on: '{cand_name}' (device {cand_id}) @ {rate}Hz", flush=True)
                    return True
                except Exception as e:
                    print(f"[AudioRecorder] Could not open '{cand_name}' (device {cand_id}) @ {rate}Hz: {e}", flush=True)
                    self._refresh_portaudio()

        # If every candidate failed:
        print("[AudioRecorder] Error: All candidate audio input devices failed to start.", flush=True)
        with self._lock:
            self.is_recording = False
        return False

    def stop(self) -> np.ndarray:
        """Stop recording and return captured audio as 1D float32 16kHz numpy array."""
        self.is_recording = False
            
        stream = self._stream
        self._stream = None
        if stream:
            try:
                stream.abort()
                stream.close()
            except Exception as e:
                print(f"[AudioRecorder] Error closing stream: {e}", flush=True)

        with self._lock:
            if not self._frames:
                print("[AudioRecorder] Warning: No frames captured during recording.", flush=True)
                return np.array([], dtype=np.float32)
            raw_audio = np.concatenate(self._frames, axis=0)
            self._frames.clear()

        # Resample to pristine 16000Hz for Whisper AI
        audio_16k = resample_to_16k(raw_audio, self.stream_sample_rate)
        duration_s = len(audio_16k) / self.sample_rate
        print(f"[AudioRecorder] Captured {len(audio_16k)} samples ({duration_s:.2f}s), peak RMS = {self.peak_level:.5f}", flush=True)
            
        self.current_level = 0.0
        return audio_16k

    def get_level(self) -> float:
        return float(self.current_level)

    def get_current_audio(self) -> np.ndarray:
        """Returns snapshot of captured audio frames downsampled to 16kHz so far."""
        with self._lock:
            if not self._frames:
                return np.array([], dtype=np.float32)
            raw_audio = np.concatenate(self._frames, axis=0)
        return resample_to_16k(raw_audio, self.stream_sample_rate)
