"""
Record training samples and auto-train a custom "Hey Vello" wake word model.

Usage:
    python scripts/train_wake_word.py

Steps performed automatically:
  1. Record 25 positive samples of "Hey Vello"
  2. Collect background noise as negative samples
  3. Attempt openWakeWord auto-training (requires tensorflow)
  4. Copy trained model to ~/.vello/models/wakeword/hey_vello.onnx
  5. Print manual instructions if auto-training is unavailable
"""
import os
import sys
import time
import wave
import shutil

SAMPLE_COUNT  = 25
SAMPLE_RATE   = 16000
SAMPLE_SECS   = 2
CHUNK         = 1024
POSITIVE_DIR  = os.path.expanduser("~/.vello/training/hey_vello/positive")
NEGATIVE_DIR  = os.path.expanduser("~/.vello/training/hey_vello/negative")
OUTPUT_MODEL  = os.path.expanduser("~/.vello/models/wakeword/hey_vello.onnx")
OWW_TRAIN_URL = "https://github.com/dscripka/openWakeWord#training"


# ── Step 1: Record positive samples ───────────────────────────────────────────

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

    print(f"  [{index + 1}/{SAMPLE_COUNT}] Say 'Hey Vello' now...", end=" ", flush=True)
    time.sleep(0.3)

    frames     = []
    num_chunks = int(SAMPLE_RATE / CHUNK * SAMPLE_SECS)
    for _ in range(num_chunks):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))

    stream.stop_stream()
    stream.close()
    pa.terminate()
    print("recorded.")

    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)   # paInt16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))


def record_positive_samples():
    os.makedirs(POSITIVE_DIR, exist_ok=True)

    print()
    print("=" * 60)
    print("  Step 1 — Record positive samples")
    print("=" * 60)
    print(f"  Recording {SAMPLE_COUNT} samples of 'Hey Vello'.")
    print(f"  Each sample is {SAMPLE_SECS} seconds. Speak clearly.")
    print(f"  Output: {POSITIVE_DIR}")
    print()

    for i in range(SAMPLE_COUNT):
        input(f"  Press Enter to record sample {i + 1}/{SAMPLE_COUNT}...")
        filepath = os.path.join(POSITIVE_DIR, f"hey_vello_{i:03d}.wav")
        record_sample(i, filepath)
        time.sleep(0.3)

    print()
    print(f"  Done. {SAMPLE_COUNT} positive samples saved.")


# ── Step 2: Collect negative (background noise) samples ───────────────────────

def collect_negative_samples():
    os.makedirs(NEGATIVE_DIR, exist_ok=True)

    existing = [f for f in os.listdir(NEGATIVE_DIR) if f.endswith(".wav")]
    if len(existing) >= 5:
        print(f"\n  Negative samples already present ({len(existing)} files). Skipping.")
        return

    print()
    print("=" * 60)
    print("  Step 2 — Record background noise (negative samples)")
    print("=" * 60)
    print("  Stay quiet — this records ambient room noise.")
    print("  Duration: 10 seconds")
    input("  Press Enter to start...")

    try:
        import pyaudio
    except ImportError:
        print("  pyaudio not installed — skipping negative samples.")
        return

    pa     = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16, channels=1,
        rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK,
    )
    print("  Recording ambient noise...", end=" ", flush=True)
    frames = []
    for _ in range(int(SAMPLE_RATE / CHUNK * 10)):
        frames.append(stream.read(CHUNK, exception_on_overflow=False))
    stream.stop_stream()
    stream.close()
    pa.terminate()
    print("done.")

    noise_path = os.path.join(NEGATIVE_DIR, "ambient_noise.wav")
    with wave.open(noise_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    print(f"  Saved: {noise_path}")

    # Also copy from openWakeWord built-in resources if available
    try:
        import openwakeword
        oww_path  = os.path.dirname(openwakeword.__file__)
        noise_src = os.path.join(oww_path, "resources", "negative_data")
        if os.path.isdir(noise_src):
            copied = 0
            for f in os.listdir(noise_src)[:20]:
                if f.endswith(".wav"):
                    shutil.copy2(os.path.join(noise_src, f), NEGATIVE_DIR)
                    copied += 1
            if copied:
                print(f"  Copied {copied} extra background samples from openWakeWord.")
    except Exception:
        pass


# ── Step 3: Auto-train with openWakeWord ──────────────────────────────────────

def attempt_auto_train() -> bool:
    """Try to run openWakeWord training. Returns True if model was produced."""
    print()
    print("=" * 60)
    print("  Step 3 — Auto-training wake word model")
    print("=" * 60)

    try:
        from openwakeword.train import train_model
    except ImportError:
        print("  openWakeWord not installed. Run: pip install openwakeword")
        return False
    except AttributeError:
        print("  openWakeWord training API not found.")
        print("  Try: pip install 'openwakeword[train]' tensorflow")
        return False

    positive_files = [
        os.path.join(POSITIVE_DIR, f)
        for f in os.listdir(POSITIVE_DIR)
        if f.endswith(".wav")
    ]
    negative_files = [
        os.path.join(NEGATIVE_DIR, f)
        for f in os.listdir(NEGATIVE_DIR)
        if f.endswith(".wav")
    ] if os.path.isdir(NEGATIVE_DIR) else []

    if len(positive_files) < 5:
        print(f"  Not enough positive samples ({len(positive_files)} found, need 5+).")
        return False

    output_dir = os.path.expanduser("~/.vello/training/output")
    os.makedirs(output_dir, exist_ok=True)

    print(f"  {len(positive_files)} positive, {len(negative_files)} negative samples.")
    print("  Training — this may take a few minutes...")

    try:
        train_model(
            positive_reference_clips=positive_files,
            negative_reference_clips=negative_files if negative_files else None,
            output_dir=output_dir,
            model_name="hey_vello",
        )
        # Find and copy the .onnx output
        for root, _, files in os.walk(output_dir):
            for f in files:
                if f.endswith(".onnx"):
                    src = os.path.join(root, f)
                    os.makedirs(os.path.dirname(OUTPUT_MODEL), exist_ok=True)
                    shutil.copy2(src, OUTPUT_MODEL)
                    print(f"  Model saved to: {OUTPUT_MODEL}")
                    return True
        print("  Training finished but no .onnx file found in output.")
        return False
    except Exception as e:
        print(f"  Auto-training failed: {e}")
        return False


# ── Step 4: Manual fallback instructions ──────────────────────────────────────

def print_manual_instructions():
    print()
    print("=" * 60)
    print("  Manual training instructions")
    print("=" * 60)
    print()
    print("  Your recorded samples are ready at:")
    print(f"    Positive: {POSITIVE_DIR}")
    print(f"    Negative: {NEGATIVE_DIR}")
    print()
    print("  To train manually:")
    print()
    print("  1. Install training dependencies:")
    print("       pip install 'openwakeword[train]' tensorflow")
    print()
    print(f"  2. Follow training guide: {OWW_TRAIN_URL}")
    print()
    print("  3. Place the trained model at:")
    print(f"       {OUTPUT_MODEL}")
    print()
    print("  4. Restart Vello — it will auto-load your custom wake word.")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   Vello — Custom Wake Word Trainer           ║")
    print("╚══════════════════════════════════════════════╝")

    record_positive_samples()
    collect_negative_samples()
    trained = attempt_auto_train()

    print()
    if trained:
        print("=" * 60)
        print("  Wake word training complete!")
        print(f"  Model: {OUTPUT_MODEL}")
        print("  Restart Vello to activate 'Hey Vello'.")
        print("=" * 60)
    else:
        print_manual_instructions()


if __name__ == "__main__":
    main()
