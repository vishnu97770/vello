from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging

logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s %(name)s: %(message)s")

# ── Environment (must be first) ───────────────────────────────────────────────
from vello.environment import VelloEnvironment
env = VelloEnvironment()

# ── Core modules ──────────────────────────────────────────────────────────────
from vello.context        import VelloContext
from vello.app_registry   import build_app_registry
from vello.audio_control  import AudioController
from vello.music_player   import MusicPlayer
from vello.reminders      import ReminderSystem
from vello.network_control import NetworkController
from vello.clipboard      import ClipboardController
from vello.package_manager import PackageManager
from vello.tts.speaker    import Speaker
from core.intent_engine   import IntentEngine
from core.command_router  import CommandRouter
from core.ai_brain        import AIBrain


WAKE_WORDS = [
    "hey vello", "hey jarvis", "jarvis", "vello", "ok vello", "hey buddy",
    "hey buddy what's up", "hey buddy whats up",
]


def _startup_report(env, music, network, reminders, clipboard):
    audio_label = env.audio_backend.capitalize()
    disp_label  = env.display_server.capitalize()
    de_label    = env.desktop_env.split(":")[0].capitalize() or "Unknown"
    pm_label    = env.package_manager or "None detected"

    def tick(cond): return "✓" if cond else "✗"

    has_vol    = env.audio_backend in ("pipewire", "pulseaudio")
    has_shot   = bool(env.capabilities & {"gnome-screenshot", "grim", "scrot"})
    has_music  = music.can_play if music else False
    has_wifi   = network.nmcli_available if network else False
    has_remind = reminders._enabled if reminders else False
    has_clip   = bool(env.capabilities & {"xclip", "wl-copy"})
    has_notify = "notify-send" in env.capabilities

    print()
    print("┌─────────────────────────────────────────┐")
    print("│  VELLO — Starting up                    │")
    print(f"│  Audio:    {audio_label:<28} │")
    print(f"│  Display:  {disp_label:<28} │")
    print(f"│  Desktop:  {de_label:<28} │")
    print(f"│  Packages: {pm_label:<28} │")
    print("│  STT:      Vosk (offline)               │")
    print("│  TTS:      Piper                        │")
    print("├─────────────────────────────────────────┤")
    print(f"│  {tick(has_vol)}  Volume control                      │")
    print(f"│  {tick(has_shot)}  Screenshots                         │")
    print(f"│  {tick(has_music)}  Music playback (mpv + yt-dlp)       │")
    print(f"│  {tick(has_wifi)}  Wi-Fi control (nmcli)               │")
    print(f"│  {tick(has_remind)}  Reminders (APScheduler)             │")
    print(f"│  {tick(has_clip)}  Clipboard (xclip / wl-clipboard)    │")
    print(f"│  {tick(has_notify)}  Desktop notifications (notify-send) │")
    print("└─────────────────────────────────────────┘")
    print()


def _load_stt():
    """Load VoskSTT, fall back to Google STT if Vosk model missing."""
    try:
        from vello.stt.vosk_stt import VoskSTT
        stt = VoskSTT()
        print("  STT: Vosk (offline) loaded successfully.")
        return stt, "vosk"
    except SystemExit:
        print()
        print("  Falling back to Google Speech Recognition (online).")
        print("  Download the Vosk model for offline operation.")
        print()
        from voice.speech_to_text import SpeechToText
        return SpeechToText(), "google"
    except Exception as e:
        print(f"  Vosk unavailable ({e}). Using Google STT.")
        from voice.speech_to_text import SpeechToText
        return SpeechToText(), "google"


def main():
    # ── Build app registry ────────────────────────────────────────
    print("Building app registry from .desktop files...")
    app_registry = build_app_registry()

    # ── Initialize Speaker (TTS) ──────────────────────────────────
    speaker = Speaker()

    # ── STT ───────────────────────────────────────────────────────
    stt, stt_backend = _load_stt()

    # ── Subsystems ────────────────────────────────────────────────
    context   = VelloContext()
    audio     = AudioController(env)
    music     = MusicPlayer(env)
    reminders = ReminderSystem(speaker.speak)
    network   = NetworkController(env)
    clipboard = ClipboardController(env)
    packages  = PackageManager(
        env,
        speak_fn  = speaker.speak,
        listen_fn = (stt.listen if stt_backend == "vosk" else
                     getattr(stt, "listen", None)),
    )

    # ── Core pipeline ─────────────────────────────────────────────
    engine = IntentEngine()
    router = CommandRouter(
        tts          = speaker,
        context      = context,
        env          = env,
        audio_ctrl   = audio,
        music        = music,
        reminders    = reminders,
        network      = network,
        clipboard    = clipboard,
        packages     = packages,
        app_registry = app_registry,
        stt          = stt,
    )
    ai = AIBrain()

    # ── Startup report ────────────────────────────────────────────
    _startup_report(env, music, network, reminders, clipboard)
    speaker.speak("Vello is ready. Say Hey Vello to begin.")

    # ── Main loop ─────────────────────────────────────────────────
    while True:
        # --- Step 1: Wait for wake word ---
        print("[Vello] Listening for wake word...")

        if hasattr(stt, "listen_for_wake_word"):
            heard = stt.listen_for_wake_word(WAKE_WORDS)
        else:
            from audio.wake_word import WakeWordDetector
            heard = WakeWordDetector(stt).listen()

        if not heard:
            continue

        # --- Step 2: Acknowledge ---
        print("[Vello] Wake word detected!")
        speaker.speak("Yes?")

        # --- Step 3: Conversation loop ---
        while True:
            try:
                # --- Listen for command ---
                print("[Vello] Listening for command...")
                command = stt.listen() if hasattr(stt, "listen") else stt.listen()
                print(f"[Vello] Heard: '{command}'")

                if not command or command.strip() == "":
                    speaker.speak("I didn't catch that. Try again.")
                    continue

                # --- Classify intent ---
                intent = engine.classify(command)
                print(f"[Vello] Intent: {intent}")

                # --- Greeting ---
                if intent == "greeting":
                    from vello.nlp.normalizer import Normalizer
                    speaker.speak(Normalizer().get_greeting_response())
                    continue

                # --- Exit check ---
                if intent in ("goodbye", "exit", "quit"):
                    speaker.speak("Goodbye. Have an awesome day!")
                    context.reset()
                    break

                # --- Execute command ---
                print("[Vello] Routing command...")
                result = router.execute(intent, command)
                print(f"[Vello] Result: {result}")

                # --- AI fallback ---
                if result == "USE_AI":
                    print("[Vello] Falling back to AI brain...")
                    messages = context.build_gpt_messages(command)
                    result   = ai.ask_with_context(messages)
                    print(f"[Vello] AI result: {result}")
                    context.add("ask_ai", command, result)

                # --- Speak result ---
                if result and result != "USE_AI":
                    speaker.speak(result)
                else:
                    speaker.speak("Done.")

                # --- Update context ---
                if result and result not in ("USE_AI", "Done."):
                    context.add(intent, command, result)

                print("[Vello] Waiting for next command...")

            except KeyboardInterrupt:
                print("\n[Vello] Shutting down...")
                speaker.speak("Goodbye for now!")
                return
            except Exception as e:
                print(f"[Vello] Error in conversation: {e}")
                speaker.speak("Oops! I ran into a snag. What was that again?")


if __name__ == "__main__":
    main()
