import datetime
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Vello, a helpful AI assistant running on Ubuntu Linux. "
    "Keep your answers short and clear since they will be spoken aloud. "
    "When the user refers to previous questions, use that context to give "
    "a coherent follow-up answer."
)


class VelloContext:
    """
    Unified context — tracks system state (active app, pending action)
    AND conversation history for GPT multi-turn exchanges.
    """

    def __init__(self, window: int = 5):
        # System state (replaces old ContextManager)
        self.active_app    = None
        self.active_task   = None
        self.pending_action = None
        self.last_subject  = None

        # Conversation history for GPT (also used by tests as ctx.history)
        self.history: list[dict] = []
        self.window = window

        # Action history (last N intents for context-aware routing)
        self._action_log: list[str] = []

    # ── System state helpers (backward-compatible with ContextManager) ──

    def set_app(self, app_name: str):
        self.active_app  = app_name.lower()
        self.active_task = None
        self._action_log.append(f"opened:{app_name}")
        self.last_subject = app_name

    def set_task(self, task: str):
        self.active_task = task.lower()
        self._action_log.append(f"task:{task}")

    def set_pending(self, action: str):
        self.pending_action = action

    def clear_pending(self):
        self.pending_action = None

    def get_context_summary(self) -> dict:
        return {
            "active_app":  self.active_app,
            "active_task": self.active_task,
            "pending":     self.pending_action,
            "recent":      self._action_log[-5:] if self._action_log else [],
        }

    def reset(self):
        self.active_app    = None
        self.active_task   = None
        self.pending_action = None
        self.clear()

    # ── Conversation history ─────────────────────────────────────

    def add(self, intent: str, command: str, result: str,
            timestamp=None):
        """Record a completed exchange."""
        self.history.append({
            "intent":    intent,
            "command":   command,
            "result":    result,
            "timestamp": timestamp or datetime.datetime.now().isoformat(),
        })
        # Trim to window
        if len(self.history) > self.window:
            self.history = self.history[-self.window:]
        self.last_subject = command

    def last_intent(self) -> str | None:
        return self.history[-1]["intent"] if self.history else None

    def last_command(self) -> str | None:
        return self.history[-1]["command"] if self.history else None

    def last_result(self) -> str | None:
        return self.history[-1]["result"] if self.history else None

    def build_gpt_messages(self, new_query: str) -> list[dict]:
        """Build OpenAI-style message list with up to last 3 exchanges."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for ex in self.history[-3:]:
            messages.append({"role": "user",      "content": ex["command"]})
            messages.append({"role": "assistant", "content": ex["result"]})
        messages.append({"role": "user", "content": new_query})
        return messages

    def clear(self):
        self.history      = []
        self._action_log  = []
        self.last_subject = None
