"""MPRIS2 D-Bus media controller — works with Spotify, VLC, Rhythmbox, Chrome, etc."""
import subprocess
import re
import logging

logger = logging.getLogger(__name__)


class DBusMediaController:
    """Control any MPRIS2-compatible media player via D-Bus."""

    _LIST_NAMES_CMD = [
        "dbus-send", "--session", "--print-reply",
        "--dest=org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus.ListNames",
    ]

    def __init__(self, environment):
        self.env       = environment
        self.available = self._check_dbus()

    def _check_dbus(self) -> bool:
        try:
            result = subprocess.run(
                self._LIST_NAMES_CMD,
                capture_output=True, timeout=3,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_active_player(self) -> str | None:
        try:
            result = subprocess.run(
                self._LIST_NAMES_CMD,
                capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.splitlines():
                if "org.mpris.MediaPlayer2." in line:
                    m = re.search(r'"(org\.mpris\.MediaPlayer2\.[^"]+)"', line)
                    if m:
                        return m.group(1)
        except Exception as e:
            logger.warning("_get_active_player error: %s", e)
        return None

    def _mpris_call(self, player: str, method: str) -> bool:
        try:
            result = subprocess.run(
                [
                    "dbus-send", "--session", "--print-reply",
                    f"--dest={player}",
                    "/org/mpris/MediaPlayer2",
                    f"org.mpris.MediaPlayer2.Player.{method}",
                ],
                capture_output=True, timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning("_mpris_call %s error: %s", method, e)
            return False

    def play_pause(self) -> str:
        if not self.available:
            return "D-Bus media control not available"
        player = self._get_active_player()
        if not player:
            return "No media player found running"
        return "Toggled playback" if self._mpris_call(player, "PlayPause") \
            else "Could not toggle playback"

    def stop(self) -> str:
        if not self.available:
            return "D-Bus media control not available"
        player = self._get_active_player()
        if not player:
            return "No media player found running"
        return "Stopped playback" if self._mpris_call(player, "Stop") \
            else "Could not stop playback"

    def next_track(self) -> str:
        if not self.available:
            return "D-Bus media control not available"
        player = self._get_active_player()
        if not player:
            return "No media player found running"
        return "Skipped to next track" if self._mpris_call(player, "Next") \
            else "Could not skip track"

    def previous_track(self) -> str:
        if not self.available:
            return "D-Bus media control not available"
        player = self._get_active_player()
        if not player:
            return "No media player found running"
        return "Going back to previous track" \
            if self._mpris_call(player, "Previous") \
            else "Could not go back"

    def get_now_playing(self) -> str:
        if not self.available:
            return "D-Bus media control not available"
        player = self._get_active_player()
        if not player:
            return "Nothing is playing"
        try:
            result = subprocess.run(
                [
                    "dbus-send", "--session", "--print-reply",
                    f"--dest={player}",
                    "/org/mpris/MediaPlayer2",
                    "org.freedesktop.DBus.Properties.Get",
                    "string:org.mpris.MediaPlayer2.Player",
                    "string:Metadata",
                ],
                capture_output=True, text=True, timeout=5,
            )
            output  = result.stdout
            title_m  = re.search(r'xesam:title[^"]*"([^"]+)"', output)
            artist_m = re.search(r'xesam:artist[^"]*"([^"]+)"', output)
            if title_m:
                title  = title_m.group(1)
                artist = artist_m.group(1) if artist_m else None
                return f"Playing {title} by {artist}" if artist \
                    else f"Playing {title}"
        except Exception as e:
            logger.warning("get_now_playing error: %s", e)
        return "Nothing is playing"
