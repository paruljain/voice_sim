import pyaudio
import wave
import os

if not os.path.isfile('config.py'):
    os.rename('config_sample.py', 'config.py')

from config import config

# create an audio object
p = pyaudio.PyAudio()

def openDevice():
    # open the file for reading.
    wf = wave.open('notification.wav', 'rb')

    # open stream based on the wave object which has been input.
    try:
        global stream
        stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                        channels = wf.getnchannels(),
                        rate = wf.getframerate(),
                        output = True,
                        output_device_index=config['audio_playback_device_id'])
        # read all the frames in the file into memory
        global data
        data = wf.readframes(wf.getnframes())
        wf.close()
    except:
        print('Error opening audio playback device. Check the playback device ID in config.py')
        exit(1)

openDevice()

def notify():
    try:
        stream.write(data)
    except OSError:
        # It is possible that the device ID was remapped to another device by OS due to USB PnP etc.
        # Try again
        stream.close()
        openDevice()
        stream.write(data)
