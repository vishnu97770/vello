"""
Wake word detector.
Uses custom OpenWakeWord model if trained, otherwise falls back to
Vosk keyword spotting which supports "hey vello", "vello", etc. natively.
"""
import os
import logging

logger = logging.getLogger(__name__)

CUSTOM_MODEL_PATH = os.path.expanduser(
    "~/.vello/models/wakeword/hey_vello.onnx"
)


class WakeWordDetector:

    THRESHOLD  = 0.5
    CHUNK_SIZE = 1280   # 80 ms @ 16 kHz (required by openWakeWord)
    RATE       = 16000
    CHANNELS   = 1

    def __init__(self):
        if os.path.isfile(CUSTOM_MODEL_PATH):
            self.oww_available = self._try_load_custom()
        else:
            # No custom "hey vello" model — use Vosk keyword detection instead.
            # Vosk understands "vello", "hey vello", "jarvis", etc. directly.
            self.oww_available = False
            self.model = None
            print("[WakeWord] No custom model — using Vosk keyword detection.")
            print("[WakeWord] Say 'Hey Vello' or just 'Vello' to wake up.")
            print("[WakeWord] Train your own: python scripts/train_wake_word.py")

    def _try_load_custom(self) -> bool:
        """Load custom .onnx model. Returns True on success."""
        try:
            from openwakeword.model import Model
            self.model = Model(wakeword_model_paths=[CUSTOM_MODEL_PATH])
            print("[WakeWord] Custom 'Hey Vello' model loaded")
            return True
        except Exception as e:
            logger.warning("Could not load custom wake word model: %s", e)
            self.model = None
            return False

    def listen(self, timeout: float | None = None) -> bool:
        """Stream audio until custom wake word detected. Returns bool."""
        if not self.oww_available or self.model is None:
            return False

        try:
            import pyaudio
            import numpy as np
            import time
        except ImportError:
            logger.warning("pyaudio or numpy not installed")
            return False

        pa     = pyaudio.PyAudio()
        stream = pa.open(
            rate=self.RATE,
            channels=self.CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.CHUNK_SIZE,
        )

        start = time.time()
        try:
            while True:
                if timeout and (time.time() - start) > timeout:
                    return False
                chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                audio = np.frombuffer(chunk, dtype=np.int16)
                preds = self.model.predict(audio)
                for name, score in preds.items():
                    if isinstance(score, (list, tuple)):
                        score = score[-1]
                    if score > self.THRESHOLD:
                        print(f"[WakeWord] Detected: {name} (score={score:.2f})")
                        return True
        except Exception as e:
            logger.warning("WakeWordDetector listen error: %s", e)
            return False
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def set_threshold(self, value: float):
        self.THRESHOLD = max(0.1, min(0.99, value))
