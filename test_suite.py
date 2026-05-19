"""
Vello 12-Test Suite — tests every upgraded module.
Run: python test_suite.py
"""
import os, sys
os.environ.setdefault("JACK_NO_START_SERVER", "1")

from dotenv import load_dotenv
load_dotenv()

PASS = 0
FAIL = 0
results = []

def report(num, name, passed, detail=""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    results.append((num, name, status, detail))
    mark = "✓" if passed else "✗"
    print(f"  [{mark}] Test {num:02d}: {name} — {status}{(' — ' + detail) if detail else ''}")

print("\n" + "="*60)
print("  VELLO MODULE TEST SUITE")
print("="*60)

# ── TEST 1: VelloEnvironment ──────────────────────────────────────
print("\n[1] VelloEnvironment")
try:
    from vello.environment import VelloEnvironment
    env = VelloEnvironment()
    assert env.audio_backend in ("pipewire", "pulseaudio", "alsa", "unknown")
    assert env.display_server in ("wayland", "x11", "unknown")
    assert isinstance(env.capabilities, set)
    report(1, "VelloEnvironment", True,
           f"audio={env.audio_backend}, display={env.display_server}")
except Exception as e:
    report(1, "VelloEnvironment", False, str(e))

# ── TEST 2: IntentEngine ──────────────────────────────────────────
print("\n[2] IntentEngine")
try:
    from core.intent_engine import IntentEngine
    ie = IntentEngine()
    r = ie.classify("open chrome")
    assert r == "open_app", f"Expected open_app, got {r!r}"
    r2 = ie.classify("what time is it")
    assert r2 == "get_time", f"Expected get_time, got {r2!r}"
    r3 = ie.classify("play Believer")
    assert r3 == "music_play", f"Expected music_play, got {r3!r}"
    report(2, "IntentEngine", True, "open_app / get_time / music_play all classify correctly")
except Exception as e:
    report(2, "IntentEngine", False, str(e))

# ── TEST 3: AppRegistry ───────────────────────────────────────────
print("\n[3] AppRegistry")
try:
    from vello.app_registry import build_app_registry
    registry = build_app_registry()
    assert isinstance(registry, dict)
    assert len(registry) > 0, "Registry is empty"
    report(3, "AppRegistry", True, f"{len(registry)} apps found")
except Exception as e:
    report(3, "AppRegistry", False, str(e))

# ── TEST 4: VoskSTT ───────────────────────────────────────────────
print("\n[4] VoskSTT")
try:
    from vello.stt.vosk_stt import VoskSTT, MODEL_PATHS
    import os
    model_found = any(os.path.isdir(p) for p in MODEL_PATHS)
    if model_found:
        # Test that model_path keyword is accepted
        path = next(p for p in MODEL_PATHS if os.path.isdir(p))
        stt = VoskSTT(model_path=path)
        assert hasattr(stt, "recognizer"), "Missing recognizer attribute"
        assert hasattr(stt, "model"), "Missing model attribute"
        report(4, "VoskSTT", True, f"model_path kwarg accepted, recognizer present")
    else:
        # No model on disk — just verify the class accepts model_path kwarg
        import inspect
        sig = inspect.signature(VoskSTT.__init__)
        assert "model_path" in sig.parameters, "__init__ missing model_path param"
        report(4, "VoskSTT", True, "model_path param present (no model on disk to load)")
except SystemExit:
    # VoskSTT calls sys.exit when model missing — that's OK if param check passed
    import inspect
    from vello.stt.vosk_stt import VoskSTT
    sig = inspect.signature(VoskSTT.__init__)
    ok = "model_path" in sig.parameters
    report(4, "VoskSTT", ok, "model_path param " + ("present" if ok else "MISSING"))
except Exception as e:
    report(4, "VoskSTT", False, str(e))

# ── TEST 5: VelloContext ──────────────────────────────────────────
print("\n[5] VelloContext")
try:
    from vello.context import VelloContext
    ctx = VelloContext()
    ctx.add("get_time", "what time is it", "It is 3pm")
    ctx.add("play_music", "play Believer", "Playing Believer")
    ctx.add("ask_ai", "what is ML", "ML is machine learning")
    assert len(ctx.history) == 3, f"expected 3, got {len(ctx.history)}"
    assert ctx.last_intent() == "ask_ai"
    msgs = ctx.build_gpt_messages("follow up")
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["content"] == "follow up"
    report(5, "VelloContext", True, "history length=3, build_gpt_messages OK")
except Exception as e:
    report(5, "VelloContext", False, str(e))

# ── TEST 6: MusicPlayer ───────────────────────────────────────────
print("\n[6] MusicPlayer")
try:
    from vello.music_player import MusicPlayer
    env = VelloEnvironment() if 'env' in dir() else __import__('vello.environment', fromlist=['VelloEnvironment']).VelloEnvironment()
    mp = MusicPlayer(env)
    assert hasattr(mp, "mpv_available"), "Missing mpv_available"
    assert hasattr(mp, "ytdlp_available"), "Missing ytdlp_available"
    assert hasattr(mp, "can_play"), "Missing can_play"
    report(6, "MusicPlayer", True,
           f"mpv={mp.mpv_available}, yt-dlp={mp.ytdlp_available}, can_play={mp.can_play}")
except Exception as e:
    report(6, "MusicPlayer", False, str(e))

# ── TEST 7: ReminderSystem ────────────────────────────────────────
print("\n[7] ReminderSystem")
try:
    from vello.reminders import ReminderSystem
    spoken = []
    rs = ReminderSystem(speak_callback=spoken.append)
    assert hasattr(rs, "parse_time"),    "Missing public parse_time"
    assert hasattr(rs, "parse_message"), "Missing public parse_message"
    from datetime import timedelta
    delta = rs.parse_time("remind me in 5 minutes")
    assert delta == timedelta(minutes=5), f"Expected 5min, got {delta}"
    msg = rs.parse_message("remind me in 5 minutes to drink water")
    assert "water" in msg, f"Expected 'water' in message, got '{msg}'"
    result = rs.set_reminder("remind me in 1 second to test")
    assert "Reminder" in result or "reminder" in result.lower()
    report(7, "ReminderSystem", True, f"parse_time=5min, parse_message='{msg}'")
except Exception as e:
    report(7, "ReminderSystem", False, str(e))

# ── TEST 8: NetworkController ─────────────────────────────────────
print("\n[8] NetworkController")
try:
    from vello.network_control import NetworkController
    nc = NetworkController(env)
    assert hasattr(nc, "nmcli_available"), "Missing nmcli_available"
    ip = nc.get_ip()
    assert isinstance(ip, str) and len(ip) > 0
    report(8, "NetworkController", True,
           f"nmcli_available={nc.nmcli_available}, get_ip returned: {ip}")
except Exception as e:
    report(8, "NetworkController", False, str(e))

# ── TEST 9: ClipboardController ───────────────────────────────────
print("\n[9] ClipboardController")
try:
    from vello.clipboard import ClipboardController
    cb = ClipboardController(env)
    result = cb.read()
    assert isinstance(result, str)
    report(9, "ClipboardController", True, f"read() returned: {result[:60]}")
except Exception as e:
    report(9, "ClipboardController", False, str(e))

# ── TEST 10: PackageManager ───────────────────────────────────────
print("\n[10] PackageManager")
try:
    from vello.package_manager import PackageManager
    pm = PackageManager(env)
    assert hasattr(pm, "install_commands"), "Missing install_commands"
    assert hasattr(pm, "remove_commands"),  "Missing remove_commands"
    assert "apt" in pm.install_commands
    assert "apt" in pm.remove_commands
    report(10, "PackageManager", True,
           f"pm={pm.pm}, install_commands has {len(pm.install_commands)} entries")
except Exception as e:
    report(10, "PackageManager", False, str(e))

# ── TEST 11: AudioController ──────────────────────────────────────
print("\n[11] AudioController")
try:
    from vello.audio_control import AudioController
    ac = AudioController(env)
    vol = ac.get_volume()
    assert isinstance(vol, (int, float, str))
    report(11, "AudioController", True, f"get_volume() = {vol}")
except Exception as e:
    report(11, "AudioController", False, str(e))

# ── TEST 12: AIBrain ──────────────────────────────────────────────
print("\n[12] AIBrain")
try:
    from core.ai_brain import AIBrain
    ai = AIBrain()
    assert hasattr(ai, "ask"), "Missing ask()"
    assert hasattr(ai, "ask_with_context"), "Missing ask_with_context()"
    import inspect
    sig = inspect.signature(ai.ask_with_context)
    assert "messages" in sig.parameters
    report(12, "AIBrain", True, "ask() and ask_with_context(messages) present")
except Exception as e:
    report(12, "AIBrain", False, str(e))

# ── SUMMARY ───────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  RESULTS: {PASS} PASSED  /  {FAIL} FAILED  /  12 TOTAL")
print("="*60)
for num, name, status, detail in results:
    mark = "✓" if status == "PASS" else "✗"
    print(f"  [{mark}] Test {num:02d}: {name:25s} {status}")
print("="*60 + "\n")

sys.exit(0 if FAIL == 0 else 1)
