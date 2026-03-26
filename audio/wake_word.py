import pvporcupine
import pyaudio
import struct


class WakeWordDetector:

    def __init__(self, access_key):

        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["jarvis"]
        )

        self.pa = pyaudio.PyAudio()

        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

    def listen(self):

        print("Listening for wake word...")

        while True:

            pcm = self.stream.read(self.porcupine.frame_length)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)

            keyword_index = self.porcupine.process(pcm)

            if keyword_index >= 0:
                print("Wake word detected!")
                return True