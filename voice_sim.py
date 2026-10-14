"""Push-to-talk voice controls for Microsoft Flight Simulator."""
import os
import argparse
import sys
from time import sleep

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from SimConnect import AircraftEvents, SimConnect

from commands import parse_command
from open_router import get_command
from play_audio import AudioNotifier
from record_audio import AudioRecorder
from settings import load_config, validate_api_config


def execute_command(events, command):
    parsed = parse_command(command)
    if parsed is None:
        return
    name, parameter = parsed
    event = events.find(name)
    if event is None:
        print(f'SimConnect has no such command: {name}')
        return
    if parameter is None:
        event()
    else:
        event(parameter)
    print(f'Sent to simulator: {command}')


def main():
    config = load_config()
    validate_api_config(config)
    trigger_key = config.get('trigger_key')
    joy_config = config.get('trigger_joystick_button') or {}
    joystick_id = joy_config.get('joystick_id')
    button = joy_config.get('button')
    use_joystick = joystick_id is not None and button is not None
    if not use_joystick and not trigger_key:
        raise ValueError('Configure a trigger_key or both joystick_id and button in config.py.')
    joystick = None
    pygame = None
    sm = None
    notifier = None
    recorder = AudioRecorder(config.get('audio_record_device_id'))
    recording = False
    try:
        if use_joystick:
            import pygame
            pygame.init()
            joystick = pygame.joystick.Joystick(joystick_id)
            joystick.init()
            if not isinstance(button, int) or not 0 <= button < joystick.get_numbuttons():
                raise ValueError('Joystick button is outside the available button range.')
        else:
            import keyboard
            keyboard.key_to_scan_codes(trigger_key)  # Validate before waiting for MSFS.

        print('Waiting to connect to MSFS (Ctrl+C to quit)')
        while sm is None:
            try:
                sm = SimConnect()
            except ConnectionError:
                sleep(5)
        events = AircraftEvents(sm)
        notifier = AudioNotifier(config.get('audio_playback_device_id'))
        print(f'VoiceSim started. STT: {config["speech_to_text_model"]}; generation: {config["generation_model"]}')

        def press():
            nonlocal recording
            if recording:
                return
            try:
                notifier.notify()
                recorder.start()
                recording = True
            except (OSError, RuntimeError) as exc:
                print(f'Audio error: {exc}')

        def release():
            nonlocal recording
            if not recording:
                return
            recording = False
            try:
                audio = recorder.stop()
                if audio is None:
                    return
                with audio:
                    # A WAV header alone means the trigger was released too quickly.
                    if audio.getbuffer().nbytes <= 44:
                        return
                    command = get_command(audio, config)
                if command is not None:
                    execute_command(events, command)
            except (OSError, RuntimeError, ValueError) as exc:
                print(f'Command failed: {exc}')

        while True:
            if joystick is not None:
                for event in pygame.event.get():
                    if (event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP)
                            and event.instance_id == joystick.get_instance_id()
                            and event.button == button):
                        press() if event.type == pygame.JOYBUTTONDOWN else release()
                sleep(0.01)
            else:
                event = keyboard.read_event()
                if event.name == trigger_key:
                    press() if event.event_type == keyboard.KEY_DOWN else release()
    except KeyboardInterrupt:
        print('\nVoiceSim stopped.')
    finally:
        try:
            recorder.close()
        except RuntimeError as exc:
            print(f'Audio cleanup: {exc}')
        if notifier is not None:
            notifier.close()
        if joystick is not None:
            joystick.quit()
        if pygame is not None:
            pygame.quit()
        if sm is not None:
            sm.exit()


def self_test():
    """Verify packaged native libraries/resources without hardware or API calls."""
    import ctypes
    import importlib
    import wave
    import keyboard
    import pygame
    import pyaudio
    import requests
    from settings import RESOURCE_DIR

    simconnect = importlib.import_module('SimConnect.SimConnect')
    ctypes.WinDLL(simconnect._library_path)
    with wave.open(str(RESOURCE_DIR / 'notification.wav'), 'rb') as wav:
        if not wav.getnframes():
            raise ValueError('Notification sound is empty.')
    if not (RESOURCE_DIR / 'config_sample.py').is_file():
        raise ValueError('Sample configuration is missing.')
    if not os.path.isfile(requests.certs.where()):
        raise ValueError('HTTPS certificate bundle is missing.')
    keyboard.key_to_scan_codes('alt')
    print('Self-test passed: SimConnect DLL, audio/input libraries, resources, and HTTPS certificates.')


def cli(argv=None):
    parser = argparse.ArgumentParser(description='Push-to-talk voice controls for Microsoft Flight Simulator.')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--setup', action='store_true', help='Create config.py and commands.txt beside VoiceSim.')
    actions.add_argument('--list-audio-devices', action='store_true', help='Show microphone and playback device IDs.')
    actions.add_argument('--list-joysticks', action='store_true', help='Show joystick IDs.')
    actions.add_argument('--list-joystick-buttons', type=int, metavar='ID', help='Show pressed buttons for a joystick.')
    actions.add_argument('--self-test', action='store_true', help='Check bundled libraries and resources without connecting.')
    args = parser.parse_args(argv)
    try:
        if args.setup:
            load_config()
            from settings import APP_DIR
            print(f'Edit {APP_DIR / "config.py"} to set your OpenRouter key and preferences.')
        elif args.self_test:
            self_test()
        elif args.list_audio_devices:
            from device_tools import list_audio_devices
            list_audio_devices()
        elif args.list_joysticks:
            from device_tools import list_joysticks
            list_joysticks()
        elif args.list_joystick_buttons is not None:
            from device_tools import list_joystick_buttons
            list_joystick_buttons(args.list_joystick_buttons)
        else:
            main()
    except (ValueError, OSError, RuntimeError, SyntaxError) as exc:
        print(f'VoiceSim: {exc}', file=sys.stderr)
        # Keep startup errors visible when the executable is double-clicked.
        if getattr(sys, 'frozen', False) and len(sys.argv) == 1 and sys.stdin.isatty():
            try:
                input('Press Enter to close...')
            except (EOFError, KeyboardInterrupt):
                pass
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(cli())
