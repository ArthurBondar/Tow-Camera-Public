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
import ConfigParser, logging  
import datetime as dt 
from defines import *
from time import sleep 
from util import Timer              # sleep function in seconds
from gpio import Gpio               # custom made class to switch led's
from sensors import DS18B20         # custom class to make timing events
from camera import Camera           # wrapper class for picamera module

sys_param = {
    "debug mode"        : "off",
    "software version"  : "Dredge Camera v1.3 April 26, 2020",
    "usb device"        : "/dev/sda1",
    "usb folder"        : "/home/pi/USB",
    "setup file"        : "/home/pi/USB/setup.txt",
    "log file"          : "/home/pi/USB/log.txt",
    "internal log file" : INT_LOG,
    "copy internal log" : "off",
    "camera driver"     : "/home/pi/ffmpeg/ffmpeg",
    "use date-time"     : "off",
    "set date-time"     : "2020-04-26 T 12:30:00",
    "temp cpu"          : "99",
    "temp sensor 1"     : "99",
    "log detail"        : "30",
    "log interval"      : "15",
    "disk check interval":"1",
    "recording led interval":"0.5"
    "hdmi"              : "off",
    "copy kernel log"   : "off",
    "kernel log"        : "/var/log/syslog",
    "run script"        : "off",
    "script"            : ""
}

video_param = {
    "recording program" : "/home/pi/ffmpeg/ffmpeg",
    "recording folder"  : "/home/pi/USB",
    "camera device"     : "/dev/video2",
    "audio device"      : "hw:1",
    "video input codec" : "h264",
    "section length"    : "25",
    "resolution"        : "1920x1080",
    "section index"     : "1",
    "framerate"         : "25",
    "bitrate"           : "10",
    "microphone rate"   : "48000"
}

camera_param = {}

NO_PRESS = 3
LONG_PRESS = 2
SHORT_PRESS = 1
BATTERY_LOW = 1
BATTERY_NORMAL = 0
BUTTON_DELAY_S = 3
BLINK_DELAY_S = 0.1

# Parse data from config file [section] into dictionary {dest_dict}
def parseConfig(dest_dict, section):
    ret = SUCCESS
    msg = section+' parsed succesfully'
    try:
        config = ConfigParser.RawConfigParser()
        config.read(sys_param['setup file'])
        for key in dest_dict:
            try:
                dest_dict[key] = config.get(section, key)
            except ConfigParser.NoOptionError: pass
            except ConfigParser.Error as e: 
                ret = WARN
                msg = str(e) 
    except Exception as e:
        return FAILED, str(e)
    else:
        return ret, msg

# Run Linux Shell Command and wait for completion return 1/0
def run_cmd(args):
    try: 
        output = subprocess.check_output(args, stderr=subprocess.STDOUT).decode()             # run command and wait for output
    except subprocess.CalledProcessError as e:    # catch non 0 process exit status
        logging.warning("run_cmd(): cmd = %s returned = %s output = %s", e.cmd, e.returncode, e.output )
        return FAILED
    except:  
        logging.warning("run_cmd(): cmd %s failed", args)
        return FAILED
    else:
        return SUCCESS, output

# Turns the Pi off if debug mode is not active
def shutdown():
    global io
    io.blink("PowerLED", BLINK_DELAY_S*25, 5)
    try:
        if sys_param["debug_mode"] == "off":
            subprocess.call(['umount', sys_param["usb_d"]])
            sleep(2)
            subprocess.call(['poweroff'])
    else:
        exit(0)

# Test whether a path exists. Returns False for broken symbolic links
def exists(path):
    try:
        os.stat(path)
    except OSError:
        logging.exception("exists(): OS error")
        return FAILED
    else:
        return SUCCESS

# check free disk memory 
def checkDisk(path):
    code, out = run_cmd([ 'df', path ])
    if(code == 1):
        out = ( (out.splitlines()[1]).split() ) [4]
        out = int( out.replace("%", "") )
        if out > 98:    
            logging.warning("checkDisk(): Out of storage memory - %s%", out)
            return FAILED
        else:
            logging.info("checkDisk(): disk space = %s%", out)
            return SUCCESS
    else:
        logging.warning("checkDisk(): disk check command failed")
        return SUCCESS

# return 0 if short press | 1 for long press
def checkButton(_gpio):
    if io.getPin("Switch") == 0:
        sleep(BUTTON_DELAY_S)
        if io.getPin("Switch") == 0: return LONG_PRESS
        else: return SHORT_PRESS
    else: return NO_PRESS

# write message to internal log file (not in USB)
def int_log(msg):
    with open(sys_param['internal log file'], 'a') as _file:
        _file.write(dt.datetime.now().strftime("%Y-%m-%d_%H-%M")+" | "+msg)

# check battery voltage
def getBattery():
    global io
    if io.getPin("BattLow") == 1: return BATTERY_LOW
    else: return BATTERY_NORMAL

def criticalError():
    global io
    for i in range(20):
        io.setPin("PowerLED", 1)
        io.setPin("ErrorLED", 1)
        sleep(BLINK_DELAY_S)
        io.clearLEDs()
        sleep(BLINK_DELAY_S)
    shutdown()

# # # # #

try:
    io = Gpio()
    io.inverseLogic(True)
except Exception as e:
    int_log("failed to instantiate GPIO class")
    sleep(5)
    criticalError()

# Loop for starting and stopping recording
second_loop = False
turnoff = False
while turnoff == False:

    io.clearLEDs()
    io.blink("PowerLED", BLINK_DELAY_S*2, 5)
    io.setPin("PowerLED", 1)

    ''' 
        Waiting to mount the USB
    '''
    if str(sys.argv[1]) == "true":  mounted = True
    else:                           mounted = False
    # LOOP to mount the USB
    while mounted == False:
        btn = checkButton()
        if btn == LONG_PRESS:
            shutdown()
        elif btn == SHORT_PRESS and exists(sys_param["usb_d"]) == True:
            try: msg = subprocess.check_output([ 'mount', '-t', 'exfat', sys_param["usb_d"], sys_param["usb_f"] ] )
            except Exception as e: int_log("failed to mount the USB drive!\r\nerr:"+str(e))
            else: mounted = True
        # Check for low battery condition
        if getBattery() == BATTERY_LOW:
            int_log('battery low detected, shutting down')
            shutdown()

        sleep(BLINK_DELAY_S)
        io.togglePin("ErrorLED")

    io.setPin("ErrorLED", 0)
    sleep(2)

    ''' 
        Waiting for button press to start recording
    '''
    while( checkButton() == NO_PRESS ):
        io.togglePin("PowerLED")
        # Check for low battery condition
        if getBattery() == BATTERY_LOW:
            int_log('battery low detected, shutting down')
            shutdown()
        sleep(BLINK_DELAY_S*2)

    if checkButton() == LONG_PRESS: # long button press - shutdown
        shutdown()

    io.setPin("PowerLED", 1)

    ''' 
        Parsing the setupfile and loading settings
    '''
    # config file parsing
    int_log(str(parseConfig(sys_param, 'debug')))
    int_log(str(parseConfig(video_param, 'video')))
    parseConfig(camera_param, 'camera')
    # log creationg
    logging.basicConfig(
            filename=sys_param['log file'],
            filemode='a',
            format='%(asctime)s %(levelname)-8s %(module)-8s %(message)s',
            level=int(sys_param['log detail'])
    )
    logging.info(" - - - - - - - - - - - - - ")
    logging.info(sys_param["software_v"])
    logging.info("disk mount: %s", msg)
    
    try:
        if video_param['use date-time'] == 'on' and second_loop == False: 
            run_cmd(['date', '+\'%Y-%m-%dT%H:%M:%S\'', '-s', sys_param['set date-time']])
        if sys_param['hdmi'] == "off" and second_loop == False:
            code, out = run_cmd(['/usr/bin/tvservice', '-o'])
            if code == SUCCESS: logging.info("HDMI service disabled")
    except:
        logging.warning("error setting date-time and hdmi", exc_info=True)
        pass

    logging.debug("System parameters: %s", sys_param)
    logging.debug("Video parameters: %s", video_param)
    logging.debug("Camera parameters: %s", camera_param)
    if(sys_param["copy kernel log"] == 'on'):
        try:
            logging.debug("OS log dump: \r\n%s", subprocess.check_output("cat "+sys_param["kernel log"]+" | grep rc.local", shell=True).decode() )
        except: 
            logging.warning("Failed to copy kernel log", exc_info=True)
            pass

    # Recording temperature
    temp_sensor = None
    try:
        temp_sensor = DS18B20()
        sys_param["temp sensor 1"] = temp_sensor.tempC()
    except Exception:
        logging.warning("Failed to create/read temperature sensor", exc_info=True)
        pass
    logging.info("Temperature = "+str(sys_param["temp sensor 1"]))
    sleep(0.5)

    ''' 
        Initializing camera
    '''
    cam = Camera(video_param, camera_param)
    if cam.init() == FAILED: 
        criticalError()
    logging.debug("Caemra parameters:\nVideo: %s\nCamera: %s\nScript: %s\nList Camera parameters: %s", 
                    cam.getVideoParameters(), cam.getCameraParameters(), cam.getVideoScript(), cam.listCameraParameters())

    ''' 
        Starting first video section
    '''
    if cam.start_recording(float(video_param[section index])) == FAILED:
        criticalError()
            
    ''' 
        Recording in a loop
    '''
    io.clearLEDs()
    log_timer = Timer( float(sys_param['log interval']), 0)
    disk_timer = Timer( float(sys_param['disk check interval']), 0)
    led_timer = Timer(0, float(sys_param['recording led interval']))
    '''
    logging.info("main_code: entering recording loop")
    exit_video = False
    while( exit_video == False ):

        # Toggling recording pins
        if led_timer.check() == True:
            io.togglePin("RecLED")
            io.togglePin("Rec2LED")
            led_timer.reset()

        # Checking button press to end the video
        if io.getPin("Switch") == 0:
            logging.warning("Button was pressed, recording stopped")
            exit_video = True

        # Checking video for errors and new sections
        code, out = cam.check_recording(0.1)
        if code != 1:
            io.setPin("ErrorLED", 1)
            log.write(ERROR, "Recording stopped! error: "+out)
            exit_video = True

        # Check for low battery condition
        if io.getPin("BattLow") == 1:
            logging.warning("Battery Low! shutting down")
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
                    logging.warning("Get memory command failed: "+out)
            disk_timer.reset()

        # Logging temperature and parameters
        if log_timer.check() == True:
            # logging DS18B20 sensor
            if temp_sensor != None:
                sys_param["temp1"] = temp_sensor.tempC()
                logging.info("Temperature = "+str(sys_param["temp1"]))

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
        logging.warning("Failed to stop recording and close the camera object, error: "+out)
    vid_section_ID = cam.getSectionID()

    # checking for long button press
    switch = io.getPin("Switch")
    sleep(3)
    if io.getPin("Switch") == 0:
        logging.warning("Long button press detected")
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
logging.info("Shutting down")
shutdown()
