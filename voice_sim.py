"""Push-to-talk voice controls for Microsoft Flight Simulator."""
import os
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


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError) as exc:
        raise SystemExit(f'VoiceSim: {exc}') from exc
