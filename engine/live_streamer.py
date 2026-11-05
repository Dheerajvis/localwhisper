import re
import time
import threading
import numpy as np
from typing import List, Optional, Callable

# Known Whisper hallucinations to strictly filter on quiet/ambient audio
PHANTOM_WORDS = {
    "you", "u", "thank you", "thanks", "thanks for watching", "subtitles",
    "bye", "okay", "ok", "um", "uh", "so", "yeah", "yes", "no", "...", "--",
    "mbc", "amara", "amara.org", "the", "a", "an", "i"
}

def clean_tok(w: str) -> str:
    """Strips outer punctuation and returns lowercased word for robust alignment."""
    return re.sub(r'^[^\w]+|[^\w]+$', '', w).lower()

def is_valid_word(w: str) -> bool:
    """Filters out non-ASCII foreign characters, gibberish, and hallucinated non-word tokens."""
    c = clean_tok(w)
    if not c or len(c) == 0:
        return False
    # Strictly filter non-ASCII gibberish from misdetected languages
    if not all(ord(ch) < 128 for ch in w):
        return False
    # Single letter words must be legitimate English words ('a' or 'I')
    if len(c) == 1 and c not in {'a', 'i'}:
        return False
    return not bool(re.match(r'^(uh|um|mm|//|--|\.\.)$', c))

def trim_overlap(typed_words: List[str], candidate_words: List[str]) -> List[str]:
    """
    Detects if any prefix of candidate_words overlaps with the tail of typed_words,
    and strips the overlapping duplicate words.
    """
    typed_clean = [clean_tok(w) for w in typed_words]
    cand_clean = [clean_tok(w) for w in candidate_words]
    if not typed_clean or not cand_clean:
        return candidate_words

    max_check = min(len(typed_clean), len(cand_clean))
    for k in range(max_check, 0, -1):
        if typed_clean[-k:] == cand_clean[:k]:
            return candidate_words[k:]
    return candidate_words

def strip_repeating_ngrams(words: List[str]) -> List[str]:
    """
    Detects and collapses repeating n-grams caused by Whisper silence/repetition loops.
    E.g. ['thank', 'you', 'thank', 'you'] -> ['thank', 'you'].
    """
    if len(words) < 4:
        return words
    clean = [clean_tok(w) for w in words]
    # Check 1-gram loop
    if len(clean) >= 3 and len(set(clean)) == 1:
        return [words[0]]
    # Check 2-gram and 3-gram loops
    for n in [2, 3]:
        if len(words) >= 2 * n:
            is_repeating = True
            for i in range(n, len(words)):
                if clean[i] != clean[i % n]:
                    is_repeating = False
                    break
            if is_repeating:
                return words[:n]
    return words

def strip_hallucinated_replay(typed_words: List[str], candidate_words: List[str]) -> List[str]:
    """
    Strips hallucinated replays of earlier spoken sentences or phrases caused by Whisper prompt looping.
    """
    if not typed_words or not candidate_words:
        return candidate_words
    T = [clean_tok(w) for w in typed_words]
    C = [clean_tok(w) for w in candidate_words]

    # Check 1: Candidate starts matching from the beginning of typed_words (k >= 2)
    match_len = 0
    for i in range(min(len(T), len(C))):
        if T[i] == C[i]:
            match_len += 1
        else:
            break
    if match_len >= 2:
        return candidate_words[match_len:]

    # Check 2: Leading 3+ words of candidate appear as a contiguous block in typed_words
    t_str = " " + " ".join(T) + " "
    for k in range(min(len(C), len(T)), 2, -1):
        c_sub = " " + " ".join(C[:k]) + " "
        if c_sub in t_str:
            return candidate_words[k:]

    return candidate_words

class LiveStreamer:
    """
    Hardened Real-Time Streaming Transcriber.
    
    Guarantees:
    1. Zero Duplicate Words: Monotonic Cutoff Floor prevents earlier words from ever being re-typed.
    2. Zero Gibberish / Loops: Strict English ASCII validation, VAD gating, and repetition loop collapsing.
    3. Multi-Tick Local Agreement: Incomplete trailing words are held back until confirmed across ticks.
    4. Cursor Typing: Real-time native typing directly at active cursor without clipboard destruction.
    """

    def __init__(
        self,
        recorder,
        transcriber,
        injector,
        formatter=None,
        on_partial_text: Optional[Callable[[str], None]] = None
    ):
        self.recorder = recorder
        self.transcriber = transcriber
        self.injector = injector
        self.formatter = formatter
        self.on_partial_text = on_partial_text

        self.is_streaming = False
        self._thread: Optional[threading.Thread] = None
        self.typed_words: List[str] = []
        self.last_candidate: Optional[str] = None
        self.candidate_count: int = 0
        self._lock = threading.Lock()

    def reset(self):
        """Resets streaming state for a new utterance."""
        with self._lock:
            self.typed_words = []
            self.last_candidate = None
            self.candidate_count = 0
        if self.injector and hasattr(self.injector, "reset"):
            self.injector.reset()

    def start(self):
        """Starts real-time live typing streaming loop for current active recording session."""
        with self._lock:
            self.is_streaming = True
            self.typed_words = []
            self.last_candidate = None
            self.candidate_count = 0
        if self.injector and hasattr(self.injector, "reset"):
            self.injector.reset()
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

    def stop_and_finalize(self, final_audio: Optional[np.ndarray] = None) -> str:
        """Stops streaming loop and immediately emits any remaining words from final audio."""
        with self._lock:
            self.is_streaming = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.6)

        # Final pass on audio to capture any trailing words
        if final_audio is not None and len(final_audio) >= 4800:
            with self._lock:
                self.process_audio(final_audio, is_final=True)

        with self._lock:
            full_result = " ".join(self.typed_words)
            # Cleanly reset session state so no words leak to subsequent recordings
            self.typed_words = []
            self.last_candidate = None
            self.candidate_count = 0

        if self.injector and hasattr(self.injector, "reset"):
            self.injector.reset()

        return full_result

    def _stream_loop(self):
        """Continuously pulls audio snapshots, decodes partial speech, and types deltas at cursor."""
        print("[LiveStreamer] Real-time live dictation active: typing to cursor as you speak...", flush=True)
        time.sleep(0.35)  # Initial accumulation wait

        while self.is_streaming and self.recorder and self.recorder.is_recording:
            t0 = time.time()
            audio_snapshot = self.recorder.get_current_audio()
            if len(audio_snapshot) < 16000 * 0.40:
                time.sleep(0.12)
                continue

            with self._lock:
                if not self.is_streaming:
                    break
                self.process_audio(audio_snapshot, is_final=False)

            # Fast responsive streaming loop (~350ms)
            elapsed = time.time() - t0
            sleep_time = max(0.08, 0.35 - elapsed)
            time.sleep(sleep_time)

    def _extract_new_words(self, valid_words: List[str]) -> List[str]:
        """
        Monotonic Sequence Alignment & Extraction Engine.
        
        Guarantees that words spoken earlier from the beginning of the audio snapshot
        are NEVER re-typed, even if Whisper revises earlier syllables or drops unstressed words.
        """
        if not valid_words:
            return []

        # Collapse any repetition loops in hypothesis
        valid_words = strip_repeating_ngrams(valid_words)

        if not self.typed_words:
            return valid_words

        T = [clean_tok(w) for w in self.typed_words]
        V = [clean_tok(w) for w in valid_words]
        K = len(T)
        M = len(V)

        # 1. Longest Suffix Match: Search for the end of typed_words within valid_words
        best_match_end = -1
        for L in range(min(K, 8), 0, -1):
            tail = T[-L:]
            for i in range(M - L, -1, -1):
                if V[i:i + L] == tail:
                    best_match_end = i + L
                    break
            if best_match_end != -1:
                break

        # 2. Exact Prefix Match
        prefix_match = 0
        for i in range(min(K, M)):
            if T[i] == V[i]:
                prefix_match += 1
            else:
                break

        # 3. Monotonic Safety Floor (The Inviolable Duplicate Invariant):
        # The cutoff index can NEVER fall back to 0. It must correspond to what was already committed.
        if best_match_end != -1:
            cutoff = max(best_match_end, prefix_match)
            # Allow at most 1 word revision buffer, but never rewind before K-1
            cutoff = max(cutoff, K - 1)
        else:
            # Suffix match not found: Cutoff is strictly pinned to K (words already typed)
            cutoff = max(prefix_match, K)

        cutoff = min(M, cutoff)
        candidate_words = valid_words[cutoff:]

        # 4. Overlap & Leading Duplicate Trimming
        new_words = trim_overlap(self.typed_words, candidate_words)

        # Strip any leading word matching the immediate previous word
        while new_words and self.typed_words and clean_tok(new_words[0]) == clean_tok(self.typed_words[-1]):
            new_words = new_words[1:]

        # Strip any 2-word phrase duplicate
        if len(new_words) >= 2 and len(self.typed_words) >= 2:
            if [clean_tok(w) for w in new_words[:2]] == [clean_tok(w) for w in self.typed_words[-2:]]:
                new_words = new_words[2:]

        # Repetition loop filter: Check if candidate words merely repeat the tail of typed words
        if new_words and len(self.typed_words) >= len(new_words):
            if [clean_tok(w) for w in new_words] == [clean_tok(w) for w in self.typed_words[-len(new_words):]]:
                new_words = []

        # 5. Hallucinated Prompt Replay Stripper (Prevents Whisper replaying earlier sentences)
        new_words = strip_hallucinated_replay(self.typed_words, new_words)

        return new_words

    def process_audio(self, audio: np.ndarray, is_final: bool = False) -> str:
        """
        Decodes audio segment, detects newly recognized words, and types them into cursor.
        Returns the delta text that was typed (or empty string).
        """
        if audio is None or len(audio) < 16000 * 0.35:
            return ""

        peak = float(np.max(np.abs(audio)))
        rms = float(np.sqrt(np.mean(audio ** 2)))

        # Speech energy gate: reject ambient room noise and low breathing
        if peak < 0.010 or rms < 0.0014:
            return ""

        # Safe volume normalization: scales real speech without amplifying faint noise (never >3.5x)
        if 0.010 <= peak < 0.45:
            scale = min(0.70 / max(peak, 0.16), 3.5)
            scaled_audio = audio * scale
        else:
            scaled_audio = audio
        scaled_audio = np.ascontiguousarray(scaled_audio, dtype=np.float32)

        try:
            if self.transcriber.model is None:
                self.transcriber.load_model()

            segments, _ = self.transcriber.model.transcribe(
                scaled_audio,
                beam_size=1,
                language="en",
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

            raw_words: List[str] = []
            for seg in segments:
                # Reject segments with high no-speech probability or low confidence
                if seg.no_speech_prob > 0.50:
                    continue
                if hasattr(seg, "avg_logprob") and seg.avg_logprob < -1.15 and seg.no_speech_prob > 0.35:
                    continue
                raw_words.extend(seg.text.split())

            valid_words = [w for w in raw_words if is_valid_word(w)]
            if not valid_words:
                return ""

            # Reject isolated phantom hallucinations on quiet audio
            if len(valid_words) == 1:
                clean = clean_tok(valid_words[0])
                if clean in PHANTOM_WORDS or len(clean) <= 1:
                    return ""

            # Reject repetitive loop hallucinations (e.g. "you you", "okay okay")
            clean_words = [clean_tok(w) for w in valid_words if w]
            if len(clean_words) >= 2 and len(set(clean_words)) == 1:
                return ""

            # Extract only brand new words using robust monotonic alignment
            new_words = self._extract_new_words(valid_words)
            if not new_words:
                return ""

            to_emit: List[str] = []
            if is_final:
                to_emit = new_words
                self.last_candidate = None
                self.candidate_count = 0
            else:
                # Local Agreement: emit stable words, hold back the trailing partial word
                if len(new_words) > 1:
                    to_emit = new_words[:-1]
                    self.last_candidate = new_words[-1]
                    self.candidate_count = 1
                elif len(new_words) == 1:
                    # Trailing word must survive 2 decodes before committing to prevent partial typo duplicates
                    if self.last_candidate == new_words[0]:
                        self.candidate_count += 1
                        if self.candidate_count >= 2:
                            to_emit = [new_words[0]]
                            self.last_candidate = None
                            self.candidate_count = 0
                        else:
                            to_emit = []
                    else:
                        self.last_candidate = new_words[0]
                        self.candidate_count = 1
                        to_emit = []

            if to_emit:
                delta = " ".join(to_emit)
                print(f"[LiveStreamer] Typing delta to cursor: \"{delta}\"", flush=True)
                self._inject_to_cursor(delta)
                self.typed_words.extend(to_emit)

                if self.on_partial_text:
                    self.on_partial_text(" ".join(self.typed_words))
                return delta

            return ""
        except Exception as e:
            print(f"[LiveStreamer] Processing error: {e}", flush=True)
            return ""

    def _inject_to_cursor(self, text: str):
        """Delivers keystrokes directly into active cursor input box via native Quartz Unicode."""
        self.injector.type_text_at_cursor(text)
