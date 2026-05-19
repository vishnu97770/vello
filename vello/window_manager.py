"""Window management via wmctrl / xdotool (X11 only)."""
import shutil
import subprocess
import re
import logging

logger = logging.getLogger(__name__)


class WindowManager:

    def __init__(self, environment):
        self.env     = environment
        self.wmctrl  = shutil.which("wmctrl")
        self.xdotool = shutil.which("xdotool")
        self.available = (
            environment.display_server == "x11" and
            bool(self.wmctrl or self.xdotool)
        )

    def _wayland_warning(self) -> str:
        return ("Window control is limited on Wayland. "
                "This feature works on X11.")

    def _need(self, tool: str) -> str | None:
        """Return an install-hint string if tool is missing, else None."""
        if not shutil.which(tool):
            return (f"{tool} not installed. "
                    f"Run: sudo apt install {tool}")
        return None

    def _get_active_id(self) -> str | None:
        try:
            out = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                text=True, stderr=subprocess.DEVNULL, timeout=3,
            )
            return out.strip()
        except Exception:
            return None

    def close_window(self) -> str:
        if self.env.display_server == "wayland":
            return self._wayland_warning()
        err = self._need("xdotool")
        if err:
            return err
        try:
            subprocess.run(
                ["xdotool", "getactivewindow", "windowclose"],
                check=True, capture_output=True, timeout=5,
            )
            return "Window closed"
        except Exception:
            return "Could not close window"

    def minimize_window(self) -> str:
        if self.env.display_server == "wayland":
            return self._wayland_warning()
        err = self._need("xdotool")
        if err:
            return err
        try:
            subprocess.run(
                ["xdotool", "getactivewindow", "windowminimize"],
                check=True, capture_output=True, timeout=5,
            )
            return "Window minimized"
        except Exception:
            return "Could not minimize window"

    def maximize_window(self) -> str:
        if self.env.display_server == "wayland":
            return self._wayland_warning()
        for tool in ("xdotool", "wmctrl"):
            err = self._need(tool)
            if err:
                return err
        try:
            win_id = self._get_active_id()
            if not win_id:
                return "Could not identify active window"
            subprocess.run(
                ["wmctrl", "-ir", win_id, "-b",
                 "add,maximized_vert,maximized_horz"],
                check=True, capture_output=True, timeout=5,
            )
            return "Window maximized"
        except Exception:
            return "Could not maximize window"

    def snap_left(self) -> str:
        if self.env.display_server == "wayland":
            return self._wayland_warning()
        err = self._need("xdotool")
        if err:
            return err
        sw, sh = self._screen_dims()
        win_id = self._get_active_id()
        if not win_id:
            return "Could not identify active window"
        try:
            subprocess.run(
                ["xdotool", "windowmove", win_id, "0", "0",
                 "windowsize", win_id, str(sw // 2), str(sh)],
                check=True, capture_output=True, timeout=5,
            )
            return "Window snapped to left"
        except Exception:
            return "Could not snap window left"

    def snap_right(self) -> str:
        if self.env.display_server == "wayland":
            return self._wayland_warning()
        err = self._need("xdotool")
        if err:
            return err
        sw, sh = self._screen_dims()
        win_id = self._get_active_id()
        if not win_id:
            return "Could not identify active window"
        try:
            subprocess.run(
                ["xdotool", "windowmove", win_id, str(sw // 2), "0",
                 "windowsize", win_id, str(sw // 2), str(sh)],
                check=True, capture_output=True, timeout=5,
            )
            return "Window snapped to right"
        except Exception:
            return "Could not snap window right"

    def list_windows(self) -> str:
        if self.env.display_server == "wayland":
            return self._wayland_warning()
        err = self._need("wmctrl")
        if err:
            return err
        try:
            out = subprocess.check_output(
                ["wmctrl", "-l"],
                text=True, stderr=subprocess.DEVNULL, timeout=5,
            )
            titles = []
            for line in out.strip().splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    title = parts[3].strip()
                    if title and title != "N/A":
                        titles.append(title)
            if not titles:
                return "No windows found"
            count  = len(titles)
            listed = ", ".join(titles[:5])
            suffix = f" and {count - 5} more" if count > 5 else ""
            return f"You have {count} window{'s' if count != 1 else ''} open: {listed}{suffix}"
        except Exception:
            return "Could not list windows"

    def _screen_dims(self):
        m = re.match(r"(\d+)x(\d+)", getattr(self.env, "screen_resolution", "") or "")
        return (int(m.group(1)), int(m.group(2))) if m else (1920, 1080)
