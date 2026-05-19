import subprocess
import logging

logger = logging.getLogger(__name__)


class ClipboardController:
    """Read/write clipboard — supports both X11 (xclip) and Wayland (wl-clipboard)."""

    def __init__(self, environment):
        self.display = environment.display_server
        self._caps   = environment.capabilities

    def read(self) -> str:
        try:
            if self.display == "wayland" and "wl-paste" in self._caps:
                return subprocess.check_output(
                    ["wl-paste", "--no-newline"],
                    text=True, stderr=subprocess.DEVNULL
                ).strip()
            if "xclip" in self._caps:
                return subprocess.check_output(
                    ["xclip", "-o", "-selection", "clipboard"],
                    text=True, stderr=subprocess.DEVNULL
                ).strip()
            return ""
        except Exception as e:
            logger.warning("clipboard read error: %s", e)
            return ""

    def write(self, text: str) -> str:
        try:
            if self.display == "wayland" and "wl-copy" in self._caps:
                proc = subprocess.Popen(
                    ["wl-copy"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.communicate(input=text.encode())
            elif "xclip" in self._caps:
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                proc.communicate(input=text.encode())
            else:
                return "Clipboard tool not available. Install xclip or wl-clipboard."
            preview = text[:50] + ("..." if len(text) > 50 else "")
            return f"Copied to clipboard: {preview}"
        except Exception as e:
            logger.warning("clipboard write error: %s", e)
            return "Could not write to clipboard"
