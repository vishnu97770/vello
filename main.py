from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging
import threading

logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s %(name)s: %(message)s")

# ── Environment (must be first) ───────────────────────────────────────────────
from vello.environment import VelloEnvironment
env = VelloEnvironment()

# ── Core modules ──────────────────────────────────────────────────────────────
from vello.context          import VelloContext
from vello.app_registry     import build_app_registry
from vello.audio_control    import AudioController
from vello.music_player     import MusicPlayer
from vello.reminders        import ReminderSystem
from vello.network_control  import NetworkController
from vello.clipboard        import ClipboardController
from vello.package_manager  import PackageManager
from vello.dbus_control     import DBusMediaController
from vello.window_manager   import WindowManager
from vello.file_ops         import FileOps
from vello.brightness       import BrightnessController
from vello.tts.speaker      import Speaker
from vello.stt.wake_word    import WakeWordDetector
from core.intent_engine     import IntentEngine
from core.command_router    import CommandRouter
from core.ai_brain          import AIBrain


WAKE_WORDS = [
    "hey vello", "hey jarvis", "jarvis", "vello", "ok vello", "hey buddy",
    "hey buddy what's up", "hey buddy whats up",
]


def _background_interrupt_listener(speaker, stt, wake_words,
                                   stop_event, interrupt_event):
    """Listen for wake word during TTS playback to allow interruption."""
    while not stop_event.is_set():
        try:
            heard = stt.listen(timeout=1)
            if heard:
                for ww in wake_words:
                    if ww.lower() in heard.lower():
                        interrupt_event.set()
                        speaker.interrupt()
                        return
        except Exception:
            pass


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
    context        = VelloContext()
    audio          = AudioController(env)
    music          = MusicPlayer(env)
    reminders      = ReminderSystem(speaker.speak)
    network        = NetworkController(env)
    clipboard      = ClipboardController(env)
    dbus_media     = DBusMediaController(env)
    window_manager = WindowManager(env)
    file_ops       = FileOps(env)
    brightness     = BrightnessController(env)
    packages       = PackageManager(
        env,
        speak_fn  = speaker.speak,
        listen_fn = (stt.listen if stt_backend == "vosk" else
                     getattr(stt, "listen", None)),
    )

    # ── Wake word detector ────────────────────────────────────────
    wake_detector = WakeWordDetector()

    # ── Core pipeline ─────────────────────────────────────────────
    engine = IntentEngine()
    router = CommandRouter(
        tts            = speaker,
        context        = context,
        env            = env,
        audio_ctrl     = audio,
        music          = music,
        reminders      = reminders,
        network        = network,
        clipboard      = clipboard,
        packages       = packages,
        app_registry   = app_registry,
        stt            = stt,
        dbus_media     = dbus_media,
        window_manager = window_manager,
        file_ops       = file_ops,
        brightness     = brightness,
    )
    ai = AIBrain()

    # ── Startup banner ────────────────────────────────────────────
    env.print_startup_banner()
    speaker.speak("Vello is ready. Say Hey Vello to begin.")

    # ── Main loop ─────────────────────────────────────────────────
    while True:
        # --- Step 1: Wait for wake word ---
        print("[Vello] Listening for wake word...")

        if wake_detector.oww_available:
            heard = wake_detector.listen()
        elif hasattr(stt, "listen_for_wake_word"):
            heard = stt.listen_for_wake_word(WAKE_WORDS)
        else:
            from audio.wake_word import WakeWordDetector as LegacyDetector
            heard = LegacyDetector(stt).listen()

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

                # --- Speak with interrupt support ---
                if result and result != "USE_AI":
                    interrupt_event = threading.Event()
                    stop_event      = threading.Event()
                    t = threading.Thread(
                        target=_background_interrupt_listener,
                        args=(speaker, stt, WAKE_WORDS,
                              stop_event, interrupt_event),
                        daemon=True,
                    )
                    t.start()
                    speaker.speak(result, interrupt_event=interrupt_event)
                    stop_event.set()
                    t.join(timeout=1)
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
