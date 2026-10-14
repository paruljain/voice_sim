from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

pygame.joystick.init()

try:
    for device_id in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(device_id)
        joystick.init()
        print('ID:', device_id, '----', joystick.get_name())
        joystick.quit()
finally:
    pygame.joystick.quit()
