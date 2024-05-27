#!/usr/bin/python2

'''
    March 22, 2019

    Class to interract with pi camera

'''


import os, sys
from time import sleep
import datetime as dt
import picamera
import subprocess

class Camera():

    initialized = False
    sec_i = 1
    start_time = 0
    mic_initialized = False
    temp_dir = "/home/pi/"
    video_f = "video"
    audio_f = "audio"

    # loading video paramters as dictionary
    def __init__(self, param):
        self.rec_param = param

    # initializing the pi camera module
    def init(self):
        try:
            self.cam = picamera.PiCamera(
                resolution = self.rec_param["resolution"],
                framerate = self.rec_param["fps"]
                #sensor_mode = self.rec_param["video_mode"]
            )
            self.cam.rotation = self.rec_param["rotation"]
            if self.rec_param["use_time"] == True:
                # Annotation settings
                self.cam.annotate_background = picamera.color.Color('#000')
                self.cam.annotate_text_size = 32
            self.initialized = True

            if self.rec_param["mic_enable"] == True:
                # Check the pressence of a USB Mic
                out = subprocess.check_output(['arecord', '-l'])
                out = out.decode().splitlines()
                if len(out) > 1:
                    # setting microphone gain (0 to 16 max)
                    out = subprocess.check_output(['amixer', '-c', '1', 'cset', 'numid=3', str(self.rec_param["mic_gain"])])
                    self.mic_initialized = True

        except Exception as e:
            return 0, str(e)
        else:
            if self.mic_initialized == True:
                return 1, "camera and microphone initialized"
            else:
                return 1, "camera initialized, microphone not activated"


    # starting to capture video in a file
    def start_recording(self):
        if self.initialized == True:
            try:
                self.start_time = dt.datetime.now()
                self.video_f = '{}/{:03d}_{}'.format( self.rec_param["rec_f"], self.sec_i, self.start_time.strftime("%Y-%m-%d_%H-%M") )
                self.audio_f = '{}/{:03d}_{}'.format( self.temp_dir, self.sec_i, self.start_time.strftime("%Y-%m-%d_%H-%M") )
                if self.rec_param["bitrate"] == 0:
                    self.cam.start_recording ( self.video_f+".h264" )
                else:
                    self.cam.start_recording ( self.video_f+".h264", bitrate = int(self.rec_param["bitrate"]) * 1000000 )
                
                # start microphone recording
                if self.mic_initialized == True:
                    self.mic_proc = subprocess.Popen([ 
                        'arecord', '--device=plughw:1,0',
                        '--format', 'S16_LE',
                        '--rate', str(self.rec_param["mic_rate"]),
                        '-c', '1',
                        self.audio_f+".wav"
                    ], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
                
            except Exception as e:
                return 0, str(e)
            else:
                return 1, "recording started"
        else:
            return 0, "camera is not initialized"

    # check the status of the recording and start new section
    def check_recording(self, timeout):
        if(self.initialized == True):

            # checking for video recording errors
            try:
                self.cam.wait_recording(timeout)
            except Exception as e:
                return 0, str(e)
            
            # annotate datetime
            if self.rec_param['use_time'] == True:
                self.cam.annotate_text = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check for end of section
            if (dt.datetime.now() - self.start_time).seconds > (int(self.rec_param["section"])*60):
                try:
                    # stopping camera recording
                    self.cam.stop_recording()
                    self.sec_i += 1
                    # stopping microphone recording
                    if self.mic_initialized == True:
                        if self.mic_proc.poll() == None: 
                            self.mic_proc.kill()
                            sleep(0.2)
                            # moving the audio file
                            subprocess.call([ 'mv', self.audio_f+".wav", self.rec_param["rec_f"] ])
                    sleep(0.2)
                    self.start_recording()
                except Exception as e:
                    return 0, str(e)
            
            return 1, "recording in progress, no errors"
        else:
            return 0, "camera is not initialized"

    # check microphone status
    def check_mic(self):
        try:
            if(self.mic_initialized == True):
                if self.mic_proc.poll() != None:
                    return 0, "Mic process returned: "+self.mic_proc.stderr.read().decode()+" | code = "+str(self.mic_proc.returncode)
                else:
                    return 1, "Mic process pid: "+str(self.mic_proc.pid)+" | poll code: "+str(self.mic_proc.poll())+" | recording ..."
            else:
                return 0, "Microphone not initialized/enabled"
        except Exception as e:
            return 0, str(e)


    # stop video recording and close the camera resource
    def close_camera(self):
        if(self.initialized == True):
            try:
                self.cam.stop_recording()
                sleep(0.2)
                self.cam.close()
                # stopping microphone recording
                if self.mic_initialized == True:
                    if self.mic_proc.poll() == None: 
                        self.mic_proc.kill()
                        sleep(0.2)
                        # moving the audio file
                        subprocess.call([ 'mv', self.audio_f+".wav", self.rec_param["rec_f"] ])
                sleep(0.2)
            except Exception as e:
                return 0, str(e)
            else:
                return 1, "camera closed"
        else:
            return 0, "camera is not initialized"

    def parameters(self):
        return str(self.rec_param)

    def getSectionID(self):
        return self.sec_i

    def setSectionID(self, newID):
        self.sec_i = newID

# When class module is started by itself
# Following code is used for testing the Class
if __name__ == '__main__':

    test_len_m = 2

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

    mycam = Camera(rec_param)
    print "parameters:"
    print mycam.parameters()
    print "initializing ... "
    print( str(mycam.init()) )
    sleep(2)
    print "start recording for "+str(test_len_m)+"m ... "
    print(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print( str(mycam.start_recording()) )
    print( str(mycam.check_recording(0.5)) )
    sleep(2)
    for i in range(test_len_m*240):
        code, out = mycam.check_recording(0.25)
        if code != 1: 
            print("error occured: "+out)
            break
    sleep(2)
    print "closing camera ... "
    print( str(mycam.close_camera()) )