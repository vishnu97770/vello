import subprocess
import logging
import re

logger = logging.getLogger(__name__)


class AudioController:
    """Volume and mute control — supports PipeWire, PulseAudio, and ALSA."""

    def __init__(self, environment):
        self.backend = environment.audio_backend

    # ── Public API ────────────────────────────────────────────────

    def volume_up(self, amount: int = 10) -> str:
        if self.backend == "pipewire":
            self._run("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                      f"{amount}%+")
        else:
            self._run("pactl", "set-sink-volume", "@DEFAULT_SINK@",
                      f"+{amount}%")
        vol = self.get_volume()
        return f"Volume is now {vol} percent"

    def volume_down(self, amount: int = 10) -> str:
        if self.backend == "pipewire":
            self._run("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                      f"{amount}%-")
        else:
            self._run("pactl", "set-sink-volume", "@DEFAULT_SINK@",
                      f"-{amount}%")
        vol = self.get_volume()
        return f"Volume is now {vol} percent"

    def mute_toggle(self) -> str:
        if self.backend == "pipewire":
            self._run("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")
        else:
            self._run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle")
        return "Mute toggled"

    def get_volume(self) -> int:
        try:
            if self.backend == "pipewire":
                out = subprocess.check_output(
                    ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                    text=True, stderr=subprocess.DEVNULL
                )
                # "Volume: 0.70" → 70
                m = re.search(r"[\d.]+", out)
                if m:
                    return min(100, int(float(m.group()) * 100))
            else:
                out = subprocess.check_output(
                    ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                    text=True, stderr=subprocess.DEVNULL
                )
                m = re.search(r"(\d+)%", out)
                if m:
                    return int(m.group(1))
        except Exception as e:
            logger.warning("get_volume failed: %s", e)
        return 50

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        if self.backend == "pipewire":
            self._run("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                      f"{level / 100:.2f}")
        else:
            self._run("pactl", "set-sink-volume", "@DEFAULT_SINK@",
                      f"{level}%")
        return f"Volume set to {level} percent"

    # ── Internal ──────────────────────────────────────────────────

    def _run(self, *args):
        try:
            subprocess.run(list(args), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.warning("AudioController command failed %s: %s", args, e)
