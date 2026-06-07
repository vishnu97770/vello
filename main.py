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

# ── New intelligence modules ──────────────────────────────────────────────────
from vello.memory           import MemoryManager
from vello.profile          import UserProfile
from vello.goals            import GoalEngine
from vello.agents           import ExecutiveAgent, ResearchAgent, CodingAgent
from vello.proactive        import ProactiveEngine

from core.intent_engine     import IntentEngine
from core.command_router    import CommandRouter
from core.ai_brain          import AIBrain


WAKE_WORDS = [
    # These are passed only to the background interrupt listener (fuzzy matched).
    # listen_for_wake_word() uses its own built-in grammar + fuzzy logic;
    # it does not use this list.
    "hey vello", "vello", "ok vello",
    "hey jarvis", "jarvis",
    "hey buddy",
]

# Set True to enable per-frame audio diagnostics (rate, SNR, similarity scores)
DEBUG_WAKE = False


def _background_interrupt_listener(speaker, stt, wake_words,
                                   stop_event, interrupt_event):
    """Listen for wake word during TTS playback to allow interruption."""
    from vello.stt.vosk_stt import is_wake_word
    while not stop_event.is_set():
        try:
            heard = stt.listen(timeout=1, quiet=True) if hasattr(stt, "listen") else ""
            if heard:
                matched, _ = is_wake_word(heard)
                if matched:
                    interrupt_event.set()
                    speaker.interrupt()
                    return
        except Exception:
            pass


class _GoogleSTT:
    """Minimal Google STT fallback using SpeechRecognition."""

    def __init__(self):
        import speech_recognition as sr
        self._sr = sr
        self._rec = sr.Recognizer()

    def listen(self, timeout: int = 8) -> str:
        with self._sr.Microphone() as src:
            self._rec.adjust_for_ambient_noise(src, duration=0.5)
            try:
                audio = self._rec.listen(src, timeout=timeout, phrase_time_limit=15)
                return self._rec.recognize_google(audio)
            except self._sr.WaitTimeoutError:
                return ""
            except self._sr.UnknownValueError:
                return ""
            except Exception as e:
                print(f"  [GoogleSTT] Error: {e}")
                return ""


def _load_stt():
    """Load VoskSTT; fall back to Google STT (via SpeechRecognition) if model missing."""
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
        return _GoogleSTT(), "google"
    except Exception as e:
        print(f"  Vosk unavailable ({e}). Using Google STT.")
        return _GoogleSTT(), "google"


def main():
    # ── Build app registry ────────────────────────────────────────
    print("Building app registry from .desktop files...")
    app_registry = build_app_registry()

    # ── Intelligence layer ────────────────────────────────────────
    print("Initializing memory and profile systems...")
    memory  = MemoryManager()
    profile = UserProfile()

    goal_engine     = GoalEngine(profile=profile, memory=memory)
    executive       = ExecutiveAgent(memory=memory, profile=profile)
    research_agent  = ResearchAgent(memory=memory, profile=profile)
    coding_agent    = CodingAgent(memory=memory, profile=profile)

    proactive = ProactiveEngine(profile=profile, memory=memory)
    proactive.start()

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
        # Intelligence
        memory         = memory,
        profile        = profile,
        goal_engine    = goal_engine,
        research_agent = research_agent,
        coding_agent   = coding_agent,
    )
    ai = AIBrain(memory=memory, profile=profile)

    # ── Startup banner ────────────────────────────────────────────
    env.print_startup_banner()
    greeting = "Vello is ready."
    if profile.name:
        greeting = f"Welcome back, {profile.name}. Vello is ready."
    speaker.speak(greeting + " Say Hey Vello to begin.")

    # ── Main loop ─────────────────────────────────────────────────
    while True:
        # --- Proactive suggestion check (between wake-word listens) ---
        suggestion = proactive.pop_suggestion()
        if suggestion:
            print(f"[Vello] Proactive: {suggestion}")
            speaker.speak(suggestion)

        # --- Step 1: Wait for wake word ---
        print("[Vello] Listening for wake word...")

        if wake_detector.oww_available:
            heard = wake_detector.listen()
        elif hasattr(stt, "listen_for_wake_word"):
            heard = stt.listen_for_wake_word(debug_audio=DEBUG_WAKE)
        else:
            # Inline keyword fallback — listen once and check for wake words
            snippet = stt.listen(timeout=3)
            heard = bool(snippet and any(
                ww in snippet.lower() for ww in WAKE_WORDS
            ))

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

                # --- Route through Executive Agent for AI fallback ---
                # Let command router handle known intents first
                print("[Vello] Routing command...")
                result = router.execute(intent, command)
                print(f"[Vello] Result: {result}")

                # --- AI fallback ---
                if result == "USE_AI":
                    # Executive Agent picks the right specialist
                    agent_type = executive.route(command)
                    print(f"[Vello] Executive routed to: {agent_type}")

                    if agent_type == "research":
                        result = research_agent.research(command)
                    elif agent_type == "coding":
                        result = coding_agent.assist(command)
                    elif agent_type == "goals":
                        result = goal_engine.set_goal(command)
                    elif agent_type == "memory":
                        result = memory.spoken_recall(command)
                    elif agent_type == "profile":
                        result = profile.to_spoken_summary()
                    else:
                        # General GPT — stream directly into TTS for minimum latency
                        if ai.enabled:
                            interrupt_event = threading.Event()
                            stop_event      = threading.Event()
                            t = threading.Thread(
                                target=_background_interrupt_listener,
                                args=(speaker, stt, WAKE_WORDS,
                                      stop_event, interrupt_event),
                                daemon=True,
                            )
                            t.start()
                            stream  = ai.ask_streaming(command)
                            speaker.speak_streaming(stream,
                                                    interrupt_event=interrupt_event)
                            stop_event.set()
                            t.join(timeout=1)
                            result = "__streamed__"
                        else:
                            messages = context.build_gpt_messages(command)
                            result   = ai.ask_with_context(messages)

                    if result != "__streamed__":
                        print(f"[Vello] Agent result: {result}")
                    context.add("ask_ai", command, result or "")

                # --- Store important interactions in long-term memory ---
                if result and result not in ("USE_AI", "Done.", "__streamed__"):
                    if intent in ("set_goal", "update_profile", "recall_memory"):
                        memory.remember(
                            "episodic",
                            f"Intent={intent}: {command[:100]}",
                            context=result[:100],
                            importance=0.7,
                        )

                # --- Speak with interrupt support (non-streamed results) ---
                if result and result not in ("USE_AI", "__streamed__"):
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
                elif result == "USE_AI":
                    speaker.speak("Done.")

                # --- Update session context ---
                if result and result not in ("USE_AI", "Done."):
                    context.add(intent, command, result)

                print("[Vello] Waiting for next command...")

            except KeyboardInterrupt:
                print("\n[Vello] Shutting down...")
                proactive.stop()
                speaker.speak("Goodbye for now!")
                return
            except Exception as e:
                print(f"[Vello] Error in conversation: {e}")
                speaker.speak("Oops! I ran into a snag. What was that again?")


if __name__ == "__main__":
    main()
