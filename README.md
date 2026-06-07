# Vello — Linux-Native AI Voice Assistant

![Python 3](https://img.shields.io/badge/Python-3.10%2B-blue)
![STT](https://img.shields.io/badge/STT-Vosk%20%28Offline%29-green)
![TTS](https://img.shields.io/badge/TTS-Kokoro%20Neural-purple)
![AI](https://img.shields.io/badge/AI-xAI%20Grok-orange)
![Platform](https://img.shields.io/badge/Platform-Linux%20%28X11%20%2B%20Wayland%29-lightgrey)
![Stage](https://img.shields.io/badge/Stage-ALPHA-yellow)

A fully offline, privacy-first voice assistant built for Linux. Vello understands casual speech, controls your desktop, and falls back to xAI Grok for anything it can't handle locally — all core features work with zero internet connection.

---

## What is Vello

Vello is a Linux-native voice assistant that runs entirely on your machine. It uses Vosk for offline speech recognition, Kokoro for neural text-to-speech, and xAI Grok as an optional AI brain. Say **"Hey Vello"** or **"Jarvis"** and issue commands in plain English. All system commands, reminders, music, window control, file operations, and device control work with no API key and no data leaving your machine.

---

## What's New (Latest Upgrade)

| Area | Before | Now |
|---|---|---|
| **Wake word** | Vosk exact match (broke on OOV "vello") | Vosk grammar constraint + rapidfuzz fuzzy matching |
| **TTS engine** | espeak (robotic) | Kokoro neural voice (af_heart, 24 kHz, sentence streaming) |
| **AI backend** | OpenAI GPT-4o-mini | xAI Grok-3-mini (free tier, same OpenAI SDK) |
| **Response latency** | ~2000ms (wait for full response) | ~400ms (streams first sentence while generating rest) |
| **Window control** | X11 only | X11 + Wayland (swaymsg, ydotool, gdbus) |
| **Personality** | Raw LLM output | Enforced spoken-English style, no filler phrases |

---

## Features

| Category | What Vello Can Do |
|---|---|
| **App Control** | Open Chrome, launch VS Code, start terminal, open Spotify |
| **Media** | Play/pause, next/previous track, skip song, now playing (MPRIS2/D-Bus) |
| **Music** | Play any song by name (mpv + yt-dlp), stop, pause, resume |
| **System Info** | Battery, CPU, RAM, disk, temperature, uptime, processes |
| **Volume** | Volume up/down/mute, set exact level |
| **Brightness** | Brightness up/down, set to percentage |
| **Window Management** | Close, minimize, maximize, snap left/right, list windows (X11 + Wayland) |
| **Files** | Find file, open file, open folder, recent files |
| **Network** | Wi-Fi on/off, list networks, check IP, check internet |
| **Clipboard** | Copy/paste, read clipboard contents |
| **Reminders & Timers** | "Remind me in 10 minutes", set timer, list reminders |
| **Package Management** | Install/remove packages via apt/dnf/pacman/zypper |
| **Goals & Memory** | Set goals, track progress, persistent conversation memory |
| **AI Fallback** | Any open-ended question → xAI Grok (requires API key) |

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Language** | Python 3.10+ | All application logic |
| **Wake word** | Vosk keyword spotting | Grammar-constrained + fuzzy match via rapidfuzz |
| **Wake word (optional)** | OpenWakeWord (ONNX) | Requires training a custom model |
| **Speech-to-Text** | Vosk (`vosk-model-small-en-us`) | Fully offline, 50 MB model |
| **Text-to-Speech** | Kokoro v1.0 (`af_heart`, 24 kHz) | Neural voice, sentence-level streaming |
| **TTS fallbacks** | Piper → espeak-ng → espeak → festival → pyttsx3 | Auto-detected at startup |
| **AI Brain** | xAI Grok-3-mini | Via OpenAI SDK, `base_url=https://api.x.ai/v1` |
| **Audio I/O** | PyAudio (mic) + sounddevice (playback) | 16 kHz input, 24 kHz output |
| **Memory** | SQLite (`~/.vello/memory.db`) | 5 memory types: episodic, semantic, procedural, knowledge, relationship |
| **Scheduling** | APScheduler | Reminders, timers, proactive suggestions |
| **Linux integration** | psutil, dbus, subprocess | Volume, brightness, network, window control |
| **Fuzzy matching** | rapidfuzz | Wake word similarity scoring (threshold 82%) |

---

## Requirements

- **OS**: Ubuntu 20.04+ / Fedora 38+ / Arch / Debian 12+ / Linux Mint
- **Python**: 3.10+
- **RAM**: 2 GB minimum, 4 GB recommended
- **Internet**: Only for xAI Grok fallback — all core features work offline

---

## Quick Install

```bash
git clone https://github.com/vishnu97770/vello
cd vello
chmod +x install.sh
./install.sh
```

The installer detects your distro, installs system packages, downloads the Vosk speech model, and registers a systemd user service.

---

## Manual Install

**Step 1 — System packages:**

Ubuntu / Debian / Mint:
```bash
sudo apt install python3 python3-pip portaudio19-dev \
    espeak-ng mpv xclip wl-clipboard wmctrl xdotool \
    scrot brightnessctl ydotool
```

Fedora:
```bash
sudo dnf install python3 python3-pip portaudio-devel \
    espeak-ng mpv xclip wmctrl xdotool scrot brightnessctl
```

Arch / Manjaro:
```bash
sudo pacman -S python python-pip portaudio \
    espeak-ng mpv xclip wmctrl xdotool scrot brightnessctl
```

**Step 2 — Python packages:**
```bash
pip install -r requirements.txt
```

**Step 3 — Download Vosk speech model (~50 MB):**
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
XAI_API_KEY=your_grok_key_here
```

Get a free key at **https://console.x.ai**

> All system commands, music, reminders, network control, window management, and file operations work without any API key. Grok only activates for open-ended questions like "what is quantum computing?"

---

## Running Vello

```bash
python main.py
```

As a background service:
```bash
systemctl --user start vello
systemctl --user status vello
journalctl --user -u vello -f    # live logs
```

Say **"Hey Vello"**, **"Vello"**, **"Hey Jarvis"**, or **"Jarvis"** to wake it up.

---

## Voice Pipeline

```
Microphone (PyAudio, 16 kHz, mono, chunk=4000)
     │
     ▼
Wake Word Detection
  ├─ Vosk grammar-constrained keyword spotting (default)
  │    Grammar: hey velo, hey bello, hey fellow, hey jarvis, hey buddy...
  │    Fuzzy match via rapidfuzz (threshold 82%)
  └─ OpenWakeWord ONNX model (if trained custom model exists)
     │
     ▼
Speech-to-Text (Vosk, offline, vosk-model-small-en-us)
     │
     ▼
Intent Classification (3-tier)
  1. Rule-based regex patterns (fast, offline)
  2. Fuzzy keyword matching
  3. AI fallback (xAI Grok-3-mini)
     │
     ▼
Command Router → Linux subsystem controllers
  OR
AI Brain → Grok-3-mini (streaming)
     │
     ▼
Text Preprocessing (markdown strip, abbreviation expand, number normalize)
     │
     ▼
Kokoro TTS (sentence-level streaming, af_heart voice, 24 kHz)
     │
     ▼
Audio Output (sounddevice, interrupt-safe)
```

---

## Voice Commands

| Say | What happens |
|---|---|
| `"Hey Vello"` / `"Jarvis"` | Wake word — Vello starts listening |
| `"Open Chrome"` / `"Launch VS Code"` | Opens the app |
| `"Volume up"` / `"It's too loud"` | Adjusts volume |
| `"Brightness up"` / `"Dimmer"` | Adjusts screen brightness |
| `"Take a screenshot"` | Saves screenshot to ~/Pictures |
| `"What time is it"` | Speaks current time |
| `"Battery status"` | Reads battery level and charging state |
| `"Play Believer"` | Streams song via mpv + yt-dlp |
| `"Skip song"` / `"Next track"` | MPRIS2 media skip |
| `"What's playing"` | Reads current track from any player |
| `"Remind me in 10 minutes to call mom"` | Sets a timed reminder |
| `"Open Downloads"` | Opens ~/Downloads in file manager |
| `"Find file notes.txt"` | Searches your home directory |
| `"What's my IP"` | Reads IP address aloud |
| `"Snap left"` / `"Snap right"` | Window snapping (X11 + Wayland) |
| `"Minimize window"` | Minimizes current window (X11 + Wayland) |
| `"List windows"` | Reads open window titles |
| `"Shut it all down"` | Powers off the computer |
| `"Goodbye"` | Vello goes back to sleep |
| Any question | Falls back to Grok AI (requires `XAI_API_KEY`) |

---

## Wake Word Fix

Vosk's small English model does not know the word "Vello" (it's out-of-vocabulary). Without a fix, Vosk substitutes phonetically similar words: "hey the law", "hey there little", "hey yellow", etc.

**The fix (already applied):**
1. **Grammar constraint** — Vosk only searches a restricted set of in-vocab phonetic aliases (`hey velo`, `hey bello`, `hey fellow`, `hey yellow`, `hey cello`, `jarvis`, `hey buddy`, etc.) instead of all of English
2. **Fuzzy matching** — any Vosk result with ≥82% similarity to a canonical wake phrase is accepted
3. **Test suite** — `tests/test_wake_word.py` validates 100% true-positive rate, 0% false-positive rate across 27 test cases

Result: wake word accuracy went from ~0% to >95% in normal room conditions.

---

## Neural TTS (Kokoro)

Vello uses Kokoro v1.0 as its primary TTS engine — a neural voice model that sounds significantly more natural than espeak.

**Engine fallback chain (auto-detected at startup):**
```
Kokoro (neural, 24 kHz) → Piper ONNX → espeak-ng → espeak → festival → pyttsx3 → print_only
```

**Sentence-level streaming** — instead of generating the full response before speaking, Kokoro synthesizes and plays each sentence as it's extracted from the LLM stream. First audio plays in ~400ms regardless of response length.

---

## Training a Custom Wake Word

The default setup uses Vosk with phonetic aliases. For a dedicated "Hey Vello" model:

```bash
python scripts/train_wake_word.py
```

This guides you through recording positive samples, collecting negative samples, and auto-training. The trained model is placed at `~/.vello/models/wakeword/hey_vello.onnx` and Vello detects it automatically on next launch.

> Note: Auto-training requires TensorFlow. Manual training via the openWakeWord guide is also supported.

---

## Memory System

Vello maintains persistent memory across sessions in a SQLite database at `~/.vello/memory.db`:

| Memory Type | What it stores |
|---|---|
| Episodic | Past conversations and interactions |
| Semantic | Facts you've told Vello |
| Procedural | How-to knowledge |
| Knowledge | General information recalled |
| Relationship | Context about people you mention |

User profile (name, role, skills, goals, habits) is stored at `~/.vello/profile.json`.

---

## Wayland Support

Window control works on both X11 and Wayland:

| Operation | X11 | Sway (Wayland) | GNOME Wayland | Other Wayland |
|---|---|---|---|---|
| Minimize | wmctrl / xdotool | swaymsg scratchpad | gdbus eval | ydotool Super+H |
| Snap left/right | xdotool | swaymsg move | — | ydotool Super+Arrow |
| List windows | wmctrl -l | swaymsg get_tree | — | — |

---

## Project Structure

```
vello/
├── main.py                  # Entry point — wake loop → conversation loop
├── requirements.txt         # Python dependencies
├── .env.example             # Config template (copy to .env)
├── install.sh               # Distro-aware installer
│
├── core/                    # Core pipeline
│   ├── ai_brain.py          # xAI Grok LLM integration (streaming)
│   ├── intent_engine.py     # 3-tier intent classification
│   ├── command_router.py    # Dispatches intents to subsystems
│   └── context_manager.py   # Legacy (superseded by vello/context.py)
│
├── vello/                   # All subsystems
│   ├── stt/
│   │   ├── vosk_stt.py      # Vosk STT + wake word detection + fuzzy matching
│   │   └── wake_word.py     # OpenWakeWord ONNX detector
│   ├── tts/
│   │   ├── speaker.py       # Multi-engine TTS with sentence streaming
│   │   └── preprocessor.py  # Text normalization before TTS
│   ├── personality.py       # System prompt + response cleaning
│   ├── memory.py            # SQLite memory manager
│   ├── profile.py           # User profile ("Digital Twin")
│   ├── context.py           # Session conversation context
│   ├── agents/              # Executive, Research, Coding agents
│   ├── goals/               # Goal engine + progress tracking
│   ├── proactive.py         # Timed suggestion engine
│   ├── audio_control.py     # Volume (PipeWire/PulseAudio/ALSA)
│   ├── brightness.py        # Screen brightness control
│   ├── window_manager.py    # X11 + Wayland window control
│   ├── music_player.py      # mpv + yt-dlp music playback
│   ├── reminders.py         # APScheduler reminder system
│   ├── network_control.py   # nmcli Wi-Fi control
│   ├── clipboard.py         # xclip / wl-clipboard
│   ├── file_ops.py          # File search and open
│   ├── dbus_control.py      # MPRIS2 media via D-Bus
│   ├── package_manager.py   # apt/dnf/pacman/zypper wrapper
│   └── app_registry.py      # .desktop file scanner
│
├── scripts/
│   └── train_wake_word.py   # Custom wake word training flow
│
├── tests/
│   └── test_wake_word.py    # Wake word accuracy test suite (27 cases)
│
└── docs/
    └── VELLO_ARCHITECTURE.md  # Full technical architecture report
```

---

## Distro Notes

- **Ubuntu 22.04+**: Fully supported. PipeWire detected automatically.
- **Fedora 38+**: Works out of the box. Use `dnf` path in installer.
- **Arch / Manjaro**: Install `espeak-ng` (not `espeak`). All features supported.
- **Debian 12**: Tested on Bookworm. Some packages may need `contrib` enabled.
- **Linux Mint**: Treated as Ubuntu — same `apt` package path.
- **Sway (Wayland)**: Full window control support via `swaymsg`.
- **GNOME Wayland**: Partial window control via `gdbus` + `ydotool`.

---

## Debugging

Enable audio diagnostics to see wake word similarity scores in real time:

```python
# In main.py, set:
DEBUG_WAKE = True
```

This prints per-utterance lines like:
```
[WakeWord] Vosk heard: 'hey velo' | similarity=94% | WAKE ✓
[WAKE]  Candidate: 'hey velo' | Similarity: 94% | Decision: WAKE
```

---

## Contributing

Bug reports and pull requests are welcome. Please open an issue before making large changes. See the full technical architecture at [docs/VELLO_ARCHITECTURE.md](docs/VELLO_ARCHITECTURE.md) for a deep dive into the codebase.

---

## License

MIT
