import re
import subprocess
import logging
import datetime
from datetime import timedelta

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed — reminders disabled. "
                   "Run: pip install APScheduler")


class ReminderSystem:
    """Set voice reminders and timers using APScheduler."""

    def __init__(self, speak_callback):
        self.speak     = speak_callback
        self.reminders = {}
        self._counter  = 0
        self._enabled  = _HAS_APSCHEDULER

        if self._enabled:
            self.scheduler = BackgroundScheduler()
            self.scheduler.start()
        else:
            self.scheduler = None

    # ── Public API ────────────────────────────────────────────────

    def set_reminder(self, command: str) -> str:
        if not self._enabled:
            return "Reminders are not available. Install APScheduler."
        delta = self.parse_time(command)
        if delta is None:
            return ("I didn't understand the time. "
                    "Say something like: remind me in 10 minutes")
        message = self.parse_message(command)
        run_at  = datetime.datetime.now() + delta
        rid     = self._next_id()
        self.scheduler.add_job(
            self._fire, "date", run_date=run_at,
            args=[message], id=rid,
        )
        self.reminders[rid] = {"message": message, "run_at": run_at}
        amount, unit = self._describe_delta(delta)
        return f"Reminder set for {amount} {unit}: {message}"

    def set_timer(self, command: str) -> str:
        if not self._enabled:
            return "Timers are not available. Install APScheduler."
        delta = self.parse_time(command)
        if delta is None:
            return ("I didn't understand the time. "
                    "Say something like: set a timer for 5 minutes")
        run_at = datetime.datetime.now() + delta
        rid    = self._next_id()
        self.scheduler.add_job(
            self._fire, "date", run_date=run_at,
            args=["Timer done!"], id=rid,
        )
        self.reminders[rid] = {"message": "Timer done!", "run_at": run_at}
        amount, unit = self._describe_delta(delta)
        return f"Timer set for {amount} {unit}"

    def list_reminders(self) -> str:
        if not self.reminders:
            return "You have no pending reminders"
        now   = datetime.datetime.now()
        parts = []
        for rid, info in self.reminders.items():
            delta = info["run_at"] - now
            secs  = int(delta.total_seconds())
            if secs > 0:
                parts.append(f"{info['message']} in {self._secs_to_text(secs)}")
        if not parts:
            return "No upcoming reminders"
        return "Your reminders: " + ". ".join(parts)

    # ── Internals ─────────────────────────────────────────────────

    def _fire(self, message: str):
        self.speak(message)
        try:
            subprocess.run(["notify-send", "Vello Reminder", message],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def parse_time(self, text: str) -> timedelta | None:
        text = text.lower()
        patterns = [
            (r"(\d+)\s*second",  "seconds"),
            (r"(\d+)\s*minute",  "minutes"),
            (r"(\d+)\s*hour",    "hours"),
        ]
        for pattern, unit in patterns:
            m = re.search(pattern, text)
            if m:
                n = int(m.group(1))
                return timedelta(**{unit: n})
        return None

    def parse_message(self, text: str) -> str:
        m = re.search(r"\bto\b(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return "reminder"

    def _describe_delta(self, delta: timedelta) -> tuple[int, str]:
        secs = int(delta.total_seconds())
        if secs < 60:
            return secs, "seconds"
        if secs < 3600:
            return secs // 60, "minutes"
        return secs // 3600, "hours"

    def _secs_to_text(self, secs: int) -> str:
        if secs < 60:   return f"{secs} seconds"
        if secs < 3600: return f"{secs // 60} minutes"
        return f"{secs // 3600} hours"

    def _next_id(self) -> str:
        self._counter += 1
        return f"vello_reminder_{self._counter}"
