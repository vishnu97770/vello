import shutil
import signal
import subprocess
import webbrowser
import logging

logger = logging.getLogger(__name__)


class MusicPlayer:
    """Real audio playback via mpv + yt-dlp, with browser fallback."""

    def __init__(self, environment):
        self._process      = None
        self.current_track = None
        self._has_mpv      = environment.is_tool_available("mpv")
        self._has_ytdlp    = environment.is_tool_available("yt-dlp")
        self.mpv_available  = self._has_mpv
        self.ytdlp_available = self._has_ytdlp
        self.can_play      = self._has_mpv and self._has_ytdlp

        if not self.can_play:
            missing = []
            if not self._has_mpv:   missing.append("mpv")
            if not self._has_ytdlp: missing.append("yt-dlp")
            logger.warning("Music playback limited — missing: %s", missing)

    def play(self, query: str) -> str:
        if not query:
            return "What song should I play?"

        self.stop()

        if self.can_play:
            self._process = subprocess.Popen(
                ["mpv", "--no-video", "--really-quiet",
                 f"ytdl://ytsearch1:{query}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.current_track = query
            return f"Playing {query}"
        else:
            webbrowser.open(
                f"https://www.youtube.com/results?search_query="
                f"{query.replace(' ', '+')}"
            )
            return (
                f"mpv or yt-dlp not found. Opening YouTube in browser instead. "
                f"Install mpv and yt-dlp for real playback."
            )

    def stop(self) -> str:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process      = None
        self.current_track = None
        return "Music stopped"

    def pause(self) -> str:
        if self._process and self._process.poll() is None:
            self._process.send_signal(signal.SIGSTOP)
            return "Music paused"
        return "Nothing is playing"

    def resume(self) -> str:
        if self._process and self._process.poll() is None:
            self._process.send_signal(signal.SIGCONT)
            return "Music resumed"
        return "Nothing to resume"

    def is_playing(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def status(self) -> str:
        if self.is_playing():
            return f"Currently playing: {self.current_track}"
        return "Nothing is playing right now"
