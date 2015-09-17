#!/usr/bin/env python
'''
Adaptation of Matt Williamson's joystick.py for communicating with
a serial ppm-sum receiver (xbee + arduino pro).
'''
__author__ = 'Aaron Wood'
import time
from datetime import datetime
import serial

try:
    import pygame.joystick
except ImportError:
    print 'What happened to pygame?'
    quit()

XBEE_DESTINATION_NODE = 'XbeeThesis'
BAUD_RATE = 38400
SERIAL_PORT = 'socket://192.168.0.2:2616'

# 50hz
FREQUENCY = float(1/100)

MIN_PPM = 0
MAX_PPM = 250

AXIS_ROLL = 0
AXIS_PITCH = 1
AXIS_THROTTLE = 2
AXIS_YAW = 3

BUTTON_AUX1 = 1 # Button 2
BUTTON_AUX2 = 2 # Button 2
BUTTON_AUX3 = 3 # Button 3
BUTTON_AUX4 = 0 # Trigger

class ControllerState(object):
    throttle = MIN_PPM
    roll = MIN_PPM
    pitch = MIN_PPM
    yaw = MIN_PPM
    aux1 = MAX_PPM
    aux2 = MIN_PPM
    aux3 = MIN_PPM
    aux4 = MIN_PPM
    t1 = datetime.now()

    def __str__(self):
        status = 'Roll:%d, Pitch:%d, Throttle:%d, Yaw:%d' % (self.roll, self.pitch, self.throttle, self.yaw)
        return status

    def serial_format(self):
        return chr(self.roll) + chr(self.pitch) + chr(self.throttle) + chr(self.yaw) + \
            chr(self.aux1) + chr(self.aux2) + chr(self.aux3) + chr(self.aux4) + \
            chr(254) # sync byte

    # Joystick
    def handleJoyEvent(self, e):
        # Identify joystick axes and assign events
        if e.type == pygame.JOYAXISMOTION:
            axis = e.dict['axis']

            # Convert -1.0 - +1.0 to 0 - 255
            value = int(e.dict['value'] * (MAX_PPM / 2)) + (MAX_PPM / 2)

            print 'Axis: %d, value: %.2f' % (axis, value)

            if axis == AXIS_ROLL:
                self.roll = value
            elif axis == AXIS_PITCH:
                self.pitch = MAX_PPM - value
            elif axis == AXIS_THROTTLE:
                self.throttle = MAX_PPM - value
            elif axis == AXIS_YAW:
                self.yaw = value

        # Button Presses (toggle)
        elif e.type == pygame.JOYBUTTONDOWN:
            # For future expansion
            pass

        print self

# Main method
def main():
    with serial.serial_for_url(SERIAL_PORT, BAUD_RATE, timeout=0) as xbee:
        controller_state = ControllerState()
        watchdog_timer = 0
        joysticks = []

        # Initialize PyGame
        pygame.joystick.init()
        pygame.display.init()

        if not pygame.joystick.get_count():
            print "Please connect a joystick and run again."
            quit()

        print "%s joystick(s) detected." % pygame.joystick.get_count()

        for i in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            joysticks.append(joystick)
            print "Joystick %d: " % (i) + joysticks[i].get_name()

        # Set destination node
        if XBEE_DESTINATION_NODE:
            print 'Setting XBee destination node to %s' % XBEE_DESTINATION_NODE
            xbee.write('+++')
            time.sleep(.5)
            xbee.write('ATDN')
            xbee.write(XBEE_DESTINATION_NODE)
            xbee.write('\r')
            time.sleep(1)
            print 'Destination node set'

        # Run joystick listener loop
        while True:
            poll_started = datetime.now()

            while True:
                # Process joystick events
                e = pygame.event.poll()
                if e.type in (pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION):
                    controller_state.handleJoyEvent(e)
                if e.type == pygame.NOEVENT:
                    break

            # Sleep only long enough to keep the output at 50Hz
            poll_ended = datetime.now()
            sleep_time = FREQUENCY - ((poll_ended - poll_started).microseconds / 1000000.0)

            if sleep_time > 0.0:
                time.sleep(sleep_time)
                xbee.write(controller_state.serial_format())

            write_ended = datetime.now()

            watchdog_timer += (write_ended - poll_started).microseconds

            # Print out the state every once in a while to make sure the program hasn't died
            if watchdog_timer > 5 * 1000000:
                print controller_state
                watchdog_timer = 0

# Allow use as a module or standalone script
if __name__ == "__main__":
    main()