#!/usr/bin/python3

import time
import threading
import datetime
import os
import numpy as np

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from picamera2.outputs import FfmpegOutput

class CameraManager:

    def __init__(self, motion_callback=None, file_callback=None):
        self.video_config = {
            "main": {"size": (1280, 720), "format": "YUV420"},
            "lores": {"size": (320, 240), "format": "YUV420"}
        }
        self.picam2 = Picamera2()
        self.stream = None
        self.stop_camera = False
        self.prev = None
        self.motion_callback = motion_callback
        self.file_callback = file_callback
        self.motion_threshold = 7
        self.encoder = None
        self.encoder_rec = None  
        self.streaming = False     
        self.recording = False 
        self.motion_recording_ctrl = False    
        self.recording_cnt = 0

    def start(self):        
        config = self.picam2.create_video_configuration(**self.video_config)

        self.picam2.configure(config)      
        self.picam2.controls.FrameRate = 15  
        self.encoder = H264Encoder(1000000)
        self.encoder_rec = H264Encoder(1000000)
        self.picam2.controls.FrameRate = 15.0
        self.picam2.start()
        capture_motion_thread = threading.Thread(target=self._capture_motion_th)
        capture_motion_thread.start()                     

    def set_stream(self, stream):        
        if self.streaming:
            self.picam2.stop_encoder(self.encoder)                    
        print("Starting encoder")
        self.encoder.output = FileOutput(stream)
        self.picam2.start_encoder(self.encoder, name="main")
        self.streaming = True

    def stop_stream(self):
        if self.streaming:
            print("Stopping encoder")
            self.picam2.stop_encoder(self.encoder)
            self.streaming = False        

    def start_stream(self):
        if not self.streaming:
            print("Start streaming")
            self.picam2.start_encoder(self.encoder, name="main")
            self.streaming = True

    def is_streaming(self):
        return self.streaming

    def get_lux(self):
        metadata = self.picam2.capture_metadata()
        return round(metadata["Lux"], 1)

    def start_recording(self, alarm_enabled):        
        if self.motion_recording_ctrl:
            if self.recording and not alarm_enabled:
                self.recording_cnt = 10
            if not self.recording:           
                self.recording_cnt = 10
                print("starting recording thread")               
                recording_thread = threading.Thread(target=self._recording_th)      
                recording_thread.start()  

    def set_motion_recording(self, enable):
        self.motion_recording_ctrl = enable

    def is_motion_recording_enabled(self):
        return self.motion_recording_ctrl

    def get_number_of_events_today(self):
        current_date = datetime.datetime.now().strftime("%y_%m_%d")
        working_path = os.path.join(os.getcwd(), current_date)
        if not os.path.exists(working_path) or not os.path.isdir(working_path):
            return 0
        
        files = os.listdir(working_path)
        num_files = len(files)
        return num_files

    def is_recording(self):
        return True if self.recording_cnt > 0 else False

    def _recording_th(self):
        self.recording = True
        current_date = datetime.datetime.now().strftime("%y_%m_%d")
        working_path = os.path.join(os.getcwd(), current_date)
        
        # Create the folder if it does not exist
        if not os.path.exists(working_path):
            os.makedirs(working_path)

        current_time = datetime.datetime.now().strftime("%H_%M_%S")
        file_name = f"{current_time}.mp4"
        file_path = os.path.join(working_path, file_name)

        print(f"Start recording to file: {file_path}")
        self.encoder_rec.output = FfmpegOutput(file_path)        
        self.picam2.start_encoder(self.encoder_rec)
        while self.recording_cnt > 0:
            self.recording_cnt -= 1
            time.sleep(1)
        self.picam2.stop_encoder(self.encoder_rec)
        print("Stop recording...") 
        if self.file_callback:
            self.file_callback(file_path)  
        self.recording = False     

    def _capture_motion_th(self):
        while not self.stop_camera:
            cur = self.picam2.capture_buffer("lores")
            cur = cur[:self.video_config["lores"]["size"][0] * self.video_config["lores"]["size"][1]].reshape(
                self.video_config["lores"]["size"][1], self.video_config["lores"]["size"][0])
            if self.prev is not None:
                mse = np.square(np.subtract(cur, self.prev)).mean()
                if mse > self.motion_threshold:
                    #print("New Motion Detected:", mse)
                    if self.motion_callback:
                        self.motion_callback(mse)
            self.prev = cur
            time.sleep(0.5)

    def stop(self):
        print("Stopping Camera")
        self.stop_camera = True
        self.picam2.stop()        
        