"""Screen brightness control — brightnessctl, xbacklight, or sysfs."""
import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)


class BrightnessController:

    def __init__(self, environment):
        self.env            = environment
        self._backlight_path = None
        self.backend        = self._detect_backend()
        logger.info("Brightness backend: %s", self.backend)

    def _detect_backend(self) -> str:
        if shutil.which("brightnessctl"):
            return "brightnessctl"
        if shutil.which("xbacklight"):
            return "xbacklight"
        try:
            entries = os.listdir("/sys/class/backlight")
            if entries:
                self._backlight_path = f"/sys/class/backlight/{entries[0]}"
                return "sysfs"
        except (FileNotFoundError, PermissionError):
            pass
        return "none"

    def get_brightness(self) -> int:
        """Return 0-100 percentage, or -1 if unavailable."""
        try:
            if self.backend == "brightnessctl":
                cur = int(subprocess.check_output(
                    ["brightnessctl", "get"],
                    text=True, stderr=subprocess.DEVNULL, timeout=3,
                ).strip())
                mx = int(subprocess.check_output(
                    ["brightnessctl", "max"],
                    text=True, stderr=subprocess.DEVNULL, timeout=3,
                ).strip())
                return int(cur / mx * 100) if mx else -1

            if self.backend == "xbacklight":
                out = subprocess.check_output(
                    ["xbacklight", "-get"],
                    text=True, stderr=subprocess.DEVNULL, timeout=3,
                ).strip()
                return int(float(out))

            if self.backend == "sysfs" and self._backlight_path:
                with open(f"{self._backlight_path}/brightness") as f:
                    cur = int(f.read().strip())
                with open(f"{self._backlight_path}/max_brightness") as f:
                    mx = int(f.read().strip())
                return int(cur / mx * 100) if mx else -1

        except Exception as e:
            logger.warning("get_brightness error: %s", e)
        return -1

    def set_brightness(self, level: int) -> str:
        level = max(5, min(100, level))

        if self.backend == "none":
            return "No brightness control available on this system"

        try:
            if self.backend == "brightnessctl":
                subprocess.run(
                    ["brightnessctl", "set", f"{level}%"],
                    check=True, capture_output=True, timeout=5,
                )
            elif self.backend == "xbacklight":
                subprocess.run(
                    ["xbacklight", "-set", str(level)],
                    check=True, capture_output=True, timeout=5,
                )
            elif self.backend == "sysfs" and self._backlight_path:
                with open(f"{self._backlight_path}/max_brightness") as f:
                    mx = int(f.read().strip())
                value = int(level / 100 * mx)
                with open(f"{self._backlight_path}/brightness", "w") as f:
                    f.write(str(value))
            return f"Brightness set to {level} percent"
        except PermissionError:
            return ("Permission denied. "
                    "Run: sudo usermod -aG video $USER")
        except Exception as e:
            logger.warning("set_brightness error: %s", e)
            return "Could not change brightness"

    def brightness_up(self, step: int = 10) -> str:
        cur = self.get_brightness()
        if cur < 0:
            return "Cannot read current brightness"
        return self.set_brightness(cur + step)

    def brightness_down(self, step: int = 10) -> str:
        cur = self.get_brightness()
        if cur < 0:
            return "Cannot read current brightness"
        return self.set_brightness(cur - step)
