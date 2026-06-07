"""
Speaker — multi-engine TTS with sentence-level streaming.

Engine priority:
  1. Kokoro v1.0  — 24kHz neural, offline, ~400ms first-chunk latency
  2. Piper ONNX   — 22kHz neural, offline, fast
  3. espeak-ng    — robotic fallback, always available
  4. espeak       — older robotic fallback
  5. festival     — legacy fallback
  6. pyttsx3      — Python fallback
  7. print_only   — silent emergency fallback

Why sentence-level streaming matters:
  With a blocking full-text approach, a 4-sentence response takes 3-5 seconds
  before the user hears anything. Streaming plays sentence 1 while sentence
  2-4 are being synthesized, cutting perceived latency to ~400ms.
"""
import subprocess
import shutil
import threading
import queue
import glob
import time
import os
import numpy as np

from vello.tts.preprocessor import clean_for_tts, split_into_chunks


class Speaker:

    SAMPLE_RATE = 24000   # Kokoro native rate

    def __init__(self):
        self._interrupt_flag = threading.Event()
        self._tts_process    = None
        self.engine          = self._detect_engine()
        self._kokoro_pipeline = None
        if self.engine == "kokoro":
            self._init_kokoro()
        print(f"[TTS] Engine selected: {self.engine}")

    # ── Engine detection ───────────────────────────────────────────────────────

    def _detect_engine(self) -> str:
        try:
            import kokoro          # noqa: F401
            import sounddevice     # noqa: F401
            return "kokoro"
        except ImportError:
            pass

        if shutil.which("piper"):
            model = self._find_piper_model()
            if model:
                self._piper_model = model
                return "piper"
            print("[TTS] Piper found but no model — run: python -m vello.tts.piper_setup")

        for eng in ("espeak-ng", "espeak"):
            if shutil.which(eng):
                return eng

        if shutil.which("festival"):
            return "festival"

        try:
            import pyttsx3   # noqa: F401
            return "pyttsx3"
        except ImportError:
            pass

        return "print_only"

    def _find_piper_model(self) -> str | None:
        patterns = [
            os.path.expanduser("~/.vello/models/**/*.onnx"),
            os.path.expanduser("~/.local/share/piper/**/*.onnx"),
            "/opt/vello/models/**/*.onnx",
            "./models/**/*.onnx",
        ]
        for p in patterns:
            files = glob.glob(p, recursive=True)
            if files:
                return files[0]
        return None

    def _init_kokoro(self):
        """Load Kokoro pipeline once at startup — not per utterance."""
        try:
            from kokoro import KPipeline
            # lang_code='a' = American English
            self._kokoro_pipeline = KPipeline(lang_code='a')
            print("[TTS] Kokoro pipeline ready (af_heart voice, 24kHz)")
        except Exception as e:
            print(f"[TTS] Kokoro init failed: {e} — falling back to espeak")
            self.engine = "espeak-ng" if shutil.which("espeak-ng") else "espeak"

    # ── Public API ─────────────────────────────────────────────────────────────

    def speak(self, text: str, interrupt_event: threading.Event | None = None):
        """Speak text. Preprocesses, then streams sentence by sentence."""
        if not text or not text.strip():
            return

        self._interrupt_flag = interrupt_event or threading.Event()
        cleaned = clean_for_tts(text)
        if not cleaned:
            return

        print(f"[Vello says]: {text}")

        try:
            if self.engine == "kokoro":
                self._speak_kokoro_streaming(cleaned)
            elif self.engine == "piper":
                self._speak_piper(cleaned)
            elif self.engine == "espeak-ng":
                self._speak_subprocess(["espeak-ng", "-s", "145", "-v", "en-us", cleaned])
            elif self.engine == "espeak":
                self._speak_subprocess(["espeak", "-s", "145", "-v", "en-us", "-a", "200", cleaned])
            elif self.engine == "festival":
                self._speak_festival(cleaned)
            elif self.engine == "pyttsx3":
                self._speak_pyttsx3(cleaned)
        except Exception as e:
            print(f"[TTS] {self.engine} failed: {e}")
            self._emergency_fallback(cleaned)

    def interrupt(self):
        """Stop playback immediately."""
        self._interrupt_flag.set()
        if self._tts_process and self._tts_process.poll() is None:
            self._tts_process.terminate()

    def speak_streaming(self, text_generator, interrupt_event: threading.Event | None = None):
        """
        Stream LLM tokens into TTS in real time.
        text_generator yields text chunks (words/sentences from LLM stream).
        Plays each sentence as soon as it's complete — no waiting for full response.
        """
        self._interrupt_flag = interrupt_event or threading.Event()
        buffer = ""

        for chunk in text_generator:
            if self._interrupt_flag.is_set():
                break
            buffer += chunk
            # Speak whenever a sentence boundary is reached
            sentences = _extract_complete_sentences(buffer)
            for sentence in sentences:
                if self._interrupt_flag.is_set():
                    break
                cleaned = clean_for_tts(sentence)
                if cleaned:
                    print(f"[Vello says]: {cleaned}")
                    self._speak_one_chunk(cleaned)
                buffer = buffer[len(sentence):].lstrip()

        # Flush remaining text
        if buffer.strip() and not self._interrupt_flag.is_set():
            cleaned = clean_for_tts(buffer)
            if cleaned:
                print(f"[Vello says]: {cleaned}")
                self._speak_one_chunk(cleaned)

    # ── Kokoro engine (primary) ────────────────────────────────────────────────

    def _speak_kokoro_streaming(self, text: str):
        """
        Generate and play audio sentence by sentence.
        First chunk starts playing in ~400ms regardless of total response length.
        """
        if not self._kokoro_pipeline:
            self._emergency_fallback(text)
            return

        import sounddevice as sd

        chunks = split_into_chunks(text, max_chars=200)
        if not chunks:
            chunks = [text]

        for chunk in chunks:
            if self._interrupt_flag.is_set():
                break
            if not chunk.strip():
                continue
            try:
                audio_data = self._kokoro_synthesize(chunk)
                if audio_data is None:
                    continue
                self._play_numpy(audio_data, self.SAMPLE_RATE)
            except Exception as e:
                print(f"[TTS] Kokoro chunk failed: {e}")
                self._speak_subprocess(
                    ["espeak-ng" if shutil.which("espeak-ng") else "espeak",
                     "-s", "145", chunk]
                )

    def _kokoro_synthesize(self, text: str) -> np.ndarray | None:
        """Synthesize one chunk of text. Returns float32 numpy array or None."""
        try:
            gen = self._kokoro_pipeline(
                text,
                voice='af_heart',
                speed=0.95,      # slightly slower = more natural for assistant
                split_pattern=None,
            )
            parts = []
            for _, _, audio in gen:
                arr = audio.numpy() if hasattr(audio, 'numpy') else np.array(audio)
                parts.append(arr)
            return np.concatenate(parts) if parts else None
        except Exception as e:
            print(f"[TTS] Kokoro synthesis error: {e}")
            return None

    def _speak_one_chunk(self, text: str):
        """Synthesize and play a single chunk — used by speak_streaming."""
        if self.engine == "kokoro" and self._kokoro_pipeline:
            audio = self._kokoro_synthesize(text)
            if audio is not None:
                self._play_numpy(audio, self.SAMPLE_RATE)
                return
        # Fallback for non-Kokoro or synthesis failure
        cmd = (["espeak-ng", "-s", "145", text]
               if shutil.which("espeak-ng")
               else ["espeak", "-s", "145", text])
        self._speak_subprocess(cmd)

    def _play_numpy(self, audio: np.ndarray, rate: int):
        """Play float32 numpy audio via sounddevice with interrupt support."""
        try:
            import sounddevice as sd
            # sounddevice expects float32 in [-1.0, 1.0]
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            peak = np.abs(audio).max()
            if peak > 1.0:
                audio = audio / peak

            sd.play(audio, rate, blocking=False)
            # Poll for interrupt while audio plays
            duration = len(audio) / rate
            elapsed  = 0.0
            interval = 0.05
            while elapsed < duration:
                if self._interrupt_flag.is_set():
                    sd.stop()
                    print("[TTS] Interrupted")
                    return
                time.sleep(interval)
                elapsed += interval
            sd.wait()
        except Exception as e:
            print(f"[TTS] Playback error: {e}")

    # ── Other engine implementations ───────────────────────────────────────────

    def _speak_piper(self, text: str):
        piper_proc = subprocess.Popen(
            ["piper", "--model", self._piper_model, "--output-raw"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        audio_data, _ = piper_proc.communicate(input=text.encode(), timeout=15)
        if self._interrupt_flag.is_set():
            return
        self._tts_process = subprocess.Popen(
            ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        self._tts_process.stdin.write(audio_data)
        self._tts_process.stdin.close()
        self._wait_interruptible(self._tts_process)

    def _speak_subprocess(self, cmd: list):
        self._tts_process = subprocess.Popen(cmd, stderr=subprocess.DEVNULL)
        self._wait_interruptible(self._tts_process)

    def _wait_interruptible(self, proc):
        while proc.poll() is None:
            if self._interrupt_flag.is_set():
                proc.terminate()
                print("[TTS] Interrupted")
                return
            time.sleep(0.05)

    def _speak_festival(self, text: str):
        proc = subprocess.Popen(
            ["festival", "--tts"],
            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=text.encode(), timeout=30)

    def _speak_pyttsx3(self, text: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.say(text)
        engine.runAndWait()
        engine.stop()

    def _emergency_fallback(self, text: str):
        """Last-resort: try espeak, then just print."""
        for cmd in (["espeak-ng", "-s", "145", text],
                    ["espeak", "-s", "145", text]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, timeout=10, stderr=subprocess.DEVNULL)
                    return
                except Exception:
                    pass
        print(f"[TTS FALLBACK] {text}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_complete_sentences(text: str) -> list[str]:
    """
    Pull complete sentences from the front of a streaming text buffer.
    Returns only utterances ending with sentence-final punctuation.
    """
    import re
    sentences = []
    pattern   = re.compile(r'[^.!?]*[.!?]+\s*')
    for m in pattern.finditer(text):
        sentences.append(m.group())
    return sentences
