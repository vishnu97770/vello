"""File search and folder operations."""
import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

FOLDER_MAP = {
    "home":       "~",
    "downloads":  "~/Downloads",
    "download":   "~/Downloads",
    "documents":  "~/Documents",
    "document":   "~/Documents",
    "desktop":    "~/Desktop",
    "pictures":   "~/Pictures",
    "picture":    "~/Pictures",
    "music":      "~/Music",
    "videos":     "~/Videos",
    "video":      "~/Videos",
}


class FileOps:

    def __init__(self, environment):
        self.env  = environment
        self.fd   = shutil.which("fd")
        self.find = shutil.which("find")

    def search_files(self, query: str) -> str:
        if not query:
            return "What file should I search for?"
        home = os.path.expanduser("~")
        try:
            if self.fd:
                result = subprocess.run(
                    ["fd", "--type", "f", query, home],
                    capture_output=True, text=True, timeout=10,
                )
            else:
                result = subprocess.run(
                    ["find", home, "-type", "f",
                     "-iname", f"*{query}*",
                     "-not", "-path", "*/.*"],
                    capture_output=True, text=True, timeout=10,
                )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if not lines:
                return f"No files found matching {query}"
            top5      = lines[:5]
            basenames = [os.path.basename(p) for p in top5]
            count     = len(lines)
            listed    = ", ".join(basenames)
            suffix    = f" and {count - 5} more" if count > 5 else ""
            return (f"Found {count} file{'s' if count != 1 else ''}: "
                    f"{listed}{suffix}")
        except subprocess.TimeoutExpired:
            return "File search timed out. Try a more specific name."
        except Exception as e:
            logger.warning("search_files error: %s", e)
            return "Could not search files"

    def open_file(self, filename: str) -> str:
        if not filename:
            return "Which file should I open?"
        expanded = os.path.expanduser(filename)
        if os.path.exists(expanded):
            subprocess.Popen(
                ["xdg-open", expanded],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opening {os.path.basename(expanded)}"

        home = os.path.expanduser("~")
        try:
            if self.fd:
                result = subprocess.run(
                    ["fd", "--type", "f", filename, home],
                    capture_output=True, text=True, timeout=10,
                )
            else:
                result = subprocess.run(
                    ["find", home, "-type", "f",
                     "-iname", f"*{filename}*",
                     "-not", "-path", "*/.*"],
                    capture_output=True, text=True, timeout=10,
                )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if lines:
                subprocess.Popen(
                    ["xdg-open", lines[0]],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Opening {os.path.basename(lines[0])}"
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            logger.warning("open_file search error: %s", e)
        return f"Could not find {filename}"

    def open_folder(self, folder: str) -> str:
        if not folder:
            return "Which folder should I open?"
        folder_lower = folder.lower().strip()
        for key, path in FOLDER_MAP.items():
            if key in folder_lower:
                full = os.path.expanduser(path)
                if os.path.isdir(full):
                    subprocess.Popen(
                        ["xdg-open", full],
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return f"Opening {key} folder"
                return f"Folder not found: {full}"
        full = os.path.expanduser(folder)
        if os.path.isdir(full):
            subprocess.Popen(
                ["xdg-open", full],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opening {folder}"
        return f"Folder not found: {folder}"

    def recent_files(self) -> str:
        home = os.path.expanduser("~")
        try:
            result = subprocess.run(
                ["find", home, "-type", "f",
                 "-mtime", "-1",
                 "-not", "-path", "*/.*",
                 "-not", "-path", "*/venv/*",
                 "-not", "-path", "*/__pycache__/*"],
                capture_output=True, text=True, timeout=10,
            )
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            if not lines:
                return "No recently modified files found"
            count  = len(lines)
            top5   = [os.path.basename(p) for p in lines[:5]]
            listed = ", ".join(top5)
            suffix = f" and {count - 5} more" if count > 5 else ""
            return (f"{count} recent file{'s' if count != 1 else ''}: "
                    f"{listed}{suffix}")
        except subprocess.TimeoutExpired:
            return "Recent file search timed out"
        except Exception as e:
            logger.warning("recent_files error: %s", e)
            return "Could not retrieve recent files"
