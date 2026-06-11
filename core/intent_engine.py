import re
from vello.nlp.normalizer import Normalizer
from vello.nlp.fuzzy_matcher import FuzzyMatcher

# Conversational filler that trails after the real command.
# Strip everything from these words onward before matching.
# "can you open VSCode because I want to code" → "can you open vscode"
_TRAILING_FILLER = re.compile(
    r'\s+(?:because|so\s+that|since|as\s+i|i\s+want\s+to|'
    r'if\s+you\s+can|if\s+possible|thanks?|thank\s+you)\b.*$',
    re.IGNORECASE,
)

# Leading conversational padding before the real verb.
# "hey can you please open firefox" → "open firefox"
_LEADING_FILLER = re.compile(
    r'^(?:hey[,\s]+)?(?:can\s+you\s+)?(?:please\s+)?(?:could\s+you\s+)?'
    r'(?:would\s+you\s+)?(?:go\s+ahead\s+and\s+)?',
    re.IGNORECASE,
)


def _strip_filler(text: str) -> str:
    """Remove conversational padding so intent patterns match cleanly."""
    text = _TRAILING_FILLER.sub("", text.strip())
    text = _LEADING_FILLER.sub("", text.strip())
    return text.strip()


class IntentEngine:
    """
    3-tier intent classifier:
      Tier 1 — Normalizer   (casual → clean phrase)
      Tier 2 — Rule-based   (fast, offline exact patterns)
      Tier 3 — Fuzzy        (keyword scoring safety net)
    Returns a plain string intent name.
    When context is provided (dict or VelloContext) the method
    also works — context is used only for active_app fallback.
    """

    APP_KEYWORDS = {
        "chrome":      ["chrome", "google chrome", "browser"],
        "google":      ["google", "search engine"],
        "terminal":    ["terminal", "shell", "console", "command line"],
        "vscode":      ["vscode", "vs code", "code editor", "visual studio code"],
        "calculator":  ["calculator"],
        "libreoffice": ["libreoffice", "office", "writer", "calc"],
        "files":       ["files", "file manager", "nautilus"],
        "vlc":         ["vlc", "media player"],
        "spotify":     ["spotify", "music player"],
    }

    def __init__(self):
        self.normalizer = Normalizer()
        self.fuzzy      = FuzzyMatcher()

    # ── Public API ─────────────────────────────────────────────────

    def classify(self, raw_text: str, context=None) -> str:
        """
        Classify raw speech into an intent string.
        context is optional — accepted for backward compatibility
        but the return is always a plain string intent name.
        """
        # Resolve context
        if hasattr(context, "get_context_summary"):
            ctx = context.get_context_summary()
        else:
            ctx = context or {}

        # --- TIER 1: Normalize casual speech ---
        normalized = self.normalizer.normalize(raw_text)
        # Strip conversational filler before rule matching
        stripped = _strip_filler(normalized)
        if stripped != normalized:
            print(f"[Intent] Filler stripped: '{normalized}' → '{stripped}'")
            normalized = stripped
        print(f"[Intent] Raw: '{raw_text}'")
        print(f"[Intent] Normalized: '{normalized}'")

        # Handle pure greeting
        if normalized == "__greeting__":
            print("[Intent] Rule match: greeting")
            return "greeting"

        # --- TIER 2: Rule-based matching ---
        intent = self._rule_match(normalized, ctx)
        if intent:
            print(f"[Intent] Rule match: {intent}")
            return intent

        # --- TIER 3: Fuzzy keyword scoring ---
        intent = self.fuzzy.match(normalized)
        if intent:
            print(f"[Intent] Fuzzy match: {intent}")
            return intent

        # Also try fuzzy on original raw text (catches missed normalizations)
        intent = self.fuzzy.match(raw_text.lower())
        if intent:
            print(f"[Intent] Fuzzy match (raw): {intent}")
            return intent

        # --- TIER 4: AI fallback ---
        print("[Intent] No match — AI fallback")
        return "ai_fallback"

    # ── Rule-based tier ────────────────────────────────────────────

    def _rule_match(self, text: str, ctx: dict = None) -> str:
        """
        Fast regex / substring matching on normalized text.
        Returns an intent string or empty string if no match.
        """
        cmd        = text.lower().strip()
        ctx        = ctx or {}
        active_app = ctx.get("active_app") or ""

        # ── MPRIS2 media control ──────────────────────────────────
        if re.search(r"\bnext\s+(?:track|song)\b|\bskip\b|\bskip\s+song\b", cmd):
            return "media_next"
        if re.search(r"\bprevious\s+(?:track|song)\b|\bgo\s+back\b"
                     r"|\blast\s+song\b|\bprev\b", cmd):
            return "media_previous"
        if re.search(r"\bwhat.s\s+playing\b|\bcurrent\s+song\b"
                     r"|\bnow\s+playing\b|\bwhat\s+is\s+playing\b", cmd):
            return "media_now_playing"
        if re.search(r"\btoggle\s+music\b|\bplay\s*pause\b|\bplaypause\b", cmd):
            return "media_playpause"

        # ── Music control (before exit so "stop music" ≠ quit) ───
        if re.search(r"\bstop\s+music\b|\bstop\s+playing\b", cmd):
            return "music_stop"
        if re.search(r"\bpause\s+music\b|\bpause\b", cmd):
            return "music_pause"
        if re.search(r"\bresume\s+music\b|\bresume\s+playing\b"
                     r"|\bresume\s+(?:the\s+)?(?:song|track|audio|playback)\b", cmd):
            return "music_resume"

        # ── Exit / goodbye ────────────────────────────────────────
        if any(w in cmd for w in ["goodbye", "bye", "quit"]):
            return "goodbye"
        # "exit" / "stop" only if not a system command context
        if re.search(r"\bexit\b|\bstop\b", cmd) and not re.search(
            r"\bstop\s+music\b|\bstop\s+playing\b", cmd
        ):
            return "goodbye"

        # ── Window management ─────────────────────────────────────
        if re.search(r"\bclose\s+(?:this\s+)?window\b|\bclose\s+this\b", cmd):
            return "window_close"
        if re.search(r"\bminimi[sz]e\b", cmd):
            return "window_minimize"
        if re.search(r"\bmaxi[ms]i[sz]e\b|\bmaximize\b|\bmaximise\b", cmd):
            return "window_maximize"
        if re.search(r"\bsnap\s+left\b|\bmove\s+window\s+left\b|\bwindow\s+left\b", cmd):
            return "window_snap_left"
        if re.search(r"\bsnap\s+right\b|\bmove\s+window\s+right\b|\bwindow\s+right\b", cmd):
            return "window_snap_right"
        if re.search(r"\blist\s+windows?\b|\bwhat\s+windows?\b|\bshow\s+windows?\b", cmd):
            return "window_list"

        # ── Package management ────────────────────────────────────
        if re.search(r"\binstall\b", cmd):
            return "package_install"
        if re.search(r"\buninstall\b|\bremove\s+package\b", cmd):
            return "package_remove"
        if re.search(r"\bupdate\s+system\b|\bupgrade\s+system\b|\bupdate\s+packages\b", cmd):
            return "system_update"

        # ── Reminders and timers ──────────────────────────────────
        if re.search(r"\bremind\s+me\b|\bset\s+a?\s*reminder\b", cmd):
            return "set_reminder"
        if re.search(r"\bset\s+a?\s*timer\b|\btimer\s+for\b", cmd):
            return "set_timer"
        if re.search(r"\blist\s+reminders\b|\bmy\s+reminders\b|\bwhat\s+are\s+my\s+reminders\b", cmd):
            return "list_reminders"

        # ── Network / Wi-Fi ───────────────────────────────────────
        if re.search(r"\bwifi\s+on\b|\bturn\s+on\s+wi.?fi\b|\benable\s+wi.?fi\b", cmd):
            return "wifi_on"
        if re.search(r"\bwifi\s+off\b|\bturn\s+off\s+wi.?fi\b|\bdisable\s+wi.?fi\b", cmd):
            return "wifi_off"
        if re.search(r"\blist\s+networks\b|\bavailable\s+networks\b|\bshow\s+wi.?fi\b|\bscan\s+wifi\b", cmd):
            return "list_networks"
        if re.search(r"\bconnect\s+to\b", cmd):
            return "connect_wifi"
        if re.search(r"\bmy\s+ip\b|\bip\s+address\b|\bwhat.s\s+my\s+ip\b", cmd):
            return "get_ip"
        if re.search(r"\bcheck\s+internet\b|\bam\s+i\s+connected\b|\binternet\s+connection\b", cmd):
            return "check_internet"

        # ── System info (extended) ────────────────────────────────
        if re.search(r"\bmemory\b|\bram\b|\bhow\s+much\s+ram\b", cmd):
            return "memory_usage"
        if re.search(r"\bdisk\b|\bstorage\b|\bhow\s+much\s+space\b|\bdisk\s+usage\b", cmd):
            return "disk_usage"
        if re.search(r"\btemperature\b|\bcpu\s+temp\b|\bhow\s+hot\b", cmd):
            return "temperature"
        if re.search(r"\bnetwork\s+usage\b|\bdata\s+usage\b|\bbandwidth\b", cmd):
            return "network_usage"
        if re.search(r"\buptime\b|\bhow\s+long\s+running\b|\bsystem\s+uptime\b", cmd):
            return "uptime"
        if re.search(r"\bprocesses\b|\bhow\s+many\s+processes\b|\brunning\s+processes\b", cmd):
            return "processes"

        # ── Clipboard ─────────────────────────────────────────────
        if re.search(r"\bclipboard\b|\bwhat\s+did\s+i\s+copy\b|\bread\s+clipboard\b|\bpaste\b", cmd):
            return "clipboard_read"
        if re.search(r"^copy\s+", cmd):
            return "clipboard_write"

        # ── File ops (before open_app / web_search to avoid collision) ──

        # Latest/newest download
        if re.search(
            r"\b(?:latest|last|newest|most\s+recent)\s+download\b"
            r"|\blast\s+(?:thing|file)\s+(?:i\s+)?downloaded\b"
            r"|\bwhat\s+did\s+i\s+(?:just\s+)?download\b"
            r"|\bopen\s+(?:my\s+)?(?:latest|newest|last)\s+download\b",
            cmd,
        ):
            return "latest_download"

        # Recent documents / files worked on
        if re.search(
            r"\brecent\s+(?:documents?|files?|stuff)\b"
            r"|\bfiles?\s+i\s+(?:worked\s+on|was\s+working\s+on|edited)\b"
            r"|\bwhat\s+(?:have\s+i|did\s+i)\s+(?:been\s+)?working\s+on\b"
            r"|\brecently\s+(?:modified|edited|changed)\s+files?\b",
            cmd,
        ):
            return "recent_docs"

        # Generic recent files
        if re.search(r"\brecent\s+files?\b|\bwhat\s+did\s+i\s+work\s+on\b", cmd):
            return "recent_files"

        # Open a specific file
        if re.search(
            r"\bopen\s+(?:my\s+|the\s+)?(?:file\s+)?\S+\.\S{2,5}\b"  # "open report.pdf"
            r"|\bopen\s+(?:my|the)\s+\w+\s+(?:file|document|pdf|video|image)\b"
            r"|\bshow\s+(?:me\s+)?(?:my\s+)?\S+\.\S{2,5}\b",
            cmd,
        ):
            return "open_file"

        # Find / locate a file
        if re.search(
            r"\bfind\s+(?:a\s+|my\s+|the\s+)?(?:file\b|pdf\b|photo\b|video\b|document\b)"
            r"|\bfind\s+my\s+\w+"          # "find my resume", "find my notes"
            r"|\bwhere\s+is\s+(?:my\s+)?\S+"
            r"|\blocate\s+\S+"
            r"|\bsearch\s+(?:for\s+)?(?:a\s+)?file\b",
            cmd,
        ):
            return "find_file"

        # ── Multi-step: "open X and do Y" ─────────────────────────
        if " and " in cmd:
            return self._handle_chain(cmd, ctx)

        # ── Folder / file open (before generic open_app) ──────────
        if re.search(
            r"\bopen\s+(?:my\s+)?(?:downloads?|documents?|desktop"
            r"|pictures?|music|videos?|home)\b"
            r"|\bopen\s+(?:the\s+)?(?:downloads?|documents?|desktop)\s+folder\b"
            r"|\bgo\s+to\b|\bopen\s+folder\b", cmd
        ):
            return "folder_open"
        if re.search(r"\bopen\s+(?:the\s+)?file\b|\bopen\s+\S+\.\S+\b", cmd):
            return "file_open"

        # ── Open apps ─────────────────────────────────────────────
        if re.search(r"\bopen\b|\blaunch\b|\bstart\b|\brun\b", cmd):
            return "open_app"

        # ── Time / date ───────────────────────────────────────────
        if re.search(r"\btime\b|\bwhat.s the time\b|\bwhat time\b|\bcurrent time\b", cmd):
            return "get_time"
        if re.search(r"\bdate\b|\bwhat.s the date\b|\bwhat day\b|\btoday.s date\b", cmd):
            return "get_date"

        # ── Volume control ────────────────────────────────────────
        if re.search(r"\bvolume\s+up\b|\bturn.*volume.*up\b", cmd):
            return "volume_up"
        if re.search(r"\bvolume\s+down\b|\bturn.*volume.*down\b", cmd):
            return "volume_down"
        if re.search(r"\bmute\b", cmd):
            return "mute"

        # ── Brightness control ────────────────────────────────────
        if re.search(r"\bbrightness\s+up\b|\bbrighter\b|\bincrease\s+brightness\b", cmd):
            return "brightness_up"
        if re.search(r"\bbrightness\s+down\b|\bdimmer\b|\bdecrease\s+brightness\b|\bdim\b", cmd):
            return "brightness_down"
        if re.search(r"\bset\s+brightness\s+to\b|\bbright(?:ness)?\s+to\b"
                     r"|\bbright(?:ness)?\s+\d+\b", cmd):
            return "brightness_set"
        if re.search(r"\bwhat.s\s+my\s+brightness\b|\bbright(?:ness)?\s+level\b"
                     r"|\bcheck\s+brightness\b", cmd):
            return "brightness_get"

        # ── Specific system actions ───────────────────────────────
        if re.search(r"\bscreenshot\b|\btake.*screen\b", cmd):
            return "screenshot"
        if re.search(r"\bbattery\b", cmd):
            return "battery"
        if re.search(r"\bcpu\b|\bprocessor\b", cmd):
            return "cpu_usage"
        if re.search(r"\bshutdown\b|\bshut\s+down\b|\bpower\s+off\b", cmd):
            return "shutdown"
        if re.search(r"\brestart\b|\breboot\b", cmd):
            return "restart"
        if re.search(r"\block\b", cmd):
            return "lock_screen"

        # ── Goals ─────────────────────────────────────────────────
        # Match both raw speech and post-normalizer text
        if re.search(
            r"\bi\s+want\s+to\s+(?:become|be|learn|master|get\s+into|start)\b"
            r"|\bmy\s+goal\s+is\b|\bset\s+(?:a\s+)?goal\b"
            r"|\bi\s+am\s+trying\s+to\b|\bi\s+'?m\s+trying\s+to\b"
            r"|\bi\s+want\s+to\s+achieve\b|\bhelp\s+me\s+become\b"
            r"|\bbecome\s+(?:a\s+|an\s+)?\w+\s*(?:engineer|developer|designer"
            r"|scientist|analyst|manager|architect|expert|professional)\b"
            r"|\blearn\s+(?:to\s+)?(?:code|program|python|ml|ai|machine\s+learning)\b"
            r"|\bmaster\s+\w+\b", cmd
        ):
            return "set_goal"
        if re.search(
            r"\blist\s+(?:my\s+)?goals?\b|\bshow\s+(?:my\s+)?goals?\b"
            r"|\bwhat\s+are\s+my\s+goals?\b|\bmy\s+goals?\b", cmd
        ):
            return "list_goals"
        if re.search(
            r"\bplan\s+for\b|\bcreate\s+(?:a\s+)?plan\b|\baction\s+plan\b"
            r"|\bhow\s+do\s+i\s+achieve\b|\bsteps\s+to\b|\broadmap\b", cmd
        ):
            return "goal_plan"
        if re.search(
            r"\bupdate\s+(?:my\s+)?goal\b|\bgoal\s+progress\b"
            r"|\bi\s+(?:finished|completed|done\s+with)\b", cmd
        ):
            return "update_goal"

        # ── User profile / Digital Twin ────────────────────────────
        if re.search(
            r"\bmy\s+name\s+is\b|\bcall\s+me\b|\bi\s+am\s+(?:a\s+)?(?:\w+)\s+"
            r"(?:developer|engineer|designer|student|manager|doctor|teacher|analyst)\b"
            r"|\bi\s+work\s+as\b|\bi\s+'?m\s+a\b.*(?:developer|engineer|student)\b", cmd
        ):
            return "update_profile"
        if re.search(
            r"\bwhat\s+do\s+you\s+know\s+about\s+me\b|\btell\s+me\s+about\s+myself\b"
            r"|\bdo\s+you\s+remember\s+me\b|\bmy\s+profile\b"
            r"|\bwhat\s+do\s+(?:about\s+)?me\b|\babout\s+me\b", cmd
        ):
            return "show_profile"

        # ── Long-term memory recall ────────────────────────────────
        if re.search(
            r"\bdo\s+you\s+remember\b|\bwhat\s+did\s+i\s+(?:tell|say|ask)\b"
            r"|\brecall\b|\bremember\s+when\b|\bwhat\s+did\s+we\s+talk\b", cmd
        ):
            return "recall_memory"

        # ── Research agent ─────────────────────────────────────────
        if re.search(
            r"\bresearch\b|\btell\s+me\s+about\b|\bexplain\b"
            r"|\bwhat\s+is\b|\bwhat\s+are\b|\bhow\s+does\b|\bhow\s+do\b"
            r"|\blearn\s+about\b|\bwho\s+is\b|\bwho\s+was\b"
            r"|\bcompare\b|\bdifference\s+between\b", cmd
        ):
            return "research"

        # ── Coding agent ───────────────────────────────────────────
        if re.search(
            r"\bhelp\s+me\s+(?:with\s+)?code\b|\bdebugg?\b|\bfix\s+(?:this|my|the)\s+(?:code|bug|error)\b"
            r"|\bexplain\s+this\s+code\b|\bhow\s+to\s+code\b|\bcoding\s+help\b"
            r"|\bwrite\s+(?:a\s+)?(?:function|class|script|program)\b"
            r"|\bcode\s+review\b|\bwhat\s+does\s+this\s+code\b", cmd
        ):
            return "coding_help"

        # ── Web search ────────────────────────────────────────────
        if any(w in cmd for w in ["search", "google", "look up", "find"]):
            return "web_search"

        # ── Play music ────────────────────────────────────────────
        if any(w in cmd for w in ["play", "song", "music", "put on"]):
            return "music_play"

        # ── Terminal commands ─────────────────────────────────────
        if any(w in cmd for w in
               ["run ", "execute ", "sudo ", "apt ", "ls ", "cd ", "mkdir "]):
            return "terminal_run"
        if active_app == "terminal" and len(cmd.split()) > 1:
            return "terminal_run"

        return ""  # No rule match — fall through to fuzzy

    # ── Chain handler ──────────────────────────────────────────────

    def _handle_chain(self, cmd: str, ctx: dict) -> str:
        """For chained commands like 'open chrome and search X',
        return the primary intent (router handles chaining separately)."""
        parts = cmd.split(" and ")
        return self._rule_match(parts[0].strip(), ctx) or "open_app"
