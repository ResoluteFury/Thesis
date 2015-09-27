#!/usr/bin/env python
"""
Adaptation of Matt Williamson's joystick.py for communicating with
a serial ppm-sum receiver (xbee + arduino pro).
"""
import time
from datetime import datetime
import serial
try:
    import pygame.joystick
except ImportError:
    print 'What happened to pygame?'
    quit()

__author__ = 'Aaron Wood'


XBEE_DESTINATION_NODE = 'XbeeThesis'
BAUD_RATE = 38400
SERIAL_PORT = 'socket://192.168.1.101:9750'

# 50hz
FREQUENCY = float(1 / 100)

MIN_PPM = 0
MAX_PPM = 250

AXIS_ROLL = 2
AXIS_PITCH = 3
AXIS_THROTTLE = 13
AXIS_YAW = 0

BUTTON_AUX1 = 1  # Button 2
BUTTON_AUX2 = 2  # Button 2
BUTTON_AUX3 = 3  # Button 3
BUTTON_AUX4 = 0  # Trigger

'''
joymap stores the mappings from axis to function of axis
This allows us to extend the controller functionality to new controller types without
rewriting the joystick event handler

Controllers are stored as dictionaries. At minimum, the dictionary must contain usable_axes, roll, pitch, throttle,
and yaw entries.
'''

joymap = {
    'Sony PLAYSTATION(R)3 Controller':
        {
            'usable_axes': [0, 2, 3, 13],
            0: ('yaw', 125, 125),
            2: ('roll', 125, 125),
            3: ('pitch', 125, 125),
            13: ('throttle', 250, 250),
        }
}


class ControllerState(object):
    name = None
    jsmap = None
    js = None
    axes = None
    disable = False
    state = {
        'throttle': MIN_PPM,
        'roll': MIN_PPM,
        'pitch': MIN_PPM,
        'yaw': MIN_PPM,
        'aux1': MAX_PPM,
        'aux2': MAX_PPM,
        'aux3': MAX_PPM,
        'aux4': MAX_PPM
    }
    t1 = datetime.now()

    def __init__(self):
        # Initialize PyGame
        pygame.joystick.init()
        #  pygame.display.init()

        if not pygame.joystick.get_count():
            print "Please connect a joystick and run again."
            quit()

        self.js = pygame.joystick.Joystick(0)
        self.js.init()
        self.name = self.js.get_name()
        self.jsmap = joymap[self.name]
        self.axes = self.jsmap['usable_axes']
        print "Joystick: %s" % self.name

    def __str__(self):
        status = 'Roll:%d, Pitch:%d, Throttle:%d, Yaw:%d' % \
                 (self.state['roll'], self.state['pitch'], self.state['throttle'], self.state['yaw'])
        return status

    def serial_format(self):
        return chr(self.state['roll']) + chr(self.state['pitch']) + chr(self.state['throttle']) + \
               chr(self.state['yaw']) + chr(self.state['aux1']) + chr(self.state['aux2']) + chr(self.state['aux3']) + \
               chr(self.state['aux4']) + chr(254)  # sync byte

    # Joystick
    def handle_joy_event(self, e):
        # Identify joystick axes and assign events
        if e.type == pygame.JOYAXISMOTION and not self.disable:
            # Extract the mapping and compute the value of the axis
            axis = e.axis
            if axis not in self.axes:
                return

            axis_type, mul, offset = self.jsmap[axis]
            value = max(min(e.value * mul + offset, MAX_PPM), MIN_PPM)
            self.state[axis_type] = value

            print 'Axis: %d, value: %.2f' % (axis, value)

        # Button Presses (toggle)
        elif e.type == pygame.JOYBUTTONDOWN:
            # For future expansion
            if e.button == 0:
                self.disable = True
                self.state['aux2'] = MIN_PPM
            if e.button == 3:
                self.disable = False
                self.state['aux2'] = MAX_PPM


# Main method
def main():
    with serial.serial_for_url(SERIAL_PORT, BAUD_RATE, timeout=0) as xbee:
        controller_state = ControllerState()
        watchdog_timer = 0

        # Run joystick listener loop
        while True:
            poll_started = datetime.now()

            while True:
                # Process joystick events
                for e in pygame.event.get():
                    if e.type in (pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION):
                        controller_state.handle_joy_event(e)
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
