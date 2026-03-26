import speech_recognition as sr


class SpeechToText:

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def listen(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
            print("🎤 Speak...")

            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=6
                )
            except sr.WaitTimeoutError:
                # silence — return None, don't crash
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