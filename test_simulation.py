import os, sys, re
from dotenv import load_dotenv
load_dotenv()

from unittest.mock import MagicMock
import subprocess
import webbrowser

# --- Patch subprocess so no real apps open ---
def fake_popen(args, **kwargs):
    cmd_str = ' '.join(args) if isinstance(args, list) else str(args)
    print(f"  [SYSTEM]: Would launch -> {cmd_str}")
    m = MagicMock()
    m.returncode = 0
    return m
subprocess.Popen = fake_popen

# --- Patch webbrowser ---
def fake_open(url, *args, **kwargs):
    print(f"  [BROWSER]: Would open -> {url}")
webbrowser.open = fake_open

# --- Patch os.system ---
def fake_os_system(cmd):
    print(f"  [OS CMD]: Would run -> {cmd}")
    return 0
os.system = fake_os_system

# --- Mock TTS ---
class MockTTS:
    def speak(self, text):
        clean = re.sub(r'[^\x00-\x7F]+', '', text).strip()
        print(f"  [VELLO]: {clean}")

# --- Mock AI Brain ---
class MockAIBrain:
    def ask(self, query):
        print(f"  [AI BRAIN]: Calling GPT-4o-mini with -> '{query}'")
        return "Machine learning is a field of AI where computers learn from data to make predictions without being explicitly programmed."

# --- Import real core modules ---
from core.intent_engine import IntentEngine
from core.context_manager import ContextManager
from core.command_router import CommandRouter

tts     = MockTTS()
context = ContextManager()
intent  = IntentEngine()
ai      = MockAIBrain()
router  = CommandRouter(tts, context)

# --- Test Commands ---
test_commands = [
    "open Chrome",
    "open VS Code",
    "play Believer on YouTube",
    "search Python tutorials",
    "what is the time",
    "battery level",
    "what is machine learning",
    "goodbye",
]

print("=" * 60)
print("  VELLO SIMULATION TEST")
print("=" * 60)

for cmd in test_commands:
    print(f"\nYOU: \"{cmd}\"")
    ctx_summary = context.get_context_summary()
    intent_data = intent.classify(cmd, ctx_summary)
    print(f"  [INTENT]: {intent_data['intent']}  app={intent_data.get('app')}  target={intent_data.get('target')}")

    if intent_data.get("intent") == "exit":
        tts.speak("Goodbye! Have an awesome day!")
        context.reset()
        print("  [ACTION]: Back to wake word mode.")
        break

    result = router.route(intent_data, cmd)

    if result == "USE_AI":
        response = ai.ask(cmd)
        tts.speak(response)

print()
print("=" * 60)
print("  ALL TESTS COMPLETE")
print("=" * 60)
