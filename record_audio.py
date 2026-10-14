"""Capture a push-to-talk recording as a finalized, in-memory WAV."""
import io
from threading import Event, Thread
import wave

import pyaudio


class AudioRecorder:
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.stop_requested = Event()
        self.thread = None
        self.audio = None
        self.error = None

    def start(self):
        if self.thread is not None:
            raise RuntimeError('Previous recording has not been stopped. Restart VoiceSim.')
        self.stop_requested.clear()
        self.audio = None
        self.error = None
        self.thread = Thread(target=self._record, daemon=True)
        self.thread.start()

    def _record(self):
        audio = io.BytesIO()
        interface = None
        stream = None
        try:
            interface = pyaudio.PyAudio()
            stream = interface.open(
                format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                frames_per_buffer=1024, input_device_index=self.device_id,
            )
            with wave.open(audio, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                while not self.stop_requested.is_set():
                    wav.writeframesraw(stream.read(1024, exception_on_overflow=False))
            audio.seek(0)
            self.audio = audio
        except Exception as exc:
            self.error = exc
            audio.close()
        finally:
            # Cleanup failures must not hide the original recording error.
            try:
                if stream is not None:
                    stream.close()
            finally:
                if interface is not None:
                    interface.terminate()

    def stop(self):
        if self.thread is None:
            return None
        self.stop_requested.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError('Microphone did not stop. Restart VoiceSim and check your audio device.')
        self.thread = None
        if self.error is not None:
            raise RuntimeError('Could not record audio. Check audio_record_device_id and microphone access.') from self.error
        return self.audio

    def close(self):
        if self.thread is not None:
            audio = self.stop()
            if audio is not None:
                audio.close()
