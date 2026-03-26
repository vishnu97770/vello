from dotenv import load_dotenv
load_dotenv()

import os
from audio.wake_word        import WakeWordDetector
from voice.speech_to_text   import SpeechToText
from voice.text_to_speech   import TextToSpeech
from core.context_manager   import ContextManager
from core.intent_engine     import IntentEngine
from core.command_router    import CommandRouter
from core.ai_brain          import AIBrain

ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")


def main():

    wake    = WakeWordDetector(ACCESS_KEY)
    stt     = SpeechToText()
    tts     = TextToSpeech()
    context = ContextManager()
    intent  = IntentEngine()
    router  = CommandRouter(tts, context)
    ai      = AIBrain()

    tts.speak("Vello is ready")

    while True:

        print("\nWaiting for wake word...")
        wake.listen()
        tts.speak("Yes?")

        while True:
            try:
                command = stt.listen()

                if not command:
                    print("Listening... (silence)")
                    continue

                print(f"\nCommand : {command}")
                print(f"Context : {context.get_context_summary()}")

                command_lower = command.lower()

                if context.pending_action:
                    print(f"Resolving pending: {context.pending_action}")
                    context.clear_pending()
                    intent_data = intent.classify(command, context.get_context_summary())
                    result = router.route(intent_data, command)
                    if result == "USE_AI":
                        response = ai.ask(command)
                        tts.speak(response)
                    continue

                intent_data = intent.classify(command, context.get_context_summary())
                print(f"Intent  : {intent_data}")

                result = router.route(intent_data, command)

                if result == "USE_AI":
                    response = ai.ask(command)
                    tts.speak(response)

            except KeyboardInterrupt:
                print("\nShutting down Vello...")
                tts.speak("Goodbye")
                return


if __name__ == "__main__":
    main()
    