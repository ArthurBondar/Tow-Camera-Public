#!/usr/bin/python2

# file paths
TEMP_VIDEO = "/home/pi/video_temp"
INT_LOG = "/home/pi/internal_log.txt"
VIDEO_FRMT = "mkv"

# function returns
SUCCESS = 0
FAILED = 1
WARN = 2

# defines
NO_PRESS = 3
LONG_PRESS = 2
SHORT_PRESS = 1
BATTERY_LOW = 1
BATTERY_NORMAL = 0

# parameters
BUTTON_DELAY_S = 3
BLINK_DELAY_S = 0.25         # delay for blink led (not recording led)
REC_LOOP_DELAY_S = 0.05