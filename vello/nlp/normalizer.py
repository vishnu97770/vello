import re
import random

FILLER_WORDS = [
    "bro", "buddy", "man", "dude", "mate", "hey", "ok",
    "okay", "please", "can you", "could you", "would you",
    "i need you to", "i want you to", "i need to",
    "i want to", "for me", "right now", "quickly",
    "just", "simply", "basically", "actually", "like",
    "you know", "kind of", "sort of", "a bit", "a little",
    "vello", "jarvis", "good morning", "good evening",
    "good afternoon", "good night", "what's up", "sup",
    "yo", "hello", "hi there", "hey there", "greetings",
]

CASUAL_MAPPINGS = {
    # Volume
    "it's too loud":           "volume down",
    "its too loud":            "volume down",
    "too loud":                "volume down",
    "turn it down":            "volume down",
    "lower the volume":        "volume down",
    "make it quieter":         "volume down",
    "reduce the sound":        "volume down",
    "not so loud":             "volume down",
    "it's too quiet":          "volume up",
    "its too quiet":           "volume up",
    "too quiet":               "volume up",
    "turn it up":              "volume up",
    "louder please":           "volume up",
    "increase the volume":     "volume up",
    "make it louder":          "volume up",
    "cant hear anything":      "volume up",
    "can't hear anything":     "volume up",
    "silence":                 "mute",
    "shut up":                 "mute",
    "stop the noise":          "mute",
    "keep it quiet":           "mute",

    # Time and date
    "what time is it":         "what is the time",
    "tell me the time":        "what is the time",
    "what's the time":         "what is the time",
    "whats the time":          "what is the time",
    "current time":            "what is the time",
    "what day is it":          "what is the date",
    "tell me the date":        "what is the date",
    "what's today":            "what is the date",
    "whats today":             "what is the date",
    "today's date":            "what is the date",

    # Battery
    "my battery is dying":     "battery level",
    "how much battery":        "battery level",
    "battery dying":           "battery level",
    "how's my battery":        "battery level",
    "hows my battery":         "battery level",
    "is my battery low":       "battery level",
    "battery status":          "battery level",

    # CPU / system
    "what's my cpu doing":     "cpu usage",
    "whats my cpu doing":      "cpu usage",
    "is my cpu high":          "cpu usage",
    "how's my cpu":            "cpu usage",
    "hows my cpu":             "cpu usage",
    "computer running slow":   "cpu usage",
    "why is it so slow":       "cpu usage",
    "how much ram":            "memory usage",
    "ram usage":               "memory usage",
    "how much storage":        "disk usage",
    "running out of space":    "disk usage",

    # Music
    "i'm bored":               "play some music",
    "im bored":                "play some music",
    "put on some music":       "play some music",
    "put some music on":       "play some music",
    "i want music":            "play some music",
    "play something":          "play some music",
    "play a song":             "play some music",
    "stop the music":          "stop music",
    "turn off the music":      "stop music",
    "pause the music":         "pause music",
    "keep playing":            "resume music",
    "continue music":          "resume music",

    # Screenshot
    "take a picture of my screen": "take a screenshot",
    "take a picture of screen":    "take a screenshot",
    "picture of my screen":        "take a screenshot",
    "capture my screen":           "take a screenshot",
    "screenshot please":           "take a screenshot",
    "snap my screen":              "take a screenshot",

    # Shutdown / lock
    "shut it all down":        "shutdown",
    "turn off my computer":    "shutdown",
    "power off":               "shutdown",
    "shut down the system":    "shutdown",
    "lock it":                 "lock screen",
    "lock my computer":        "lock screen",
    "lock the screen":         "lock screen",

    # Search
    "look something up":       "search",
    "i need to search":        "search",
    "search the web":          "search",
    "google something":        "search",
    "find something online":   "search",
}

GREETING_PATTERNS = [
    "good morning", "good evening", "good afternoon",
    "good night", "how are you", "how's it going",
    "hows it going", "what's up", "whats up", "sup",
    "how do you do", "nice to meet you", "hello",
    "hi vello", "hey vello", "morning", "evening",
]

GREETING_RESPONSES = [
    "Hey! Good to hear from you. What can I do for you?",
    "Hello! I'm doing great. How can I help?",
    "Hey there! What do you need?",
    "Hi! Ready to help. What's on your mind?",
    "Good to hear you! What can I do for you today?",
]


class Normalizer:

    def normalize(self, raw_text: str) -> str:
        text = raw_text.lower().strip()

        # Step 1: Check greeting patterns first
        for pattern in GREETING_PATTERNS:
            if pattern in text:
                cleaned = text.replace(pattern, "").strip()
                if len(cleaned) < 4:
                    return "__greeting__"
                # If remaining text is also a greeting → pure greeting
                if any(p in cleaned for p in GREETING_PATTERNS):
                    return "__greeting__"
                # Strip filler words from the remainder — if nothing useful left, it's a greeting
                stripped = cleaned
                for filler in sorted(FILLER_WORDS, key=len, reverse=True):
                    stripped = re.sub(rf'\b{re.escape(filler)}\b', '', stripped)
                stripped = re.sub(r'\s+', ' ', stripped).strip()
                if len(stripped) < 2:
                    return "__greeting__"
                # Otherwise process remaining text as the command
                text = cleaned
                break

        # Step 2: Check casual mappings — longest match first
        for casual, clean in sorted(CASUAL_MAPPINGS.items(),
                                    key=lambda x: len(x[0]),
                                    reverse=True):
            if casual in text:
                return clean

        # Step 3: Strip filler words (longest first to avoid partial matches)
        for filler in sorted(FILLER_WORDS, key=len, reverse=True):
            text = re.sub(rf'\b{re.escape(filler)}\b', '', text)

        # Step 4: Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Step 5: If nothing useful left — return original
        if len(text) < 2:
            return raw_text.lower().strip()

        return text

    def is_greeting(self, text: str) -> bool:
        return self.normalize(text) == "__greeting__"

    def get_greeting_response(self) -> str:
        return random.choice(GREETING_RESPONSES)
