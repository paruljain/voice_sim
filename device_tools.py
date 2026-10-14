"""Device discovery shared by the executable and source helper scripts."""
from time import sleep


def list_audio_devices():
    import pyaudio

    interface = pyaudio.PyAudio()
    try:
        for device_id in range(interface.get_device_count()):
            device = interface.get_device_info_by_index(device_id)
            if device['maxInputChannels'] > 0:
                print('Input Device id', device_id, '-', device['name'])
            if device['maxOutputChannels'] > 0:
                print('Output Device id', device_id, '-', device['name'])
    finally:
        interface.terminate()


def list_joysticks():
    import pygame

    pygame.joystick.init()
    try:
        count = pygame.joystick.get_count()
        if not count:
            print('No joysticks detected.')
        for device_id in range(count):
            joystick = pygame.joystick.Joystick(device_id)
            joystick.init()
            try:
                print('ID:', device_id, '----', joystick.get_name())
            finally:
                joystick.quit()
    finally:
        pygame.joystick.quit()


def list_joystick_buttons(device_id):
    import pygame

    pygame.init()
    joystick = None
    try:
        if not 0 <= device_id < pygame.joystick.get_count():
            raise ValueError('Joystick ID is outside the available device range.')
        joystick = pygame.joystick.Joystick(device_id)
        joystick.init()
        print('Waiting for button presses on joystick', joystick.get_name())
        print('Ctrl+C to end')
        while True:
            for event in pygame.event.get():
                if (event.type == pygame.JOYBUTTONDOWN
                        and event.instance_id == joystick.get_instance_id()):
                    print('Joystick Button:', event.button)
            sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        if joystick is not None:
            joystick.quit()
        pygame.quit()
