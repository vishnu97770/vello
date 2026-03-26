class ContextManager:
    """
    Tracks the current active application and session state.
    """

    def __init__(self):
        self.active_app = None        # e.g. "chrome", "vscode"
        self.active_task = None       # e.g. "youtube", "search"
        self.pending_action = None    # waiting for user input
        self.history = []             # last N actions

    def set_app(self, app_name):
        self.active_app = app_name.lower()
        self.active_task = None
        self.history.append(f"opened:{app_name}")

    def set_task(self, task):
        self.active_task = task.lower()
        self.history.append(f"task:{task}")

    def set_pending(self, action):
        """Set when we are waiting for user to clarify something."""
        self.pending_action = action

    def clear_pending(self):
        self.pending_action = None

    def get_context_summary(self):
        return {
            "active_app":    self.active_app,
            "active_task":   self.active_task,
            "pending":       self.pending_action,
            "recent":        self.history[-5:] if self.history else []
        }

    def reset(self):
        self.active_app = None
        self.active_task = None
        self.pending_action = None