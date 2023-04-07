from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from record_audio import *
from open_ai import *
from SimConnect import *
from play_audio import notify
import os
from time import sleep

if not os.path.isfile('config.py'):
    os.rename('config_sample.py', 'config.py')

from config import config

# SIMCONNECT init
sm = None
print('Waiting to connect to MSFS')
while sm == None:
    try:
        sm = SimConnect()
        print('Connected to SIM')
    except ConnectionError:
        sleep(5)

ae = AircraftEvents(sm)

# Triggers init
# Keyboard
trigger_key = None
if 'trigger_key' in config and config['trigger_key'] != None and config['trigger_key'] != '':
    trigger_key = config['trigger_key']
    import keyboard

# Joystick
joystick = False
joystick_button = None
if 'trigger_joystick_button' in config:
    joy_config = config['trigger_joystick_button']
    joystick_id = None
    if 'joystick_id' in joy_config and joy_config['joystick_id'] != None:
        joystick_id = joy_config['joystick_id']
    if 'button' in joy_config and joy_config['button'] != None:
        joystick_button = joy_config['button']
    if joystick_id != None and joystick_button != None:
        joystick = True
        import pygame
        pygame.init()
        joystick = pygame.joystick.Joystick(joystick_id)
        joystick.init()

def trigger_pressed():
    notify()
    start_recording()

def trigger_released():
    mem_file = stop_recording()
    mem_file.seek(0)
    cmd = getCommand(mem_file)
    mem_file.close()
    if cmd == None:
        return
    if ',' in cmd:
        # This SIMCONNECT command has a parameter
        try:
            cmd, param = cmd.split(',')
        except ValueError:
            # There may be too many values to unpack error
            # Ignore
            return
        # Process param
        if cmd.endswith('_RADIO_SET'):
            param = int(param.replace('.', ''), 16)
        else:
            param = int(param)

        sim_cmd_fn = ae.find(cmd)
        if sim_cmd_fn != None:
            sim_cmd_fn(param)
            print('Cmd:', cmd, 'Param:', param)
        else:
            print('SIMCONNECT: No such command:', cmd)
    else:
        # This SIMCONNECT command does not have a parameter
        sim_cmd_fn = ae.find(cmd)
        if sim_cmd_fn != None:
            sim_cmd_fn()
            print('Cmd:', cmd)
        else:
            print('SIMCONNECT: No such command:', cmd)

print('VoiceSim started')

try:
    key_down = False
    while True:
        if joystick:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.JOYBUTTONDOWN and event.button == joystick_button:
                    trigger_pressed()
                elif event.type == pygame.JOYBUTTONUP and event.button == joystick_button:
                    trigger_released()
        
        elif trigger_key != None:
            event = keyboard.read_event()
            if not key_down and event.event_type == keyboard.KEY_DOWN and event.name == trigger_key:
                key_down = True
                trigger_pressed()
            elif key_down and event.event_type == keyboard.KEY_UP and event.name == trigger_key:
                key_down = False
                trigger_released()

except KeyboardInterrupt:
    # Some cleanup
    if joystick:
        joystick.quit()
        pygame.quit()
