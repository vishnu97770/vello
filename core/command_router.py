from core.response_generator import ResponseGenerator
from vello.nlp.normalizer import Normalizer
import webbrowser
import subprocess
import os
import re
import datetime
import psutil
import logging

logger = logging.getLogger(__name__)
_normalizer = Normalizer()


class _DummyContext:
    """Fallback when no context is provided."""
    active_app     = None
    active_task    = None
    pending_action = None
    last_subject   = None

    def set_app(self, x):      self.active_app  = x.lower()
    def set_task(self, x):     self.active_task = x.lower()
    def set_pending(self, x):  self.pending_action = x
    def clear_pending(self):   self.pending_action = None
    def get_context_summary(self):
        return {"active_app": self.active_app, "active_task": self.active_task,
                "pending": self.pending_action, "recent": []}


class _DummyTTS:
    def speak(self, text): print(f"[TTS-dummy]: {text}")


class CommandRouter:
    """
    Routes intents to the appropriate handler.
    Every handler returns a non-empty string.
    execute() is the primary public API.
    route() is kept for backward compatibility.
    """

    DANGEROUS_COMMANDS = [
        "rm -rf", "sudo rm", "mkfs", "dd if=",
        "> /dev/sda", ":(){ :|:& };:",
    ]

    OVERRIDES_PENDING = {
        "open_app", "open_url", "play_music", "search_web",
        "system_control", "terminal_run", "music_stop",
        "music_pause", "music_resume", "wifi_on", "wifi_off",
        "get_time", "get_date",
        # new intent names
        "music_play", "web_search", "volume_up", "volume_down",
        "mute", "screenshot", "shutdown", "restart", "lock_screen",
        "goodbye", "greeting",
        "media_next", "media_previous", "media_now_playing", "media_playpause",
        "window_close", "window_minimize", "window_maximize",
        "window_snap_left", "window_snap_right", "window_list",
        "brightness_up", "brightness_down", "brightness_set", "brightness_get",
        "file_search", "file_open", "folder_open", "recent_files",
    }

    def __init__(self, tts=None, context=None, env=None, audio_ctrl=None,
                 music=None, reminders=None, network=None,
                 clipboard=None, packages=None, app_registry=None,
                 stt=None, dbus_media=None, window_manager=None,
                 file_ops=None, brightness=None):
        self.tts            = tts or _DummyTTS()
        self.context        = context or _DummyContext()
        self.response       = ResponseGenerator()
        self.env            = env
        self.audio          = audio_ctrl
        self.music          = music
        self.reminders      = reminders
        self.network        = network
        self.clipboard      = clipboard
        self.packages       = packages
        self.app_registry   = app_registry
        self.stt            = stt
        self.dbus_media     = dbus_media
        self.window_manager = window_manager
        self.file_ops       = file_ops
        self.brightness     = brightness

    # ── Primary public API ─────────────────────────────────────────

    def execute(self, intent, command: str = "") -> str:
        """
        Route intent → return a non-empty response string.
        Never calls tts.speak() — the caller is responsible for speaking.
        intent may be a dict (from IntentEngine.classify) or a plain string.
        """
        print(f"[Vello] execute() called — intent={intent!r}, command={command!r}")

        if isinstance(intent, dict):
            intent_data = intent
        else:
            intent_data = {"intent": str(intent), "app": None,
                           "target": None, "chain": []}

        ctx_intent = intent_data.get("intent")

        # Pending action handling
        if self.context.pending_action and ctx_intent not in self.OVERRIDES_PENDING:
            result = self._handle_pending_return(
                self.context.pending_action, command)
        else:
            if self.context.pending_action and ctx_intent in self.OVERRIDES_PENDING:
                self.context.clear_pending()
            result = self._dispatch(
                ctx_intent,
                intent_data.get("app"),
                intent_data.get("target"),
                command,
            )

        # Handle chained commands (e.g. "open chrome and search python")
        for step in intent_data.get("chain", []):
            step_result = self._dispatch(
                step.get("intent"),
                step.get("app") or self.context.active_app,
                step.get("target"),
                command,
            )
            # Speak chain steps via tts so they happen before the final speak
            if step_result:
                self.tts.speak(step_result)

        return result or "Done."

    # ── Backward-compatible route() ────────────────────────────────

    def route(self, intent_data, original_command=""):
        """Legacy API: execute + speak the result via self.tts."""
        result = self.execute(intent_data, original_command)
        if result and result != "USE_AI":
            self.tts.speak(result)
        return result

    # ── Core dispatcher — always returns a string ──────────────────

    def _dispatch(self, intent, app, target, command="") -> str:

        # ── Greeting ──────────────────────────────────────────────
        if intent == "greeting":
            return _normalizer.get_greeting_response()

        # ── Goodbye ───────────────────────────────────────────────
        if intent in ("goodbye", "exit"):
            return "Goodbye. Have an awesome day!"

        # ── AI fallback ───────────────────────────────────────────
        if intent in ("ai_fallback", "ask_ai"):
            return "USE_AI"

        # ── MPRIS2 media control ──────────────────────────────────
        if intent == "media_next":
            return self.dbus_media.next_track() if self.dbus_media \
                else "Media control not available"
        if intent == "media_previous":
            return self.dbus_media.previous_track() if self.dbus_media \
                else "Media control not available"
        if intent == "media_now_playing":
            return self.dbus_media.get_now_playing() if self.dbus_media \
                else "Media control not available"
        if intent == "media_playpause":
            return self.dbus_media.play_pause() if self.dbus_media \
                else "Media control not available"

        # ── Window management ─────────────────────────────────────
        if intent == "window_close":
            return self.window_manager.close_window() if self.window_manager \
                else "Window manager not available"
        if intent == "window_minimize":
            return self.window_manager.minimize_window() if self.window_manager \
                else "Window manager not available"
        if intent == "window_maximize":
            return self.window_manager.maximize_window() if self.window_manager \
                else "Window manager not available"
        if intent == "window_snap_left":
            return self.window_manager.snap_left() if self.window_manager \
                else "Window manager not available"
        if intent == "window_snap_right":
            return self.window_manager.snap_right() if self.window_manager \
                else "Window manager not available"
        if intent == "window_list":
            return self.window_manager.list_windows() if self.window_manager \
                else "Window manager not available"

        # ── Brightness ────────────────────────────────────────────
        if intent == "brightness_up":
            return self.brightness.brightness_up() if self.brightness \
                else "Brightness control not available"
        if intent == "brightness_down":
            return self.brightness.brightness_down() if self.brightness \
                else "Brightness control not available"
        if intent == "brightness_set":
            level = self._extract_brightness_level(command)
            if level is None:
                return "What brightness level? Say a number like 70."
            return self.brightness.set_brightness(level) if self.brightness \
                else "Brightness control not available"
        if intent == "brightness_get":
            if not self.brightness:
                return "Brightness control not available"
            val = self.brightness.get_brightness()
            return f"Brightness is at {val} percent" if val >= 0 \
                else "Could not read brightness level"

        # ── File operations ───────────────────────────────────────
        if intent == "file_search":
            query = self._extract_file_query(command)
            return self.file_ops.search_files(query) if self.file_ops \
                else "File search not available"
        if intent == "file_open":
            fname = self._extract_file_name(command)
            return self.file_ops.open_file(fname) if self.file_ops \
                else "File open not available"
        if intent == "folder_open":
            folder = self._extract_folder_name(command)
            return self.file_ops.open_folder(folder) if self.file_ops \
                else "Folder open not available"
        if intent == "recent_files":
            return self.file_ops.recent_files() if self.file_ops \
                else "File ops not available"

        # ── Time / date ───────────────────────────────────────────
        if intent == "get_time":
            t = datetime.datetime.now().strftime("%I:%M %p")
            return f"The time is {t}"

        if intent == "get_date":
            d = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {d}"

        # ── Volume control (direct intents) ───────────────────────
        if intent == "volume_up":
            if self.audio:
                return self.audio.volume_up()
            os.system("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%+ 2>/dev/null"
                      " || pactl set-sink-volume @DEFAULT_SINK@ +10%")
            return "Volume increased"

        if intent == "volume_down":
            if self.audio:
                return self.audio.volume_down()
            os.system("wpctl set-volume @DEFAULT_AUDIO_SINK@ 10%- 2>/dev/null"
                      " || pactl set-sink-volume @DEFAULT_SINK@ -10%")
            return "Volume decreased"

        if intent == "mute":
            if self.audio:
                return self.audio.mute_toggle()
            os.system("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle 2>/dev/null"
                      " || pactl set-sink-mute @DEFAULT_SINK@ toggle")
            return "Muted"

        # ── System info (direct intents) ──────────────────────────
        if intent == "battery":
            b = psutil.sensors_battery()
            if b:
                status = "plugged in" if b.power_plugged else "running on battery"
                return f"Battery is at {int(b.percent)} percent, {status}"
            return "Battery information not available"

        if intent == "cpu_usage":
            usage = psutil.cpu_percent(interval=1)
            return f"CPU usage is at {usage} percent"

        if intent == "memory_usage":
            return self._system_info("memory")

        if intent == "disk_usage":
            return self._system_info("disk")

        if intent == "temperature":
            return self._system_info("temperature")

        if intent == "network_usage":
            return self._system_info("network_usage")

        if intent == "uptime":
            return self._system_info("uptime")

        if intent == "processes":
            return self._system_info("processes")

        # ── Screenshot ────────────────────────────────────────────
        if intent == "screenshot":
            return self._take_screenshot()

        # ── Shutdown / restart / lock ─────────────────────────────
        if intent == "shutdown":
            os.system("shutdown now")
            return "Shutting down"

        if intent == "restart":
            os.system("reboot")
            return "Restarting"

        if intent == "lock_screen":
            self._lock_screen()
            return "Locking the screen"

        # ── App opening ───────────────────────────────────────────
        if intent == "open_app":
            return self._open_app(app or self._extract_app_name(command))

        # ── Web / search ──────────────────────────────────────────
        if intent == "open_url":
            return self._open_url(target)

        if intent in ("search_web", "web_search"):
            return self._search_web(target or self._extract_search_query(command))

        # ── Music ─────────────────────────────────────────────────
        if intent in ("play_music", "music_play"):
            return self._play_music(target or self._extract_music_query(command))

        if intent == "music_stop":
            if self.music:
                result = self.music.stop()
                return result if result else "Music stopped"
            return "Music player not available"

        if intent == "music_pause":
            if self.music:
                result = self.music.pause()
                return result if result else "Music paused"
            return "Music player not available"

        if intent == "music_resume":
            if self.music:
                result = self.music.resume()
                return result if result else "Music resumed"
            return "Music player not available"

        if intent == "music_status":
            if self.music:
                result = self.music.status()
                return result if result else "Nothing playing right now"
            return "Music player not available"

        # ── System control (legacy) ───────────────────────────────
        if intent == "system_control":
            return self._system_control(command)

        # ── System info (legacy) ──────────────────────────────────
        if intent == "system_info":
            return self._system_info(target)

        # ── Reminders ─────────────────────────────────────────────
        if intent == "set_reminder":
            reminder_text = target or self._extract_reminder_query(command)
            return (self.reminders.set_reminder(reminder_text)
                    if self.reminders else "Reminders not available")

        if intent == "set_timer":
            return (self.reminders.set_timer(target or command)
                    if self.reminders else "Timers not available")

        if intent == "list_reminders":
            return (self.reminders.list_reminders()
                    if self.reminders else "Reminders not available")

        # ── Network ───────────────────────────────────────────────
        if intent == "wifi_on":
            return self.network.wifi_on() if self.network else "Network control unavailable"

        if intent == "wifi_off":
            return self.network.wifi_off() if self.network else "Network control unavailable"

        if intent == "list_networks":
            return self.network.list_networks() if self.network else "Network control unavailable"

        if intent == "connect_wifi":
            return (self.network.connect_to(target)
                    if self.network else "Network control unavailable")

        if intent == "get_ip":
            return self.network.get_ip() if self.network else "Network control unavailable"

        if intent == "check_internet":
            return (self.network.check_connection()
                    if self.network else "Network control unavailable")

        # ── Clipboard ─────────────────────────────────────────────
        if intent == "clipboard_read":
            if not self.clipboard:
                return "Clipboard not available"
            text = self.clipboard.read()
            if text:
                preview = text[:100] + (" and more" if len(text) > 100 else "")
                return f"Your clipboard contains: {preview}"
            return "Your clipboard is empty"

        if intent == "clipboard_write":
            if not self.clipboard or not target:
                return "What should I copy?"
            return self.clipboard.write(target)

        # ── Package management ────────────────────────────────────
        if intent == "package_install":
            if not self.packages:
                return "Package manager not available"
            return self.packages.install(target or "")

        if intent == "package_remove":
            if not self.packages:
                return "Package manager not available"
            return self.packages.remove(target or "")

        if intent == "system_update":
            if not self.packages:
                return "Package manager not available"
            return self.packages.update_system()

        # ── Terminal ──────────────────────────────────────────────
        if intent == "terminal_run":
            return self._run_terminal_command(target)

        # ── Misc ──────────────────────────────────────────────────
        if intent == "open_folder":
            return self._open_folder(target)

        if intent == "open_file":
            return self._open_file(target)

        if intent == "clarify":
            self.context.set_pending(target)
            return f"Could you be more specific? What {target} should I use?"

        return "I am not sure how to handle that. Please try again."

    # ── Pending action handler ────────────────────────────────────

    def _handle_pending_return(self, pending_type, command) -> str:
        self.context.clear_pending()
        if pending_type == "search_query":
            return self._search_web(command)
        if pending_type == "terminal_command":
            return self._run_terminal_command(command)
        if pending_type == "coding_task":
            return f"Opening VS Code for {command}"
        if pending_type == "work_task":
            return f"Opening LibreOffice for {command}"
        return f"Processing your request for {command}"

    # ── Smart query extractors ────────────────────────────────────

    def _extract_app_name(self, command: str) -> str:
        """Pull the app name from raw command text."""
        cmd = command.lower().strip()
        for prefix in ("open ", "launch ", "start ", "run "):
            if cmd.startswith(prefix):
                return cmd[len(prefix):].strip()
        m = re.search(r'\b(?:open|launch|start|run)\s+(\S+(?:\s+\S+)?)', cmd)
        if m:
            return m.group(1).strip()
        return cmd

    def _extract_search_query(self, command: str) -> str:
        """Pull the search query from raw command text."""
        cmd = command.lower().strip()
        for prefix in ("search for ", "search ", "google ", "look up ",
                       "find ", "look for "):
            if prefix in cmd:
                return cmd.split(prefix, 1)[1].strip()
        return cmd

    def _extract_music_query(self, command: str) -> str:
        """Pull the song/artist from raw command text."""
        cmd = command.lower().strip()
        for prefix in ("play ", "put on ", "listen to "):
            if prefix in cmd:
                after = cmd.split(prefix, 1)[1].strip()
                # strip trailing filler
                after = re.sub(r'\s*(?:for me|please)\s*$', '', after).strip()
                return after
        return cmd

    def _extract_reminder_query(self, command: str) -> str:
        """Pull reminder content from raw command text."""
        cmd = command.lower().strip()
        m = re.search(r'\bremind\s+me\s+(?:to\s+)?(.+)', cmd)
        if m:
            return m.group(1).strip()
        return cmd

    def _extract_brightness_level(self, command: str):
        """Extract integer brightness level from command, or None."""
        m = re.search(r'\b(\d{1,3})\b', command)
        if m:
            return int(m.group(1))
        return None

    def _extract_file_query(self, command: str) -> str:
        """Extract file search term from command."""
        cmd = command.lower().strip()
        for prefix in ("find file ", "search for file ", "where is ",
                       "search file ", "find my "):
            if prefix in cmd:
                return cmd.split(prefix, 1)[1].strip()
        return cmd

    def _extract_file_name(self, command: str) -> str:
        """Extract filename from command."""
        cmd = command.lower().strip()
        for prefix in ("open file ", "open the file "):
            if cmd.startswith(prefix):
                return cmd[len(prefix):].strip()
        m = re.search(r'\bopen\s+(?:the\s+)?file\s+(.+)', cmd)
        if m:
            return m.group(1).strip()
        return cmd

    def _extract_folder_name(self, command: str) -> str:
        """Extract folder name from command."""
        cmd = command.lower().strip()
        for prefix in ("open folder ", "open the folder ",
                       "open my ", "go to ", "open "):
            if cmd.startswith(prefix):
                return cmd[len(prefix):].strip()
        return cmd

    # ── App opening ───────────────────────────────────────────────

    def _open_app(self, app_name) -> str:
        if not app_name:
            self.context.set_pending("app_name")
            return "Which application should I open?"

        app_key = app_name.lower()

        # Try dynamic registry first
        cmd = None
        if self.app_registry:
            from vello.app_registry import find_app
            cmd = find_app(app_key)

        # Fallback to hardcoded map
        if not cmd:
            cmd = _HARDCODED_APPS.get(app_key)

        if cmd:
            subprocess.Popen(
                cmd.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.context.set_app(app_name)

            # Multi-step follow-ups — combine into single response
            if app_key in ["chrome", "google"]:
                self.context.set_pending("search_query")
                return f"Opening {app_name}. What would you like to search?"
            elif app_key == "terminal":
                self.context.set_pending("terminal_command")
                return f"Opening terminal. What command should I run?"
            elif app_key == "vscode":
                self.context.set_pending("coding_task")
                return f"VS Code is ready. What are you coding today?"
            elif app_key == "libreoffice":
                self.context.set_pending("work_task")
                return f"Opening LibreOffice. What would you like to work on?"
            return f"Opening {app_name}"
        else:
            # Try running the app name directly
            try:
                subprocess.Popen(
                    [app_key],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.context.set_app(app_name)
                return f"Opening {app_name}"
            except FileNotFoundError:
                return f"I couldn't find {app_name}. Is it installed?"

    # ── Terminal ──────────────────────────────────────────────────

    def _run_terminal_command(self, command) -> str:
        if not command:
            self.context.set_pending("terminal_command")
            return "What command should I run?"
        for danger in self.DANGEROUS_COMMANDS:
            if danger in command.lower():
                return "That command looks dangerous. I cannot execute it for safety reasons."
        try:
            subprocess.Popen(
                ["gnome-terminal", "--", "bash", "-c",
                 f"{command}; exec bash"]
            )
            return f"Running: {command}"
        except Exception:
            return "Something went wrong while running that command."

    # ── Web / URL / Search / Music ────────────────────────────────

    def _open_url(self, url) -> str:
        if not url:
            return "Which website should I open?"
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        self.context.set_task("browsing")
        return f"Opening {url}"

    def _play_music(self, song) -> str:
        if not song:
            self.context.set_pending("song_name")
            return "Which song should I play?"
        if self.music:
            msg = self.music.play(song)
            self.context.set_task("music")
            return msg
        webbrowser.open(
            f"https://www.youtube.com/results?search_query="
            f"{song.replace(' ', '+')}"
        )
        self.context.set_task("music")
        return f"Playing {song} on YouTube"

    def _search_web(self, query) -> str:
        if not query:
            self.context.set_pending("search_query")
            return "What should I search for?"
        webbrowser.open(
            f"https://www.google.com/search?q={query.replace(' ', '+')}"
        )
        self.context.set_task("searching")
        return f"Searching for {query}"

    def _open_folder(self, folder_name) -> str:
        if not folder_name:
            self.context.set_pending("folder_name")
            return "Which folder should I open?"
        folder_path = os.path.expanduser(f"~/{folder_name}")
        subprocess.Popen(
            ["nautilus", folder_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.context.set_task(f"folder:{folder_name}")
        return f"Opening folder {folder_name}"

    def _open_file(self, file_name) -> str:
        if not file_name:
            self.context.set_pending("file_name")
            return "Which file should I open?"
        subprocess.Popen(
            ["xdg-open", file_name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return f"Opening {file_name}"

    # ── System control ────────────────────────────────────────────

    def _system_control(self, command) -> str:
        cmd = command.lower()

        if "volume up" in cmd:
            if self.audio:
                return self.audio.volume_up()
            os.system("pactl set-sink-volume @DEFAULT_SINK@ +10%")
            return "Volume increased"

        if "volume down" in cmd:
            if self.audio:
                return self.audio.volume_down()
            os.system("pactl set-sink-volume @DEFAULT_SINK@ -10%")
            return "Volume decreased"

        if "mute" in cmd:
            if self.audio:
                return self.audio.mute_toggle()
            os.system("pactl set-sink-mute @DEFAULT_SINK@ toggle")
            return "Mute toggled"

        if "screenshot" in cmd:
            return self._take_screenshot()

        if "battery" in cmd:
            b = psutil.sensors_battery()
            if b:
                status = "plugged in" if b.power_plugged else "running on battery"
                return f"Battery is at {int(b.percent)} percent, {status}"
            return "Battery information not available"

        if "cpu" in cmd:
            usage = psutil.cpu_percent(interval=1)
            return f"CPU usage is at {usage} percent"

        if "shutdown" in cmd or "shut down" in cmd:
            os.system("shutdown now")
            return "Shutting down"

        if "restart" in cmd or "reboot" in cmd:
            os.system("reboot")
            return "Restarting"

        if "lock" in cmd:
            self._lock_screen()
            return "Locking the screen"

        return "I am not sure how to handle that system command"

    # ── System info ───────────────────────────────────────────────

    def _system_info(self, sub_type: str) -> str:
        try:
            if sub_type == "memory":
                mem = psutil.virtual_memory()
                free_mb = mem.available // (1024 ** 2)
                return (f"RAM usage is {mem.percent} percent, "
                        f"{free_mb} megabytes free")

            if sub_type == "disk":
                disk = psutil.disk_usage("/")
                free_gb = disk.free // (1024 ** 3)
                return (f"Disk usage is {disk.percent} percent, "
                        f"{free_gb} gigabytes free")

            if sub_type == "temperature":
                temps = psutil.sensors_temperatures()
                keys  = [k for k in temps if k in ("coretemp", "k10temp",
                                                     "cpu_thermal", "acpitz")]
                if keys:
                    readings = temps[keys[0]]
                    avg = sum(r.current for r in readings) / len(readings)
                    return f"Average CPU temperature is {avg:.1f} degrees Celsius"
                return "Temperature sensors are not available on this system"

            if sub_type == "network_usage":
                net = psutil.net_io_counters()
                sent_mb = net.bytes_sent // (1024 ** 2)
                recv_mb = net.bytes_recv // (1024 ** 2)
                return (f"Sent {sent_mb} megabytes, "
                        f"received {recv_mb} megabytes since last boot")

            if sub_type == "uptime":
                boot  = datetime.datetime.fromtimestamp(psutil.boot_time())
                delta = datetime.datetime.now() - boot
                days  = delta.days
                hours = delta.seconds // 3600
                mins  = (delta.seconds % 3600) // 60
                parts = []
                if days:  parts.append(f"{days} day{'s' if days != 1 else ''}")
                if hours: parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                if mins:  parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
                return f"System has been running for {', '.join(parts) or 'less than a minute'}"

            if sub_type == "processes":
                count = len(psutil.pids())
                return f"There are {count} processes currently running"

        except Exception as e:
            logger.warning("system_info error for %s: %s", sub_type, e)
            return "Could not retrieve that system information"

        return "Unknown system info type"

    # ── Screenshot ────────────────────────────────────────────────

    def _take_screenshot(self) -> str:
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Pictures/screenshot_{ts}.png")
        os.makedirs(os.path.expanduser("~/Pictures"), exist_ok=True)

        env  = self.env
        disp = env.display_server if env else "x11"
        caps = env.capabilities  if env else set()

        if disp == "wayland":
            if "grim" in caps:
                subprocess.run(["grim", path], stderr=subprocess.DEVNULL)
                return "Screenshot saved to Pictures folder"
            if "gnome-screenshot" in caps:
                subprocess.run(["gnome-screenshot", "-f", path], stderr=subprocess.DEVNULL)
                return "Screenshot saved to Pictures folder"
            return "Screenshot tool not found. Install grim for Wayland."
        else:
            if "gnome-screenshot" in caps:
                subprocess.run(["gnome-screenshot", "-f", path], stderr=subprocess.DEVNULL)
                return "Screenshot saved to Pictures folder"
            if "scrot" in caps:
                subprocess.run(["scrot", path], stderr=subprocess.DEVNULL)
                return "Screenshot saved to Pictures folder"
            return "No screenshot tool found. Install scrot."

    def _lock_screen(self):
        env = self.env
        de  = env.desktop_env if env else "unknown"
        if "gnome" in de.lower():
            os.system("gnome-screensaver-command -l 2>/dev/null || loginctl lock-session 2>/dev/null")
        elif "kde" in de.lower():
            os.system("loginctl lock-session")
        else:
            os.system("xdg-screensaver lock 2>/dev/null || loginctl lock-session 2>/dev/null")


# ── Hardcoded app fallback map ────────────────────────────────────────────────
_HARDCODED_APPS = {
    "chrome":       "google-chrome",
    "browser":      "google-chrome",
    "google":       "google-chrome",
    "firefox":      "firefox",
    "terminal":     "gnome-terminal",
    "vscode":       "code",
    "vs code":      "code",
    "files":        "nautilus",
    "file manager": "nautilus",
    "calculator":   "gnome-calculator",
    "settings":     "gnome-control-center",
    "vlc":          "vlc",
    "spotify":      "spotify",
    "discord":      "discord",
    "zoom":         "zoom",
    "telegram":     "telegram-desktop",
    "gedit":        "gedit",
    "notepad":      "gedit",
    "libreoffice":  "libreoffice",
    "writer":       "libreoffice --writer",
}
