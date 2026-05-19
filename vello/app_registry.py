import os
import glob
import shutil
import logging
import configparser

logger = logging.getLogger(__name__)

_DESKTOP_PATHS = [
    "/usr/share/applications/*.desktop",
    os.path.expanduser("~/.local/share/applications/*.desktop"),
]

_ALIASES = {
    "browser":  ["google-chrome", "firefox", "chromium-browser", "brave-browser"],
    "editor":   ["code", "gedit", "nano", "kate"],
    "terminal": ["gnome-terminal", "xterm", "konsole", "xfce4-terminal"],
    "files":    ["nautilus", "dolphin", "thunar", "nemo"],
}

_registry: dict = {}
_mtime_snapshot: dict = {}


def _clean_exec(exec_str: str) -> str:
    """Strip field codes and extra whitespace from Exec= value."""
    idx = exec_str.find("%")
    if idx != -1:
        exec_str = exec_str[:idx]
    return exec_str.strip().split()[0] if exec_str.strip() else ""


def _resolve_alias(key: str) -> str | None:
    candidates = _ALIASES.get(key, [])
    for cmd in candidates:
        if shutil.which(cmd):
            return cmd
    return None


def build_app_registry() -> dict:
    """Scan .desktop files and build name→command mapping."""
    global _registry, _mtime_snapshot
    reg = {}

    for pattern in _DESKTOP_PATHS:
        for path in glob.glob(pattern):
            try:
                mtime = os.path.getmtime(path)
                _mtime_snapshot[path] = mtime

                cfg = configparser.ConfigParser(strict=False,
                                                interpolation=None)
                cfg.read(path, encoding="utf-8")

                if not cfg.has_section("Desktop Entry"):
                    continue
                entry = cfg["Desktop Entry"]

                # Skip non-application entries
                if entry.get("Type", "") != "Application":
                    continue
                if entry.get("NoDisplay", "false").lower() == "true":
                    continue

                exec_val = entry.get("Exec", "").strip()
                cmd = _clean_exec(exec_val)
                if not cmd:
                    continue

                # Map name variants
                for field in ["Name", "GenericName"]:
                    val = entry.get(field, "").strip().lower()
                    if val:
                        reg[val] = cmd

                # Map keywords
                keywords = entry.get("Keywords", "")
                for kw in keywords.replace(";", " ").split():
                    kw = kw.strip().lower()
                    if kw:
                        reg[kw] = cmd

            except Exception as e:
                logger.debug("Skipped %s: %s", path, e)

    # Resolve common aliases on top
    for alias, _ in _ALIASES.items():
        resolved = _resolve_alias(alias)
        if resolved:
            reg[alias] = resolved

    _registry = reg
    logger.info("App registry built: %d entries", len(reg))
    return reg


def _needs_rebuild() -> bool:
    for pattern in _DESKTOP_PATHS:
        for path in glob.glob(pattern):
            try:
                if os.path.getmtime(path) != _mtime_snapshot.get(path):
                    return True
            except OSError:
                pass
    return False


def find_app(query: str) -> str | None:
    """Fuzzy lookup: exact → starts-with → contains. Returns exec cmd or None."""
    global _registry
    if not _registry or _needs_rebuild():
        build_app_registry()

    q = query.lower().strip()

    # 1. Exact
    if q in _registry:
        return _registry[q]

    # 2. Starts-with
    for name, cmd in _registry.items():
        if name.startswith(q):
            return cmd

    # 3. Contains
    for name, cmd in _registry.items():
        if q in name:
            return cmd

    return None
