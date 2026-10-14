import pyaudio

p = pyaudio.PyAudio()
try:
    for i in range(p.get_device_count()):
        device = p.get_device_info_by_index(i)
        if device['maxInputChannels'] > 0:
            print('Input Device id', i, '-', device['name'])
        if device['maxOutputChannels'] > 0:
            print('Output Device id', i, '-', device['name'])
finally:
    p.terminate()
    
