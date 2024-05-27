#!/usr/bin/python2

'''
    July 20, 2020
    Version 1.3
    Tow Camera Rev. A

    Main program flow:
    LOOP
        1.  Wait for USB presence and button press
        2.  Load and parse the setup file
        3.  Start recording in sections
        LOOP
            4.  Record until one of the following conditions is true:
                - button pressed
                - battery is low
                - disk out of space
                - error occured
        END LOOP
        5. umount USB
    END LOOP:
    6.  shutdown

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
    "software version"      : "Dredge Camera v1.3 (30/05/2020)",
    "set date-time"         : "2020-05-30 T 12:30:00",
    "usb device"            : "/dev/sda1",
    "usb folder"            : "/home/pi/USB",
    "setup file"            : "/home/pi/USB/setup.txt",
    "log file"              : "/home/pi/USB/log.txt",
    "log detail"            : "20",
    "debug mode"            : "off",
    "internal log file"     : INT_LOG,
    "status update interval": "2",
    "status log interval"   : "10",
    "sensor log interval"   : "5",
    "disk check interval"   : "2",
    "led interval"          : "0.25",
    "hdmi"                  : "off",
    "copy logs"             : "off",
    "run script"            : "off",
    "script path"           : "/home/pi/Software/script.sh"
}

sys_status = {
    "timestamp"         : "2020-05-27 T 12:30:00",
    "status"            : "booting",
    "usb mounted"       : "false",
    "temp sensor 1"     : "Not read",
    "cpu temp"          : "Not read",
    "cpu usage"         : "Not read",
    "cpu freq"          : "Not read",
    "cpu throttle"      : "Not read",
    "disk usage"        : "Not read",
    "ram usage"         : "Not read"
}

video_param = {
    "recording program" : "/home/pi/ffmpeg/ffmpeg",
    "video format"      : VIDEO_FRMT,
    "recording folder"  : "/home/pi/USB",
    "camera device"     : "/dev/video2",
    "audio device"      : "hw:1,0",
    "section length"    : "30",
    "resolution"        : "1920x1080",
    "section index"     : "1",
}

camera_param = {

}

# Parse data from config file [section] into dictionary {dest_dict}
def parseConfig(dest_dict, section):
    ret = SUCCESS
    msg = section+' parsed succesfully'
    try:
        config = ConfigParser.RawConfigParser()
        config.read(sys_param['setup file'])
        for item in config.items(section):
            try:
                dest_dict[item[0]] = item[1]
            except ConfigParser.NoOptionError: pass
            except ConfigParser.Error as e: 
                ret = WARN
                msg = str(e) 
    except Exception as e:
        return FAILED, str(e)
    else:
        return ret, msg

# Run Linux Shell Command and wait for completion return 1/0
def run_cmd(args, shell=False):
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT, shell=shell).decode()
    except subprocess.CalledProcessError as e:    # catch non 0 process exit status
        logging.warning("run_cmd(): cmd = %s returned = %s output = %s", e.cmd, e.returncode, e.output )
        return FAILED, "Failed"
    except:  
        logging.warning("run_cmd(): cmd = %s failed", args)
        return FAILED, "Failed"
    else:
        return SUCCESS, output

# Turns the Pi off if debug mode is not active
def shutdown():
    global io
    io.blink("PowerLED", BLINK_DELAY_S, 5)
    if sys_param["debug mode"] == "off":
        try: logging.shutdown()
        except: pass
        try: subprocess.call(['umount', sys_param["usb device"]])
        except: pass
        sleep(2)
        try: subprocess.call(['poweroff'])
        except: pass
    exit(0)

# Test whether a path exists. Returns False for broken symbolic links
def exists(path):
    try:
        os.stat(path)
    except OSError:
        int_log("main_code: exists(): path - {} doesnt exists".format(path))
        return FAILED
    else:
        return SUCCESS

# check free disk memory 
def checkDisk(path):
    code, out = run_cmd([ 'df', path ])
    if code == SUCCESS:
        out = ( (out.splitlines()[1]).split() ) [4]
        out = int( out.replace("%", "") )
        if out > 98:    
            logging.warning( "checkDisk(): out of storage memory = {}%".format(out) )
            return FAILED
        else:
            logging.info( "checkDisk(): disk space = {}%".format(out) )
            return SUCCESS
    else:
        logging.warning("checkDisk(): disk check command failed")
        return SUCCESS

# return 0 if short press | 1 for long press
def getButton():
    global io
    if io.getPin("Switch") == 0:
        io.clearLEDs()
        sleep(BUTTON_DELAY_S)
        if io.getPin("Switch") == 0: return LONG_PRESS
        else: return SHORT_PRESS
    else: return NO_PRESS

# write message to internal log file (not in USB)
def int_log(msg):
    with open(sys_param['internal log file'], 'a') as _file:
        _file.write(dt.datetime.now().strftime("%Y/%m/%d %H:%M:%S")+" | "+msg+"\r\n")

# check battery voltage
def getBattery():
    global io
    if io.getPin("BattLow") == 1: return BATTERY_LOW
    else: return BATTERY_NORMAL

# indicate an error and shutdown the system
def criticalError():
    global io
    for i in range(15):
        io.setPin("PowerLED", 1)
        io.setPin("ErrorLED", 1)
        sleep(BLINK_DELAY_S)
        io.clearLEDs()
        sleep(BLINK_DELAY_S)
    shutdown()

# populate system status variables
def updateStatus():
    try:
        global sys_status
        code, out = (FAILED, "None")
        sys_status["timestamp"] = dt.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        sys_status["temp sensor 1"] = str( temp_sensor.tempC() )
        code, out = run_cmd(['/opt/vc/bin/vcgencmd', 'measure_temp'])
        if code == SUCCESS: sys_status['cpu temp'] = out.decode().splitlines()[0]
        code, out = run_cmd(['uptime'])
        if code == SUCCESS: sys_status['cpu usage'] = (out.decode().splitlines()[0])[30:-1]
        code, out = run_cmd(['/opt/vc/bin/vcgencmd', 'measure_clock', 'arm'])
        if code == SUCCESS: sys_status['cpu freq'] = (out.decode().splitlines())[0]
        code, out = run_cmd(['/opt/vc/bin/vcgencmd', 'get_throttled'])
        if code == SUCCESS: sys_status['cpu throttle'] = out.decode().splitlines()[0]
        code, out = run_cmd(['df', '-h', sys_param['usb folder'] ])
        if code == SUCCESS: sys_status['disk usage'] = (out.decode().splitlines())[1]
        code, out = run_cmd(['free', '-h'])
        if code == SUCCESS: sys_status['ram usage'] = (out.decode().splitlines()[1])[39:-36]
    except:
        logging.warning("updateStatus(): error during status update", exc_info=True)
        pass

# # # # #

try:
    io = Gpio()
    io.inverseLogic(True)
except Exception as e:
    int_log("failed to instantiate GPIO class")
    criticalError()
io.clearLEDs()
io.blink("PowerLED", BLINK_DELAY_S, 5)
io.setPin("PowerLED", 1)

# checking if USB was pre-mounted by rc.local script
try: sys_status['usb mounted'] = sys.argv[1]
except:
    int_log("failed to read usb status flag from system arguments")
    pass

'''
    LOOP: main program loop recording and USB swaping
'''
second_loop = False
end_operation = False
while end_operation == False:

    ''' 
        Wait for USB presence and button press
    '''
    disk_mount_message = "None"
    mounted = False
    while mounted == False:
        btn = getButton()
        if btn == LONG_PRESS: 
            shutdown()
        elif btn == SHORT_PRESS:
            if sys_status['usb mounted'] == "true":
                    mounted = True
            elif exists(sys_param["usb device"]) == SUCCESS:
                try: disk_mount_message = subprocess.check_output([ 'mount', '-t', 'exfat', sys_param["usb device"], sys_param["usb folder"] ] )
                except Exception as e: int_log("failed to mount the USB drive!\r\nerr:"+str(e))
                else:
                    sys_status['usb mounted'] = "true"
                    mounted = True
            else:
                io.blink("ErrorLED", BLINK_DELAY_S, 10)
                io.setPin("ErrorLED", 0)
        # Check for low battery condition
        if getBattery() == BATTERY_LOW:
            int_log('battery low detected, shutting down')
            shutdown()
        
        io.togglePin("PowerLED")
        sleep(BLINK_DELAY_S)

    ''' 
        Parsing the setupfile and loading settings
    '''
    # config file parsing
    parseConfig(sys_param, 'system')
    parseConfig(video_param, 'video')
    parseConfig(camera_param, 'camera')
    # log creationg
    logging.basicConfig(
            filename=sys_param['log file'],
            filemode='a',
            format='%(asctime)s %(levelname)-8s %(module)-11s %(message)s',
            level=int(sys_param['log detail'])
    )
    logging.info("\r\n- - - - - - - - - - - - - - -")
    logging.info(sys_param["software version"])
    logging.debug("disk mount message: %s", disk_mount_message)
    logging.debug("parameter dump\r\nsystem: %s\r\nvideo: %s\r\ncamera: %s", str(sys_param), str(video_param), str(camera_param))

    try:
        if second_loop == False: 
            run_cmd(['date', '+\'%Y-%m-%dT%H:%M:%S\'', '-s', sys_param['set date-time']])
            logging.info("date-time is set")
            if sys_param['hdmi'] == "off":
                run_cmd(['/usr/bin/tvservice', '-o'])
                logging.debug("HDMI service disabled")
        if sys_param["copy logs"] == 'on':  # copying internal script
            run_cmd(['mv', '-r', '/var/log', sys_param['usb folder'] ])
            run_cmd(['mv',  sys_param['internal log file'], sys_param['usb folder'] ])
            logging.info("copy logs finished")
        if sys_param["run script"] == 'on':         # runing custom script
            logging.info("custom script finished - %s", run_cmd([ 'bash', sys_param["script path"] ]) )
    except:
        logging.warning("error in date-time / hdmi / copy log / script / int log", exc_info=True)
        pass

    # Recording temperature
    temp_sensor = None
    try:
        temp_sensor = DS18B20()
        sys_param["temp sensor 1"] = temp_sensor.tempC()
    except Exception:
        logging.warning("failed to create/read temperature sensor", exc_info=True)
        pass
    else:
        logging.info("temp sensor 1 = "+str(sys_param["temp sensor 1"]))

    # Initializing camera
    cam = Camera(video_param, camera_param)
    if cam.init() == FAILED: 
        criticalError()
    logging.debug("camera parameters:\r\nVideo: %s\r\nCamera: %s\r\nScript: %s\r\nList Camera parameters: \r\n%s", 
                    cam.getVideoParameters(), cam.getCameraParameters(), cam.getVideoScript(), cam.listCameraParameters())

    # Starting first video section
    if cam.start_recording(int(video_param['section index'])) == FAILED:
        criticalError()
            
    ''' 
        Recording loop
    '''
    io.clearLEDs()
    status_update_timer = Timer( float(sys_param['status update interval']), 0)
    status_log_timer = Timer( float(sys_param['status log interval']), 0)
    sensor_log_timer = Timer( float(sys_param['sensor log interval']), 0)
    disk_timer = Timer( float(sys_param['disk check interval']), 0)
    led_timer = Timer(0, float(sys_param['led interval']))
    batt_timer = Timer(0, 30)

    logging.info("entering recording loop")
    exit_video = False
    while( exit_video == False ):

        # toggling recording leds
        if led_timer.check() == True:
            io.togglePin("RecLED")
            io.togglePin("Rec2LED")

        # checking button press to end the video
        btn = getButton()
        if btn != NO_PRESS:
            logging.info("recording interrupted - button pressed")
            exit_video = True

        # checking video for errors and new sections
        if cam.check_recording() == FAILED:
            logging.error("recording interrupted - camera error")
            cam.stop_recording(2)
            criticalError()

        # check for low battery condition
        if batt_timer.check() == True:
            if getBattery() == BATTERY_LOW:
                logging.warning("recording interrupted - battery low")
                cam.stop_recording(2)
                shutdown()

        # checking disk space
        if disk_timer.check() == True:
            if checkDisk(sys_param["usb folder"]) == FAILED:
                logging.info("recording interrupted - out of disk space")
                exit_video = True

        # updating system/sensor info
        if status_update_timer.check() == True:
            updateStatus()

        # logging sensors
        if sensor_log_timer.check() == True:
            logging.info("temperature sensor 1 = %s", sys_status["temp sensor 1"])

        # logging system info
        if status_log_timer.check() == True:
            logging.debug("status registers print")
            for key in sys_status:
                logging.debug("%s = %s", key, sys_status[key])
        
        sleep(REC_LOOP_DELAY_S)

    # # # # # END REC LOOP

    '''
        Stopping video
    '''
    io.clearLEDs()
    cam.stop_recording(2)

    # checking for long button press
    if btn == LONG_PRESS:
        logging.warning("long button press detected")
        end_operation = True
    if btn == SHORT_PRESS or checkDisk(sys_param["usb folder"]) == FAILED:
        logging.shutdown()
        code, out = run_cmd([ 'umount', sys_param["usb device"] ])
        if code == FAILED:   
            int_log("failed to unmount the USB drive, out = "+out)
            criticalError()
        else:
            sys_status['usb mounted'] = "false"
        video_param["section index"] = cam.getSectionID()
        end_operation = False
        second_loop = True
        # cleaning the objects and jumping to new recording
        del cam, temp_sensor, status_update_timer, disk_timer, led_timer, batt_timer, status_log_timer, sensor_log_timer
    
# # # # # END PROGRAM LOOP

logging.info("shutting down")
logging.shutdown()
shutdown()