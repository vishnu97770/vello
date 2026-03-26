import os
import subprocess
import webbrowser
import datetime
import psutil


class SystemCommands:

    def __init__(self, tts):
        self.tts = tts

        # App name → actual linux command mapping
        self.app_map = {
            "chrome":       "google-chrome",
            "browser":      "google-chrome",
            "firefox":      "firefox",
            "terminal":     "gnome-terminal",
            "vscode":       "code",
            "vs code":      "code",
            "files":        "nautilus",
            "file manager": "nautilus",
            "calculator":   "gnome-calculator",
            "text editor":  "gedit",
            "settings":     "gnome-control-center",
            "camera":       "cheese",
            "music":        "rhythmbox",
            "videos":       "totem",
            "vlc":          "vlc",
            "spotify":      "spotify",
            "discord":      "discord",
            "slack":        "slack",
            "zoom":         "zoom",
            "telegram":     "telegram-desktop",
            "whatsapp":     "whatsapp-for-linux",
            "notepad":      "gedit",
            "screenshot":   "gnome-screenshot",
        }

    def execute(self, command):

        command_lower = command.lower()

        # ── Open Applications ──────────────────────────────────────
        if "open" in command_lower:
            self._handle_open(command_lower)

        # ── Search Web ─────────────────────────────────────────────
        elif "search" in command_lower or "google" in command_lower:
            self._handle_search(command_lower)

        # ── YouTube ────────────────────────────────────────────────
        elif "youtube" in command_lower:
            self._handle_youtube(command_lower)

        # ── Time ───────────────────────────────────────────────────
        elif "time" in command_lower:
            self._handle_time()

        # ── Date ───────────────────────────────────────────────────
        elif "date" in command_lower:
            self._handle_date()

        # ── Volume ─────────────────────────────────────────────────
        elif "volume up" in command_lower:
            self._volume_up()

        elif "volume down" in command_lower:
            self._volume_down()

        elif "mute" in command_lower:
            self._mute()

        # ── Screenshot ─────────────────────────────────────────────
        elif "screenshot" in command_lower:
            self._screenshot()

        # ── System Info ────────────────────────────────────────────
        elif "battery" in command_lower:
            self._battery()

        elif "cpu" in command_lower:
            self._cpu_usage()

        # ── Close App ──────────────────────────────────────────────
        elif "close" in command_lower:
            self._handle_close(command_lower)

        # ── Shutdown / Restart ─────────────────────────────────────
        elif "shutdown" in command_lower or "shut down" in command_lower:
            self.tts.speak("Shutting down the system")
            os.system("shutdown now")

        elif "restart" in command_lower or "reboot" in command_lower:
            self.tts.speak("Restarting the system")
            os.system("reboot")

        # ── Lock Screen ────────────────────────────────────────────
        elif "lock" in command_lower:
            self.tts.speak("Locking the screen")
            os.system("gnome-screensaver-command -l")

        else:
            self.tts.speak("Sorry, I could not find that command")

    # ── HELPER METHODS ────────────────────────────────────────────

    def _handle_open(self, command_lower):
        for app_name, app_cmd in self.app_map.items():
            if app_name in command_lower:
                self.tts.speak(f"Opening {app_name}")
                subprocess.Popen([app_cmd],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return

        # If app not in map, try running it directly
        words = command_lower.replace("open", "").strip().split()
        if words:
            app = words[0]
            self.tts.speak(f"Trying to open {app}")
            try:
                subprocess.Popen([app],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                self.tts.speak(f"Sorry, I could not find {app} on your system")

    def _handle_search(self, command_lower):
        query = command_lower.replace("search", "").replace("google", "").strip()
        if query:
            self.tts.speak(f"Searching for {query}")
            webbrowser.open(f"https://www.google.com/search?q={query}")
        else:
            self.tts.speak("What should I search for?")

    def _handle_youtube(self, command_lower):
        query = command_lower.replace("youtube", "").replace("play", "").replace("search", "").strip()
        if query:
            self.tts.speak(f"Searching YouTube for {query}")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        else:
            self.tts.speak("Opening YouTube")
            webbrowser.open("https://www.youtube.com")

    def _handle_time(self):
        time_now = datetime.datetime.now().strftime("%I:%M %p")
        self.tts.speak(f"The current time is {time_now}")

    def _handle_date(self):
        date_today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        self.tts.speak(f"Today is {date_today}")

    def _volume_up(self):
        self.tts.speak("Increasing volume")
        os.system("pactl set-sink-volume @DEFAULT_SINK@ +10%")

    def _volume_down(self):
        self.tts.speak("Decreasing volume")
        os.system("pactl set-sink-volume @DEFAULT_SINK@ -10%")

    def _mute(self):
        self.tts.speak("Toggling mute")
        os.system("pactl set-sink-mute @DEFAULT_SINK@ toggle")

    def _screenshot(self):
        self.tts.speak("Taking a screenshot")
        os.system("gnome-screenshot")

    def _battery(self):
        battery = psutil.sensors_battery()
        if battery:
            percent = int(battery.percent)
            status = "charging" if battery.power_plugged else "not charging"
            self.tts.speak(f"Battery is at {percent} percent and {status}")
        else:
            self.tts.speak("Could not read battery information")

    def _cpu_usage(self):
        usage = psutil.cpu_percent(interval=1)
        self.tts.speak(f"CPU usage is {usage} percent")

    def _handle_close(self, command_lower):
        for app_name in self.app_map:
            if app_name in command_lower:
                self.tts.speak(f"Closing {app_name}")
                os.system(f"pkill -f {self.app_map[app_name]}")
                return
        self.tts.speak("Which application should I close?")