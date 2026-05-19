# Vello — Linux-Native AI Voice Assistant

![Python 3](https://img.shields.io/badge/Python-3.10%2B-blue)
![Offline STT](https://img.shields.io/badge/STT-Offline%20%28Vosk%29-green)
![Linux Desktop](https://img.shields.io/badge/Platform-Linux%20Desktop-orange)

A fully offline, privacy-first voice assistant built for Linux. Vello understands casual speech, controls your desktop, and falls back to GPT for anything it can't handle locally.

---

## What is Vello

Vello is a Linux-native voice assistant that runs entirely on your machine. It uses Vosk for offline speech recognition and espeak/Piper for text-to-speech — no cloud required for core features. Say "Hey Vello" and issue commands in plain English; Vello handles them with zero latency and zero data leaving your machine.

---

## Features

| Category | Commands |
|---|---|
| **App Control** | Open Chrome, launch VS Code, start terminal, open Spotify |
| **Media** | Play/pause, next/previous track, skip song, now playing (MPRIS2) |
| **Music** | Play Believer, stop music, pause, resume (mpv + yt-dlp) |
| **System Info** | Battery, CPU, RAM, disk, temperature, uptime, processes |
| **Volume & Brightness** | Volume up/down, mute, brightness up/down, set brightness to 70 |
| **Window Management** | Close window, minimize, maximize, snap left/right, list windows |
| **Files** | Find file, open file, open Downloads folder, recent files |
| **Network** | Wi-Fi on/off, list networks, check IP, check internet |
| **Reminders** | Remind me in 10 minutes, set a timer, list reminders |
| **Web & AI** | Search for X, Google Y, any question falls back to GPT |

---

## Requirements

- **OS**: Ubuntu 20.04+ / Fedora 38+ / Arch / Debian 12+ / Linux Mint
- **Python**: 3.10+
- **RAM**: 2 GB minimum, 4 GB recommended
- **Internet**: Only for GPT fallback — all core features work offline

---

## Quick Install

```bash
git clone https://github.com/yourname/vello
cd vello
chmod +x install.sh
./install.sh
```

The installer detects your distro, installs all system packages, sets up a Python venv, downloads the Vosk speech model, and registers a systemd user service.

---

## Manual Install

If `install.sh` fails, install manually:

**Ubuntu / Debian / Mint:**
```bash
sudo apt install python3 python3-venv python3-pip \
    portaudio19-dev espeak mpv xclip wmctrl xdotool \
    scrot nmcli alsa-utils
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip portaudio-devel \
    espeak mpv xclip wmctrl xdotool scrot NetworkManager alsa-utils
```

**Arch / Manjaro:**
```bash
sudo pacman -S python python-pip portaudio \
    espeak-ng mpv xclip wmctrl xdotool scrot networkmanager alsa-utils
```

**Python packages:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Download Vosk model (~50 MB):**
```bash
mkdir -p ~/.vello/models && cd ~/.vello/models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-small-en-us
```

---

## Configuration

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=your_key_here
```

> GPT fallback is optional — all system commands, music, reminders, network control, and file operations work without an API key. GPT only activates for open-ended questions like "what is machine learning?".

---

## Running Vello

**Directly:**
```bash
source venv/bin/activate
python main.py
```

**As a background service:**
```bash
systemctl --user start vello
systemctl --user status vello
journalctl --user -u vello -f   # live logs
```

Say **"Hey Vello"** to wake it up, then speak your command.

---

## Voice Commands

| Say | What happens |
|---|---|
| `"Hey Vello"` | Wake word — Vello starts listening |
| `"Open Chrome"` / `"Launch VS Code"` | Opens the app |
| `"It's too loud"` / `"Volume down"` | Reduces volume |
| `"Bro take a screenshot"` | Saves screenshot to ~/Pictures |
| `"What time is it"` | Speaks current time |
| `"Play Believer"` | Streams song via mpv + yt-dlp |
| `"Skip song"` / `"Next track"` | MPRIS2 media skip |
| `"What's playing"` | Reads current track from any player |
| `"Remind me in 10 minutes to call mom"` | Sets a timed reminder |
| `"Open Downloads"` | Opens ~/Downloads in file manager |
| `"Find file notes.txt"` | Searches your home directory |
| `"What's my IP"` | Reads IP address aloud |
| `"Brightness up"` / `"Dimmer"` | Adjusts screen brightness |
| `"Close window"` / `"Snap left"` | Window management (X11) |
| `"Shut it all down"` | Powers off the computer |
| `"Goodbye"` | Vello goes back to sleep |
| Any question | Falls back to GPT (requires API key) |

---

## Upgrading TTS to Piper

Piper produces dramatically more natural speech than espeak. Download the model (~65 MB):

```bash
source venv/bin/activate
python -m vello.tts.piper_setup
```

Restart Vello and it will automatically detect and use Piper.

---

## Training a Custom Wake Word

The default setup uses Vosk keyword spotting for wake detection. For a faster, more accurate custom "Hey Vello" model using openWakeWord:

**Step 1 — Record training samples:**
```bash
pip install openwakeword
python scripts/train_wake_word.py
```

**Step 2 — Train the model:**
Follow the openWakeWord training guide: https://github.com/dscripka/openWakeWord#training

**Step 3 — Install the model:**
```bash
cp hey_vello.onnx ~/.vello/models/wakeword/hey_vello.onnx
```

Vello auto-detects the custom model on next launch.

---

## Distro Notes

- **Ubuntu 22.04+**: Fully supported. PipeWire detected automatically.
- **Fedora 38+**: Works out of the box. Use `dnf` path in installer.
- **Arch / Manjaro**: Install `espeak-ng` (not `espeak`). All features supported.
- **Debian 12**: Tested on Bookworm. Some packages may need `contrib` enabled.
- **Linux Mint**: Treated as Ubuntu — same `apt` package path.

---

## Contributing

Bug reports and pull requests are welcome. Please open an issue before making large changes so the approach can be discussed first. See [issues](https://github.com/yourname/vello/issues) for the current backlog.

---

## License

MIT
