#!/usr/bin/python2

'''
    Changed: October 9, 2018

    Class to make timing evens
    To toggle LED or make GPS recordings

'''

import datetime
from time import sleep              # sleep function in seconds

class Timer():

    INVERVAL_S = 0                  # inverval in seconds
    START = 0
    INHIBIT = False

    # Constructor
    # Uses min and seconds to set the timer
    def __init__(self, _min, _sec):
        self.set_time(_min, _sec)   # Save users time interval
        self.reset()                # set the timer

    # check if time since reset passed
    def check(self):
        if (datetime.datetime.now() - self.START).seconds > self.INVERVAL_S and self.INHIBIT == False:
            self.reset()
            return True
        else:
            return False

    # reset the stopwatch, start new count
    def reset(self):
        self.START = datetime.datetime.now()

    # set time for timer
    def set_time(self, _min, _sec):
        if _min > 0 or _sec > 0: # Save users time interval
            self.INVERVAL_S = _min*60 + _sec
            self.INHIBIT = False
        else:
            self.INHIBIT = True
