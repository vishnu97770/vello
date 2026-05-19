"""
OpenWakeWord-based wake word detector.
Falls back gracefully when openWakeWord or PyAudio is not installed.
"""
import os
import time
import logging

logger = logging.getLogger(__name__)

CUSTOM_MODEL_PATH = os.path.expanduser(
    "~/.vello/models/wakeword/hey_vello.onnx"
)


class WakeWordDetector:

    THRESHOLD  = 0.5
    CHUNK_SIZE = 1280   # required by openWakeWord (80 ms @ 16 kHz)
    RATE       = 16000
    CHANNELS   = 1

    def __init__(self):
        self.oww_available = self._check_oww()
        if self.oww_available:
            self._load_model()
        else:
            print("[WakeWord] openWakeWord not installed.")
            print("[WakeWord] pip install openwakeword")
            print("[WakeWord] Falling back to Vosk keyword detection.")

    def _check_oww(self) -> bool:
        try:
            import openwakeword  # noqa: F401
            return True
        except ImportError:
            return False

    def _load_model(self):
        from openwakeword.model import Model
        if os.path.isfile(CUSTOM_MODEL_PATH):
            self.model = Model(
                wakeword_models=[CUSTOM_MODEL_PATH],
                inference_framework="onnx",
            )
            print("[WakeWord] Custom model loaded")
        else:
            self.model = Model(inference_framework="onnx")
            print("[WakeWord] Using pretrained models.")
            print("[WakeWord] Train custom model: "
                  "python scripts/train_wake_word.py")

    def listen(self, timeout: float | None = None) -> bool:
        """Stream audio until wake word detected or timeout. Returns bool."""
        if not self.oww_available:
            return False

        try:
            import pyaudio
            import numpy as np
        except ImportError:
            logger.warning("pyaudio or numpy not installed — WakeWordDetector disabled")
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
                chunk  = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                audio  = np.frombuffer(chunk, dtype=np.int16)
                preds  = self.model.predict(audio)
                for name, scores in preds.items():
                    if scores and scores[-1] > self.THRESHOLD:
                        print(f"[WakeWord] Detected: {name} "
                              f"(score={scores[-1]:.2f})")
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
