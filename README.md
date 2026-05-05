# Vello - Context-Aware AI Voice Assistant for Linux

**Vello** is an offline-capable, context-aware AI voice assistant built specifically for Ubuntu Linux. Designed to act as a personal desktop companion, Vello listens for a wake word, processes spoken commands offline for rapid system tasks, and seamlessly falls back to a cloud-based AI brain (OpenAI GPT-4o-mini) for complex queries. 

With Vello, you can control your desktop, open applications, search the web, and get intelligent conversational answers entirely hands-free.

---

## 🚀 Features

- **Wake Word Detection:** Passively listens for the wake word ("Jarvis") with low CPU overhead.
- **Offline Intent Parsing:** Fast, offline rule-based engine to handle common tasks without API latency.
- **Context Awareness:** Remembers active applications to provide contextual follow-ups (e.g., "open folder" will open in VS Code if it is your active application).
- **Multi-step Commands:** Understands and executes chained actions sequentially like *"open chrome and play believer on youtube"*.
- **System Automation:** Control volume, take screenshots, check battery/CPU, shutdown, and lock the screen using voice commands.
- **Cloud AI Fallback:** Integrates with OpenAI's `gpt-4o-mini` to answer general knowledge questions conversationally when local commands don't match.
- **Fast Local TTS:** Uses Piper TTS with local ONNX models for smooth, ultra-fast, and natural-sounding voice responses.

---

## 🛠️ Tech Stack & Architecture

- **Programming Language:** Python 3
- **Wake Word Engine:** [Picovoice Porcupine](https://picovoice.ai/) (`pvporcupine`)
- **Speech-to-Text (STT):** `SpeechRecognition` library (utilizing Google Speech Recognition)
- **Text-to-Speech (TTS):** [Piper TTS](https://github.com/rhasspy/piper) with local `.onnx` models
- **Audio Processing:** `PyAudio`
- **Cloud AI:** OpenAI API (`gpt-4o-mini`)
- **System Control & Metrics:** `psutil`, `subprocess`, `os`, `webbrowser`

---

## 📚 Libraries and Models Detailed Overview

### Core Libraries
- **`pvporcupine`**: The official Python binding for Picovoice's Porcupine engine. It processes audio frames locally, ensuring privacy and highly accurate, low-latency wake word detection.
- **`SpeechRecognition`**: A robust wrapper for various speech APIs. In this project, it interfaces with the free Google Web Speech API to convert recorded audio from your microphone into text.
- **`pyaudio`**: Provides Python bindings for PortAudio, the cross-platform audio I/O library. It captures live audio streams from the system microphone and feeds it into the wake word detector and STT engine.
- **`openai`**: The official Python client for OpenAI's API. It allows Vello to seamlessly fall back to a powerful cloud-based LLM when local intents are not matched, making conversations fluid and intelligent.
- **`psutil`**: A cross-platform library for retrieving information on running processes and system utilization. Vello uses it to report real-time hardware metrics like battery levels and CPU load.
- **`python-dotenv`**: A utility that reads key-value pairs from a `.env` file and sets them as environment variables, keeping sensitive information like your API keys secure.

### AI & Machine Learning Models
- **Porcupine Wake Word Model**: A highly optimized, lightweight neural network trained specifically to detect the "Jarvis" keyword from a continuous audio stream without needing an internet connection.
- **Piper TTS ONNX Models**: Piper is a fast, local neural text-to-speech engine. Vello uses `.onnx` models (such as `en_US-lessac-medium.onnx`), which are acoustic models trained on human voices to synthesize incredibly realistic and fast speech offline.
- **GPT-4o-mini (OpenAI)**: OpenAI’s highly efficient and fast Large Language Model. It acts as the "Brain" of Vello, providing dynamic conversational capabilities, answering complex factual questions, and understanding context far beyond rigid offline rules.

---

## 📁 Project Structure

```text
vello-1/
├── main.py                 # Application entry point & main listening loop
├── .env                    # Environment variables (API keys)
├── requirements.txt        # Python dependencies list
├── audio/
│   ├── listener.py         # Audio input stream configurations
│   └── wake_word.py        # Picovoice Porcupine wake word detector logic
├── voice/
│   ├── speech_to_text.py   # Microphone listener & Google STT integration
│   └── text_to_speech.py   # Piper TTS local audio generation & playback
├── core/
│   ├── ai_brain.py         # OpenAI GPT-4o-mini API integration and system prompting
│   ├── command_router.py   # Routes intents to system execution commands
│   ├── context_manager.py  # Tracks active apps and conversation context/pending actions
│   └── intent_engine.py    # Offline rule-based intent parser & multi-command chain handler
├── automation/
│   └── system_commands.py  # Linux specific system and app control scripts
└── data/
    └── models/             # Local Piper TTS ONNX models (e.g., en_US-lessac)
```

---

## ⚙️ Core Logic & Flow

1. **Passive Listening:** The `WakeWordDetector` continuously monitors the microphone buffer for the keyword ("Jarvis") using the Porcupine engine.
2. **Command Capture:** Once triggered, Vello chimes in and `SpeechToText` captures the user's spoken instruction.
3. **Context Resolution:** The `ContextManager` checks for any pending actions or active context (e.g., clarifying which file to open if previously unspecified).
4. **Intent Classification:** The `IntentEngine` parses the text locally. It looks for actionable patterns (open apps, play music, chained commands using "and").
5. **Execution:** The `CommandRouter` triggers local Linux terminal commands (via `automation/system_commands.py`) to launch applications, manipulate files, or adjust system settings.
6. **AI Fallback:** If the command is purely conversational or lacks a local system trigger, the `AIBrain` sends the query to OpenAI. The generated response is spoken back via Piper TTS.

---

## 💻 Installation & Setup

### 1. Prerequisites
Ensure you are running **Ubuntu Linux** (or a similar Debian-based distro) with Python 3 installed. You will also need essential system audio and utility packages:
```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev alsa-utils gnome-screenshot xdg-utils
```
*Note: You also need the [Piper TTS binary](https://github.com/rhasspy/piper) installed and accessible in your system's PATH.*

### 2. Clone the Repository
```bash
git clone <repository-url>
cd vello-1
```

### 3. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies
Install the required packages. Ensure your `requirements.txt` includes the following core libraries:
```bash
pip install pvporcupine SpeechRecognition pyaudio openai psutil python-dotenv
```

### 5. Environment Variables
Create a `.env` file in the root directory and securely add your API keys:
```env
PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 6. Download TTS Model
Download a Piper TTS ONNX model (e.g., `en_US-lessac-medium.onnx` and its corresponding `.json` config file) and place it in the `data/models/` directory as expected by `text_to_speech.py`.

---

## ▶️ How to Run

Start Vello by executing the main script from your terminal:
```bash
python main.py

```
*Wait for the console to output `Waiting for wake word...` and simply say **"Jarvis"** to activate your new assistant!*

---

## 🎙️ Example Demo Output

Here is a real-world example of how Vello listens, parses context, and executes commands sequentially:

```text
VELLO: Vello is ready

Waiting for wake word...
Listening for wake word...
Wake word detected!
VELLO: Yes?
🎤 Speak...
You said: open terminal

Command : open terminal
Context : {'active_app': None, 'active_task': None, 'pending': None, 'recent': []}
Intent  : {'intent': 'open_app', 'app': 'terminal', 'target': None, 'chain': []}
VELLO: Opening terminal
VELLO: Terminal is open. What would you like to run?

🎤 Speak...
You said: pseudo update

Command : pseudo update
Context : {'active_app': 'terminal', 'active_task': None, 'pending': None, 'recent': ['opened:terminal']}
Intent  : {'intent': 'system_control', 'app': None, 'target': 'date', 'chain': []}
VELLO: Today is Tuesday, May 05, 2026

🎤 Speak...
You said: open Chrome

Command : open Chrome
Context : {'active_app': 'terminal', 'active_task': None, 'pending': None, 'recent': ['opened:terminal']}
Intent  : {'intent': 'open_app', 'app': 'chrome', 'target': None, 'chain': []}
VELLO: Opening chrome
VELLO: Chrome is open. You can say: search something, open YouTube, or open any website.

🎤 Speak...
You said: in YouTube play a song

Command : in YouTube play a song
Context : {'active_app': 'chrome', 'active_task': 'searching', 'pending': None, 'recent': ['opened:terminal', 'opened:chrome', 'task:browsing', 'task:searching']}
Intent  : {'intent': 'play_music', 'app': 'chrome', 'target': 'in youtube a song', 'chain': []}
VELLO: Playing in youtube a song on YouTube
```

---

## 🔮 Future Improvements
- **Custom Wake Words:** Implement custom trained wake words dynamically.
- **Fully Offline STT:** Replace Google Speech Recognition with an offline engine like `Whisper.cpp` or `Vosk` for complete privacy and zero-latency command parsing.
- **Advanced Context:** Extend context awareness to dynamically read active window titles using Linux window managers (like `xdotool` or `wmctrl`).
- **GUI Dashboard:** Create a lightweight system tray app or dashboard to monitor Vello's status, API usage, and recognized commands.

---

## 📝 Project Summary

Vello represents a powerful bridge between simple local automation scripts and advanced cloud artificial intelligence. By processing the wake word, intent classification, system commands, and text-to-speech synthesis entirely offline, it guarantees lightning-fast response times and deep, secure integration with the Linux desktop ecosystem. However, by gracefully falling back to OpenAI's GPT-4o-mini when local rules fall short, it avoids the typical limitations of rigid scripts. The result is a rich, conversational, and genuinely helpful desktop assistant experience that empowers power users to control their system completely hands-free.

---

## 🧑‍💻 Author / Credits
Developed as an advanced, context-aware AI desktop assistant for Linux power users.
Built utilizing [Picovoice Porcupine](https://picovoice.ai/) for wake word detection, [Piper TTS](https://github.com/rhasspy/piper) for synthesis, and [OpenAI](https://openai.com/) for intelligent conversational fallback.
