"""Install Vello as a systemd user service."""
import os
import sys
import subprocess

SERVICE_TEMPLATE = """\
[Unit]
Description=Vello Linux Voice Assistant
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={python} {main_py}
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0
Environment=PULSE_RUNTIME_PATH=/run/user/%U/pulse
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
"""


def install_service():
    # 1. Detect vello root
    vello_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py    = os.path.join(vello_root, "main.py")

    # 2. Find Python (prefer venv)
    venv_python = os.path.join(vello_root, "venv", "bin", "python")
    python      = venv_python if os.path.isfile(venv_python) else sys.executable

    # 3. Write service file
    service_dir  = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(service_dir, exist_ok=True)
    service_path = os.path.join(service_dir, "vello.service")

    with open(service_path, "w") as f:
        f.write(SERVICE_TEMPLATE.format(python=python, main_py=main_py))

    print(f"Service installed at {service_path}")

    # 4. Reload and enable
    for cmd in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "vello"],
    ):
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: {' '.join(cmd)} failed: {e}")
        except FileNotFoundError:
            print("systemctl not found — service file written but not enabled.")
            break

    # 5. Usage
    print()
    print("  Start:    systemctl --user start vello")
    print("  Status:   systemctl --user status vello")
    print("  Logs:     journalctl --user -u vello -f")
    print("  Stop:     systemctl --user stop vello")
    print("  Disable:  systemctl --user disable vello")


if __name__ == "__main__":
    install_service()
