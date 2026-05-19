import os, sys, re
from dotenv import load_dotenv
load_dotenv()

from unittest.mock import MagicMock
import subprocess
import webbrowser

# --- Patches ---
def fake_popen(args, **kwargs):
    cmd_str = ' '.join(args) if isinstance(args, list) else str(args)
    print(f"    >> LAUNCH: {cmd_str}")
    return MagicMock()
subprocess.Popen = fake_popen

def fake_open(url, *args, **kwargs):
    print(f"    >> BROWSER: {url}")
webbrowser.open = fake_open

def fake_os_system(cmd):
    print(f"    >> OS: {cmd}")
    return 0
os.system = fake_os_system

import psutil
real_battery = psutil.sensors_battery
def fake_battery():
    class B: percent=72; power_plugged=True
    return B()
psutil.sensors_battery = fake_battery

real_cpu = psutil.cpu_percent
psutil.cpu_percent = lambda interval=None: 34.5

class MockTTS:
    def speak(self, text):
        clean = re.sub(r'[^\x00-\x7F]+', '', text).strip()
        print(f"    VELLO: {clean}")

class MockAI:
    def ask(self, query):
        print(f"    >> AI (GPT-4o-mini): '{query}'")
        return "Here is your AI answer for: " + query

from core.intent_engine import IntentEngine
from core.context_manager import ContextManager
from core.command_router import CommandRouter

tts     = MockTTS()
context = ContextManager()
intent  = IntentEngine()
ai      = MockAI()
router  = CommandRouter(tts, context)

PASS = []
FAIL = []

def run(label, cmd, expected_intent):
    context.clear_pending()
    ctx = context.get_context_summary()
    result = intent.classify(cmd, ctx)
    got = result.get("intent")
    status = "PASS" if got == expected_intent else "FAIL"
    if status == "PASS":
        PASS.append(label)
    else:
        FAIL.append(f"{label}  [expected={expected_intent}, got={got}]")

    print(f"\n  [{status}] {label}")
    print(f"         You say: \"{cmd}\"")
    print(f"         Intent : {got}  | app={result.get('app')} | target={result.get('target')}")

    if got != "exit":
        r = router.route(result, cmd)
        if r == "USE_AI":
            resp = ai.ask(cmd)
            tts.speak(resp)

# ─────────────────────────────────────────────
print("=" * 62)
print("  VELLO — FULL COMMAND VERIFICATION TEST")
print("=" * 62)

# ── OPEN APPS ──────────────────────────────────────────────
print("\n── OPEN APPLICATIONS ──────────────────────────────────────")
run("Open Chrome",        "open chrome",               "open_app")
run("Open Firefox",       "open firefox",              "open_app")
run("Open Terminal",      "open terminal",             "open_app")
run("Open VS Code",       "open vscode",               "open_app")
run("Open VS Code (alt)", "open vs code",              "open_app")
run("Open LibreOffice",   "open libreoffice",          "open_app")
run("Open Files",         "open files",                "open_app")
run("Open VLC",           "open vlc",                  "open_app")
run("Open Spotify",       "open spotify",              "open_app")
run("Open Discord",       "open discord",              "open_app")
run("Open Zoom",          "open zoom",                 "open_app")
run("Open Telegram",      "open telegram",             "open_app")
run("Open Calculator",    "open calculator",           "open_app")
run("Open Settings",      "open settings",             "open_app")
run("Open Notepad",       "open notepad",              "open_app")
run("Launch app",         "launch spotify",            "open_app")
run("Start app",          "start discord",             "open_app")

# ── SYSTEM CONTROLS ────────────────────────────────────────
print("\n── SYSTEM CONTROLS ────────────────────────────────────────")
run("Time",               "what is the time",          "system_control")
run("Date",               "what is the date",          "system_control")
run("Volume Up",          "volume up",                 "system_control")
run("Volume Down",        "volume down",               "system_control")
run("Mute",               "mute",                      "system_control")
run("Screenshot",         "take a screenshot",         "system_control")
run("Battery",            "battery level",             "system_control")
run("CPU",                "cpu usage",                 "system_control")
run("Lock",               "lock screen",               "system_control")

# ── WEB SEARCH ─────────────────────────────────────────────
print("\n── WEB & SEARCH ───────────────────────────────────────────")
run("Search query",       "search python tutorials",   "search_web")
run("Google query",       "google machine learning",   "search_web")
run("Look up",            "look up best linux apps",   "search_web")
run("Find",               "find how to use grep",      "search_web")

# ── MUSIC / YOUTUBE ────────────────────────────────────────
print("\n── MUSIC & YOUTUBE ────────────────────────────────────────")
run("Play song",          "play believer on youtube",  "play_music")
run("Play music",         "play some music",           "play_music")
run("Song name",          "play shape of you",         "play_music")

# ── TERMINAL COMMANDS ──────────────────────────────────────
print("\n── TERMINAL COMMANDS ──────────────────────────────────────")
run("Run command",        "run ls -la",                "terminal_run")
run("Execute command",    "execute pwd",               "terminal_run")
run("sudo",               "sudo apt update",           "terminal_run")
run("apt install",        "apt install vlc",           "terminal_run")
run("mkdir",              "mkdir new_project",         "terminal_run")

# ── FILES & FOLDERS ────────────────────────────────────────
print("\n── FILES & FOLDERS ────────────────────────────────────────")
run("Open folder",        "open folder downloads",     "open_app")
run("Open file",          "open file resume.pdf",      "open_app")

# ── MULTI-STEP CHAINED ─────────────────────────────────────
print("\n── MULTI-STEP CHAINED COMMANDS ────────────────────────────")
context.clear_pending()
cmd = "open chrome and search python tutorials"
ctx = context.get_context_summary()
result = intent.classify(cmd, ctx)
chain = result.get("chain", [])
status = "PASS" if result["intent"] == "open_app" and len(chain) > 0 else "FAIL"
if status == "PASS": PASS.append("Chain: open+search")
else: FAIL.append("Chain: open+search")
print(f"\n  [{status}] Chain: open Chrome AND search Python tutorials")
print(f"         Step 1 intent : {result['intent']} app={result['app']}")
for i, s in enumerate(chain):
    print(f"         Step {i+2} intent : {s['intent']} target={s.get('target')}")

context.clear_pending()
cmd2 = "open chrome and play believer on youtube"
result2 = intent.classify(cmd2, context.get_context_summary())
chain2 = result2.get("chain", [])
status2 = "PASS" if result2["intent"] == "open_app" and len(chain2) > 0 else "FAIL"
if status2 == "PASS": PASS.append("Chain: open+play")
else: FAIL.append("Chain: open+play")
print(f"\n  [{status2}] Chain: open Chrome AND play Believer on YouTube")
print(f"         Step 1 intent : {result2['intent']} app={result2['app']}")
for i, s in enumerate(chain2):
    print(f"         Step {i+2} intent : {s['intent']} target={s.get('target')}")

# ── AI FALLBACK ────────────────────────────────────────────
print("\n── AI FALLBACK (GPT-4o-mini) ──────────────────────────────")
run("What is ML",         "what is machine learning",  "ask_ai")
run("Who is Elon Musk",   "who is elon musk",          "ask_ai")
run("Python question",    "how do I reverse a list in python", "ask_ai")
run("General question",   "what is the capital of japan", "ask_ai")
run("Creative",           "write a short poem about linux", "ask_ai")

# ── EXIT ───────────────────────────────────────────────────
print("\n── EXIT / STOP ────────────────────────────────────────────")
run("Goodbye",            "goodbye",                   "exit")
run("Bye",                "bye",                       "exit")
run("Stop",               "stop",                      "exit")
run("Quit",               "quit",                      "exit")

# ─────────────────────────────────────────────
print("\n" + "=" * 62)
print(f"  RESULTS:  {len(PASS)} PASSED   {len(FAIL)} FAILED")
print("=" * 62)
if FAIL:
    print("\n  FAILED COMMANDS:")
    for f in FAIL:
        print(f"    - {f}")
else:
    print("\n  ALL COMMANDS WORKING CORRECTLY!")
print()
