import threading
import datetime
import logging

logger = logging.getLogger(__name__)


class ProactiveEngine:
    """
    Runs in the background and queues proactive suggestions.
    The main loop calls pop_suggestion() and speaks any pending message.

    Triggers
    --------
    08:00–09:00  Morning briefing — active goals + day framing
    12:00–13:00  Midday nudge    — goal progress reminder
    18:00–19:00  Evening wrap-up — summary + reflection prompt
    """

    CHECK_INTERVAL = 300  # seconds between background ticks (5 min)

    def __init__(self, profile=None, memory=None):
        self.profile  = profile
        self.memory   = memory
        self._stop    = threading.Event()
        self._thread  = None
        self._queue: list[str] = []
        self._fired_today: set[str] = set()
        self._last_date: str | None = None

    # ── Public API ────────────────────────────────────────────────

    def start(self):
        """Launch background thread."""
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="VelloProactive",
        )
        self._thread.start()
        logger.info("ProactiveEngine started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def pop_suggestion(self) -> str | None:
        """Return and remove the next pending suggestion, or None."""
        return self._queue.pop(0) if self._queue else None

    # ── Background loop ───────────────────────────────────────────

    def _run(self):
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.warning("ProactiveEngine tick error: %s", e)
            self._stop.wait(self.CHECK_INTERVAL)

    def _tick(self):
        now  = datetime.datetime.now()
        date = now.strftime("%Y-%m-%d")

        # Reset fired set on a new day
        if date != self._last_date:
            self._fired_today.clear()
            self._last_date = date

        hour = now.hour

        if 8 <= hour < 9 and "morning" not in self._fired_today:
            msg = self._morning_briefing()
            if msg:
                self._queue.append(msg)
                self._fired_today.add("morning")

        if 12 <= hour < 13 and "midday" not in self._fired_today:
            msg = self._midday_nudge()
            if msg:
                self._queue.append(msg)
                self._fired_today.add("midday")

        if 18 <= hour < 19 and "evening" not in self._fired_today:
            msg = self._evening_wrap()
            if msg:
                self._queue.append(msg)
                self._fired_today.add("evening")

    # ── Message builders ─────────────────────────────────────────

    def _morning_briefing(self) -> str | None:
        if not self.profile:
            return None
        goals = self.profile.get_active_goals()
        name  = self.profile.name or ""
        greeting = f"Good morning{', ' + name if name else ''}!"
        if not goals:
            return (
                f"{greeting} You have no active goals yet. "
                "Tell me what you want to achieve today."
            )
        top  = goals[0]
        pct  = top.get("progress", 0)
        return (
            f"{greeting} Today's focus: {top['title']}, currently at {pct} percent. "
            f"You have {len(goals)} active goal(s) in total. "
            "Say 'plan for' followed by your goal to get started."
        )

    def _midday_nudge(self) -> str | None:
        if not self.profile:
            return None
        goals = self.profile.get_active_goals()
        if not goals:
            return None
        behind = [g for g in goals if g.get("progress", 0) < 50]
        if not behind:
            return None
        g = behind[0]
        return (
            f"Midday check-in: '{g['title']}' is at {g.get('progress', 0)} percent. "
            "Would you like to work on it now? "
            "Say 'plan for' followed by the goal name."
        )

    def _evening_wrap(self) -> str | None:
        if not self.profile:
            return None
        goals = self.profile.get_active_goals()
        if not goals:
            return None
        return (
            f"Evening wrap-up: you have {len(goals)} active goal(s). "
            "Say 'list my goals' for a full update, "
            "or tell me what you accomplished today."
        )
