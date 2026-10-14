"""Play the notification and release audio devices on exit."""
import wave

import pyaudio

from settings import RESOURCE_DIR


class AudioNotifier:
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.interface = pyaudio.PyAudio()
        self.stream = None
        with wave.open(str(RESOURCE_DIR / 'notification.wav'), 'rb') as wav:
            self.width = wav.getsampwidth()
            self.channels = wav.getnchannels()
            self.rate = wav.getframerate()
            self.data = wav.readframes(wav.getnframes())

    def _open(self):
        self.stream = self.interface.open(
            format=self.interface.get_format_from_width(self.width),
            channels=self.channels, rate=self.rate, output=True,
            output_device_index=self.device_id,
        )

    def notify(self):
        try:
            if self.stream is None:
                self._open()
            self.stream.write(self.data)
        except OSError:
            if self.stream is not None:
                self.stream.close()
                self.stream = None
            self._open()
            self.stream.write(self.data)

    def close(self):
        try:
            if self.stream is not None:
                self.stream.close()
                self.stream = None
        finally:
            self.interface.terminate()
