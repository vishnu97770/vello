from core.response_generator import ResponseGenerator
import webbrowser
import subprocess
import os
import datetime
import psutil

class CommandRouter:
    """
    Receives structured intent from IntentEngine and executes actions.
    Now with fun responses, multi-step flows, and safety checks.
    """

    APP_COMMANDS = {
        "chrome":        "google-chrome",
        "browser":       "google-chrome",
        "google":        "google-chrome",
        "firefox":       "firefox",
        "terminal":      "gnome-terminal",
        "vscode":        "code",
        "vs code":       "code",
        "files":         "nautilus",
        "file manager":  "nautilus",
        "calculator":    "gnome-calculator",
        "settings":      "gnome-control-center",
        "vlc":           "vlc",
        "spotify":       "spotify",
        "discord":       "discord",
        "zoom":          "zoom",
        "telegram":      "telegram-desktop",
        "gedit":         "gedit",
        "notepad":       "gedit",
        "screenshot":    "gnome-screenshot",
        "libreoffice":   "libreoffice",
        "writer":        "libreoffice --writer",
    }

    DANGEROUS_COMMANDS = ["rm -rf", "sudo rm", "mkfs", "dd if=", "> /dev/sda", ":(){ :|:& };:"]

    def __init__(self, tts, context):
        self.tts      = tts
        self.context  = context
        self.response = ResponseGenerator()

    def route(self, intent_data, original_command=""):
        intent  = intent_data.get("intent")
        app     = intent_data.get("app")
        target  = intent_data.get("target")
        chain   = intent_data.get("chain", [])

        # Handle pending actions first if any
        if self.context.pending_action:
            return self._handle_pending(self.context.pending_action, original_command)

        # Execute primary intent
        result = self._execute(intent, app, target, original_command)

        # Execute chained actions (multi-step commands)
        for step in chain:
            self._execute(
                step.get("intent"),
                step.get("app") or self.context.active_app,
                step.get("target"),
                original_command
            )
        
        return result

    def _execute(self, intent, app, target, original_command=""):

        if intent == "open_app":
            return self._open_app(app)

        elif intent == "open_url":
            self._open_url(target)

        elif intent == "play_music":
            self._play_music(target)

        elif intent == "search_web":
            self._search_web(target)

        elif intent == "open_folder":
            self._open_folder(target)

        elif intent == "open_file":
            self._open_file(target)

        elif intent == "system_control":
            self._system_control(original_command)

        elif intent == "terminal_run":
            self._run_terminal_command(target)

        elif intent == "clarify":
            question = f"Could you be more specific? What {target} should I use?"
            self.tts.speak(question)
            self.context.set_pending(target)

        elif intent == "ask_ai":
            return "USE_AI"

        else:
            self.tts.speak("I am not sure how to handle that. Please try again.")

    def _handle_pending(self, pending_type, command):
        self.context.clear_pending()
        
        if pending_type == "search_query":
            self._search_web(command)
        elif pending_type == "terminal_command":
            self._run_terminal_command(command)
        elif pending_type == "coding_task":
            self.tts.speak(f"Awesome! Let's get to work on {command}. I've opened VS Code for you.")
        elif pending_type == "work_task":
            self.tts.speak(f"Got it! Opening LibreOffice for your work on {command}.")
        else:
            self.tts.speak(f"Processing your request for {command}")

    # ── ACTION HANDLERS ───────────────────────────────────────────

    def _open_app(self, app_name):
        if not app_name:
            self.tts.speak("Which application should I open?")
            self.context.set_pending("app_name")
            return

        app_key = app_name.lower()
        cmd = self.APP_COMMANDS.get(app_key)

        if cmd:
            # Fun responses
            response_key = f"open_{app_key}" if f"open_{app_key}" in self.response.RESPONSES else "generic_success"
            self.tts.speak(self.response.get_response(response_key))
            
            subprocess.Popen(
                cmd.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.context.set_app(app_name)

            # Multi-step logic
            if app_key in ["chrome", "google"]:
                import time
                time.sleep(1)
                self.tts.speak(self.response.get_response("search_ask"))
                self.context.set_pending("search_query")
            elif app_key == "terminal":
                import time
                time.sleep(1)
                self.tts.speak(self.response.get_response("terminal_ask"))
                self.context.set_pending("terminal_command")
            elif app_key == "vscode":
                import time
                time.sleep(1)
                self.tts.speak(self.response.get_response("vscode_greet"))
                self.context.set_pending("coding_task")
            elif app_key == "libreoffice":
                import time
                time.sleep(1)
                self.tts.speak(self.response.get_response("libreoffice_greet"))
                self.context.set_pending("work_task")

        else:
            self.tts.speak(f"Trying to open {app_name}")
            try:
                subprocess.Popen(
                    [app_name.lower()],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.context.set_app(app_name)
            except FileNotFoundError:
                self.tts.speak(f"Sorry, I could not find {app_name} on your system.")

    def _run_terminal_command(self, command):
        if not command:
            self.tts.speak("What command should I run?")
            self.context.set_pending("terminal_command")
            return

        # Safety Check
        for danger in self.DANGEROUS_COMMANDS:
            if danger in command.lower():
                self.tts.speak("Whoa there! That command looks dangerous. I can't execute that for safety reasons. 🛑")
                return

        self.tts.speak(self.response.get_response("execute_command"))
        try:
            # Execute in a new terminal or just run it? 
            # User said "Open terminal" then "Run command". Usually means running it IN a terminal or just executing it.
            # We'll execute it and show the result if possible, or just run it in background.
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"{command}; exec bash"])
        except Exception as e:
            self.tts.speak(f"Oops! Something went wrong while running that command.")

    def _open_url(self, url):
        if not url:
            self.tts.speak("Which website should I open?")
            return
        if not url.startswith("http"):
            url = "https://" + url
        self.tts.speak(f"Alright, let's explore {url} 🌐")
        webbrowser.open(url)
        self.context.set_task("browsing")

    def _play_music(self, song):
        if not song:
            self.tts.speak("Which song should I play?")
            self.context.set_pending("song_name")
            return
        self.tts.speak(f"Playing {song} on YouTube. Enjoy the vibes! 🎶")
        query = song.replace(" ", "+")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        self.context.set_task("music")

    def _search_web(self, query):
        if not query:
            self.tts.speak(self.response.get_response("search_ask"))
            self.context.set_pending("search_query")
            return
        self.tts.speak(self.response.get_response("execute_command"))
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        self.context.set_task("searching")

    def _open_folder(self, folder_name):
        if not folder_name:
            self.tts.speak("Which folder should I open?")
            self.context.set_pending("folder_name")
            return
        folder_path = os.path.expanduser(f"~/{folder_name}")
        self.tts.speak(f"Opening folder {folder_name} for you. 📁")
        subprocess.Popen(["nautilus", folder_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.context.set_task(f"folder:{folder_name}")

    def _open_file(self, file_name):
        if not file_name:
            self.tts.speak("Which file should I open?")
            self.context.set_pending("file_name")
            return
        self.tts.speak(f"Opening {file_name} right away. 📄")
        subprocess.Popen(["xdg-open", file_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _system_control(self, command):
        cmd = command.lower()
        if "time" in cmd:
            t = datetime.datetime.now().strftime("%I:%M %p")
            self.tts.speak(f"The time is {t} 🕒")
        elif "date" in cmd:
            d = datetime.datetime.now().strftime("%A, %B %d, %Y")
            self.tts.speak(f"Today is {d} 📅")
        elif "volume up" in cmd:
            os.system("pactl set-sink-volume @DEFAULT_SINK@ +10%")
            self.tts.speak("Volume increased! 🔊")
        elif "volume down" in cmd:
            os.system("pactl set-sink-volume @DEFAULT_SINK@ -10%")
            self.tts.speak("Volume decreased! 🔉")
        elif "mute" in cmd:
            os.system("pactl set-sink-mute @DEFAULT_SINK@ toggle")
            self.tts.speak("Toggled mute! 🔇")
        elif "screenshot" in cmd:
            os.system("gnome-screenshot")
            self.tts.speak("Captured that for you! 📸")
        elif "battery" in cmd:
            b = psutil.sensors_battery()
            if b:
                self.tts.speak(f"Battery is at {int(b.percent)} percent. {'Plugged in ⚡' if b.power_plugged else 'Running on battery 🔋'}")
        elif "cpu" in cmd:
            usage = psutil.cpu_percent(interval=1)
            self.tts.speak(f"CPU usage is at {usage} percent. 💻")
        elif "shutdown" in cmd:
            self.tts.speak("Shutting down. See you later! 👋")
            os.system("shutdown now")
        elif "lock" in cmd:
            self.tts.speak("Locking the screen. Stay safe! 🔒")
            os.system("gnome-screensaver-command -l")
        else:
            self.tts.speak("I'm not quite sure how to handle that system command yet.")