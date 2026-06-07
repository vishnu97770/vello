"""Window management — X11 (wmctrl/xdotool) and Wayland (swaymsg/gdbus/ydotool)."""
import json
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
        self.swaymsg = shutil.which("swaymsg")
        self.ydotool = shutil.which("ydotool")
        self.gdbus   = shutil.which("gdbus")

        is_x11     = environment.display_server == "x11"
        is_wayland = environment.display_server == "wayland"

        self.available = (
            (is_x11 and bool(self.wmctrl or self.xdotool)) or
            (is_wayland and bool(self.swaymsg or self.ydotool or self.gdbus))
        )

    # ── Internal helpers ───────────────────────────────────────────

    def _is_sway(self) -> bool:
        """Detect Sway compositor via env var or swaymsg availability."""
        import os
        return bool(
            os.environ.get("SWAYSOCK") or
            (self.swaymsg and self._sway_cmd("nop"))
        )

    def _sway_cmd(self, cmd: str) -> bool:
        if not self.swaymsg:
            return False
        try:
            subprocess.run(
                ["swaymsg", cmd],
                check=True, capture_output=True, timeout=5,
            )
            return True
        except Exception:
            return False

    def _ydotool_key(self, *keys: str) -> bool:
        """Send key combo via ydotool (Wayland-native input simulation)."""
        if not self.ydotool:
            return False
        try:
            subprocess.run(
                ["ydotool", "key"] + list(keys),
                check=True, capture_output=True, timeout=5,
            )
            return True
        except Exception:
            return False

    def _gdbus_eval(self, js: str) -> bool:
        """Run JS in GNOME Shell via gdbus (GNOME Wayland only)."""
        if not self.gdbus:
            return False
        try:
            subprocess.run(
                [
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.Shell",
                    "--object-path", "/org/gnome/Shell",
                    "--method", "org.gnome.Shell.Eval", js,
                ],
                check=True, capture_output=True, timeout=5,
            )
            return True
        except Exception:
            return False

    def _get_active_id(self) -> str | None:
        try:
            out = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                text=True, stderr=subprocess.DEVNULL, timeout=3,
            )
            return out.strip()
        except Exception:
            return None

    def _screen_dims(self):
        m = re.match(r"(\d+)x(\d+)", getattr(self.env, "screen_resolution", "") or "")
        return (int(m.group(1)), int(m.group(2))) if m else (1920, 1080)

    def _need(self, tool: str) -> str | None:
        if not shutil.which(tool):
            return f"{tool} not installed. Run: sudo apt install {tool}"
        return None

    def _no_wayland_tool(self) -> str:
        return (
            "Window control on Wayland needs swaymsg (Sway) or ydotool. "
            "Install ydotool: sudo apt install ydotool — then start ydotoold."
        )

    # ── Public API — each method tries Wayland then X11 ───────────

    def close_window(self) -> str:
        if self.env.display_server == "wayland":
            if self._is_sway() and self._sway_cmd("kill"):
                return "Window closed"
            if self._gdbus_eval(
                "global.display.focus_window.delete(global.get_current_time())"
            ):
                return "Window closed"
            if self._ydotool_key("alt+F4"):
                return "Window closed"
            return self._no_wayland_tool()

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
            # Sway: move focused window to scratchpad (equivalent of minimize)
            if self._is_sway() and self._sway_cmd("move scratchpad"):
                return "Window minimized"
            if self._gdbus_eval("global.display.focus_window.minimize()"):
                return "Window minimized"
            # GNOME default minimize shortcut: Super+H
            if self._ydotool_key("super+h"):
                return "Window minimized"
            return self._no_wayland_tool()

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
            if self._is_sway() and self._sway_cmd("fullscreen toggle"):
                return "Window maximized"
            if self._gdbus_eval(
                "global.display.focus_window.maximize(Meta.MaximizeFlags.BOTH)"
            ):
                return "Window maximized"
            if self._ydotool_key("super+Up"):
                return "Window maximized"
            return self._no_wayland_tool()

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
            if self._is_sway() and self._sway_cmd("move left"):
                return "Window snapped to left"
            if self._ydotool_key("super+Left"):
                return "Window snapped to left"
            return self._no_wayland_tool()

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
            if self._is_sway() and self._sway_cmd("move right"):
                return "Window snapped to right"
            if self._ydotool_key("super+Right"):
                return "Window snapped to right"
            return self._no_wayland_tool()

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
            # Sway: parse window tree
            if self._is_sway() and self.swaymsg:
                try:
                    out = subprocess.check_output(
                        ["swaymsg", "-t", "get_tree"],
                        text=True, stderr=subprocess.DEVNULL, timeout=5,
                    )
                    tree  = json.loads(out)
                    titles = _extract_sway_titles(tree)
                    if titles:
                        count  = len(titles)
                        listed = ", ".join(titles[:5])
                        suffix = f" and {count - 5} more" if count > 5 else ""
                        return (f"You have {count} window"
                                f"{'s' if count != 1 else ''} open: "
                                f"{listed}{suffix}")
                    return "No windows found"
                except Exception:
                    pass

            # GNOME Wayland: wmctrl still works for XWayland apps
            if self.wmctrl:
                return self._list_via_wmctrl()

            return self._no_wayland_tool()

        return self._list_via_wmctrl()

    def _list_via_wmctrl(self) -> str:
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
            return (f"You have {count} window{'s' if count != 1 else ''} "
                    f"open: {listed}{suffix}")
        except Exception:
            return "Could not list windows"


def _extract_sway_titles(node: dict, titles: list | None = None) -> list:
    """Recursively pull visible window titles from a Sway tree JSON."""
    if titles is None:
        titles = []
    name = node.get("name") or ""
    type_ = node.get("type", "")
    if type_ == "con" and name and name != "root":
        titles.append(name)
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        _extract_sway_titles(child, titles)
    return titles
