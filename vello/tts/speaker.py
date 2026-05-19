import subprocess
import shutil
import glob
import os
import tempfile


class Speaker:

    def __init__(self):
        self.engine = self._detect_engine()
        print(f"[TTS] Engine selected: {self.engine}")

    def _detect_engine(self) -> str:
        # Check Piper AND model file exists
        if shutil.which("piper"):
            model = self._find_piper_model()
            if model:
                self._piper_model = model
                return "piper"
            else:
                print("[TTS] Piper found but no .onnx model — skipping")

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

    def speak(self, text: str):
        if not text or not text.strip():
            return

        # Always print so we can see it even if audio fails
        print(f"[Vello says]: {text}")

        try:
            if self.engine == "piper":
                self._speak_piper(text)
            elif self.engine == "espeak":
                self._speak_espeak(text)
            elif self.engine == "espeak-ng":
                self._speak_espeak_ng(text)
            elif self.engine == "festival":
                self._speak_festival(text)
            elif self.engine == "pyttsx3":
                self._speak_pyttsx3(text)
            else:
                pass  # print_only — already printed above

        except Exception as e:
            print(f"[TTS ERROR] {self.engine} failed: {e}")
            print(f"[TTS] Trying pyttsx3 emergency fallback...")
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
