import re


class IntentEngine:
    """
    Rule-based intent classifier — works fully offline, no API needed.
    """

    def classify(self, command, context):

        cmd        = command.lower().strip()
        active_app = context.get("active_app") or ""

        # ── Multi-step: "open X and do Y" ─────────────────────────
        if " and " in cmd:
            return self._handle_chain(cmd, context)

        # ── Open ──────────────────────────────────────────────────
        if cmd.startswith("open "):
            target = cmd.replace("open", "").strip()

            # Websites
            websites = [
                "youtube", "google", "github", "gmail",
                "instagram", "twitter", "facebook", "linkedin",
                "stackoverflow", "wikipedia", "netflix", "reddit"
            ]
            for site in websites:
                if site in target:
                    return {
                        "intent": "open_url",
                        "app":    active_app,
                        "target": f"https://www.{site}.com",
                        "chain":  []
                    }

            # Known apps
            apps = [
                "chrome", "firefox", "terminal", "vscode",
                "vs code", "files", "calculator", "settings",
                "vlc", "spotify", "discord", "zoom",
                "telegram", "notepad", "gedit", "file manager"
            ]
            for app in apps:
                if app in target:
                    return {
                        "intent": "open_app",
                        "app":    app,
                        "target": None,
                        "chain":  []
                    }

            # Folder
            if "folder" in target:
                folder = target.replace("folder", "").strip()
                return {
                    "intent": "open_folder",
                    "app":    active_app,
                    "target": folder if folder else None,
                    "chain":  []
                }

            # File
            if "file" in target:
                file_name = target.replace("file", "").strip()
                return {
                    "intent": "open_file",
                    "app":    active_app,
                    "target": file_name if file_name else None,
                    "chain":  []
                }

            # Unknown — try running directly
            return {
                "intent": "open_app",
                "app":    target,
                "target": None,
                "chain":  []
            }

        # ── Play music ────────────────────────────────────────────
        if any(w in cmd for w in ["play ", "play song", "play music"]):
            song = re.sub(r"play (song |music )?", "", cmd).strip()
            return {
                "intent": "play_music",
                "app":    active_app,
                "target": song if song else None,
                "chain":  []
            }

        # ── YouTube ───────────────────────────────────────────────
        if "youtube" in cmd:
            query = re.sub(r"(youtube|search|play|open|on)", "", cmd).strip()
            return {
                "intent": "play_music",
                "app":    active_app,
                "target": query if query else None,
                "chain":  []
            }

        # ── Web search ────────────────────────────────────────────
        if any(w in cmd for w in ["search ", "google ", "look up "]):
            query = re.sub(r"(search|google|look up)", "", cmd).strip()
            return {
                "intent": "search_web",
                "app":    active_app,
                "target": query if query else None,
                "chain":  []
            }

        # ── System controls ───────────────────────────────────────
        system_keywords = [
            "time", "date", "volume up", "volume down",
            "mute", "screenshot", "battery", "cpu",
            "shutdown", "shut down", "restart", "reboot", "lock"
        ]
        for kw in system_keywords:
            if kw in cmd:
                return {
                    "intent": "system_control",
                    "app":    None,
                    "target": kw,
                    "chain":  []
                }

        # ── Close app ─────────────────────────────────────────────
        if cmd.startswith("close "):
            app = cmd.replace("close", "").strip()
            return {
                "intent": "close_app",
                "app":    app,
                "target": None,
                "chain":  []
            }

        # ── Context-aware follow-ups (browser active) ─────────────
        if active_app in ["chrome", "firefox", "browser"]:
            websites = [
                "youtube", "google", "github", "gmail",
                "instagram", "twitter", "facebook", "netflix"
            ]
            for site in websites:
                if site in cmd:
                    return {
                        "intent": "open_url",
                        "app":    active_app,
                        "target": f"https://www.{site}.com",
                        "chain":  []
                    }

        # ── Fallback → AI ─────────────────────────────────────────
        return {
            "intent": "ask_ai",
            "app":    None,
            "target": None,
            "chain":  []
        }

    # ── CHAIN HANDLER ─────────────────────────────────────────────

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
    