import random

RESPONSES = {
    "opening_app": [
        "Opening {app} for you.",
        "Sure, launching {app}.",
        "On it — opening {app}.",
        "{app} coming right up.",
        "Got it, starting {app}.",
    ],
    "volume_up": [
        "Turning it up.",
        "Volume increased.",
        "Got it, louder now.",
        "Cranking it up.",
    ],
    "volume_down": [
        "Turning it down.",
        "Volume decreased.",
        "Got it, quieter now.",
        "Bringing it down.",
    ],
    "mute": [
        "Muted.",
        "Going quiet.",
        "Done, muted.",
    ],
    "screenshot": [
        "Screenshot saved.",
        "Got it, captured your screen.",
        "Screenshot taken.",
    ],
    "searching": [
        "Searching for {query}.",
        "Looking up {query} now.",
        "On it — searching {query}.",
        "Let me find that for you.",
    ],
    "playing_music": [
        "Playing {query}.",
        "On it — playing {query}.",
        "Sure, let's listen to {query}.",
        "Starting {query} now.",
    ],
    "music_stopped": [
        "Music stopped.",
        "Stopped.",
        "Done playing.",
    ],
    "not_found": [
        "Sorry, I couldn't find {item}.",
        "Hmm, I don't see {item} installed.",
        "I couldn't locate {item}.",
    ],
    "didnt_understand": [
        "Sorry, I didn't catch that. Can you say it again?",
        "Hmm, I'm not sure what you mean. Try again?",
        "I didn't quite get that. Could you rephrase?",
        "Not sure I understood. Say it a different way?",
    ],
    "shutdown": [
        "Shutting down. Goodbye!",
        "Powering off now. See you!",
        "Shutting down the system.",
    ],
    "goodbye": [
        "Goodbye! Call me anytime.",
        "See you later!",
        "Bye! I'll be here when you need me.",
        "Catch you later!",
    ],
    "wake_ack": [
        "Yes?",
        "Hey!",
        "I'm here.",
        "What's up?",
        "Go ahead.",
        "How can I help?",
        "Listening.",
    ],
    "no_hear": [
        "I didn't catch that.",
        "Sorry, didn't hear you.",
        "Could you repeat that?",
        "Say that again?",
    ],
}


def get_response(key: str, **kwargs) -> str:
    templates = RESPONSES.get(key, [key])
    template = random.choice(templates)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
