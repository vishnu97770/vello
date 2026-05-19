import os
import sys
import json
import ctypes
import logging
import time

logger = logging.getLogger(__name__)

# ── Silence ALSA/JACK noise (same approach as in voice/speech_to_text.py) ──
os.environ.setdefault("JACK_NO_START_SERVER", "1")

_alsa_handler_ref = None
_jack_handler_ref = None

try:
    _asound = ctypes.cdll.LoadLibrary("libasound.so.2")
    _AlsaT  = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    _alsa_handler_ref = _AlsaT(lambda *_: None)
    _asound.snd_lib_error_set_handler(_alsa_handler_ref)
except Exception:
    pass

try:
    _jack = ctypes.cdll.LoadLibrary("libjack.so.0")
    _JackT = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
    _jack_handler_ref = _JackT(lambda *_: None)
    _jack.jack_set_error_function(_jack_handler_ref)
    _jack.jack_set_info_function(_jack_handler_ref)
except Exception:
    pass

# ── Model paths to search in order ──────────────────────────────────────────
MODEL_PATHS = [
    os.path.expanduser("~/.vello/models/vosk-model-small-en-us"),
    "/opt/vello/models/vosk-model-small-en-us",
    os.path.join(os.path.dirname(__file__), "..", "..", "models",
                 "vosk-model-small-en-us"),
]

DOWNLOAD_INSTRUCTIONS = """
╔══════════════════════════════════════════════════════════════╗
║  Vosk model not found. Download it with:                     ║
║                                                              ║
║  mkdir -p ~/.vello/models                                    ║
║  cd ~/.vello/models                                          ║
║  wget https://alphacephei.com/vosk/models/                   ║
║       vosk-model-small-en-us-0.15.zip                        ║
║  unzip vosk-model-small-en-us-0.15.zip                       ║
║  mv vosk-model-small-en-us-0.15 vosk-model-small-en-us       ║
╚══════════════════════════════════════════════════════════════╝
"""


def _find_model():
    for path in MODEL_PATHS:
        if os.path.isdir(path):
            return path
    return None


class VoskSTT:
    """Fully offline speech-to-text using Vosk + PyAudio."""

    RATE             = 16000
    FRAMES_PER_BUF   = 8000
    CHUNK            = 4000

    def __init__(self, model_path: str = None):
        try:
            import vosk
            import pyaudio
        except ImportError:
            print("\nERROR: vosk or pyaudio not installed.")
            print("Run: pip install vosk pyaudio")
            sys.exit(1)

        if model_path is None:
            model_path = _find_model()
        if not model_path:
            print(DOWNLOAD_INSTRUCTIONS)
            sys.exit(1)

        vosk.SetLogLevel(-1)
        self._vosk      = vosk
        self._pa        = pyaudio
        self.model      = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, self.RATE)
        self._audio     = pyaudio.PyAudio()
        logger.info("VoskSTT ready — model: %s", model_path)

    def _open_stream(self):
        return self._audio.open(
            format=self._pa.paInt16,
            channels=1,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.FRAMES_PER_BUF,
        )

    def listen(self, timeout: int = 10) -> str:
        """Record until speech detected or timeout. Returns text or ''."""
        rec    = self._vosk.KaldiRecognizer(self.model, self.RATE)
        stream = self._open_stream()
        print("Speak...")
        start = time.time()
        try:
            while time.time() - start < timeout:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text   = result.get("text", "").strip()
                    if text:
                        print(f"You said: {text}")
                        return text
            # Final result on timeout
            result = json.loads(rec.FinalResult())
            return result.get("text", "").strip()
        finally:
            stream.stop_stream()
            stream.close()

    def listen_for_wake_word(self, wake_words: list) -> bool:
        """Stream continuously until any wake word is detected."""
        rec    = self._vosk.KaldiRecognizer(self.model, self.RATE)
        stream = self._open_stream()
        try:
            while True:
                data = stream.read(self.CHUNK, exception_on_overflow=False)

                # Check final result
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get("text", "").lower()
                    if text and any(w in text for w in wake_words):
                        print(f"Wake word detected in: '{text}'")
                        return True

                # Check partial result for faster response
                partial = json.loads(rec.PartialResult()).get("partial", "").lower()
                if partial and any(w in partial for w in wake_words):
                    print(f"Wake word detected (partial): '{partial}'")
                    return True
        finally:
            stream.stop_stream()
            stream.close()
