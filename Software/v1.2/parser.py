#!/usr/bin/python2

'''
    August 18, 2019

    Class to interract with setup.txt file
    Parses according to the following format list:
    [parameter]=[value][\n(Linux)\r\n(Windows)]

    Loading the parameter-value list into integer arrays
    Index of is used to loop throught and retrieve data
    This class relies on currect system time to calculate
    sleep and recording interval from the file
''' 

import datetime, sys
from time import sleep              # sleep function in seconds

class Parser():
    # default parameters overwritten by parsed data from setup file
    filepath = "/home/pi/USB/setup.txt"
    delim = '='     
    param = []
    value = []
    start = "08:00"
    end = "17:00"
    datetime = "18-08-2019_18:30:30"   # format +"%d-%m-%Y_%T"
    timezone = "America/Halifax"       # default TZ
    board = "underwater camera"

    # Constructor - opens the file and loads all the data into arrays
    def __init__(self, path):
        self.param = []
        self.value = []
        self.filepath = path
        # Openning the file as Universal format
        # since Windows uses /r/n convention and Unix/Linux only /n
        # loading parameter-value pair into corresponding array
        with open(self.filepath, 'rU') as _file:
            # loop throught each line
            for line in _file:
                line = line.replace(" ","")                             # remove white spaces
                if line and line[0].isalpha():                          # skip comments
                    try:
                        p,val = line.split(self.delim)                  # split delimiter (=)
                        val = val.replace("\r", "").replace("\n", "")   # strip /r/n
                        self.param.append(p)                            # save param in array (int)
                        self.value.append(val)                          # save value in array as int
                    except Exception as e: 
                        print(str(e))

    # Return value based on parameter name
    # runs throught the array and searches for parameter
    # return 0 if parameter not found
    def getParam(self, parameter):
        try:
            # returning any other parameter from the file
            for i in range(len(self.param)):
                if(self.param[i] == parameter): return self.value[i]

        except Exception as e:
            print e

        return "None"

    # Returns the full content of the param:value pair
    # used to test the class
    def dump(self):
        for i in range(len(self.param)):
            try:
                print "[{}] {} : {}".format( str(i), self.param[i], self.value[i])
            except: pass
           
# END Setup Class

# When class module is started by itself
# Following code is used for testing the parser class
# Accepts file path for setup file as input
if __name__ == '__main__':

    try:
        _SETUP_FILE = str(sys.argv[1])
    except:
        print "not enough arguments provided"
        exit()

    print "Test code started\nfile = "+_SETUP_FILE

    setup_file = Parser(_SETUP_FILE)
    print "Dumpint data -----------------------"
    setup_file.dump()
    print "Finished"