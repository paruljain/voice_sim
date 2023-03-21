from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame

pygame.joystick.init()

joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

for joystick in joysticks:
    print('ID:', joystick.get_id(), '----', joystick.get_name())

pygame.joystick.quit()