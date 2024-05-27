#!/usr/bin/python2


'''
    December 26, 2019
    Arthur Bondar

    Class to use GPIO's of the Rapsberri Pi
    primary use is to display status LED's
    and enable 'Alive' pin to let arduino know Pi is up

'''

import RPi.GPIO as GPIO
from time import sleep
import sys

class Gpio():

    inverse_logic = False

    # [ pin number, in/out, pullup, curr state ]
    io_table = {
        "PowerLED" : { 
            "Pin" : 10, 
            "InOut" : GPIO.OUT, 
            "Pullup" : False,
            "State" : 0 
        },
        "RecLED" : { 
            "Pin" : 22, 
            "InOut" : GPIO.OUT, 
            "Pullup" : False,
            "State" : 0 
        },
        "Rec2LED" : { 
            "Pin" : 9, 
            "InOut" : GPIO.OUT, 
            "Pullup" : False,
            "State" : 0 
        },
        "ErrorLED" : { 
            "Pin" : 27, 
            "InOut" : GPIO.OUT, 
            "Pullup" : False,
            "State" : 0 
        },
        "Switch" : { 
            "Pin" : 19, 
            "InOut" : GPIO.IN, 
            "Pullup" : True,
            "State" : 0 
        },
        "BattLow" : { 
            "Pin" : 13, 
            "InOut" : GPIO.IN, 
            "Pullup" : True,
            "State" : 0 
        },
        # "IO" : { 
        #     "Pin" : 6, 
        #     "InOut" : GPIO.IN, 
        #     "Pullup" : True,
        #     "State" : 0 
        # },
    }

    # Initializes the GPIO
    def __init__(self):

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for p_name, p_info in self.io_table.items():
            if p_info["Pullup"] == True:
                GPIO.setup(p_info["Pin"], p_info["InOut"], pull_up_down = GPIO.PUD_UP)
            else:
                GPIO.setup(p_info["Pin"], p_info["InOut"])

        self._setStates()

    # Sends internal IO values to the GPIOs (not used directly)
    def _setStates(self):
        for p_name, p_info in self.io_table.items():
            if p_info["InOut"] == GPIO.OUT:
                if p_info["State"] == 0:     
                    if self.inverse_logic == True: GPIO.output(p_info["Pin"], GPIO.HIGH)
                    else:                          GPIO.output(p_info["Pin"], GPIO.LOW)
                elif p_info["State"] == 1:   
                    if self.inverse_logic == True: GPIO.output(p_info["Pin"], GPIO.LOW)
                    else:                          GPIO.output(p_info["Pin"], GPIO.HIGH)

    # get internal IO values from the GPIOs (not used directly)
    def _getStates(self):
        for p_name, p_info in self.io_table.items():
            if p_info["InOut"] == GPIO.IN: 
                p_info["State"] = GPIO.input(p_info["Pin"])
                
    # set recording ON and run led OFF
    def setPin(self, pin_name, state):
        for p_name, p_info in self.io_table.items():
            if p_name == pin_name: p_info["State"] = state
        self._setStates()

    # get the value of the pin
    def getPin(self, pin_name):
        self._getStates()
        for p_name, p_info in self.io_table.items():
            if p_name == pin_name: return p_info["State"]

    # set inverselogic
    def inverseLogic(self, enable):
        if enable == True:      self.inverse_logic = True
        elif enable == False:   self.inverse_logic = False

    # set both LED's low
    def clearLEDs(self):
        self.setPin("PowerLED", 0)
        self.setPin("RecLED", 0)
        self.setPin("Rec2LED", 0)
        self.setPin("ErrorLED", 0)

    def togglePin(self, pin_name):
        for p_name, p_info in self.io_table.items():
            if p_name == pin_name and p_info["InOut"] == GPIO.OUT:
                if p_info["State"] == 0:    p_info["State"] = 1
                elif p_info["State"] == 1:    p_info["State"] = 0
        self._setStates()

    # blink run led number of times
    def blink(self, pin_name, interval, times):
        for p_name, p_info in self.io_table.items():
            if p_name == pin_name:
                for i in range (0, times):
                    p_info["State"] = 1
                    self._setStates()
                    sleep(interval)
                    p_info["State"] = 0
                    self._setStates()
                    sleep(interval)

# END GPIO Class


# When class module is started by itself
# Following code is used for testing the LED's
if __name__ == '__main__':

    _io = Gpio()
    _io.inverseLogic(True)
    # Testing Recording LED (RED)
    print("Testing setPin")
    _io.clearLEDs()
    sleep(2)
    _io.setPin("PowerLED", 1)
    sleep(2)
    _io.setPin("PowerLED", 0)
    _io.setPin("RecLED", 1)
    sleep(2)
    _io.setPin("RecLED", 0)
    _io.setPin("ErrorLED", 1)
    sleep(2)
    _io.setPin("ErrorLED", 0)
    _io.setPin("Rec2LED", 1)
    sleep(2)
    _io.setPin("Re2LED", 0)
    _io.clearLEDs()
    
    print("Testing toggle")
    for i in range(10):
        _io.togglePin("RecLED")
        sleep(0.2)

    print("Testing blink")
    _io.blink("PowerLED", 0.2, 10)

    print("Testing input\nSW = {}, BATT = {}".format(str(_io.getPin("Switch")), str(_io.getPin("BattLow"))))
    print("Press the Button ... ")
    sleep(5)
    print("Testing input\nSW = {}, BATT = {}".format(str(_io.getPin("Switch")), str(_io.getPin("BattLow"))))
    _io.clearLEDs()
    print("Test Done")
