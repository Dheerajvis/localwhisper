import os
import time
import numpy as np
from pathlib import Path
from typing import Optional, List
from faster_whisper import WhisperModel
import config

class Transcriber:
    def __init__(self, model_size: str = config.DEFAULT_WHISPER_MODEL):
        self.model_size = model_size
        self.model_dir = config.MODELS_DIR / "whisper"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model: Optional[WhisperModel] = None
        self.is_loading = False
        self.last_latency_ms: float = 0.0

    def load_model(self, model_size: Optional[str] = None) -> bool:
        """Load or switch the Whisper model."""
        if model_size:
            self.model_size = model_size

        self.is_loading = True
        print(f"[Transcriber] Loading model '{self.model_size}' from {self.model_dir}...", flush=True)
        start_time = time.time()
        
        try:
            device = "cpu"
            compute_type = config.WHISPER_COMPUTE_TYPE
            if device == "cpu" and compute_type == "float16":
                compute_type = "int8"
            
            self.model = WhisperModel(
                model_size_or_path=self.model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(self.model_dir),
                cpu_threads=4,
                num_workers=1
            )
            elapsed = (time.time() - start_time) * 1000
            print(f"[Transcriber] Model '{self.model_size}' loaded successfully in {elapsed:.1f}ms", flush=True)
            self.is_loading = False
            return True
        except Exception as e:
            print(f"[Transcriber] Failed to load model '{self.model_size}': {e}", flush=True)
            self.is_loading = False
            return False

    def transcribe(self, audio: np.ndarray, language: str = "en") -> str:
        """
        Transcribes a 1D float32 numpy array at 16kHz.
        Returns the transcribed text string.
        """
        if self.model is None:
            if not self.load_model():
                return ""

        if audio is None or len(audio) < 1600:  # Less than 0.1s
            print("[Transcriber] Audio too short to transcribe (<0.1s).", flush=True)
            return ""

        audio = np.ascontiguousarray(audio, dtype=np.float32)

        # Check audio energy (RMS & Peak). Filter true hardware silence and ambient hum
        rms = float(np.sqrt(np.mean(audio ** 2)))
        peak = float(np.max(np.abs(audio)))

        if peak < 0.010 or rms < 0.0014:
            return ""

        # Safe volume normalization (scales real speech without amplifying ambient noise)
        if 0.010 <= peak < 0.45:
            scale = min(0.70 / max(peak, 0.16), 3.5)
            audio = audio * scale

        start_time = time.time()
        try:
            target_lang = "en" if language in ("auto", "en", None) else language
            segments, info = self.model.transcribe(
                audio,
                beam_size=1,
                language=target_lang,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300, threshold=0.50),
                compression_ratio_threshold=2.2,
                no_speech_threshold=0.55,
                hallucination_silence_threshold=0.8,
                repetition_penalty=1.15,
                no_repeat_ngram_size=3
            )

            # Known Whisper silence hallucinations to strictly reject
            phantom_phrases = {
                "u", "u u", "you", "you.", "see you.", "see you", 
                "thank you.", "thank you", "...", ".", "bye.", "bye",
                "okay", "okay.", "ok", "ok.", "okay okay", "okay okay okay",
                "thank you for watching", "thank you for watching.",
                "subtitles by", "amara.org", "so", "yeah", "yes", "no"
            }

            valid_segments: List[str] = []
            for segment in segments:
                # If model is confident there is no speech, ignore segment
                if segment.no_speech_prob > 0.50:
                    continue
                txt = segment.text.strip()
                cleaned_lower = txt.lower()

                # Filter foreign non-ASCII gibberish from false language detections
                if not all(ord(c) < 128 for c in txt):
                    print(f"[Transcriber] Filtered foreign/non-ASCII gibberish: '{txt}'", flush=True)
                    continue
                
                # Check for repetitive word loops (e.g. "okay okay okay", "you you")
                words = [w.strip('.,!?:;"\'') for w in cleaned_lower.split() if w.strip('.,!?:;"\'')]
                if len(words) >= 2 and len(set(words)) == 1:
                    print(f"[Transcriber] Filtered repetitive loop hallucination: '{txt}'", flush=True)
                    continue

                if cleaned_lower in phantom_phrases or cleaned_lower.strip('.,!?') in phantom_phrases:
                    print(f"[Transcriber] Filtered hallucination token: '{txt}' (no_speech_prob={segment.no_speech_prob:.2f})", flush=True)
                    continue

                if txt:
                    valid_segments.append(txt)

            full_transcript = " ".join(valid_segments).strip()
            self.last_latency_ms = (time.time() - start_time) * 1000
            print(f"[Transcriber] Completed in {self.last_latency_ms:.1f}ms: \"{full_transcript}\"", flush=True)
            return full_transcript
        except Exception as e:
            print(f"[Transcriber] Transcription error: {e}", flush=True)
            return ""
