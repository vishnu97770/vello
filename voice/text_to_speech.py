# text_to_speech Module...now it's time for VELLO


# import pyttsx3

# class TextToSpeech:

#     def __init__(self):
#         self.engine = pyttsx3.init()
#         self.engine.setProperty("rate", 170)

#     def speak(self, text):
#         print("VELLO:", text)
#         self.engine.say(text)
#         self.engine.runAndWait()


#  For slow down the voice


# Rate	Speed
# 200	fast
# 170  	normal
# 140 	slower (recommended)
# 120	very slow


import pyttsx3

class TextToSpeech:

    def __init__(self):
        self.engine = pyttsx3.init()

        # get available voices
        voices = self.engine.getProperty("voices")

        # choose English voice
        self.engine.setProperty("voice", voices[10].id)

        # slower speaking rate
        self.engine.setProperty("rate", 140)

        # volume
        self.engine.setProperty("volume", 1)

    def speak(self, text):
        print("VELLO:", text)
        self.engine.say(text)
        self.engine.runAndWait()