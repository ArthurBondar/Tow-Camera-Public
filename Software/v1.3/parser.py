#!/usr/bin/python2

import ConfigParser, sys

SUCCESS = 1
FAILED = 0
WARN = 2

sys_param = {
    "debug mode"        : False,
    "software version"  : "Dredge Camera v1.3 April 26, 2020",
    "usb device"        : "/dev/sda1",
    "usb folder"        : "/home/pi/USB",
    "setup file"      : "/home/pi/USB/setup.txt",
    "log file"          : "/home/pi/USB/log.txt",
    "camera driver"     : "/home/pi/ffmpeg/ffmpeg",
    "camera device"     : "/dev/video2",
    "temp cpu"          : 99,
    "temp sensor 1"     : 99,
    "log detail"        : 1,
    "log interval"      : 15,
    "hdmi"              : False,
}

video_param = {
    "recording folder"  : "/home/pi/USB",
    "section length"    : 25,
    "resolution"        : "1640x1232",
    "use date-time"     : False,
    "set date-time"     : "2020-04-26 T 12:30:00",
    "framerate"         : 25,
    "rotation"          : 0,
    "bitrate"           : 10,
    "microphone rate"   : 48000,
}

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

try:
    _SETUP_FILE = str(sys.argv[1])
except:
    print "not enough arguments provided"
    exit()

print "Test code started\nfile = "+_SETUP_FILE
print "\nDictionaries\n* * * * * * *\n"+str(sys_param)+"\n\n"+str(video_param)
print "\n* * * * * * *\n"

print(str(parseConfig(sys_param, 'debug')))
print(str(parseConfig(video_param, 'video')))

print "\nDictionaries\n* * * * * * *\n"+str(sys_param)+"\n\n"+str(video_param)
print "\n* * * * * * *\n"


'''
try:
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    print "\nRead:\n"+str(config.read(_SETUP_FILE))
    print "\nDefaults:\n"+str(config.defaults())
    print "\nSections found:\n"+str(config.sections())
    print "\nItems in timing section:\n"+str(config.items('timing'))
    print "\nItems in annotation section:\n"+str(config.items('annotation'))
    print "\nItems in video section:\n"+str(config.items('video'))
    print "\nItems in camera section:\n"+str(config.items('camera'))
    print "\nItems in microphone section:\n"+str(config.items('microphone'))
    print "\nItems in debug section:\n"+str(config.items('debug'))
    
except Exception as exp:
    print str(exp)
    pass
'''
    
exit()