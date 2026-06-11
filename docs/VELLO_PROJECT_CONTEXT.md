# Vello — Project Context Document
> Paste this entire file into Claude AI to give it full context about the Vello project.
> Use it to discuss architecture decisions, plan new features, debug issues, or continue development.

---

## What is Vello?

Vello is a **Linux-native, offline-first voice assistant** built entirely in Python. Think of it as a personal Siri or Alexa, but one that runs 100% on your own machine — no cloud, no subscription, no data leaving your computer.

You say **"Hey Vello"** or **"Jarvis"** → it wakes up → you speak a command → it executes it and responds with a natural voice.

The core idea is simple: most voice assistants (Siri, Alexa, Google Assistant) send your voice to remote servers, require internet, and don't integrate deeply with your Linux desktop. Vello is the opposite — it runs offline, speaks naturally using Kokoro neural TTS, understands Linux-specific commands (window snapping, brightness, package management, D-Bus media), and only calls an AI API (xAI Grok) when the user asks an open-ended question that can't be answered locally.

---

## Why Linux? Why Not Windows or Mac?

### The Linux Focus is Intentional

Vello was built specifically for Linux because:

1. **Linux desktop users have no native voice assistant.** Windows has Cortana. Mac has Siri. Linux has nothing built-in. Vello fills that gap.

2. **Linux gives direct hardware and system access.** Commands like `brightnessctl`, `nmcli`, `pactl`, `swaymsg`, D-Bus, and systemd are Linux-native tools that let Vello control the desktop deeply — no GUI automation hacks needed.

3. **Privacy-conscious users run Linux.** The target user doesn't want cloud-dependent voice assistants. Linux users expect offline, self-hosted tools.

4. **Python on Linux has no audio friction.** PyAudio, ALSA, PipeWire, and Vosk work cleanly on Linux. The same setup on Windows requires MSVC build tools and driver workarounds.

### Does Vello Work on Windows or Mac?

**Short answer: No, not currently. It would require significant work.**

Here's why each OS would break:

| Component | Linux | Windows | Mac |
|---|---|---|---|
| PyAudio (mic input) | Works natively | Requires MSVC build tools, often fails | Works but needs PortAudio via Homebrew |
| Vosk STT | Works | Works | Works |
| Kokoro TTS | Works | Likely works | Likely works |
| `espeak-ng` fallback TTS | `apt install espeak-ng` | Complex install | Homebrew only |
| `brightnessctl` brightness | Works | Does not exist | Does not exist |
| `nmcli` network control | Works | Does not exist | Does not exist |
| `swaymsg` / `xdotool` window control | Works | Does not exist | Does not exist |
| `pactl` / `amixer` volume | Works | Does not exist | Different (osascript) |
| `dbus` MPRIS2 media | Works | Does not exist | Does not exist |
| `mpv` + `yt-dlp` music | Works | Works but paths differ | Works |
| `notify-send` reminders | Works | Does not exist | Different |
| systemd service | Works | Does not exist | launchd instead |

**The core STT/TTS/LLM pipeline (about 30% of the project) would work cross-platform.** The remaining 70% — all the Linux system integrations — would need to be rewritten per OS using Windows APIs or macOS equivalents.

**To port to Windows:** Replace all subprocess shell commands with `ctypes`/`win32api` calls, replace D-Bus with COM objects, replace `pactl` with Core Audio, and replace window management with `pywin32`. Possible but weeks of work.

**To port to Mac:** Replace with `osascript` for most system commands, use `AVFoundation` for audio. Less work than Windows but still significant.

**Verdict:** Vello is Linux-first by design and the architecture assumes Linux throughout. Cross-platform support is a medium-term future goal, not a current priority.

---

## Purpose and Goals

| Goal | Status |
|---|---|
| Replace cloud voice assistants for Linux users | ✅ Core working |
| 100% offline for system commands | ✅ Fully offline core |
| Natural-sounding voice (not robotic espeak) | ✅ Kokoro neural TTS |
| Wake word that actually works | ✅ Fixed (OOV + fuzzy matching) |
| Remember users across sessions | ✅ SQLite persistent memory |
| Deep Linux desktop integration | ✅ 12+ subsystems |
| AI fallback for unknown questions | ✅ xAI Grok (optional) |
| Low latency response | ✅ ~400ms first audio (sentence streaming) |
| Privacy-first, no telemetry | ✅ No data leaves machine (except Grok queries) |
| Custom wake word training | ⚠️ Partially done (needs TensorFlow) |
| Cross-platform (Windows/Mac) | ❌ Not implemented |
| GUI/web control panel | ❌ Not implemented |
| Multi-language support | ❌ English only currently |
| Vector-based semantic memory | ❌ SQL keyword search only |

---

## Complete Tech Stack

### Core Voice Pipeline

| Layer | Technology | Why This Choice |
|---|---|---|
| **Wake Word** | Vosk keyword spotting + rapidfuzz | "Vello" is OOV in all models; grammar constraint + fuzzy matching fixes it without training |
| **Wake Word (optional)** | OpenWakeWord (ONNX) | If user trains a custom model, gives better accuracy |
| **Speech-to-Text** | Vosk (`vosk-model-small-en-us`, 50 MB) | Fully offline, fast, runs on low-end hardware |
| **STT Fallback** | Google STT via SpeechRecognition | Online fallback if Vosk model not downloaded |
| **Text-to-Speech** | Kokoro v1.0 (af_heart voice, 24 kHz) | Best offline neural TTS available in Python |
| **TTS Fallback chain** | Piper → espeak-ng → espeak → festival → pyttsx3 | Auto-detected at startup; always has something to speak with |
| **Audio Input** | PyAudio | Industry standard for mic capture in Python |
| **Audio Output** | sounddevice | NumPy-native, interrupt-safe, no subprocess overhead |

### AI & Intelligence

| Layer | Technology | Why This Choice |
|---|---|---|
| **LLM** | xAI Grok-3-mini | Free tier, fast, OpenAI-compatible SDK |
| **LLM SDK** | openai Python package | Grok is OpenAI-compatible — same SDK, different `base_url` |
| **Intent Classification** | Custom 3-tier (regex → fuzzy → AI) | Offline-first; AI only used when local rules fail |
| **Fuzzy Matching** | rapidfuzz | Levenshtein similarity for intent and wake word |
| **Personality** | Custom system prompt + post-processing | Enforces spoken-English style, strips filler phrases |
| **Memory** | SQLite (`~/.vello/memory.db`) | Lightweight, offline, persistent across sessions |
| **Scheduling** | APScheduler | Background reminder/timer jobs |

### Linux System Integration

| Integration | Library/Tool | What It Controls |
|---|---|---|
| **Volume** | `pactl` / `amixer` / `pamixer` | PipeWire, PulseAudio, ALSA |
| **Brightness** | `brightnessctl` / `xbacklight` / sysfs | Screen brightness |
| **Network** | `nmcli` (subprocess) + psutil | Wi-Fi on/off, list networks, IP info |
| **Media** | D-Bus MPRIS2 (python3-dbus) | Play/pause/skip for any media player |
| **Window Control (X11)** | `wmctrl`, `xdotool` | Move, resize, minimize, snap |
| **Window Control (Wayland)** | `swaymsg`, `ydotool`, `gdbus` | Sway + GNOME Wayland support |
| **Clipboard** | `xclip` (X11) / `wl-clipboard` (Wayland) | Copy/paste |
| **Music** | `mpv` + `yt-dlp` subprocess | Stream any song by name |
| **Notifications** | `notify-send` | Desktop toast notifications |
| **File Search** | `fd` / `find` subprocess | Find files by name |
| **Packages** | `apt` / `dnf` / `pacman` / `zypper` | Install/remove software |
| **Screenshots** | `scrot` / `gnome-screenshot` | Full screen and area captures |
| **App Launch** | `.desktop` file scanner → `xdg-open` | Open any installed application |
| **System** | `psutil` | CPU, RAM, disk, battery, temperature |

---

## How Much of it Actually Works

### Fully Working ✅

- **Wake word** — "Hey Vello", "Vello", "Jarvis", "Hey Jarvis", "Hey Buddy" all trigger reliably after the OOV fix
- **Speech-to-Text** — Vosk transcription works well in normal room noise
- **Neural TTS** — Kokoro produces natural speech; sentence streaming means first audio in ~400ms
- **Volume control** — Tested on PipeWire/PulseAudio
- **Brightness control** — Works via `brightnessctl`
- **Battery/CPU/RAM/disk info** — All via psutil, always works
- **Time/date** — Always works offline
- **Music playback** — mpv + yt-dlp works; streams from YouTube by name
- **Reminders/timers** — APScheduler fires at correct time, speaks reminder aloud
- **Network info** — IP, connectivity check, Wi-Fi status
- **App launching** — Scans `.desktop` files, launches apps by natural name
- **Clipboard** — xclip on X11
- **File search** — Finds files in home directory
- **MPRIS2 media** — Play/pause/skip/now-playing works for any player with D-Bus support
- **Persistent memory** — SQLite stores and recalls past interactions
- **User profile** — Name, preferences, goals stored in `~/.vello/profile.json`
- **AI fallback** — Grok-3-mini responds to open questions (needs `XAI_API_KEY`)
- **Conversation interrupt** — Saying wake word during TTS stops playback immediately
- **Personality** — No "Certainly!", "Great question!", or bullet-point responses

### Partially Working ⚠️

- **Window management** — Fully working on X11; Wayland works on Sway, limited on GNOME
- **Custom wake word training** — Script exists but auto-train needs TensorFlow (not in requirements.txt)
- **Agent layer** (Executive/Research/Coding agents) — Wired up but uses `OPENAI_API_KEY` while AIBrain uses `XAI_API_KEY` — needs unification
- **Package management** — Works for install/remove but confirmation flow is basic
- **Proactive suggestions** — Background thread fires at 08:00/12:00/18:00 but suggestions are generic

### Not Yet Working ❌

- **Semantic/vector memory** — Only SQL `LIKE` keyword search; no embedding-based recall
- **Cross-platform** — Linux only as designed
- **Multi-language** — English only
- **GUI/dashboard** — Pure voice interface, no visual control panel
- **OTA updates** — No self-update mechanism
- Two stale test files (`test_all_commands.py`, `test_simulation.py`) use old API and will error

---

## Project Structure (All Files)

```
vello/
├── main.py                      # Entry point. Wake loop → conversation loop.
├── requirements.txt             # All Python dependencies.
├── .env.example                 # Config template. Copy to .env.
├── install.sh                   # Distro-aware installer (apt/dnf/pacman).
├── README.md                    # User-facing documentation.
│
├── core/                        # Pipeline core
│   ├── ai_brain.py              # xAI Grok LLM. Streaming + non-streaming.
│   ├── intent_engine.py         # 3-tier intent classifier (regex→fuzzy→AI).
│   ├── command_router.py        # Dispatches classified intents to subsystems.
│   └── context_manager.py      # Legacy session context (superseded).
│
├── vello/                       # All subsystem modules
│   ├── stt/
│   │   ├── vosk_stt.py          # VosAdd basic audio using Babylon.js sound system:
- Engine sound that scales with throttle (loop, pitch shift)
- Wind sound at high speed
- Touchdown sound on landing
- UI click sounds
- Background ambient airport sound on menu
Use free sounds from freesound.org or generate placeholder beeps 
if audio files aren't available yet.k STT + wake word with grammar + fuzzy match.
│   │   └── wake_word.py         # OpenWakeWord ONNX custom model detector.
│   ├── tts/
│   │   ├── speaker.py           # Multi-engine TTS + sentence-level streaming.
│   │   └── preprocessor.py      # Text normalization (markdown, numbers, abbrevs).
│   ├── agents/
│   │   ├── executive_agent.py   # Routes queries to specialist agents.
│   │   ├── research_agent.py    # Research-focused LLM agent.
│   │   └── coding_agent.py      # Code-focused LLM agent.
│   ├── goals/
│   │   └── goal_engine.py       # Goal setting, action planning, progress tracking.
│   ├── nlp/
│   │   └── normalizer.py        # Text normalization and greeting responses.
│   ├── personality.py           # System prompt + banned-opener cleaning.
│   ├── memory.py                # SQLite memory manager (5 types).
│   ├── profile.py               # User "Digital Twin" profile.
│   ├── context.py               # Session conversation context.
│   ├── proactive.py             # Timed background suggestion engine.
│   ├── environment.py           # Startup checks and banner.
│   ├── audio_control.py         # Volume (PipeWire/PulseAudio/ALSA).
│   ├── brightness.py            # Screen brightness (brightnessctl/xbacklight/sysfs).
│   ├── window_manager.py        # X11 + Wayland window control.
│   ├── music_player.py          # mpv + yt-dlp music streaming.
│   ├── reminders.py             # APScheduler reminder/timer system.
│   ├── network_control.py       # nmcli Wi-Fi control.
│   ├── clipboard.py             # xclip / wl-clipboard.
│   ├── file_ops.py              # File search and open.
│   ├── dbus_control.py          # MPRIS2 D-Bus media control.
│   ├── package_manager.py       # apt/dnf/pacman/zypper wrapper.
│   └── app_registry.py          # .desktop file scanner → app name map.
│
├── scripts/
│   └── train_wake_word.py       # 4-step custom wake word training flow.
│
├── tests/
│   └── test_wake_word.py        # 27-case wake word accuracy test suite.
│
├── automation/
│   └── system_commands.py       # Legacy system commands class (not active).
│
└── docs/
    ├── VELLO_ARCHITECTURE.md    # Full 1007-line technical architecture report.
    └── VELLO_PROJECT_CONTEXT.md # This file.
```

---

## Key Design Decisions (and Why)

### 1. Vosk instead of Whisper for STT
Whisper is more accurate but runs at 0.3–0.5x real-time on CPU — too slow for a responsive voice assistant. Vosk runs at 10x real-time on the same hardware with 9–10% word error rate on clean speech. For a voice assistant, speed beats maximum accuracy.

### 2. Kokoro instead of espeak for TTS
espeak sounds robotic (2/10 naturalness). Kokoro is a neural model that runs offline and sounds close to Siri quality (8/10). The `af_heart` voice is warm and natural. Sentence-level streaming means the user doesn't wait for the full response to be synthesized before hearing anything.

### 3. xAI Grok instead of OpenAI
Same OpenAI Python SDK — only `base_url` and `api_key` change. Grok has a free tier, which means users can enable AI features without paying. GPT-4o-mini also works if the user prefers (just change `_XAI_BASE_URL` and `_DEFAULT_MODEL` in `core/ai_brain.py`).

### 4. Grammar constraint for wake word
"Vello" is not in Vosk's English vocabulary (OOV). Instead of training a custom model (which needs TensorFlow and many samples), we supply a grammar list of phonetically similar in-vocab words (`hey velo`, `hey bello`, `hey fellow`, etc.) and use fuzzy matching (rapidfuzz, threshold 82%) to accept any Vosk output close enough to "hey vello". This achieves >95% accuracy with no training.

### 5. SQLite for memory instead of vector DB
A vector database (Chroma, Pinecone, Weaviate) would give semantic recall — finding memories by meaning rather than keyword. The current SQLite `LIKE` search works for simple recall but misses semantically related memories. The upgrade path is to add sentence-transformers + Chroma, which is a 1-2 week effort.

### 6. 3-tier intent classification
The classifier tries rules first (regex patterns, instant, offline), then fuzzy keyword matching (rapidfuzz, still offline), then AI (only if both fail). This means ~90% of commands are handled with zero API cost and zero latency from network.

---

## Configuration

**`~/.vello/memory.db`** — SQLite database, auto-created on first run.

**`~/.vello/profile.json`** — User profile:
```json
{
  "name": "Vishnu",
  "role": "",
  "skills": [],
  "goals": [],
  "habits": {},
  "routine": {}
}
```

**`~/.vello/models/vosk-model-small-en-us/`** — Vosk STT model (must be downloaded manually).

**`~/.vello/models/wakeword/hey_vello.onnx`** — Optional custom wake word model (auto-detected if present).

**`.env`** (copy from `.env.example`):
```
XAI_API_KEY=xai-xxxxxxxxxxxxxxxxxxxx
```

---

## Known Issues and Bugs

| Issue | Severity | File |
|---|---|---|
| Agent layer uses `OPENAI_API_KEY`, AIBrain uses `XAI_API_KEY` — both need to be unified to Grok | HIGH | `vello/agents/`, `core/ai_brain.py` |
| `numpy` used in `speaker.py` but not in `requirements.txt` directly | MEDIUM | `vello/tts/speaker.py:L26` |
| `test_all_commands.py` and `test_simulation.py` call `intent.classify()` expecting dict — returns string now | MEDIUM | `test_all_commands.py:L63` |
| `soundfile` in requirements.txt but never imported | LOW | `requirements.txt` |
| `VELLO_WAKE_WORD` env var in `.env.example` but no code reads it | LOW | `.env.example` |
| Custom wake word auto-train needs TensorFlow (not in requirements.txt) | LOW | `scripts/train_wake_word.py` |
| GNOME Wayland window control is incomplete | LOW | `vello/window_manager.py` |

---

## Future Improvements (Prioritized)

### Immediate (fix now)
1. **Unify API key** — all agents should use `XAI_API_KEY` + xAI base URL, same as `AIBrain`
2. **Add `numpy` to requirements.txt** directly (not just as transitive dep)
3. **Fix or delete** `test_all_commands.py` and `test_simulation.py` (wrong API)

### Short-term (1–4 weeks)
4. **Vector memory** — add `sentence-transformers` + `chromadb` for semantic recall
5. **TTS voice selection** — let user choose voice (`af_heart`, `af_sky`, etc.) via config
6. **Better proactive suggestions** — context-aware based on memory and profile, not generic
7. **Wayland clipboard** — current clipboard only fully works on X11 (`xclip`)

### Medium-term (1–3 months)
8. **Multi-language STT** — switch to `vosk-model-small-XX` based on `VELLO_LANGUAGE` env var
9. **Local LLM option** — Ollama integration so AI features work 100% offline
10. **Web dashboard** — simple Flask/FastAPI status page showing conversation history, memory, profile
11. **Plugin system** — allow adding custom intents without editing core files

### Long-term (3+ months)
12. **Cross-platform** — Windows and Mac support by abstracting system commands behind a platform layer
13. **Custom wake word (easy path)** — simple recording UI that auto-trains without TensorFlow
14. **Emotion/tone detection** — adjust response style based on detected speech tone

---

## How to Continue Development in This Chat

When pasting this into Claude AI, you can ask:

- **"Implement vector memory using chromadb"** — it knows the current SQLite setup and can suggest the migration
- **"Unify the API key to use Grok everywhere"** — it knows both the agents and AIBrain files
- **"Add support for [new command]"** — it knows the intent engine, command router, and how to add new intents
- **"Why is wake word detection failing?"** — full context of the Vosk OOV problem and the fix
- **"Port Vello to [distro/setup]"** — it knows all the Linux-specific dependencies
- **"What should we build next for Vello?"** — it knows exactly what's implemented vs missing

---

## Quick Reference — Running the Project

```bash
# Clone and install
git clone https://github.com/vishnu97770/vello
cd vello
pip install -r requirements.txt

# Download Vosk model (one time)
mkdir -p ~/.vello/models && cd ~/.vello/models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 vosk-model-small-en-us

# Optional: set up Grok AI
cp .env.example .env
# edit .env → XAI_API_KEY=xai-...

# Run
cd ~/path/to/vello
python main.py

# Run wake word tests
python tests/test_wake_word.py

# Enable audio debug mode
# In main.py, set DEBUG_WAKE = True
```

---

*Last updated: 2026-06-07 | Commit: a85268b | Python 3.10+ | Linux only*
