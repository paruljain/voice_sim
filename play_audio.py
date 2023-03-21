import pyaudio
import wave
from config import config

# open the file for reading.
wf = wave.open('notification.wav', 'rb')

# create an audio object
p = pyaudio.PyAudio()

# open stream based on the wave object which has been input.
try:
    stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                    channels = wf.getnchannels(),
                    rate = wf.getframerate(),
                    output = True,
                    output_device_index=config['audio_playback_device_id'])
except:
    print('Error open audio playback device. Check the playback device ID in config.py')
    exit(1)

# read all the frames in the file into memory
data = wf.readframes(wf.getnframes())
wf.close()

def notify():
    stream.write(data)
