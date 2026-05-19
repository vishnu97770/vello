import subprocess
import shutil
import threading
import glob
import time
import os


class Speaker:

    def __init__(self):
        self._tts_process    = None
        self._interrupt_flag = threading.Event()
        self.engine          = self._detect_engine()
        print(f"[TTS] Engine selected: {self.engine}")

    def _detect_engine(self) -> str:
        if shutil.which("piper"):
            # Try piper_setup location first, then other search paths
            model = None
            try:
                from vello.tts import piper_setup
                model = piper_setup.get_model_path()
            except Exception:
                pass
            if not model:
                model = self._find_piper_model()
            if model:
                self._piper_model = model
                return "piper"
            else:
                print("[TTS] Piper found but no model.")
                print("[TTS] Run: python -m vello.tts.piper_setup")

        if shutil.which("espeak"):
            return "espeak"

        if shutil.which("espeak-ng"):
            return "espeak-ng"

        if shutil.which("festival"):
            return "festival"

        try:
            import pyttsx3
            return "pyttsx3"
        except ImportError:
            pass

        print("[TTS] WARNING: No TTS engine found. Installing espeak...")
        os.system("sudo apt install -y espeak 2>/dev/null || "
                  "sudo dnf install -y espeak 2>/dev/null || "
                  "sudo pacman -S --noconfirm espeak 2>/dev/null")
        if shutil.which("espeak"):
            return "espeak"

        return "print_only"

    def _find_piper_model(self) -> str | None:
        search_paths = [
            os.path.expanduser("~/.vello/models/**/*.onnx"),
            os.path.expanduser("~/.local/share/piper/**/*.onnx"),
            "/opt/vello/models/**/*.onnx",
            "./models/**/*.onnx",
            "./data/models/**/*.onnx",
        ]
        for pattern in search_paths:
            files = glob.glob(pattern, recursive=True)
            if files:
                return files[0]
        return None

    def speak(self, text: str, interrupt_event: threading.Event | None = None):
        if not text or not text.strip():
            return

        self._interrupt_flag = interrupt_event or threading.Event()
        print(f"[Vello says]: {text}")

        try:
            if self.engine == "piper":
                self._speak_interruptible_piper(text)
            elif self.engine == "espeak":
                self._speak_interruptible_espeak(text)
            elif self.engine == "espeak-ng":
                self._speak_espeak_ng(text)
            elif self.engine == "festival":
                self._speak_festival(text)
            elif self.engine == "pyttsx3":
                self._speak_pyttsx3(text)
            # print_only — already printed above

        except Exception as e:
            print(f"[TTS ERROR] {self.engine} failed: {e}")
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", 150)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e2:
                print(f"[TTS] Emergency fallback also failed: {e2}")
                print(f"[TTS] Text was: {text}")

    def interrupt(self):
        """Signal TTS to stop immediately."""
        self._interrupt_flag.set()
        if self._tts_process and self._tts_process.poll() is None:
            self._tts_process.terminate()

    def _speak_interruptible_espeak(self, text: str):
        self._tts_process = subprocess.Popen(
            ["espeak", "-s", "145", "-v", "en-us", "-a", "200", text],
            stderr=subprocess.DEVNULL,
        )
        while self._tts_process.poll() is None:
            if self._interrupt_flag.is_set():
                self._tts_process.terminate()
                print("[TTS] Interrupted")
                return
            time.sleep(0.05)

    def _speak_espeak(self, text: str):
        subprocess.run(
            ["espeak", "-s", "145", "-v", "en-us", "-a", "200", text],
            timeout=30,
            stderr=subprocess.DEVNULL
        )

    def _speak_espeak_ng(self, text: str):
        subprocess.run(
            ["espeak-ng", "-s", "145", "-v", "en-us", text],
            timeout=30,
            stderr=subprocess.DEVNULL
        )

    def _speak_festival(self, text: str):
        proc = subprocess.Popen(
            ["festival", "--tts"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=text.encode(), timeout=30)

    def _speak_pyttsx3(self, text: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    def _speak_interruptible_piper(self, text: str):
        # Generate audio
        piper_proc = subprocess.Popen(
            ["piper", "--model", self._piper_model, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        audio_data, _ = piper_proc.communicate(input=text.encode(), timeout=15)
        if self._interrupt_flag.is_set():
            print("[TTS] Interrupted")
            return
        # Play audio
        self._tts_process = subprocess.Popen(
            ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._tts_process.stdin.write(audio_data)
        self._tts_process.stdin.close()
        while self._tts_process.poll() is None:
            if self._interrupt_flag.is_set():
                self._tts_process.terminate()
                print("[TTS] Interrupted")
                return
            time.sleep(0.05)

    def _speak_piper(self, text: str):
        process = subprocess.Popen(
            ["piper", "--model", self._piper_model,
             "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        audio_data, _ = process.communicate(
            input=text.encode(), timeout=15
        )
        play = subprocess.Popen(
            ["aplay", "-r", "22050", "-f", "S16_LE",
             "-t", "raw", "-"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        play.communicate(input=audio_data)
