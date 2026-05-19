import os
import shutil
import logging

logger = logging.getLogger(__name__)

_instance = None


class VelloEnvironment:
    """Singleton that detects the Linux environment at startup."""

    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.audio_backend  = self._detect_audio_backend()
        self.display_server = self._detect_display_server()
        self.desktop_env    = self._detect_desktop_env()
        self.package_manager = self._detect_package_manager()
        self.capabilities   = self._probe_capabilities()

    # ── Detection methods ────────────────────────────────────────

    def _detect_audio_backend(self):
        if shutil.which("wpctl"):
            return "pipewire"
        if shutil.which("pactl"):
            return "pulseaudio"
        return "alsa"

    def _detect_display_server(self):
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("DISPLAY"):
            return "x11"
        return "x11"

    def _detect_desktop_env(self):
        return os.environ.get("XDG_CURRENT_DESKTOP", "unknown").lower()

    def _detect_package_manager(self):
        for pm in ["apt", "dnf", "pacman", "zypper"]:
            if shutil.which(pm):
                return pm
        return None

    def is_tool_available(self, tool_name: str) -> bool:
        return shutil.which(tool_name) is not None

    def _probe_capabilities(self):
        tools = [
            "pactl", "wpctl",
            "notify-send",
            "xclip", "wl-copy", "wl-paste",
            "gnome-screenshot", "grim", "scrot",
            "nmcli",
            "mpv", "yt-dlp",
            "xdotool", "wmctrl",
        ]
        available = set()
        for tool in tools:
            if self.is_tool_available(tool):
                available.add(tool)
            else:
                logger.warning("Optional tool not found: %s", tool)
        return available
