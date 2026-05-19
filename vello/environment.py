import os
import re
import shutil
import subprocess
import logging

import psutil

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

        self.audio_backend    = self._detect_audio_backend()
        self.display_server   = self._detect_display_server()
        self.desktop_env      = self._detect_desktop_env()
        self.package_manager  = self._detect_package_manager()
        self.gpu              = self._detect_gpu()
        self.ram_gb           = self._detect_ram()
        self.screen_resolution = self._detect_screen_resolution()
        self.capabilities     = self._probe_capabilities()

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

    def _detect_gpu(self) -> str:
        if shutil.which("nvidia-smi"):
            return "nvidia"
        if os.path.isdir("/sys/class/drm"):
            return "amd/intel"
        return "unknown"

    def _detect_ram(self) -> int:
        try:
            return psutil.virtual_memory().total // (1024 ** 3)
        except Exception:
            return 0

    def _detect_screen_resolution(self) -> str:
        if self.display_server == "wayland":
            if shutil.which("wlr-randr"):
                try:
                    out = subprocess.check_output(
                        ["wlr-randr"], text=True,
                        stderr=subprocess.DEVNULL, timeout=3,
                    )
                    m = re.search(r"(\d{3,4})x(\d{3,4})", out)
                    if m:
                        return f"{m.group(1)}x{m.group(2)}"
                except Exception:
                    pass
            return "unknown"
        # X11
        try:
            out = subprocess.check_output(
                ["xrandr", "--current"], text=True,
                stderr=subprocess.DEVNULL, timeout=3,
            )
            m = re.search(r"current (\d+) x (\d+)", out)
            if m:
                return f"{m.group(1)}x{m.group(2)}"
        except Exception:
            pass
        return "unknown"

    def is_tool_available(self, tool_name: str) -> bool:
        return shutil.which(tool_name) is not None

    def _probe_capabilities(self) -> set:
        tools = [
            "pactl", "wpctl",
            "notify-send",
            "xclip", "wl-copy", "wl-paste",
            "gnome-screenshot", "grim", "scrot",
            "nmcli",
            "mpv", "yt-dlp",
            "xdotool", "wmctrl",
            "espeak", "espeak-ng", "piper",
            "brightnessctl", "xbacklight",
            "fd", "wlr-randr",
        ]
        available = set()
        for tool in tools:
            if self.is_tool_available(tool):
                available.add(tool)
            else:
                logger.warning("Optional tool not found: %s", tool)
        return available

    def get_summary(self) -> dict:
        return {
            "audio_backend":     self.audio_backend,
            "display_server":    self.display_server,
            "desktop_env":       self.desktop_env,
            "package_manager":   self.package_manager,
            "gpu":               self.gpu,
            "ram_gb":            self.ram_gb,
            "screen_resolution": self.screen_resolution,
            "capabilities":      list(self.capabilities),
        }

    def print_startup_banner(self):
        def tick(tool): return "✓" if tool in self.capabilities else "✗"

        de   = self.desktop_env.split(":")[0].capitalize() or "Unknown"
        pm   = self.package_manager or "None"
        ram  = f"{self.ram_gb} GB"
        gpu  = self.gpu

        print()
        print("┌──────────────────────────────────────────┐")
        print("│  VELLO — Starting                        │")
        print(f"│  Audio:    {self.audio_backend.capitalize():<28} │")
        print(f"│  Display:  {self.display_server.capitalize():<28} │")
        print(f"│  Desktop:  {de:<28} │")
        print(f"│  Packages: {pm:<28} │")
        print(f"│  RAM:      {ram} · GPU: {gpu:<18} │")
        print("├──────────────────────────────────────────┤")
        print(f"│  {tick('mpv')} mpv      "
              f"{tick('yt-dlp')} yt-dlp   "
              f"{tick('nmcli')} nmcli          │")
        print(f"│  {tick('espeak')} espeak   "
              f"{tick('piper')} piper    "
              f"{tick('notify-send')} notify-send     │")
        print(f"│  {tick('xclip')} xclip    "
              f"{tick('grim')} grim     "
              f"{tick('scrot')} scrot           │")
        print("└──────────────────────────────────────────┘")
        print()
