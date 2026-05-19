import subprocess
import socket
import logging
import psutil

logger = logging.getLogger(__name__)


class NetworkController:
    """Wi-Fi and network commands via nmcli."""

    def __init__(self, environment):
        self._available    = environment.is_tool_available("nmcli")
        self.nmcli_available = self._available
        if not self._available:
            logger.warning("nmcli not found — network control disabled.")

    def _check(self) -> str | None:
        if not self._available:
            return "Network control is not available. Install nmcli."
        return None

    # ── Wi-Fi power ───────────────────────────────────────────────

    def wifi_on(self) -> str:
        if err := self._check(): return err
        self._run("nmcli", "radio", "wifi", "on")
        return "Wi-Fi turned on"

    def wifi_off(self) -> str:
        if err := self._check(): return err
        self._run("nmcli", "radio", "wifi", "off")
        return "Wi-Fi turned off"

    # ── Network listing ───────────────────────────────────────────

    def list_networks(self) -> str:
        if err := self._check(): return err
        try:
            out = subprocess.check_output(
                ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list"],
                text=True, stderr=subprocess.DEVNULL
            )
            networks = []
            for line in out.strip().splitlines():
                parts = line.split(":")
                if len(parts) >= 2:
                    ssid, signal = parts[0].strip(), parts[1].strip()
                    if ssid:
                        networks.append((ssid, int(signal) if signal.isdigit() else 0))
            networks.sort(key=lambda x: x[1], reverse=True)
            top = networks[:3]
            if not top:
                return "No Wi-Fi networks found"
            desc = ", ".join(f"{s} at {sig}%" for s, sig in top)
            return f"Available networks: {desc}"
        except Exception as e:
            logger.warning("list_networks error: %s", e)
            return "Could not scan for networks"

    def connect_to(self, network_name: str) -> str:
        if err := self._check(): return err
        if not network_name:
            return "Which network should I connect to?"
        try:
            subprocess.run(
                ["nmcli", "device", "wifi", "connect", network_name],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return f"Connecting to {network_name}"
        except subprocess.CalledProcessError:
            return f"Could not connect to {network_name}. Check the network name or password."

    # ── IP / connectivity ─────────────────────────────────────────

    def get_ip(self) -> str:
        try:
            addrs = psutil.net_if_addrs()
            for iface, addr_list in addrs.items():
                if iface.startswith("lo"):
                    continue
                for addr in addr_list:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return f"Your IP address is {addr.address}"
            return "Could not determine your IP address"
        except Exception as e:
            logger.warning("get_ip error: %s", e)
            return "Could not determine your IP address"

    def check_connection(self) -> str:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                return "Internet is connected"
            return "No internet connection"
        except Exception:
            return "Could not check internet connection"

    # ── Internal ──────────────────────────────────────────────────

    def _run(self, *args):
        try:
            subprocess.run(list(args), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.warning("NetworkController command failed %s: %s", args, e)
