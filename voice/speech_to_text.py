import os
import ctypes
import speech_recognition as sr

# Tell JACK not to auto-start a server (prevents "Cannot connect" spam)
os.environ.setdefault("JACK_NO_START_SERVER", "1")

# Silence ALSA lib error messages via its own error handler API.
# Handlers must be kept at module level — GC'd handlers cause crashes.
_alsa_error_handler_ref = None
_jack_error_handler_ref = None

try:
    _asound = ctypes.cdll.LoadLibrary("libasound.so.2")
    _AlsaHandler = ctypes.CFUNCTYPE(
        None,
        ctypes.c_char_p, ctypes.c_int,
        ctypes.c_char_p, ctypes.c_int,
        ctypes.c_char_p,
    )
    _alsa_error_handler_ref = _AlsaHandler(lambda *_: None)
    _asound.snd_lib_error_set_handler(_alsa_error_handler_ref)
except Exception:
    pass

try:
    _jack = ctypes.cdll.LoadLibrary("libjack.so.0")
    _JackHandler = ctypes.CFUNCTYPE(None, ctypes.c_char_p)
    _jack_error_handler_ref = _JackHandler(lambda *_: None)
    _jack.jack_set_error_function(_jack_error_handler_ref)
    _jack.jack_set_info_function(_jack_error_handler_ref)
except Exception:
    pass


class SpeechToText:

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def listen(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("Speak...")

            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=6
                )
            except sr.WaitTimeoutError:
                return None

        try:
            text = self.recognizer.recognize_google(audio)
            print("You said:", text)
            return text

        except sr.UnknownValueError:
            return None

        except sr.RequestError:
            print("Speech recognition service unavailable")
            return None
