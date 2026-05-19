# Vello — Linux-Native AI Voice Assistant

**Vello** is an open-source, offline-capable, context-aware AI voice assistant
built specifically for desktop Linux (Ubuntu, Fedora, Arch, Mint, Pop!_OS).
It is the Linux equivalent of Apple Siri or Windows Cortana — a feature that
has never existed natively on Linux — built entirely in Python 3.

---

## Features

- **Offline Wake Word** — Say "Hey Vello" or "Hey Jarvis" to activate. No cloud needed.
- **Offline STT** — Vosk speech-to-text runs fully on-device (no Google, no API).
- **Offline TTS** — Piper TTS with local ONNX voice model for natural speech.
- **AI Fallback** — OpenAI GPT-4o-mini answers anything not handled locally.
- **Multi-turn Memory** — Remembers the last 3 exchanges for follow-up questions.
- **Dynamic App Registry** — Reads your installed `.desktop` files, opens any app.
- **PipeWire + PulseAudio** — Volume control auto-detects your audio backend.
- **X11 + Wayland Screenshots** — Picks the right tool (grim, scrot, gnome-screenshot).
- **Real Music Playback** — Plays audio via `mpv + yt-dlp` (no browser needed).
- **Reminders & Timers** — "Remind me in 10 minutes to drink water."
- **Wi-Fi Control** — Turn on/off, scan, connect to networks via `nmcli`.
- **Clipboard** — Read and write clipboard on X11 (xclip) and Wayland (wl-clipboard).
- **System Info** — RAM, disk, CPU temp, uptime, network usage, processes.
- **Package Management** — Install, remove, and update packages with confirmation.
- **Multi-step Commands** — "Open Chrome and search Python tutorials."
- **Safety Checks** — Dangerous commands (rm -rf, mkfs, etc.) are always blocked.

---

## Architecture

```
main.py
├── VelloEnvironment      → Detects audio/display/DE/package manager at startup
├── VoskSTT               → Offline wake word + speech recognition (Vosk)
├── TextToSpeech          → Piper TTS with local ONNX model
├── VelloContext           → Session state + GPT conversation history
├── IntentEngine          → Rule-based offline intent classifier
├── CommandRouter         → Executes all actions
│   ├── AudioController   → PipeWire / PulseAudio volume control
│   ├── MusicPlayer       → mpv + yt-dlp real audio playback
│   ├── ReminderSystem    → APScheduler timers and reminders
│   ├── NetworkController → nmcli Wi-Fi management
│   ├── ClipboardController → xclip / wl-clipboard integration
│   └── PackageManager    → apt / dnf / pacman / zypper
└── AIBrain               → OpenAI GPT-4o-mini multi-turn fallback
```

---

## Installation

### 1. System Dependencies

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev alsa-utils \
    gnome-screenshot scrot grim xclip wl-clipboard \
    nmcli mpv yt-dlp notify-send xdotool wmctrl
```

**Fedora:**
```bash
sudo dnf install python3-pyaudio portaudio-devel alsa-utils \
    gnome-screenshot scrot grim xclip wl-clipboard \
    NetworkManager-tui mpv yt-dlp libnotify xdotool wmctrl
```

**Arch Linux:**
```bash
sudo pacman -S python-pyaudio portaudio alsa-utils \
    gnome-screenshot scrot grim xclip wl-clipboard \
    networkmanager mpv yt-dlp libnotify xdotool wmctrl
```

### 2. Piper TTS Binary

Download the Piper binary and place it in your PATH:
```bash
# Download from https://github.com/rhasspy/piper/releases
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_linux_x86_64.tar.gz
tar xzf piper_linux_x86_64.tar.gz
sudo cp piper/piper /usr/local/bin/
```

### 3. Piper TTS Voice Model

```bash
mkdir -p data/models
cd data/models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

### 4. Vosk Offline STT Model

```bash
mkdir -p ~/.vello/models
cd ~/.vello/models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-small-en-us
```

### 5. Clone and Setup

```bash
git clone <repository-url>
cd vello-1
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Environment Variables

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

`.env` file:
```
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Running

```bash
source venv/bin/activate
python main.py
```

At startup you will see a capability report:

```
┌─────────────────────────────────────────┐
│  VELLO — Starting up                    │
│  Audio:    Pipewire                     │
│  Display:  Wayland                      │
│  Desktop:  Gnome                        │
│  Packages: apt                          │
│  STT:      Vosk (offline)               │
│  TTS:      Piper                        │
├─────────────────────────────────────────┤
│  ✓  Volume control                      │
│  ✓  Screenshots                         │
│  ✓  Music playback (mpv + yt-dlp)       │
│  ✓  Wi-Fi control (nmcli)               │
│  ✓  Reminders (APScheduler)             │
│  ✓  Clipboard (xclip / wl-clipboard)    │
│  ✓  Desktop notifications (notify-send) │
└─────────────────────────────────────────┘
```

Then say **"Hey Vello"** to begin.

---

## Voice Commands

### Wake Words
`Hey Vello` · `Hey Jarvis` · `Jarvis` · `Vello` · `Ok Vello` · `Hey Buddy`

### Open Applications
> "Open Chrome" · "Open VS Code" · "Open Terminal" · "Launch Spotify"
> "Start Discord" · "Open Firefox" · "Open Calculator"

Any installed application (reads your `.desktop` files automatically).

### System Controls
> "What is the time" · "What is the date"
> "Volume up" · "Volume down" · "Mute"
> "Take a screenshot" · "Lock screen"
> "Battery level" · "CPU usage" · "Shutdown"

### Extended System Info
> "Memory usage" · "Disk usage" · "CPU temperature"
> "Network usage" · "System uptime" · "How many processes"

### Music Playback
> "Play Believer" · "Play Shape of You on YouTube"
> "Pause music" · "Resume music" · "Stop music" · "What's playing"

### Web & Search
> "Search Python tutorials" · "Google machine learning"
> "Look up best Linux apps" · "Find how to use grep"

### Reminders & Timers
> "Remind me in 10 minutes to drink water"
> "Set a timer for 5 minutes"
> "List my reminders"

### Wi-Fi & Network
> "WiFi on" · "WiFi off"
> "Show available networks" · "Connect to HomeWifi"
> "What's my IP" · "Check internet connection"

### Clipboard
> "Read clipboard" · "What did I copy"
> "Copy hello world"

### Package Management
> "Install vlc" · "Uninstall gimp" · "Update system"
*(Always asks for confirmation before executing)*

### Terminal Commands
> "Run ls -la" · "Execute pwd" · "sudo apt update"

### Multi-step Chained Commands
> "Open Chrome and search Python tutorials"
> "Open Chrome and play Believer on YouTube"

### AI Fallback (any question)
> "What is machine learning?"
> "How do I reverse a list in Python?"
> "Write a poem about Linux"

### Exit
> "Goodbye" · "Bye" · "Exit" · "Quit"

---

## Project Structure

```
vello-1/
├── main.py                        # Entry point
├── .env                           # API keys
├── requirements.txt               # Python dependencies
├── vello/                         # Core Vello package
│   ├── environment.py             # OS/hardware detection singleton
│   ├── context.py                 # Session state + GPT conversation memory
│   ├── app_registry.py            # Dynamic .desktop file registry
│   ├── audio_control.py           # PipeWire / PulseAudio volume control
│   ├── music_player.py            # mpv + yt-dlp music playback
│   ├── reminders.py               # APScheduler reminders and timers
│   ├── network_control.py         # nmcli Wi-Fi management
│   ├── clipboard.py               # X11/Wayland clipboard
│   ├── package_manager.py         # apt/dnf/pacman/zypper wrapper
│   └── stt/
│       └── vosk_stt.py            # Offline Vosk speech-to-text
├── voice/
│   └── text_to_speech.py          # Piper TTS
├── core/
│   ├── intent_engine.py           # Rule-based intent classifier
│   ├── command_router.py          # Intent → action executor
│   ├── ai_brain.py                # OpenAI GPT-4o-mini multi-turn
│   └── response_generator.py      # Random fun response phrases
├── audio/
│   └── wake_word.py               # Wake word detector (Google STT fallback)
└── data/models/                   # Piper TTS ONNX models
```

---

## Why Linux Only?

Mac has Siri. Windows has Cortana. Linux has nothing.

Vello fills that gap. It uses only Linux-native tools (`pactl`/`wpctl`, `nautilus`,
`nmcli`, `gnome-screenshot`, `grim`, `xclip`, `wl-clipboard`, `xdg-open`) and
is designed to work across all major desktop environments (GNOME, KDE, XFCE,
Cinnamon) and both display servers (X11 and Wayland). It will not run correctly
on macOS or Windows by design.
