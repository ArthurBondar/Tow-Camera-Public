#!/usr/bin/python2

'''
    July 20, 2020

    Class to interract with pi camera
    Starts and stop FFMPEG process
    Records in video sections

'''


import os, sys, subprocess, signal
import datetime as dt
import logging
from defines import *
from time import sleep


class Camera():

    camera_proc = 1
    section_index = 1
    start_time = 0
    video_file = TEMP_VIDEO+'.'+VIDEO_FRMT

    video_param = {}
    camera_param = {}

    ffmpeg_param = [
        'FFREPORT=file=/home/pi/USB/fflog.txt:level=32', # Log file, level=info  (param 0)
        '/home/pi/ffmpeg/ffmpeg',       # recording program path                 (param 1)
        '-nostats',                     # don't log every frame                  (param 2)
        '-f', 'v4l2',                   # input 1                                (param 3,4)
        '-vsync', '0',                  # sync 0 - copy stream fps               (param 5,6)
        '-input_format', 'h264',        # stream input selection                 (param 7,8)
        '-video_size', '1920x1080',     # video resolution                       (param 9,10)
        '-thread_queue_size', '4096',   #                                        (param 11,12)
        '-use_wallclock_as_timestamps', '1', # helps with audio/video sync       (param 13,14)
        '-i', '/dev/video2',            # input 1 type                           (param 15,16)        
        '-f', 'alsa',                   # input 2 type                           (param 17,18)
        '-thread_queue_size', '4096',   #                                        (param 19,20)
        '-ar', '44100',                 # audio recording samplerate             (param 21,22)
        '-ac', '1',                     # audio channels                         (param 23,24)
        '-use_wallclock_as_timestamps', '1', # helps with audio/video sync       (param 25,26)
        '-i', 'hw:1,0',                 # input 2 path                           (param 27,28)
        '-codec:v', 'copy',             # output video codec                     (param 29,30)
        '-codec:a', 'copy',             # output audio codec                     (param 31,32)
        '-copyinkf',                    # copy non-key frames                    (param 33)
        TEMP_VIDEO+'.'+VIDEO_FRMT       # output path                            (param 34)
    ]

    v4l2_param = [
        'v4l2-ctl',
        '-d', '/dev/video2',
        '--set-ctrl', 'brightness=0'   # param 4
    ]

    # loading video paramters as dictionary
    def __init__(self, video_parameters, camera_parameters):
        self.video_param = video_parameters
        self.camera_param = camera_parameters

    # initializing the pi camera module
    def init(self):
        try:
            # Video parameters
            try: self.ffmpeg_param[1] = self.video_param['recording program']
            except: pass
            try: self.ffmpeg_param[28] = self.video_param['audio device']
            except: pass
            try: self.ffmpeg_param[16] = self.video_param['camera device']
            except: pass
            try: self.ffmpeg_param[8] = self.video_param['input format']
            except: pass
            try: self.ffmpeg_param[6] = self.video_param['framerate']
            except: pass
            try: self.ffmpeg_param[10] = self.video_param['resolution']
            except: pass
            try: self.ffmpeg_param[34] = TEMP_VIDEO+'.'+self.video_param['video format']
            except: pass

            # Setting camera parameters using V4L2 driver
            self.v4l2_param[2] = self.video_param['camera device']
            for key in self.camera_param:
                try:
                    self.v4l2_param[4] = key+'='+self.camera_param[key]
                    subprocess.check_call(self.v4l2_param)
                    logging.debug("init(): set camera parameter - %s", str(self.v4l2_param) )
                except: 
                    logging.warning('init(): %s failed', self.v4l2_param, exc_info=True)
                    pass

            logging.info("init(): video parameters are set")
            logging.debug("init(): ffmpeg parameters - (%s)", self.ffmpeg_param)
        except:
            logging.exception('init(): init function failed')
            return FAILED
        else:
            return SUCCESS

    # starting to capture video in a file, only called once to start the video! 
    # subsiquent calls to check_recording will call start/stop old recordings
    def start_recording(self, index):
        try:
            self.section_index = index
            self.start_time = dt.datetime.now()
            self.video_file = '{}/{:03d}_{}.{}'.format( self.video_param["recording folder"], self.section_index, self.start_time.strftime("%Y-%m-%d_%H-%M-%S"), self.video_param['video format'] )
            self.ffmpeg_param[34]  = self.video_file
            self.ffmpeg_param[0] = 'FFREPORT=file='+self.video_file+'.txt:level=32'
            self.camera_proc = subprocess.Popen(self.toString(self.ffmpeg_param), shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
            sleep(2)
            if self.camera_proc.poll() != None:
                logging.error("start_recording(): camera_proc failed return = %s", self.camera_proc.returncode)
                raise Exception("start_recording(): camera_proc failed to start")
            self.section_index += 1
            logging.info("start_recording(): camera process started, pid = %s, file = %s", self.camera_proc.pid, self.video_file)
            return SUCCESS
        except:
            logging.exception('start_recording(): failed to start recording')
            return FAILED


    # check the status of the recording and starts a new section if needed
    # return SUCCESS when section has been started / processed
    def check_recording(self):
        # checking for video recording errors
        try:
            if self.camera_proc.poll() != None:
                logging.debug("check_recording(): video process isn't running - didn't start properly return = %s", self.camera_proc.stderr.returncode)
                raise Exception("check_recording(): video process isn't running - didn't start properly")

            # Check for end of section
            if (dt.datetime.now() - self.start_time).seconds > (int(self.video_param["section length"])*60):
                # stopping camera recording
                self.stop_recording(2)
                self.start_recording(self.section_index)

        except:
            logging.exception('check_recording(): exception occured')
            return FAILED
        else:
            return SUCCESS

    # stop video recording and close the camera resource
    def stop_recording(self, timeout_s):
        try:
            if self.camera_proc.poll() != None:
                logging.warning("stop_recording(): camera process isn't running")
                raise Exception()
            for s in range(timeout_s):
                os.killpg(os.getpgid(self.camera_proc.pid), signal.SIGTERM) 
                sleep(1)
                if self.camera_proc.poll() != None:
                    if self.camera_proc.returncode != 0 and self.camera_proc.returncode != 255 and self.camera_proc.returncode != -15:
                        logging.warning("stop_recording(): process stopped with non zero return = %s", self.camera_proc.returncode)
                    logging.info("stop_recording(): recording stopped")
                    return SUCCESS
            logging.warning("stop_recording(): couldn't terminate process in timeout_s")
            raise Exception()
        except:
            logging.exception("stop_recording(): exception")
            return FAILED

    def getVideoScript(self):
        return str(self.ffmpeg_param)

    def getVideoParameters(self):
        return str(self.video_param)

    def getCameraParameters(self):
        return str(self.camera_param)

    def listCameraParameters(self):
        try:
            return (subprocess.check_output(['v4l2-ctl', '-d', self.video_param['camera device'], '--list-ctrls'])).decode()
        except:
            logging.warning("listCameraParameters(): list parameters command failed", exc_info=True)
            pass

    def getSectionID(self):
        return self.section_index

    def setSectionID(self, newID):
        self.section_index = newID

    def toString(self, array):
        string = ''
        for item in array:
            string += str(item)+' '
        return string


# When class module is started by itself
# Following code is used for testing the Class
if __name__ == '__main__':

    TEST_DUR_S = 20

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
        '''
        "contrast"        : "32",
        "saturation"      : "64",
        "gamma"           : "100",
        "test"            : "9001"
        '''
    }


    # log creationg
    logging.basicConfig(
            filename="camera_app.log",
            filemode='a',
            format='%(asctime)s %(levelname)-8s %(module)-10s %(message)s',
            level=logging.DEBUG
    )
    logging.info(" - - - - - - - - - - - - - ")

    try:
        mycam = Camera(video_param, camera_param)
        logging.info("parameters:\nVideo: %s\nCamera: %s\nScript: %s\nList Camera parameters: %s", 
            mycam.getVideoParameters(), mycam.getCameraParameters(), mycam.getVideoScript(), mycam.listCameraParameters())

        mycam.init()
        logging.info( "start recording for %s seconds", TEST_DUR_S)
        if mycam.start_recording(1) != SUCCESS:
            raise Exception("failed to start recording")

        logging.info("recording started")
        for i in range(TEST_DUR_S):
            if mycam.check_recording() != SUCCESS:
                raise Exception("check_recording returned FAILED code")
            print i
            sleep(1)
        logging.info("closing camera")
        mycam.stop_recording(2)
        logging.info("SUCCESS")
    except:
        logging.exception("FAILED")
        exit(1)
    else:
        exit(0)



