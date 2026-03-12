# from audio.listener import AudioListener

# def main():
#     listener = AudioListener()
#     listener.start_listening()

# if __name__ == "__main__":
#     main()

# This code is written for voice detect (whatever we speak it will convert voice to text...)

# from voice.speech_to_text import SpeechToText

# def main():
#     stt = SpeechToText()

#     while True:
#         command = stt.listen()

#         if command:
#             print("Command recieved:", command)

# if  __name__ == "__main__":
#     main()



# to execute the commands...

# from voice.speech_to_text import SpeechToText
# from automation.system_commands import SystemCommands

# def main():

#     stt = SpeechToText()
#     system = SystemCommands()

#     while True:
#         command = stt.listen()

#         if command:
#             print("Command received:", command)
#             system.execute(command)

# if __name__ == "__main__":
#     main()





# It's time for VELLO
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from automation.system_commands import SystemCommands


def main():
    stt = SpeechToText()
    tts = TextToSpeech()
    system = SystemCommands(tts)
    tts.speak("Vello assistant is ready")
    while True:
        command = stt.listen()
        if command:
            print("Command received:", command)
            system.execute(command)

if  __name__ == "__main__":
    main()
