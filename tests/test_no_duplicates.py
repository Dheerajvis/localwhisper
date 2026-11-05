import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Allow running from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.live_streamer import LiveStreamer
from engine.transcriber import Transcriber
from engine.injector import TextInjector

print("==================================================")
print("     TESTING ZERO-DUPLICATE STREAMING ENGINE      ")
print("==================================================")

class MockRecorder:
    def __init__(self, audio):
        self.audio = audio
        self.is_recording = True
        self.current_len = 0
    def get_current_audio(self):
        return self.audio[:self.current_len]

class MockInjector:
    def __init__(self):
        self.emitted = []
    def type_text_at_cursor(self, text):
        self.emitted.append(text)
    def reset(self):
        pass

audio_path = Path(__file__).resolve().parent / "fixtures" / "test_speech.wav"
audio, _ = sf.read(str(audio_path))
transcriber = Transcriber(model_size="base.en")
transcriber.load_model()

mock_inj = MockInjector()
rec = MockRecorder(audio)
streamer = LiveStreamer(recorder=rec, transcriber=transcriber, injector=mock_inj)

# Session 1: Stream chunks of audio
streamer.start()
step = int(16000 * 0.3)
for i in range(step, len(audio), step):
    rec.current_len = i
    streamer.process_audio(rec.get_current_audio(), is_final=False)

res1 = streamer.stop_and_finalize(audio)
typed_full1 = " ".join(mock_inj.emitted)
print(f"\n[Session 1 Result]: \"{typed_full1}\"")

# Check for duplicate words in session 1
words1 = [w.lower().strip(".,!?") for w in typed_full1.split()]
duplicates_in_session = []
for i in range(len(words1) - 1):
    if words1[i] == words1[i+1] and words1[i] not in {"had", "that"}:
        duplicates_in_session.append(words1[i])

print(f"Consecutive duplicate words in Session 1: {duplicates_in_session}")
assert len(duplicates_in_session) == 0, f"Found duplicate words: {duplicates_in_session}"

# Session 2: Second recording immediately after session 1
print("\n[Testing Session 2 immediately after Session 1]...")
mock_inj.emitted.clear()
rec2 = MockRecorder(audio)
streamer2 = LiveStreamer(recorder=rec2, transcriber=transcriber, injector=mock_inj)
streamer2.start()

for i in range(step, len(audio), step):
    rec2.current_len = i
    streamer2.process_audio(rec2.get_current_audio(), is_final=False)

res2 = streamer2.stop_and_finalize(audio)
typed_full2 = " ".join(mock_inj.emitted)
print(f"[Session 2 Result]: \"{typed_full2}\"")

# Verify that session 2 did not repeat the full session 1 buffer or duplicate
words2 = [w.lower().strip(".,!?") for w in typed_full2.split()]
duplicates_in_session2 = []
for i in range(len(words2) - 1):
    if words2[i] == words2[i+1] and words2[i] not in {"had", "that"}:
        duplicates_in_session2.append(words2[i])
assert len(duplicates_in_session2) == 0, f"Session 2 had duplicate words: {duplicates_in_session2}"

# Test 3: Simulating Whisper Revision / Hallucination Drift
print("\n[TEST 3: Simulating Whisper Revision / Hallucination Drift]")
st = LiveStreamer(recorder=None, transcriber=transcriber, injector=mock_inj)
st.start()
st.typed_words = ["hello", "world"]

# 1. Exact same words -> delta empty
d1 = st._extract_new_words(["Hello", "world."])
print(f"  -> Same words returned: {d1} (Expected: [])")
assert d1 == []

# 2. Whisper revised the first word ("yellow" instead of "hello") -> should drop revision, only emit subsequent new words
d2 = st._extract_new_words(["Yellow", "world", "of", "whisper"])
print(f"  -> Revised first word: {d2} (Expected: ['of', 'whisper'])")
assert d2 == ["of", "whisper"]

# 3. Whisper dropped a word
d3 = st._extract_new_words(["World", "today"])
print(f"  -> Dropped word: {d3} (Expected: ['today'])")
assert d3 == ["today"]

# 4. Whisper hallucinated repeat
st.typed_words = ["hello", "world"]
d4 = st._extract_new_words(["Hello", "world", "hello", "world"])
print(f"  -> Hallucinated loop: {d4} (Expected: [])")
assert d4 == []

print("\n==================================================")
print("     ALL ZERO-DUPLICATE TESTS PASSED 100%!        ")
print("==================================================")
