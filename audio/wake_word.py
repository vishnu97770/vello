# Wake word detection using STT phrase matching


class WakeWordDetector:

    def __init__(self, stt):
        self.stt = stt
        self.wake_phrases = [
            "hey buddy what's up",
            "hey buddy whats up",
            "hey buddy what is up"
        ]

    def listen(self):
        print("\nWaiting for wake phrase: 'Hey buddy what's up'...")
        
        while True:
            text = self.stt.listen()
            
            if not text:
                continue
                
            text_lower = text.lower().strip()
            print(f"Heard: {text_lower}")
            
            # Check if any wake phrase is in the heard text
            if any(phrase in text_lower for phrase in self.wake_phrases):
                print("Wake phrase detected!")
                return True