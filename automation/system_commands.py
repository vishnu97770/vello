#When i say something like - "Open chorme" VELLO will execute system commands.

# import os

# class SystemCommands:

#     def execute(self, command):

#         command = command.lower()

#         if "open chrome" in command:
#             print("Opening Chrome...")
#             os.system("google-chrome")

#         elif "open terminal" in command:
#             print("Opening Terminal...")
#             os.system("gnome-terminal")

#         elif "open vscode" in command:
#             print("Opening VS Code...")
#             os.system("code")

#         elif "shutdown laptop" in command:
#             print("Shutting down system...")
#             os.system("shutdown now")

#         else:
#             print("Command not recognized.")


# It's time for VELLO


import os

class SystemCommands:

    def __init__(self, tts):
        self.tts = tts

    def execute(self, command):

        command = command.lower()

        if "open chrome" in command:
            self.tts.speak("Opening Chrome")
            os.system("google-chrome")

        elif "open terminal" in command:
            self.tts.speak("Opening terminal")
            os.system("gnome-terminal")

        elif "open vscode" in command:
            self.tts.speak("Opening VS Code")
            os.system("code")

        elif "shutdown laptop" in command:
            self.tts.speak("Shutting down system")
            os.system("shutdown now")

        else:
            self.tts.speak("Sorry, I don't know that command.")