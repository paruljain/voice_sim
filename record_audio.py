import pyaudio
import wave
from threading import Thread, Event
import os
import io

if not os.path.isfile('config.py'):
    os.rename('config_sample.py', 'config.py')

from config import config

stop_requested = Event()
done = Event()

def __do_recording():
    global mem_file
    mem_file = io.BytesIO()
    sampleKHz = 16000
    chunk = 1024
    # Open the sound file 
    wf = wave.open(mem_file, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sampleKHz)

    # Initialize PyAudio object
    p = pyaudio.PyAudio()

    # Open the microphone stream
    try:
        stream = p.open(format=p.get_format_from_width(2),
                        channels=1,
                        rate=sampleKHz,
                        input=True,
                        frames_per_buffer=chunk,
                        input_device_index=config['audio_record_device_id'])
    except:
        print('Error opening audio recording device. Check the recording device ID in config.py')
        exit(1)

    # Record the audio
    frames = []
    while not stop_requested.is_set():
        data = stream.read(chunk)
        frames.append(data)
        
    # Stop and close the microphone stream
    stream.stop_stream()
    stream.close()

    # Terminate the PyAudio object
    p.terminate()

    # Save the audio file
    wf.writeframes(b''.join(frames))
    # wf.close()
    done.set()

def start_recording():
    stop_requested.clear()
    done.clear()
    thread = Thread(target=__do_recording)
    thread.start()

def stop_recording():
    stop_requested.set()
    while not done.is_set():
        pass
    return mem_file