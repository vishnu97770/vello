"""
Record training samples for a custom "Hey Vello" wake word.

Usage:
    python scripts/train_wake_word.py

After recording, use openWakeWord training to build the .onnx model.
See: https://github.com/dscripka/openWakeWord#training
"""
import os
import sys
import time
import wave

SAMPLE_COUNT = 25
SAMPLE_RATE  = 16000
SAMPLE_SECS  = 2
CHUNK        = 1024
OUTPUT_DIR   = os.path.expanduser(
    "~/.vello/training/hey_vello/positive"
)


def record_sample(index: int, filepath: str):
    try:
        import pyaudio
    except ImportError:
        print("pyaudio not installed. Run: pip install pyaudio")
        sys.exit(1)

    pa     = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    print(f"  [{index + 1}/{SAMPLE_COUNT}] Say 'Hey Vello' now...")
    time.sleep(0.3)

    frames     = []
    num_chunks = int(SAMPLE_RATE / CHUNK * SAMPLE_SECS)
    for _ in range(num_chunks):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))

    stream.stop_stream()
    stream.close()
    pa.terminate()

    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # paInt16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print()
    print("=" * 55)
    print("  Vello Wake Word Training Recorder")
    print("=" * 55)
    print(f"  We will record {SAMPLE_COUNT} samples of 'Hey Vello'.")
    print(f"  Each recording is {SAMPLE_SECS} seconds long.")
    print(f"  Output: {OUTPUT_DIR}")
    print()
    print("  Press Enter before each recording.")
    print("  Speak clearly, at a normal distance from the mic.")
    print("=" * 55)
    print()

    count = 0
    for i in range(SAMPLE_COUNT):
        input("  Press Enter to record...")
        filepath = os.path.join(OUTPUT_DIR, f"hey_vello_{i:03d}.wav")
        record_sample(i, filepath)
        print(f"  Saved: {os.path.basename(filepath)}")
        time.sleep(0.5)
        count += 1

    print()
    print(f"Done. {count} samples saved to {OUTPUT_DIR}")
    print()
    print("Next steps:")
    print("  1. Use openWakeWord training to build the .onnx model")
    print("  2. See: https://github.com/dscripka/openWakeWord#training")
    print("  3. Place model at: ~/.vello/models/wakeword/hey_vello.onnx")


if __name__ == "__main__":
    main()
