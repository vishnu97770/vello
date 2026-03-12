import pyaudio
import numpy as np

class AudioListener:
    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000

        self.audio = pyaudio.PyAudio()

        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

    def start_listening(self):
        print("🎤 VELLO is listening... Speak something!")

        while True:
            data = self.stream.read(self.chunk)
            audio_data = np.frombuffer(data, dtype=np.int16)

            volume = np.linalg.norm(audio_data)

            print("Volume:", volume)