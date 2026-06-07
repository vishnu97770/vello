import os
import sys
import json
import ctypes
import logging
import time

logger = logging.getLogger(__name__)

# ── Wake word phonetic aliases (in-vocab substitutes for OOV "vello") ─────────
#
# "vello" is NOT in Vosk's small-EN vocabulary — confirmed by:
#   WARNING (VoskAPI): Ignoring word missing in vocabulary: 'vello'
# Vosk substitutes phonetically similar known words instead.
# We supply those as grammar candidates so Vosk's search space is constrained,
# then use fuzzy matching to accept any result close enough to "hey vello".
#
# Vocabulary membership tested for each word (2024-06-07):
#   velo ✅  bello ✅  fellow ✅  yellow ✅  cello ✅
#   jello ✅  mellow ✅  vella ✅  jarvis ✅  buddy ✅
#   wello ❌  heyvello ❌  (OOV — excluded)

WAKE_GRAMMAR = [
    # Phonetic aliases for "hey vello" that ARE in Vosk vocab
    "hey velo",       # /vɛloʊ/ — closest single-word match
    "hey bello",      # /bɛloʊ/ — very common substitution
    "hey fellow",     # confirmed mishearing
    "hey yellow",     # confirmed mishearing
    "hey cello",      # close ending
    "hey mellow",     # close ending
    # NOTE: "hello vello" excluded — "vello" OOV reduces it to bare "hello", too broad
    # Single-word aliases (in case "hey" gets dropped)
    "velo",
    "bello",
    "fellow",
    "vella",
    # Alternate wake words that are fully in-vocab
    "jarvis",
    "hey jarvis",
    "hey buddy",
    # Required: tells Vosk to emit [unk] for unrecognised speech
    # instead of forcing a bad match from the grammar candidates
    "[unk]",
]

# Canonical phrases fuzzy-matched against Vosk output.
# Include the OOV target ("hey vello") so a lucky correct result still matches.
WAKE_PHRASES = [
    "hey vello", "hey velo", "hey bello", "hey fellow",
    "hey yellow", "hey cello", "hey mellow", "hey well",
    "vello", "velo", "bello", "fellow", "vella",
    "jarvis", "hey jarvis", "hey buddy",
]

# Similarity threshold (0-100). 82 balances recall vs false positives.
# hey velo  vs hey vello  → 94  ✅
# hey bello vs hey vello  → 89  ✅
# hey yellow vs hey vello → 82  ✅ (borderline — included because confirmed mishearing)
# hello world             → 36  ❌
# play some music         → 22  ❌
WAKE_SIMILARITY_THRESHOLD = 82


def _fuzzy_wake_score(text: str) -> float:
    """Return best similarity score (0-100) against any canonical wake phrase."""
    try:
        from rapidfuzz import fuzz
        return max(fuzz.ratio(text, phrase) for phrase in WAKE_PHRASES)
    except ImportError:
        # Fallback: exact substring match mapped to 0/100
        for phrase in WAKE_PHRASES:
            if phrase in text or text in phrase:
                return 100.0
        return 0.0


def is_wake_word(text: str) -> tuple[bool, float]:
    """Public API — used by test suite and listen_for_wake_word."""
    score = _fuzzy_wake_score(text.lower().strip())
    return score >= WAKE_SIMILARITY_THRESHOLD, score

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

    # Single-word noise that Vosk often returns for background sounds
    _NOISE_WORDS = {
        "mm", "hm", "uh", "um", "ah", "oh", "eh", "th",
        "the", "a", "i", "is", "it", "in", "an", "and",
        "them", "they", "there", "then", "that", "this",
        "haven", "even", "open",
    }

    def listen(self, timeout: int = 10, quiet: bool = False) -> str:
        """Record until speech detected or timeout. Returns text or ''.
        quiet=True suppresses console prints (used by background threads).
        """
        rec    = self._vosk.KaldiRecognizer(self.model, self.RATE)
        stream = self._open_stream()
        if not quiet:
            print("[Vello] Speak now...")
        start        = time.time()
        last_partial = ""
        silence_after_speech = 0.0
        got_speech   = False

        try:
            while time.time() - start < timeout:
                data = stream.read(self.CHUNK, exception_on_overflow=False)

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text   = result.get("text", "").strip()
                    if text and not self._is_noise(text):
                        if not quiet:
                            print(f"[Vello] You said: {text}")
                        return text
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "").strip()
                    if partial and not self._is_noise(partial):
                        got_speech           = True
                        last_partial         = partial
                        silence_after_speech = time.time()
                    elif got_speech and last_partial:
                        # 1.5 s of silence after detected speech → return
                        if time.time() - silence_after_speech > 1.5:
                            final = json.loads(rec.FinalResult()).get("text", "").strip()
                            text  = final or last_partial
                            if text and not self._is_noise(text):
                                if not quiet:
                                    print(f"[Vello] You said: {text}")
                                return text
                            got_speech   = False
                            last_partial = ""

            # Final flush on timeout
            final = json.loads(rec.FinalResult()).get("text", "").strip()
            text  = final or last_partial
            return text if not self._is_noise(text) else ""
        finally:
            stream.stop_stream()
            stream.close()

    def _is_noise(self, text: str) -> bool:
        """Return True if text is clearly background noise, not a real command."""
        words = text.lower().split()
        if not words:
            return True
        # Single word that is a known noise word
        if len(words) == 1 and words[0] in self._NOISE_WORDS:
            return True
        return False

    def listen_for_wake_word(self, wake_words: list = None,
                             debug_audio: bool = False) -> bool:
        """
        Stream continuously until a wake word is detected.

        Strategy (two-layer):
          1. Vosk grammar constraint — restricts search space to in-vocab
             phonetic aliases for "vello" + known alternate wake words.
             "vello" itself is OOV in the small model, so it is excluded;
             Vosk would warn and silently ignore it anyway.
          2. Fuzzy matching — rapidfuzz.fuzz.ratio() accepts Vosk's substituted
             output ("hey bello", "hey velo", etc.) if similarity ≥ threshold.

        debug_audio=True emits per-utterance diagnostic lines to stdout.
        """
        grammar_json = json.dumps(WAKE_GRAMMAR)
        # Grammar recognizer: Vosk only scores against our candidate set
        rec    = self._vosk.KaldiRecognizer(self.model, self.RATE, grammar_json)
        stream = self._open_stream()

        if debug_audio:
            print(f"[AUDIO] Rate: {self.RATE} Hz | Channels: 1 | "
                  f"Format: paInt16 | Chunk: {self.CHUNK} frames")
            print(f"[WAKE]  Grammar candidates: {WAKE_GRAMMAR[:-1]}")
            print(f"[WAKE]  Similarity threshold: {WAKE_SIMILARITY_THRESHOLD}")

        try:
            while True:
                data = stream.read(self.CHUNK, exception_on_overflow=False)

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text   = result.get("text", "").lower().strip()

                    if not text or text == "[unk]":
                        # Grammar returned unknown — not a wake word
                        rec = self._vosk.KaldiRecognizer(
                            self.model, self.RATE, grammar_json)
                        continue

                    matched, score = is_wake_word(text)

                    print(f"[WakeWord] Vosk heard: '{text}' | "
                          f"similarity={score:.0f}% | "
                          f"{'WAKE ✓' if matched else 'IGNORE'}")

                    if debug_audio:
                        print(f"[VOSK]  Raw result: '{text}'")
                        print(f"[WAKE]  Candidate: '{text}' | "
                              f"Similarity: {score:.0f}% | "
                              f"Decision: {'WAKE' if matched else 'IGNORE'}")

                    if matched:
                        return True

                    # Reset for next utterance
                    rec = self._vosk.KaldiRecognizer(
                        self.model, self.RATE, grammar_json)

        finally:
            stream.stop_stream()
            stream.close()
