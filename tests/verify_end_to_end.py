import sys
import time
from pathlib import Path
import numpy as np
import soundfile as sf
import pyperclip

# Allow running from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio_recorder import AudioRecorder
from engine.transcriber import Transcriber
from engine.llama_formatter import LlamaFormatter
from engine.injector import TextInjector

print("==================================================")
print("     LOCALWHISPER COMPLETE SYSTEM AUDIT           ")
print("==================================================")

# 1. Microphone Check & Device Selection
recorder = AudioRecorder()
dev_idx, dev_name = recorder.get_best_input_device()
print(f"\n[TEST 1] Best Input Device Selected: {dev_name} (Index: {dev_idx})")
assert "iphone" not in dev_name.lower(), f"Error: iPhone Continuity mic selected instead of laptop mic: {dev_name}"
assert "blackhole" not in dev_name.lower(), f"Error: Virtual loopback selected: {dev_name}"
print("  -> PASS: Correct physical microphone chosen.")

# 2. Audio Capture Test (1.5 seconds)
print("\n[TEST 2] Testing 1.5s Audio Capture from physical mic...")
success = recorder.start()
assert success, "Error: Failed to start audio recorder."
time.sleep(1.5)
audio_data = recorder.stop()
print(f"  -> Samples Captured: {len(audio_data)} ({len(audio_data)/recorder.sample_rate:.2f}s)")
print(f"  -> Peak Volume Level: {recorder.peak_level:.5f}")
assert len(audio_data) >= 16000, "Error: Too few audio frames captured."
print("  -> PASS: Audio capture is fully operational.")

# 3. Transcriber Silence & Hallucination Suppression Test
print("\n[TEST 3] Testing Hallucination Filter on Pure Silence...")
transcriber = Transcriber(model_size="base.en")
transcriber.load_model()

silence_audio = np.zeros(32000, dtype=np.float32)
silence_result = transcriber.transcribe(silence_audio)
print(f"  -> Transcript on pure silence: '{silence_result}'")
assert silence_result == "", f"Error: Silence produced hallucination: '{silence_result}'"
print("  -> PASS: Silence correctly produces empty output (no 'u u' or hallucinations).")

# 4. Transcriber Real Speech Accuracy Test
print("\n[TEST 4] Testing Whisper on Known English Speech Audio...")
audio_path = Path(__file__).resolve().parent / "fixtures" / "test_speech.wav"
speech_audio, sr = sf.read(str(audio_path))
speech_result = transcriber.transcribe(speech_audio)
print(f"  -> Speech Audio Transcript: \"{speech_result}\"")
assert "hello" in speech_result.lower() and "local voice to text" in speech_result.lower(), f"Unexpected transcript: {speech_result}"
print("  -> PASS: Whisper accurately decodes English speech.")

# 5. Smart Flow Post-Processing Test
print("\n[TEST 5] Testing Smart Flow Text Polisher...")
formatter = LlamaFormatter(mode="smart")
raw_input = "um so basically like we should test this comma new line bullet point item one"
polished = formatter.format_text(raw_input)
print(f"  -> Raw Input:  \"{raw_input}\"")
print(f"  -> Polished:   \"{polished}\"")
assert "um" not in polished.lower(), "Error: Filler 'um' not removed."
assert "•" in polished, "Error: Bullet point not generated."
print("  -> PASS: Smart Flow successfully cleans fillers and formats punctuation.")

# 6. Text Injector & Clipboard Integrity Test
print("\n[TEST 6] Testing Text Injector...")
injector = TextInjector()
test_phrase = "LocalWhisper System Verified"
injector.inject_text(test_phrase, auto_paste=False)
clip_content = pyperclip.paste()
print(f"  -> Clipboard Content: '{clip_content}'")
assert clip_content == test_phrase, f"Clipboard mismatch: expected '{test_phrase}', got '{clip_content}'"
print("  -> PASS: Text injector clipboard handling works.")

# 7. Continuous Hands-Free VAD Pipeline Test (Synthetic speech feed simulation)
print("\n[TEST 7] Testing Continuous Hands-Free VAD & Direct Cursor Typing Engine...")
from engine.settings_manager import SettingsManager
from engine.hands_free import HandsFreeEngine

captured_events = []
def on_status(st, det):
    pass
def on_transcript(txt, lat):
    captured_events.append(txt)

hf_engine = HandsFreeEngine(
    transcriber=transcriber,
    formatter=formatter,
    injector=injector,
    settings_mgr=SettingsManager(),
    on_status_change=on_status,
    on_transcript=on_transcript
)

# Start workers without actual mic stream
hf_engine.is_running = True
hf_engine.is_enabled = True
import threading
hf_engine._process_thread = threading.Thread(target=hf_engine._process_audio_loop, daemon=True)
hf_engine._worker_thread = threading.Thread(target=hf_engine._streaming_worker_loop, daemon=True)
hf_engine._process_thread.start()
hf_engine._worker_thread.start()

# Feed speech audio blocks to VAD queue
blocksize = 1024
for i in range(0, len(speech_audio), blocksize):
    chunk = speech_audio[i:i+blocksize].astype(np.float32)
    if len(chunk) < blocksize:
        chunk = np.pad(chunk, (0, blocksize - len(chunk)))
    hf_engine._raw_queue.put(chunk)
    time.sleep(0.005)

# Feed 1.2s silence to trigger end-of-speech
for _ in range(20):
    hf_engine._raw_queue.put(np.zeros(blocksize, dtype=np.float32))
    time.sleep(0.005)

# Wait for worker to finish
time.sleep(1.0)
hf_engine.stop()

print(f"  -> Hands-Free Captured Phrases: {len(captured_events)}")
assert len(captured_events) > 0, "Error: Hands-free VAD did not trigger on speech."
print(f"  -> Text: \"{captured_events[0]}\"")
print("  -> PASS: Hands-Free Voice-Activated typing pipeline operational.")

# 8. Real-Time Live Streaming Typing Test
print("\n[TEST 8] Testing Real-Time Live Streamer (Delta words typed while speaking)...")
from engine.live_streamer import LiveStreamer

class StreamTestInjector:
    def __init__(self):
        self.chars_typed = 0
        self.streamed_parts = []
    def type_text_at_cursor(self, text):
        self.chars_typed += len(text)
        self.streamed_parts.append(text)
        print(f"[TextInjector] Live typed {len(text)} chars directly at cursor: \"{text}\"")
        return True, "success"
    def reset(self):
        pass

test_inj = StreamTestInjector()
streamer = LiveStreamer(recorder=None, transcriber=transcriber, injector=test_inj)
streamer.start()

# Feed speech incrementally in 0.4s slices
chunk_step = int(16000 * 0.4)
delta_count = 0
for end in range(chunk_step, len(speech_audio) + chunk_step, chunk_step):
    chunk = speech_audio[:min(end, len(speech_audio))]
    is_final = (end >= len(speech_audio))
    delta = streamer.process_audio(chunk, is_final=is_final)
    if delta:
        delta_count += 1

final_text = streamer.stop_and_finalize(speech_audio)
print(f"  -> Live Delta Updates: {delta_count}")
print(f"  -> Final Live Streamed Text: \"{final_text}\"")
assert delta_count >= 3, f"Expected multiple live streaming deltas, got {delta_count}"
assert "offline" in final_text.lower(), "Live streaming failed to decode speech."
print("  -> PASS: Live streaming typing active and streaming text in real-time.")

print("\n==================================================")
print("     ALL 8 AUDIT TESTS PASSED WITH 100% SUCCESS   ")
print("==================================================")
