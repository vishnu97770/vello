# Wake word detection using STT phrase matching


class WakeWordDetector:

    def __init__(self, stt):
        self.stt = stt
        self.wake_phrases = [
            "hey vello",
            "hey buddy what's up",
            "hey buddy whats up",
            "hey buddy what is up",
            "hey buddy",
            "hey jarvis",
            "jarvis",
            "vello",
            "ok vello",
        ]

    def listen(self):
        print("\nWaiting for wake word... (say 'Hey Vello' or 'Hey Jarvis')")

        while True:
            text = self.stt.listen()

            if not text:
                continue

            text_lower = text.lower().strip()
            print(f"Heard: {text_lower}")

            if any(phrase in text_lower for phrase in self.wake_phrases):
                print("Wake word detected!")
                return True