__author__ = 'resfury'

import pygame.joystick
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

pygame.joystick.init()
pygame.display.init()

js = pygame.joystick.Joystick(0)
print "Joystick: %s" % js.get_name()

js.init()

while True:
    for e in pygame.event.get():
        if e.type == pygame.JOYAXISMOTION:
            if e.value > 0.8:
                print "Axis %d is high" % e.axis
        if e.type == pygame.JOYBUTTONDOWN:
            print "Button %d is pressed" % e.button