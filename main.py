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

def main():
    stt     = SpeechToText()
    wake    = WakeWordDetector(stt)
    tts     = TextToSpeech()
    context = ContextManager()
    intent  = IntentEngine()
    router  = CommandRouter(tts, context)
    ai      = AIBrain()

    tts.speak("Vello is ready and standing by! 🚀")

    while True:
        # Step 1: Wait for Wake Word
        wake.listen()
        tts.speak("Hey! I'm here. What's up? 😊")

        # Step 2: Continuous Conversation Loop
        while True:
            try:
                command = stt.listen()

                if not command:
                    print("Listening... (silence)")
                    continue

                print(f"\nUser: {command}")
                
                # Check for exit/goodbye
                intent_data = intent.classify(command, context.get_context_summary())
                
                if intent_data.get("intent") == "exit":
                    from core.response_generator import ResponseGenerator
                    resp = ResponseGenerator()
                    tts.speak(resp.get_response("goodbye"))
                    context.reset()
                    break # Go back to waiting for wake word

                # Process command
                result = router.route(intent_data, command)

                if result == "USE_AI":
                    response = ai.ask(command)
                    tts.speak(response)
                
                # If there's no pending action, we can ask "Anything else?" sometimes
                # But for now, just keep listening for the next command
                if not context.pending_action:
                    print("Waiting for next command in conversation...")

            except KeyboardInterrupt:
                print("\nShutting down Vello...")
                tts.speak("Goodbye for now! 👋")
                return
            except Exception as e:
                print(f"Error in conversation: {e}")
                tts.speak("Oops! I ran into a bit of a snag. What was that again?")
if __name__ == "__main__":
    main()
    