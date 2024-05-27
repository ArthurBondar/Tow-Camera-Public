#!/usr/bin/python2

'''
    Changed: October 9, 2018

    Class to log data in a log file
    Every message is timestamped and
    Opens and closes the file on every log

'''

import datetime, subprocess, os
from time import sleep              # sleep function in seconds

class Log():
    PATH = "/home/pi/log.txt"   # default path for storing file
    level = 1                   # 0-Error, 1-Warning, 2-Info, 3-All

    # set file path on creation of the file
    def __init__(self, file_path):
        self.PATH = file_path

    # sets the log detail lvl
    # 0-Error, 1-Warning, 2-Info, 3-All 
    def setLevel(self, lvl):
        if lvl >= 0 and lvl <= 3:
                self.level = lvl

    def getLevel(self):
        return self.level

    # writing single line statement starting with the date
    def write(self, lvl, _str):
        if lvl <= self.level:
                for line in _str.splitlines():
                        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " | "
                        print(now + line)
                        with open(self.PATH, "a") as _file:
                                _file.write(now + line + '\r\n')

    def space(self):
        with open(self.PATH, "a") as _file:
            _file.write("\r\n")

    # log CPU temperature into the file
    def logTemp(self):
        out = "empty"
        try:
                out = subprocess.check_output(['/opt/vc/bin/vcgencmd', 'measure_temp'])
                out = out.decode().splitlines()[0]
        except subprocess.CalledProcessError as e:
                out = "ERROR: command failed code = "+str(e.returncode)+" msg = "+str(e.output)
        self.write(3, "temp -> \t"+out)

    # log CPU usage
    def logCPU(self):
        # Return % of CPU used by user as a character string
        # copied from a forum
        out = "empty"
        try:
                out = subprocess.check_output(['uptime'])
                out = out.decode().splitlines()[0]
        except subprocess.CalledProcessError as e:
                out = "ERROR: command failed code = "+str(e.returncode)+" msg = "+str(e.output)
        self.write(3, "cpu -> \t"+out[30:-1])

    # log avaiable disk space on the USB
    def logDisk(self, device):
        out = "empty"
        try:
                out = subprocess.check_output(['df', '-h', device])
                out = (out.decode().splitlines())[1]
        except subprocess.CalledProcessError as e:
                out = "ERROR: command failed code = "+str(e.returncode)+" msg = "+str(e.output)
        self.write(3, "disk ->\t"+out)
        

    # logs CPU throttling register
    # 0: under-voltage
    # 1: arm frequency capped
    # 2: currently throttled
    # 16: under-voltage has occurred
    # 17: arm frequency capped has occurred
    # 18: throttling has occurred
    def logThrottle(self):
        out = "cmd failed"
        try:
                out = subprocess.check_output(['/opt/vc/bin/vcgencmd', 'get_throttled'])
                out = out.decode().splitlines()[0]
        except subprocess.CalledProcessError as e:
                out = "ERROR: command failed code = "+str(e.returncode)+" msg = "+str(e.output)
        self.write(3, "throt ->\t" + out)

    # logs RAM usage
    def logRAM(self):
        out = "cmd failed"
        try:
                out = subprocess.check_output(['free', '-h'])
                out = 
                out = out[39:-36]
        except subprocess.CalledProcessError as e:
                out = "ERROR: command failed code = "+str(e.returncode)+" msg = "+str(e.output)
	except Exception as exp:
		out = str(exp)
		print(out)
        self.write(3, "RAM -> \t"+out)

    # log CPU frequency
    def logFreq(self):
        out = "cmd failed"
        try:
                out = subprocess.check_output(['/opt/vc/bin/vcgencmd', 'measure_clock', 'arm'])
                out = (out.decode().splitlines())[0]
        except subprocess.CalledProcessError as e:
                out = "ERROR: command failed code = "+str(e.returncode)+" msg = "+str(e.output)
        self.write(3, "clock ->\t"+out)

        # logs all the parameters in a row
    def logParam(self, disk_path):
        self.write(2, " - - - - - - - ")
        self.logTemp()
        self.logCPU()
        self.logThrottle()
        self.logRAM()
        self.logFreq()
        self.logDisk(disk_path)
        self.write(3, " - - - - - - - ")

# When class module is started by itself
# Following code is used for testing the Class
if __name__ == '__main__':

    # Create instance of log class
    _log = Log("/home/pi/log_test.txt")

    print "Debugging logging class"
    # Running a series test prints to the log
    _log.write(0, "DEBUG START")
    for lvl in range (0, 3):
        _log.setLevel(lvl)
        _log.write(0, " - - - - - - - ")
        _log.write(0, "This is an error")
        _log.write(1, "This is a warning")
        _log.write(2, "This is an info")
        _log.write(3, "This is general print")
    
    _log.setLevel(3)
    _log.write(2, "Logging parameters")
    _log.logParam("/home/pi/USB")
    _log.write(0, "DEBUG FINISHED")
    # debug finished
    print "Debug session finished"
    print "Output file = /home/pi/log_test.txt"
    exit()

