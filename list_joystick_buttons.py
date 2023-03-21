from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
import sys

if len(sys.argv) != 2:
    print('Error: Missing Parameter: Joystick ID')
    exit(1)

pygame.init()
j = pygame.joystick.Joystick(int(sys.argv[1]))
j.init()
print('Waiting for button presses on joystick', j.get_name())
print('CTRL+C to end\n')

try:
    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.JOYBUTTONDOWN:
                print('Joystick Button:', event.button)
except KeyboardInterrupt:
    j.quit()