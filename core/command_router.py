import webbrowser
import subprocess
import os
import datetime
import psutil


class CommandRouter:
    """
    Receives structured intent from IntentEngine and executes actions.
    Also gives proactive suggestions after each action.
    """

    APP_COMMANDS = {
        "chrome":        "google-chrome",
        "browser":       "google-chrome",
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
    }

    # Suggestions shown after opening each app
    APP_SUGGESTIONS = {
        "chrome":   "Chrome is open. You can say: search something, open YouTube, or open any website.",
        "firefox":  "Firefox is open. You can say: search something or open a website.",
        "vscode":   "VS Code is open. You can say: open a folder or open a file.",
        "terminal": "Terminal is open. What would you like to run?",
        "spotify":  "Spotify is open. You can say: play a song or search for an artist.",
        "vlc":      "VLC is open. You can say: open a file to play.",
    }

    def __init__(self, tts, context):
        self.tts     = tts
        self.context = context

    def route(self, intent_data, original_command=""):
        intent  = intent_data.get("intent")
        app     = intent_data.get("app")
        target  = intent_data.get("target")
        chain   = intent_data.get("chain", [])

        # Execute primary intent
        self._execute(intent, app, target, original_command)

        # Execute chained actions (multi-step commands)
        for step in chain:
            self._execute(
                step.get("intent"),
                step.get("app") or self.context.active_app,
                step.get("target"),
                original_command
            )

    def _execute(self, intent, app, target, original_command=""):

        if intent == "open_app":
            self._open_app(app)

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

        elif intent == "clarify":
            question = f"Could you be more specific? What {target} should I use?"
            self.tts.speak(question)
            self.context.set_pending(target)

        elif intent == "ask_ai":
            # Signal to main loop to use AI brain
            return "USE_AI"

        else:
            self.tts.speak("I am not sure how to handle that. Please try again.")

    # ── ACTION HANDLERS ───────────────────────────────────────────

    def _open_app(self, app_name):
        if not app_name:
            self.tts.speak("Which application should I open?")
            self.context.set_pending("app_name")
            return

        cmd = self.APP_COMMANDS.get(app_name.lower())

        if cmd:
            self.tts.speak(f"Opening {app_name}")
            subprocess.Popen(
                [cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.context.set_app(app_name)

            # Give suggestion after opening
            suggestion = self.APP_SUGGESTIONS.get(app_name.lower())
            if suggestion:
                import time
                time.sleep(1.5)
                self.tts.speak(suggestion)

        else:
            # Try running it directly
            self.tts.speak(f"Trying to open {app_name}")
            try:
                subprocess.Popen(
                    [app_name.lower()],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.context.set_app(app_name)
            except FileNotFoundError:
                self.tts.speak(
                    f"Sorry, I could not find {app_name} on your system."
                )

    def _open_url(self, url):
        if not url:
            self.tts.speak("Which website should I open?")
            return

        if not url.startswith("http"):
            url = "https://" + url

        self.tts.speak(f"Opening {url}")
        webbrowser.open(url)
        self.context.set_task("browsing")

    def _play_music(self, song):
        if not song:
            self.tts.speak("Which song should I play?")
            self.context.set_pending("song_name")
            return

        self.tts.speak(f"Playing {song} on YouTube")
        query = song.replace(" ", "+")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        self.context.set_task("music")

    def _search_web(self, query):
        if not query:
            self.tts.speak("What should I search for?")
            self.context.set_pending("search_query")
            return

        self.tts.speak(f"Searching for {query}")
        webbrowser.open(
            f"https://www.google.com/search?q={query.replace(' ', '+')}"
        )
        self.context.set_task("searching")

    def _open_folder(self, folder_name):
        if not folder_name:
            self.tts.speak("Which folder should I open?")
            self.context.set_pending("folder_name")
            return

        active = self.context.active_app

        if active in ["vscode", "vs code", "code"]:
            self.tts.speak(f"Opening folder {folder_name} in VS Code")
            folder_path = os.path.expanduser(f"~/{folder_name}")
            subprocess.Popen(
                ["code", folder_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            self.tts.speak(f"Opening folder {folder_name}")
            folder_path = os.path.expanduser(f"~/{folder_name}")
            subprocess.Popen(
                ["nautilus", folder_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        self.context.set_task(f"folder:{folder_name}")

    def _open_file(self, file_name):
        if not file_name:
            self.tts.speak("Which file should I open?")
            self.context.set_pending("file_name")
            return

        active = self.context.active_app

        if active in ["vscode", "vs code", "code"]:
            self.tts.speak(f"Opening file {file_name} in VS Code")
            subprocess.Popen(
                ["code", file_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            self.tts.speak(f"Opening {file_name}")
            subprocess.Popen(
                ["xdg-open", file_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def _system_control(self, command):
        cmd = command.lower()

        if "time" in cmd:
            t = datetime.datetime.now().strftime("%I:%M %p")
            self.tts.speak(f"The time is {t}")

        elif "date" in cmd:
            d = datetime.datetime.now().strftime("%A, %B %d, %Y")
            self.tts.speak(f"Today is {d}")

        elif "volume up" in cmd:
            os.system("pactl set-sink-volume @DEFAULT_SINK@ +10%")
            self.tts.speak("Volume increased")

        elif "volume down" in cmd:
            os.system("pactl set-sink-volume @DEFAULT_SINK@ -10%")
            self.tts.speak("Volume decreased")

        elif "mute" in cmd:
            os.system("pactl set-sink-mute @DEFAULT_SINK@ toggle")
            self.tts.speak("Toggled mute")

        elif "screenshot" in cmd:
            os.system("gnome-screenshot")
            self.tts.speak("Screenshot taken")

        elif "battery" in cmd:
            b = psutil.sensors_battery()
            if b:
                self.tts.speak(
                    f"Battery is at {int(b.percent)} percent, "
                    f"{'charging' if b.power_plugged else 'not charging'}"
                )

        elif "cpu" in cmd:
            usage = psutil.cpu_percent(interval=1)
            self.tts.speak(f"CPU usage is {usage} percent")

        elif "shutdown" in cmd or "shut down" in cmd:
            self.tts.speak("Shutting down")
            os.system("shutdown now")

        elif "restart" in cmd or "reboot" in cmd:
            self.tts.speak("Restarting")
            os.system("reboot")

        elif "lock" in cmd:
            self.tts.speak("Locking screen")
            os.system("gnome-screensaver-command -l")

        else:
            self.tts.speak("System command not recognized")