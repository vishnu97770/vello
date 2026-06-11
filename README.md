# Vello — Linux Voice Assistant

A fully offline-capable, privacy-first voice assistant built specifically for Linux.  
Say **"Hey Vello"** and control your desktop, files, apps, music, brightness, network, and more — no cloud required for core commands.

---

## Why Linux?

Most voice assistants (Siri, Cortana, Google Assistant) are locked to their platforms or require constant internet.  
Vello runs locally on Linux:

- **Offline STT** via Vosk (no audio ever leaves your machine for wake word + commands)
- **Offline TTS** via Kokoro neural voice (~400ms first word, no cloud)
- **Offline AI fallback** possible — Grok API is optional; all system commands work without it
- **Native Linux integration** — D-Bus media control, MPRIS, NetworkManager, xdg-open, systemd service, Wayland + X11

---

## What Vello Can Do

| Category | Example Commands |
|---|---|
| **Apps** | "Open Firefox", "Launch VS Code", "Start Spotify" |
| **Files** | "What's my latest download?", "Find my resume", "Open my documents" |
| **Music** | "Play music", "Pause", "Next track", "Resume playing" |
| **Volume** | "Turn volume up", "Mute", "Set volume to 50 percent" |
| **Brightness** | "Increase brightness", "Dim screen" |
| **Network** | "Connect to WiFi HomeNetwork", "Disconnect WiFi", "Show network status" |
| **System** | "Take a screenshot", "Empty trash", "What time is it?" |
| **Reminders** | "Remind me to call John at 3pm" |
| **Clipboard** | "Copy this", "Paste that" |
| **Packages** | "Install VLC", "Update my system" |
| **AI Chat** | "What's the capital of France?", "Explain quantum computing" |
| **Goals/Memory** | "Remember that I prefer dark mode", "What do you know about me?" |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Wake Word** | Vosk (grammar-constrained) + rapidfuzz | Offline; fixes OOV "vello" with phonetic aliases |
| **STT** | Vosk `vosk-model-small-en-us` | Fully offline, fast, runs on any CPU |
| **TTS** | Kokoro v1.0 (neural, 24kHz) | ~400ms latency, sounds natural, offline |
| **TTS fallback** | Piper ONNX → espeak-ng → espeak → pyttsx3 | Progressive degradation, always works |
| **AI** | xAI Grok (`grok-3-mini`) via OpenAI SDK | Fast, cheap, OpenAI-compatible, optional |
| **Intent** | Regex → fuzzy keyword → AI fallback | 3-tier; most commands never hit the API |
| **App lookup** | `.desktop` file scanner + rapidfuzz | 381 entries, covers Snap/Flatpak |
| **File ops** | Python `pathlib` rglob + rapidfuzz | Time-based queries, type filtering, fuzzy names |
| **Memory** | MemoryManager (episodic/semantic) | Persists across sessions |

---

## Voice Pipeline

```
Microphone
    │
    ▼
┌─────────────────────────────────────┐
│  Wake Word Detection (Vosk)         │
│  ┌─────────────────────────────┐    │
│  │ Grammar constraint          │    │
│  │  ["hey velo", "hey bello",  │    │
│  │   "hey fellow", "jarvis"…]  │    │
│  └──────────────┬──────────────┘    │
│                 │ Vosk result       │
│  ┌──────────────▼──────────────┐    │
│  │ rapidfuzz similarity ≥ 82%  │    │
│  │  vs canonical wake phrases  │    │
│  └──────────────┬──────────────┘    │
└─────────────────┼───────────────────┘
                  │ "Yes?"
                  ▼
┌─────────────────────────────────────┐
│  Command Listen (Vosk free-form)    │
└──────────────┬──────────────────────┘
               │ raw text
               ▼
┌─────────────────────────────────────┐
│  IntentEngine — 3-tier classify     │
│  1. Regex rules (instant)           │
│  2. Fuzzy keyword matching          │
│  3. AI classification fallback      │
└──────────────┬──────────────────────┘
               │ intent label
               ▼
┌─────────────────────────────────────┐
│  CommandRouter → subsystem calls    │
│  AppRegistry / FileOps / Audio /    │
│  Music / Network / Brightness …     │
└──────────────┬──────────────────────┘
               │ result text (or USE_AI)
               ▼
┌─────────────────────────────────────┐
│  ExecutiveAgent → specialist agent  │
│  ResearchAgent / CodingAgent /      │
│  GoalEngine / AIBrain (Grok)        │
└──────────────┬──────────────────────┘
               │ spoken response
               ▼
┌─────────────────────────────────────┐
│  Speaker (Kokoro TTS streaming)     │
│  Sentence-level streaming:          │
│  sentence 1 plays while 2-4 synth   │
└─────────────────────────────────────┘
```

---

## Wake Word Fix

**Problem:** "Vello" is not in Vosk's small-EN vocabulary. Vosk would emit a warning and silently ignore it:
```
WARNING (VoskAPI): Ignoring word missing in vocabulary: 'vello'
```

**Solution — two layers:**

### Layer 1: Grammar constraint
Instead of free-form recognition, Vosk is given a fixed grammar of in-vocab phonetic aliases:

```python
WAKE_GRAMMAR = [
    "hey velo",    # /vɛloʊ/ — closest single-word match
    "hey bello",   # common substitution
    "hey fellow",  # confirmed mishearing
    "hey yellow",  # confirmed mishearing
    "hey cello",   # close ending
    "hey mellow",  # close ending
    "velo", "bello", "fellow", "vella",
    "jarvis", "hey jarvis", "hey buddy",
    "[unk]",       # lets Vosk emit [unk] instead of forcing a bad match
]
```

This constrains Vosk's search space to 14 candidates rather than 200,000+ words, dramatically reducing false positives and false negatives.

### Layer 2: rapidfuzz fuzzy matching
Every Vosk result is scored against canonical wake phrases using `fuzz.ratio`:

```python
WAKE_SIMILARITY_THRESHOLD = 82   # balances recall vs false positives
# hey velo   vs hey vello  → 94  ✅
# hey bello  vs hey vello  → 89  ✅
# hey yellow vs hey vello  → 82  ✅ (confirmed Vosk substitution)
# hello      vs hey vello  → 36  ❌
# play music vs hey vello  → 22  ❌
```

**Result:** 100% recall, 0% false positive rate on 27 test cases.

---

## Kokoro TTS

Neural text-to-speech running entirely offline:

- **Voice:** `af_heart` (US English female)
- **Sample rate:** 24kHz
- **First audio:** ~400ms (sentence-level streaming)
- **Streaming:** Sentence 1 plays while sentences 2–4 are synthesised — no waiting for full-text synthesis
- **Interrupt:** Wake word during TTS playback immediately stops speech and listens for the next command
- **Fallback chain:** Kokoro → Piper ONNX → espeak-ng → espeak → festival → pyttsx3 → silent

---

## App Registry

Scans all standard Linux `.desktop` locations:

```
/usr/share/applications/
~/.local/share/applications/
/var/lib/snapd/desktop/applications/                  ← Snap apps
~/.local/share/flatpak/exports/share/applications/    ← User Flatpak
/var/lib/flatpak/exports/share/applications/          ← System Flatpak
```

**Matching order:** exact → starts-with → contains → rapidfuzz `token_set_ratio ≥ 70%`

**Category aliases** let you say "open a browser" instead of "open firefox":

```python
"browser":      ["firefox", "google-chrome", "brave-browser", ...]
"terminal":     ["gnome-terminal", "konsole", "alacritty", ...]
"file manager": ["nautilus", "dolphin", "thunar", ...]
```

**Name aliases** handle colloquial names:

```python
"vscode" / "vs code" → "code"
"chrome"             → "google-chrome"
"word"               → "libreoffice --writer"
"excel"              → "libreoffice --calc"
```

Cache stored at `~/.vello/app_cache.json`, auto-rebuilt when `.desktop` files change.

---

## File Operations

Natural-language file queries using Python `pathlib` — no hardcoded paths:

| Command | Handler |
|---|---|
| "What's my latest download?" | `get_latest_download()` |
| "What PDF did I download last?" | `get_latest_download("pdf")` |
| "Show recent documents" | `get_recent_files("documents", days=7)` |
| "Find my resume" | `find_and_open("resume")` |
| "Open the presentation" | `find_and_open("presentation")` |

**Supported file types for filtering:** pdf, image, photo, video, document, spreadsheet, presentation, archive, audio, code

**Human-readable times:**
- < 1 min → "just now"
- < 1 hour → "3 minutes ago"
- Same day → "2 hours ago"
- Yesterday → "yesterday"
- This week → "on Monday"
- Older → "on March 15"

**Search order for `find_and_open`:** exact filename → substring → rapidfuzz partial_ratio ≥ 65%

---

## Intelligence Layer

Vello has a multi-agent AI system on top of the rule-based command layer:

```
User command (intent = USE_AI)
        │
        ▼
  ExecutiveAgent.route(command)
        │
    ┌───┴────────────────────────────────┐
    │ research  │ coding  │ goals │ general│
    ▼           ▼         ▼       ▼
ResearchAgent CodingAgent GoalEngine AIBrain
 (web search)  (code help) (tracking) (Grok)
```

- **MemoryManager** — Episodic + semantic storage, persists between sessions
- **UserProfile** — Learns your name, preferences, habits over time
- **GoalEngine** — Track and follow up on goals you set
- **ProactiveEngine** — Offers suggestions between interactions

---

## Installation

### Prerequisites
- Linux (Ubuntu/Debian/Fedora/Arch/OpenSUSE supported by installer)
- Python 3.10+
- Microphone + speakers

### Quick Install

```bash
git clone https://github.com/vishnu97770/vello.git
cd vello
chmod +x install.sh
./install.sh
```

The installer:
1. Installs system packages (`portaudio19-dev`, `espeak-ng`, `mpv`, `wmctrl`, `xdotool`, etc.)
2. Creates a Python virtual environment and installs all Python dependencies
3. Downloads the Vosk model (~50 MB) to `~/.vello/models/`
4. Creates `.env` from `.env.example`
5. Installs a systemd user service (`vello.service`)

### Manual Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download Vosk model
mkdir -p ~/.vello/models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d ~/.vello/models/
mv ~/.vello/models/vosk-model-small-en-us-0.15 ~/.vello/models/vosk-model-small-en-us
```

---

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
# Required for AI features (conversations, research, coding help)
# Get a free key at: https://console.x.ai
XAI_API_KEY=your_key_here

# Optional: override wake word (default is "hey vello")
# VELLO_WAKE_WORD=hey vello
```

All system commands (apps, files, music, volume, brightness, network, etc.) work **without** an API key. The API is only needed for open-ended conversation and AI agent tasks.

---

## Running

```bash
# Direct run
source venv/bin/activate
python main.py

# Via systemd (starts at login, runs in background)
systemctl --user start vello
systemctl --user enable vello   # auto-start on login

# Check logs
journalctl --user -u vello -f
```

---

## Wayland vs X11

| Feature | X11 | Wayland |
|---|---|---|
| Screenshot (`scrot`) | ✅ | ❌ (use `gnome-screenshot`) |
| Window focus (`xdotool`) | ✅ | ❌ (limited) |
| Clipboard (`xclip`) | ✅ | ❌ |
| Clipboard (`wl-clipboard`) | ❌ | ✅ |
| App launching (`xdg-open`) | ✅ | ✅ |
| Media control (D-Bus/MPRIS) | ✅ | ✅ |
| Volume control (amixer/pactl) | ✅ | ✅ |

Vello detects `$WAYLAND_DISPLAY` at startup and picks the right backend automatically.

---

## Project Structure

```
vello/
├── main.py                    # Entry point — boot sequence + main loop
├── install.sh                 # One-shot installer (apt/dnf/pacman/zypper)
├── requirements.txt           # Python dependencies
├── .env.example               # Config template
│
├── core/
│   ├── intent_engine.py       # 3-tier intent classification (regex→fuzzy→AI)
│   ├── command_router.py      # Routes intents to subsystem handlers
│   └── ai_brain.py            # Grok (xAI) wrapper with streaming support
│
├── vello/
│   ├── app_registry.py        # .desktop scanner, fuzzy app lookup, JSON cache
│   ├── file_ops.py            # File queries: latest download, recent, fuzzy find
│   ├── audio_control.py       # Volume: amixer/pactl/pulseaudio
│   ├── brightness.py          # Screen brightness: xrandr/brightnessctl
│   ├── music_player.py        # mpv-based music playback
│   ├── dbus_control.py        # MPRIS2 media control (D-Bus)
│   ├── network_control.py     # NetworkManager / nmcli
│   ├── clipboard.py           # xclip (X11) / wl-clipboard (Wayland)
│   ├── package_manager.py     # apt/dnf/pacman wrapper
│   ├── window_manager.py      # wmctrl / xdotool
│   ├── reminders.py           # APScheduler-based reminder system
│   ├── personality.py         # System prompt + response cleanup
│   ├── environment.py         # Detects X11/Wayland, display server, distro
│   ├── context.py             # Session conversation context
│   ├── memory.py              # Episodic + semantic long-term memory
│   ├── profile.py             # User profile (name, preferences)
│   ├── goals.py               # Goal tracking engine
│   ├── agents.py              # ExecutiveAgent, ResearchAgent, CodingAgent
│   ├── proactive.py           # Background suggestion engine
│   │
│   ├── stt/
│   │   ├── vosk_stt.py        # Vosk STT + wake word (grammar + fuzzy)
│   │   └── wake_word.py       # OpenWakeWord detector (optional)
│   │
│   └── tts/
│       ├── speaker.py         # Multi-engine TTS with sentence streaming
│       ├── preprocessor.py    # Text cleanup + sentence splitting for TTS
│       └── piper_setup.py     # Optional Piper ONNX voice download
│
├── scripts/
│   ├── install_service.py     # systemd user service installer
│   └── train_wake_word.py     # Custom wake word training helper
│
├── tests/
│   └── test_wake_word.py      # 27-case wake word test suite
│
└── docs/
    ├── VELLO_ARCHITECTURE.md       # Full technical architecture reference
    └── VELLO_PROJECT_CONTEXT.md    # Context doc for AI chat sessions
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `vosk` | Offline speech recognition |
| `pyaudio` | Microphone input |
| `kokoro` | Neural TTS (primary voice) |
| `sounddevice` / `soundfile` | Kokoro audio playback |
| `openai` | Grok API client (OpenAI-compatible SDK) |
| `rapidfuzz` | Fuzzy matching for wake word, apps, files |
| `python-dotenv` | `.env` configuration loading |
| `APScheduler` | Reminder scheduling |
| `psutil` | System info (CPU, memory, battery) |
| `requests` | HTTP for research agent |
| `SpeechRecognition` | Google STT fallback |
| `num2words` | Number-to-word conversion for TTS |
| `numpy` | Audio signal processing |

---

## Debugging

```bash
# Enable per-frame audio diagnostics for wake word
# Edit main.py line 54:
DEBUG_WAKE = True

# Test wake word matching directly
python -m pytest tests/test_wake_word.py -v

# Check what apps are in the registry
python -c "
from vello.app_registry import AppRegistry
reg = AppRegistry()
print(f'{len(reg._registry)} apps loaded')
print(reg.find('firefox'))
"

# Check TTS engine selected at startup
python main.py 2>&1 | grep '\[TTS\]'
```

---

## Status

**Stage: ALPHA** — fully working end-to-end pipeline. Known items:

- [ ] AI agents (`agents.py`) still use `OPENAI_API_KEY` env var — should be `XAI_API_KEY`
- [ ] `numpy` should be pinned explicitly in `requirements.txt`
- [ ] Stale test fixtures in `tests/` reference old API shapes
- [ ] `install.sh` step 5 still mentions "OpenAI API key" in echo text

Core voice commands, wake word detection, TTS, app launching, and file operations are stable.

---

## License

MIT
