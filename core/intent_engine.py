import re

class IntentEngine:
    """
    Rule-based intent classifier — works fully offline, no API needed.
    Now with flexible keyword matching and multi-step support.
    """

    APP_KEYWORDS = {
        "chrome":      ["chrome", "google chrome", "browser"],
        "google":      ["google", "search engine"],
        "terminal":     ["terminal", "shell", "console", "command line"],
        "vscode":       ["vscode", "vs code", "code editor", "visual studio code"],
        "libreoffice":  ["libreoffice", "office", "writer", "calc"],
        "files":        ["files", "file manager", "nautilus"],
        "vlc":          ["vlc", "media player"],
        "spotify":      ["spotify", "music player"],
    }

    def classify(self, command, context):
        cmd = command.lower().strip()
        active_app = context.get("active_app") or ""

        # ── Goodbye / Exit ───────────────────────────────────────
        if any(w in cmd for w in ["goodbye", "bye", "exit", "stop", "quit"]):
            return {"intent": "exit", "app": None, "target": None, "chain": []}

        # ── Multi-step: "open X and do Y" ─────────────────────────
        if " and " in cmd:
            return self._handle_chain(cmd, context)

        # ── Open Apps (Flexible Matching) ──────────────────────────
        if "open" in cmd or "launch" in cmd or "start" in cmd:
            for app, keywords in self.APP_KEYWORDS.items():
                if any(kw in cmd for kw in keywords):
                    return {
                        "intent": "open_app",
                        "app":    app,
                        "target": None,
                        "chain":  []
                    }
            
            # Fallback for unknown apps
            target = re.sub(r"(open|launch|start)", "", cmd).strip()
            if target:
                return {"intent": "open_app", "app": target, "target": None, "chain": []}

        # ── System controls (Whole Word Matching) ─────────────────
        system_keywords = [
            "time", "date", "volume up", "volume down",
            "mute", "screenshot", "battery", "cpu",
            "shutdown", "shut down", "restart", "reboot", "lock"
        ]
        for kw in system_keywords:
            # Match whole word only to avoid 'update' matching 'date'
            if re.search(rf"\b{kw}\b", cmd):
                return {
                    "intent": "system_control",
                    "app":    None,
                    "target": kw,
                    "chain":  []
                }

        # ── Web search ────────────────────────────────────────────
        if any(w in cmd for w in ["search", "google", "look up", "find"]):
            query = re.sub(r"(search|google|look up|find|for)", "", cmd).strip()
            return {
                "intent": "search_web",
                "app":    active_app,
                "target": query if query else None,
                "chain":  []
            }

        # ── Play music ────────────────────────────────────────────
        if any(w in cmd for w in ["play", "song", "music"]):
            song = re.sub(r"(play|song|music|on youtube)", "", cmd).strip()
            return {
                "intent": "play_music",
                "app":    active_app,
                "target": song if song else None,
                "chain":  []
            }

        # ── Terminal Command detection (More Specific) ─────────────
        # Only if "run" or "execute" is used, OR if terminal is active AND it looks like a command
        is_terminal_command = any(w in cmd for w in ["run ", "execute ", "sudo ", "apt ", "ls ", "cd ", "mkdir "])
        
        if is_terminal_command or (active_app == "terminal" and len(cmd.split()) > 1):
            target = re.sub(r"(run|execute|command)", "", cmd).strip()
            if target:
                return {
                    "intent": "terminal_run",
                    "app":    "terminal",
                    "target": target,
                    "chain":  []
                }

        # ── Fallback → AI ─────────────────────────────────────────
        return {
            "intent": "ask_ai",
            "app":    None,
            "target": None,
            "chain":  []
        }

    def _handle_chain(self, cmd, context):
        """
        Handles: 'open chrome and play believer on youtube'
        """
        parts = cmd.split(" and ")
        first = self.classify(parts[0].strip(), context)
        chain = []

        for part in parts[1:]:
            step = self.classify(part.strip(), context)
            chain.append({
                "intent": step["intent"],
                "app":    step.get("app"),
                "target": step.get("target")
            })

        first["chain"] = chain
        return first