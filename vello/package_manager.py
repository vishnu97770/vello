import subprocess
import logging

logger = logging.getLogger(__name__)

_INSTALL_CMDS = {
    "apt":    ["sudo", "apt", "install", "-y"],
    "dnf":    ["sudo", "dnf", "install", "-y"],
    "pacman": ["sudo", "pacman", "-S", "--noconfirm"],
    "zypper": ["sudo", "zypper", "install", "-y"],
}

_REMOVE_CMDS = {
    "apt":    ["sudo", "apt", "remove", "-y"],
    "dnf":    ["sudo", "dnf", "remove", "-y"],
    "pacman": ["sudo", "pacman", "-R", "--noconfirm"],
    "zypper": ["sudo", "zypper", "remove", "-y"],
}

_UPDATE_CMDS = {
    "apt":    "sudo apt update && sudo apt upgrade -y",
    "dnf":    "sudo dnf upgrade -y",
    "pacman": "sudo pacman -Syu --noconfirm",
    "zypper": "sudo zypper update -y",
}


class PackageManager:
    """Voice-controlled package management with mandatory confirmation."""

    def __init__(self, environment, speak_fn=None, listen_fn=None):
        self.pm              = environment.package_manager
        self._speak          = speak_fn
        self._listen         = listen_fn
        self.install_commands = _INSTALL_CMDS
        self.remove_commands  = _REMOVE_CMDS

    def _speak_safe(self, msg: str):
        if self._speak:
            self._speak(msg)
        else:
            print(f"  [PM]: {msg}")

    def _confirm(self, question: str) -> bool:
        self._speak_safe(question)
        if not self._listen:
            return False
        answer = self._listen() or ""
        return "yes" in answer.lower() or "yeah" in answer.lower() or "sure" in answer.lower()

    def _no_pm(self) -> str:
        return "No package manager detected on this system."

    def _run_in_terminal(self, command: str):
        subprocess.Popen(
            ["gnome-terminal", "--", "bash", "-c", f"{command}; exec bash"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    # ── Public API ────────────────────────────────────────────────

    def install(self, package: str) -> str:
        if not self.pm: return self._no_pm()
        if not package: return "Which package should I install?"
        if not self._confirm(f"Should I install {package}? Say yes to confirm."):
            return f"Installation of {package} cancelled."
        cmd = " ".join(_INSTALL_CMDS[self.pm] + [package])
        self._run_in_terminal(cmd)
        return f"Installing {package}"

    def remove(self, package: str) -> str:
        if not self.pm: return self._no_pm()
        if not package: return "Which package should I remove?"
        if not self._confirm(f"Should I remove {package}? Say yes to confirm."):
            return f"Removal of {package} cancelled."
        cmd = " ".join(_REMOVE_CMDS[self.pm] + [package])
        self._run_in_terminal(cmd)
        return f"Removing {package}"

    def update_system(self) -> str:
        if not self.pm: return self._no_pm()
        if not self._confirm("Should I update the system? Say yes to confirm."):
            return "System update cancelled."
        self._run_in_terminal(_UPDATE_CMDS[self.pm])
        return "Starting system update"
