#!/usr/bin/python2

'''
    December 26, 2019
    Line Camera Rev. A

    Uses raspberry Pi camera throught raspivid program
    Recording starts and stop at designated times
    Communication with Arduino is impelented with I2C
    Arduino is used a arduino for sleep cycle

    Main program flow:
    1. Check/Wait for USB stick presence
    2. Load and parse the setup file
    3. Wait for recording button press
    4. Start recording in sections
    LOOP:
    5. Record until battery is low or switch is pressed
    END LOOP:
    6. Shutdown

'''

import os, sys, datetime, subprocess         
from time import sleep 
from util import Timer              # sleep function in seconds
from parser import Parser           # custom made class to read setup file
from gpio import Gpio               # custom made class to switch led's
from log import Log                 # custom made class to log program status
from sensors import DS18B20         # custom class to make timing events
from camera import Camera           # wrapper class for picamera module

# Declaration of default parameters
sys_param = {
    "debug_mode" : False,
    "software_v" : "Dredge Camera v1.1 April 2, 2020",
    "usb_d"      : "/dev/sda1",
    "usb_f"      : "/home/pi/USB",
    "setup_f"    : "/home/pi/USB/setup.txt",
    "log_f"      : "/home/pi/USB/log.txt",
    "usb_f"      : "/home/pi/USB",
    "temp_cpu"   : 99,
    "temp1"      : 99,
    "log_lvl"    : 2,
    "log_intrvl" : 15,
}

rec_param = {
    "rec_f"      : "/home/pi/USB",
    "resolution" : "1640x1232",
    "section"    : 25,
    "use_time"   : False,
    "video_mode" : 4,
    "fps"        : 25,
    "rotation"   : 0,
    "bitrate"    : 10,
    "mic_enable" : True,
    "mic_rate" : 48000,
    "mic_gain" : 16
}

# Log levels
ERROR = 0
WARNING = 1
INFO = 2
ALL = 3

# Run Linux Shell Command and wait for processing
# return tuple: 1/0 - success/failuer, output string
def run_cmd(args):
    try: 
        out = subprocess.check_output(args)             # run command and wait for output
    except subprocess.CalledProcessError as e:          # catch non 0 process exit status
        return 0, str("ERROR command = "+str(e.cmd)+" | exit code = "+str(e.returncode)+" | output = "+str(e.output))
    except Exception as e:  
        return 0, str(e)
    else:
        return 1, str(out)

# Turns the Pi off if debug mode is not active
def shutdown():
    global sys_param
    if sys_param["debug_mode"] == False:
    	subprocess.call(['umount', sys_param["usb_d"]])
        sleep(2)
    	subprocess.call(['poweroff'])
    sys.exit()

# Test whether a path exists. Returns False for broken symbolic links
def exists(path):
    try:
        os.stat(path)
    except OSError:
        return False
    return True

# check free disk memory 
def checkDisk(path):
    code, out = run_cmd([ 'df', path ])
    if(code == 1):
        out = ( (out.splitlines()[1]).split() ) [4]
        out = int( out.replace("%", "") )
        if out > 98:
            return 0, "Out of disk space! "+str(out)
        else:
            return 1, "disk space: "+str(out)+"%"
    else:
        return 2, "Command failed"


# # # # #

io = Gpio()
io.inverseLogic(True)
vid_section_ID = 1
second_loop = False

# Loop for starting and stopping recording
turnoff = False
while turnoff == False:

    io.clearLEDs()
    io.blink("PowerLED", 0.25, 5)
    io.setPin("PowerLED", 1)

    ''' 
        Waiting to mount the USB
    '''
    mounted = False
    out = "none"
    # if usb present on boot, skip this step
    if str(sys.argv[1]) == "true": mounted = True
    while mounted == False: 
        if io.getPin("Switch") == 0:
            sleep(3)    
            # long button press - shutdown
            if io.getPin("Switch") == 0:
                io.blink("PowerLED", 0.25, 5)
                shutdown()
            # short press
            elif exists(sys_param["usb_d"]) == True:
                code, out = run_cmd([ 'mount', '-t', 'exfat', sys_param["usb_d"], sys_param["usb_f"] ])
                if code == 1: 
                    mounted = True
        # Check for low battery condition
        if io.getPin("BattLow") == 1:
            io.blink("PowerLED", 0.25, 5)
            shutdown()

        sleep(0.1)
        io.setPin("ErrorLED", 0)
        sleep(0.1)
        io.setPin("ErrorLED", 1)
    io.setPin("ErrorLED", 0)
    sleep(2)

    ''' 
        Waiting for button press to start recording
    '''
    while( io.getPin("Switch") == 1 ):
        io.togglePin("PowerLED")
        # Check for low battery condition
        if io.getPin("BattLow") == 1:
            io.blink("PowerLED", 0.25, 5)
            shutdown()
        sleep(0.2)
    sleep(3)
    if io.getPin("Switch") == 0: # long button press - shutdown
        io.blink("PowerLED", 0.25, 5)
        shutdown()
    io.setPin("PowerLED", 1)

    ''' 
        Parsing the setupfile and loading settings
    '''
    setup = Parser(sys_param["setup_f"])
    log = Log(sys_param["log_f"])
    log.setLevel( int(setup.getParam("logdetail")) )
    sys_param["log_lvl"] = log.getLevel()
    if second_loop == False: log.space()
    log.write(INFO, "START")
    log.write(INFO, sys_param["software_v"])
    log.write(ALL, "Disk mounted: "+out)
    if setup.getParam("debugmode") == "on":     sys_param["debug_mode"] = True
    else:                                       sys_param["debug_mode"] = False

    try:
        rec_param["resolution"] = setup.getParam("resolution")
        p = setup.getParam("section")
        if p != "None":
            if int(p) >= 0: rec_param["section"] = int(p)
        p = setup.getParam("framerate")
        if p != "None":
            if int(p) >= 1 and int(p) <= 90: rec_param["fps"] = int(p)
        p = setup.getParam("rotation")
        if p != "None":
            if int(p) >= 0 and int(p) <= 359: rec_param["rotation"] = int(p)
        p = setup.getParam("bitrate")
        if p != "None":
            if int(p) >= 0 and int(p) <= 25: rec_param["bitrate"] = int(p)
        p = setup.getParam("loginterval")
        if p != "None":
            if int(p) >= 0 and int(p) <= 999: sys_param["log_intrvl"] = int(p)

        if setup.getParam("usemic") != "on": rec_param["mic_enable"] = False
        p = setup.getParam("micsamplerate")
        if p != "None":
            if int(p) >= 2000 and int(p) <= 192000: rec_param["mic_rate"] = int(p)
        p = setup.getParam("micgain")
        if p != "None": rec_param["mic_gain"] = int(p)
    except Exception as e:
        log.write(ERROR, "Error during setup file parsing -> "+str(e))
        pass
        
    try:
        if setup.getParam("usedate-time") == "on" and second_loop == False: 
            rec_param["use_time"] = True
            new_dt = setup.getParam("setdate-time")
            code, out = run_cmd(['date', '+\'%Y-%m-%dT%H:%M:%S\'', '-s', new_dt])
            if code == 0:   log.write(WARNING, "Failed to set datetime, error: "+out)
            elif code == 1: log.write(INFO, "Datetime set succesfully")
        if setup.getParam("hdmi") == "off" and second_loop == False:
            code, out = run_cmd(['/usr/bin/tvservice', '-o'])
            if code != 1:   log.write(WARNING, "Failed to disable HDMI service, error: "+out)
            else:           log.write(INFO, "HDMI service disabled")
    except Exception as e:
        log.write(ERROR, "Error during setup file parsing -> "+str(e))
        pass

    log.write(ALL, "System parameters: "+str(sys_param))
    log.write(ALL, "Video parameters: "+str(rec_param))
    if(sys_param["log_lvl"] == ALL):
        log.write(ALL, "OS log: " + str(subprocess.check_output("cat /var/log/syslog | grep rc.local", shell=True).decode()) )

    # Recording temperature
    temp_sensor = None
    try:
        temp_sensor = DS18B20()
        sys_param["temp1"] = temp_sensor.tempC()
    except Exception:
        log.write(WARNING, "Failed to read temperature sensor")
        pass
    log.write(INFO, "Temperature = "+str(sys_param["temp1"]))
    sleep(2)



    ''' 
        Initializing camera
    '''
    cam = Camera(rec_param)
    code, out = cam.init()
    log.write(ALL, out)
    # failed to initialize the camera module
    while (code != 1):
        io.setPin("ErrorLED", 1)
        log.write(ERROR, "Failed to initialized the camera module, error: "+out)
        sleep(20)
        # Check for low battery condition
        if io.getPin("BattLow") == 1:
            log.write(WARNING, "Battery Low! shutting down")
            io.blink("PowerLED", 0.25, 5)
            shutdown()
        # check for switch press to reboot
        if io.getPin("Switch") == 0:
            log.write(WARNING, "Cannot init the camera! switch forced shutdown")
            shutdown()
    log.write(ALL, "Video parameters from camera module: "+cam.parameters())
    sleep(2)


    ''' 
        Starting first video section
    '''
    cam.setSectionID(vid_section_ID)
    code, out = cam.start_recording()
    code2, out2 = cam.check_mic()
    if code2 != 1: log.write(WARNING, out2)
    log.write(ALL, "Camera start: "+out)
    log.write(ALL, "Mic start: "+out2)
    while (code != 1):
        io.setPin("ErrorLED", 1)
        log.write(ERROR, "Failed to start recording, error: "+out)
        sleep(20)
        code, out = cam.start_recording()

        # Check for low battery condition
        if io.getPin("BattLow") == 1:
            log.write(WARNING, "Battery Low! shutting down")
            io.blink("PowerLED", 0.25, 5)
            shutdown()

        # check for switch press to reboot
        if io.getPin("Switch") == 0:
            log.write(WARNING, "Cannot start the recording! switch forced shutdown")
            shutdown()
            
    sleep(1)
    if debug_timer.check() == True and sys_param["log_lvl"] == ALL:
        log.write(ALL, "Recording return: "+out)
        code, out = cam.check_mic()
        log.write(ALL, "Mic return: "+out)
        debug_timer.reset()
    log.write(INFO, "Recording started")


    ''' 
        Recording in a loop
    '''
    io.setPin("RecLED", 0)
    io.setPin("Rec2LED", 0)
    io.setPin("PowerLED", 0)
    debug_timer = Timer(0, 20)
    log_timer = Timer(sys_param['log_intrvl'], 0)
    disk_timer = Timer(1, 0)
    led_timer = Timer(0, 0.5)

    log.write(ALL, "Entering main loop")
    exit_video = False
    while( exit_video == False ):

        # Toggling recording pins
        if led_timer.check() == True:
            io.togglePin("RecLED")
            io.togglePin("Rec2LED")
            led_timer.reset()

        # Checking button press to end the video
        if io.getPin("Switch") == 0:
            log.write(WARNING, "Button was pressed, recording stopped")
            exit_video = True

        # Checking video for errors and new sections
        code, out = cam.check_recording(0.1)
        if code != 1:
            io.setPin("ErrorLED", 1)
            log.write(ERROR, "Recording stopped! error: "+out)
            exit_video = True

        # debug video info
        if debug_timer.check() == True and sys_param["log_lvl"] == ALL:
            log.write(ALL, "Recording return: "+out)
            code, out = cam.check_mic()
            log.write(ALL, "Mic return: "+out)
            debug_timer.reset()

        # Check for low battery condition
        if io.getPin("BattLow") == 1:
            log.write(WARNING, "Battery Low! shutting down")
            exit_video = True

        # Checking disk space
        if disk_timer.check() == True:
            code, out = checkDisk(sys_param["usb_f"])
            if code != 1:
                if(code == 0):
                    log.write(ERROR, out)
                    exit_video = True
                elif(code == 2):
                    io.setPin("ErrorLED", 1)
                    log.write(WARNING, "Get memory command failed: "+out)
            disk_timer.reset()

        # Logging temperature and parameters
        if log_timer.check() == True:
            # logging DS18B20 sensor
            if temp_sensor != None:
                sys_param["temp1"] = temp_sensor.tempC()
                log.write(INFO, "Temperature = "+str(sys_param["temp1"]))

            # logging general system parameters
            log.logParam(sys_param["usb_f"])
            log_timer.reset()

    # # # # # END REC LOOP

    '''
        Stopping video
    '''
    io.setPin("RecLED", 0)
    io.setPin("Rec2LED", 0)
    code, out = cam.close_camera()
    if code != 1:
        log.write(WARNING, "Failed to stop recording and close the camera object, error: "+out)
    vid_section_ID = cam.getSectionID()

    # checking for long button press
    switch = io.getPin("Switch")
    sleep(3)
    if io.getPin("Switch") == 0:
        log.write(WARNING, "Long button press detected")
        turnoff = True
    else:
        sys.argv[1] = "false"
        turnoff = False
        code, out = run_cmd([ 'umount', sys_param["usb_d"] ])
        if code != 1:   
            log.write(ERROR, "Failed to unmount the USB drive!: "+out)
            io.blink("ErrorLED", 0.25, 30)
            shutdown()
        # cleaning the objects and jumping to new recording
        del cam, temp_sensor, log_timer, disk_timer, led_timer, debug_timer, setup, log
        second_loop = True

    
# # # # # END PROGRAM LOOP

io.blink("PowerLED", 0.25, 5)
io.setPin("PowerLED", 1)
log.write(INFO, "Shutting down")
shutdown()
