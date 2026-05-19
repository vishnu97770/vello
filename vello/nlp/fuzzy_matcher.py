from typing import Optional

# Intent keyword map — each intent has weighted keywords.
# Longer keyword phrases = higher confidence per match.
# web_search weight is lower to avoid grabbing AI questions.
INTENT_KEYWORDS = {
    "open_app": {
        "keywords": ["open", "launch", "start", "run",
                     "load", "fire up", "bring up"],
        "weight": 1.0,
    },
    "volume_up": {
        "keywords": ["louder", "volume up", "turn up",
                     "increase volume", "raise volume",
                     "crank up", "more volume"],
        "weight": 1.0,
    },
    "volume_down": {
        "keywords": ["quieter", "volume down", "turn down",
                     "decrease volume", "lower volume",
                     "reduce volume", "less volume"],
        "weight": 1.0,
    },
    "mute": {
        "keywords": ["mute", "silence", "no sound", "stop sound"],
        "weight": 1.0,
    },
    "get_time": {
        "keywords": ["time", "clock", "hour", "what time"],
        "weight": 1.0,
    },
    "get_date": {
        "keywords": ["date", "today", "calendar", "what day"],
        "weight": 1.0,
    },
    "battery": {
        "keywords": ["battery", "charge", "power level",
                     "battery life", "how charged"],
        "weight": 1.0,
    },
    "cpu_usage": {
        "keywords": ["cpu", "processor", "processing",
                     "performance", "cpu usage"],
        "weight": 1.0,
    },
    "memory_usage": {
        "keywords": ["memory", "ram", "memory usage"],
        "weight": 1.0,
    },
    "disk_usage": {
        "keywords": ["disk", "storage", "space", "drive",
                     "hard drive", "ssd", "disk usage"],
        "weight": 1.0,
    },
    "screenshot": {
        "keywords": ["screenshot", "screen capture",
                     "capture screen", "screen shot",
                     "snap screen", "picture of screen"],
        "weight": 1.0,
    },
    "web_search": {
        # Deliberately narrow — only unambiguous search triggers
        # "what is", "how do i" omitted to avoid stealing AI questions
        "keywords": ["search", "google", "look up",
                     "look for", "search up", "browse"],
        "weight": 0.8,
    },
    "music_play": {
        "keywords": ["play", "music", "song", "track",
                     "listen", "put on", "youtube"],
        "weight": 1.0,
    },
    "music_stop": {
        "keywords": ["stop music", "stop playing",
                     "stop song", "end music"],
        "weight": 1.0,
    },
    "music_pause": {
        "keywords": ["pause", "pause music", "hold music"],
        "weight": 1.0,
    },
    "music_resume": {
        "keywords": ["resume", "continue music",
                     "keep playing", "unpause"],
        "weight": 1.0,
    },
    "shutdown": {
        "keywords": ["shutdown", "shut down", "power off",
                     "turn off computer", "switch off"],
        "weight": 1.0,
    },
    "lock_screen": {
        "keywords": ["lock", "lock screen", "lock computer",
                     "screen lock", "secure screen"],
        "weight": 1.0,
    },
    "wifi_on": {
        "keywords": ["wifi on", "enable wifi",
                     "turn on wifi", "enable wireless"],
        "weight": 1.0,
    },
    "wifi_off": {
        "keywords": ["wifi off", "disable wifi",
                     "turn off wifi", "disable wireless"],
        "weight": 1.0,
    },
    "get_ip": {
        "keywords": ["ip address", "my ip", "network address"],
        "weight": 1.0,
    },
    "set_reminder": {
        "keywords": ["remind", "reminder", "remember",
                     "don't let me forget", "alert me"],
        "weight": 1.0,
    },
    "set_timer": {
        "keywords": ["timer", "countdown", "set timer",
                     "count down"],
        "weight": 1.0,
    },
    "clipboard_read": {
        "keywords": ["clipboard", "what did i copy",
                     "what's copied"],
        "weight": 1.0,
    },
    "package_install": {
        "keywords": ["install", "download and install",
                     "get package", "add package"],
        "weight": 1.0,
    },
    "system_update": {
        "keywords": ["update system", "upgrade system",
                     "system update", "update packages",
                     "run updates"],
        "weight": 1.0,
    },
    "goodbye": {
        "keywords": ["goodbye", "bye", "exit", "quit",
                     "stop vello", "see you", "later",
                     "close vello"],
        "weight": 1.0,
    },
}


class FuzzyMatcher:

    # Minimum score to accept a match
    THRESHOLD = 0.8

    def match(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for intent, data in INTENT_KEYWORDS.items():
            score = 0.0
            for keyword in data["keywords"]:
                if keyword in text_lower:
                    # Longer keyword phrase = stronger signal
                    score += len(keyword.split()) * data["weight"]
            if score > 0:
                scores[intent] = score

        if not scores:
            return None

        best_intent = max(scores, key=scores.get)

        if scores[best_intent] < self.THRESHOLD:
            return None

        return best_intent
