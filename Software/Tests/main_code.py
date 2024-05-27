#!/usr/bin/python2

import os, sys, datetime            # essentials
from time import sleep
from log import Log
from util import Timer       	    # custom class to make timing events
import subprocess                   # for subprocess opening

# Declaration of default parameters
SOFTWARE_V = "Sep 9, 2019"
REC_DUR =           2000
DUR =               480             # video duration in minutes
VIDEO_SECTION =     20              # video sections duration min
USB_FOLDER =        "/home/pi/USB/"
SETUP_FILE =        USB_FOLDER + "setup.txt"
LOG_FILE =          USB_FOLDER + "log.txt"
REC_DAY =           3               # keeps track of the current deployment day
# Global Variables
camera = None                       # camera object
poll = 1                            # check for camera thread execution
REC_FILE = ""                       # video section file name variable
led_state = False                   # boolean value to toggle PCB LED
gps_enable = 0                      # boolean value the gps module
DEBUG = False			    # code in debug mode

# Camera default paramters
# array of parameters is passed to raspivid program as cmd args
PARAM = [
    'raspivid',                     # program to call                               (param 0)
    '-t', str(VIDEO_SECTION*60*1000), # videos duration in milliseconds             (param 2)
    '-o', USB_FOLDER+"noname.h264", # output file                                   (param 4)
    '-a', '12',                     # test annotations  20:09:33 10/28/15(param 6)  (param 6)
    '-md', '1',                     # video mode - check table to change            (param 8)
    '-rot', '180',                  # rotation                                      (param 10)
    '-fps', '30',                   # frames per second                             (param 12)
    '-b', '10000000'                # video bit-rate in bits (25M max, 15M good)    (param 14)
    '-n',                           # No Preview
    '-ae', '32,0xff,0x808000',      # Text annotation - Size,TextCol,BackgCol
    '-ih',                          # Add timing to I-frames, needed for software
    '-a', '1024'                    # Text black background
]

# start new camera recording section
# return camera.poll() -> None when running
def start_section(count):
    global camera, REC_FILE
    # assemble filename
    REC_FILE = USB_FOLDER + "s"+str(count)+"_" + datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S') + ".h264"
    PARAM[4] = REC_FILE                             # parameter 4 is filename
    # start camera section
    camera = subprocess.Popen(PARAM,stdout = subprocess.PIPE,stderr = subprocess.PIPE)
    sleep(1)
    log.write( 1,"section ["+str(count)+"] started | camera pid: "+str(camera.pid)+" | ret code: "+str(camera.poll())+" | recording ...")
    return camera.poll()
    log.write( 1,"ERROR: failed setting sleep interval with Arduino ")

# Shutting down routine
# finish recording, shutdown the device
def end_operation():
    global DEBUG
    if DEBUG == False:
    	log.write( 1,"deployment FINISHED - unmounting usb\r\n")
    	subprocess.call(['umount', USB_FOLDER])
    	subprocess.call(['poweroff'])
        sys.exit()
    else:
	log.write( 1,"FINISHED - debug mode")
	sys.exit()


# Run Linux Shell Command as a process and log the result - output in log file
def run_cmd (args, cmd_name):
    out = "none"
    try:
        out = subprocess.check_output(args)             # run command and wait for output
        log.write( 1,cmd_name+" finished succesfully")
        return out
    except subprocess.CalledProcessError as e:          # catch non 0 process exit status
        log.write( 1,"ERROR: "+cmd_name+" failed | command = "+str(e.cmd)+" | exit code = "+str(e.returncode)+" | output = "+str(e.output)+" | out2 = "+str(out))

log = log.write("/home/pi/USB/log.txt")
log.setLevel(3)
log.space()
log.write("START")

# Starting first video section
i_sec = 0                                       # video section counter
if REC_DUR > 0:
    poll = start_section(i_sec)
    i_sec+=1
else:
    log.write( 1,"WARNING: recording duration is 0, device woke up before start time")


rec_timer = Timer(0, 10)

# MAIN LOOP START
# exit conditions: recording time is over / switch triggered / camera failed
# -----------------------------------------------
while REC_DUR > 0:

    # checking if section is finished and starting new section
    # poll == None -> section is still running
    if not poll == None:
        if camera.returncode != 0:		# checking for critinal camera errors
            log.write( 1,"ERROR: Camera process failed | strerr = "+camera.stderr.read().decode()+"| code = "+str(camera.returncode))
            break				# terminate if camera returned non zero
        log.write( 1,"section finished")
        # substract interval from recording time
        # if recording time not over, start new section
        REC_DUR -= VIDEO_SECTION
        if REC_DUR > 0:
            log.write( 1,"recording time left: "+str(REC_DUR)+" min")
            poll = start_section(i_sec)  # starting new camera recording
            i_sec+=1
        sleep(5)

    # Check to see if recording time is over
    # interval for readings in 1 minutes
    '''
    if rec_timer.check() == True:
        if setup_file.getParam("recording") <= 0:
            log.write( 1,"recording time is over")
            log.write( 1,"closing camera process: "+str(camera.pid))
            camera.kill()
            sleep(2)
            break          # exiting the main loop
         # reseting the timer to start a new minute
        rec_timer.reset()
        '''

    sleep(0.25)
    poll = camera.poll()
# -----------------------------------------------
# MAIN LOOP END

