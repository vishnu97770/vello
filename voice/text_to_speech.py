import subprocess
import tempfile
import os


class TextToSpeech:

    def __init__(self):
        self.model = "data/models/en_US-lessac-medium.onnx"

    def speak(self, text):

        print("VELLO:", text)

        try:
            # create temp wav file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_file = f.name

            # 🔥 faster + smoother speech
            command = [
                "piper",
                "--model", self.model,
                "--output_file", wav_file,
                "--length_scale", "0.9",     # speed up speech
                "--noise_scale", "0.6",      # smoother voice
                "--noise_w", "0.8"
            ]

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            process.communicate(input=text.encode())

            # 🔥 faster playback (quiet + fast)
            os.system(f"aplay -q {wav_file}")

            # cleanup temp file
            os.remove(wav_file)

        except Exception as e:
            print("TTS Error:", e)