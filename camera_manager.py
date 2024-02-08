#!/usr/bin/python3

import time
import threading
import datetime
import os
import numpy as np

import cv2

from picamera2 import Picamera2, MappedArray
from picamera2.encoders import H264Encoder
from picamera2.encoders  import JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.outputs import FfmpegOutput

class CameraManager:

    def __init__(self, motion_callback=None, file_callback=None):
        self.video_config = {
            "main": {"size": (1280, 720)},
            "lores": {"size": (320, 240), "format": "YUV420"}
        }
        self.picam2 = Picamera2()
        self.stream = None
        self.camera_started = False
        self.prev = None
        self.motion_callback = motion_callback
        self.file_callback = file_callback
        self.motion_threshold = 7
        self.streaming = False     
        self.recording = False 
        self.capturing_motion = False
        self.recording_cnt = 0
        self.encoder = H264Encoder(1000000)
        self.encoder_rec = H264Encoder(qp=30)   
        self.lock = threading.Lock()

    def apply_timestamp(request):
        colour = (0, 255, 0)
        origin = (0, 30)
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1
        thickness = 2
        timestamp = time.strftime("%Y-%m-%d %X")
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)

    def start(self):
        if not self.camera_started:
            self.camera_started = True

            config = self.picam2.create_video_configuration(**self.video_config)
            self.picam2.configure(config)              
            self.picam2.pre_callback = CameraManager.apply_timestamp
            self.picam2.set_controls({"FrameRate": 25})
     
            self.picam2.start()
            capture_motion_thread = threading.Thread(target=self._capture_motion_th)
            capture_motion_thread.start()
        else:
            print("Camera already started...")

    def restart(self):
        if self.camera_started:
            self.stop()
        self.start()

    def set_stream(self, stream):   
        if self.camera_started: 
            self.encoder.output = FileOutput(stream)    
            self.restart()                         
            self.start_stream()              

    def stop_stream(self):
        if self.streaming:
            print("Stopping encoder")
            self.picam2.stop_encoder(self.encoder)
            self.streaming = False        

    def start_stream(self):
        if not self.streaming and self.camera_started:
            print("Start streaming")
            self.picam2.start_encoder(self.encoder, name="main")
            self.streaming = True

    def is_streaming(self):
        return self.streaming

    def get_lux(self):
        if not self.camera_started:
            return 0.0

        metadata = self.picam2.capture_metadata()
        return round(metadata["Lux"], 1)

    def start_recording(self, alarm_enabled):        
        if self.camera_started:            
            if self.recording and not alarm_enabled:                
                self.lock.acquire()
                self.recording_cnt = 10
                self.lock.release()
            if not self.recording:     
                self.lock.acquire()      
                self.recording_cnt = 10
                self.lock.release()
                print("starting recording thread")               
                recording_thread = threading.Thread(target=self._recording_th, name="main")      
                recording_thread.start()  

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

    def is_on(self):
        return self.camera_started

    def _recording_th(self):
        self.recording = True
        current_date = datetime.datetime.now().strftime("%y_%m_%d")
        working_path = os.path.join(os.getcwd(), current_date)
        
        # Create the folder if it does not exist
        if not os.path.exists(working_path):
            os.makedirs(working_path)

        current_time = datetime.datetime.now().strftime("%H_%M_%S")
        file_name = f"{current_time}.h264"
        file_path = os.path.join(working_path, file_name)

        print(f"Start recording to file: {file_path}")           
        self.encoder_rec.output = FileOutput(file_path)
        self.picam2.start_encoder(self.encoder_rec, name="main")
        while self.recording_cnt > 0:
            self.lock.acquire()
            self.recording_cnt -= 1
            self.lock.release()
            time.sleep(1)
        self.picam2.stop_encoder(self.encoder_rec)
        print("Stop recording...") 
        if self.file_callback:
            self.file_callback(file_path)  
        self.recording = False     

    def _capture_motion_th(self):
        self.capturing_motion = True
        while self.camera_started:
            cur = self.picam2.capture_buffer("lores")
            cur = cur[:self.video_config["lores"]["size"][0] * self.video_config["lores"]["size"][1]].reshape(
                self.video_config["lores"]["size"][1], self.video_config["lores"]["size"][0])
            if self.prev is not None:
                mse = np.square(np.subtract(cur, self.prev)).mean()
                if mse > self.motion_threshold:                    
                    if self.motion_callback:
                        self.motion_callback(mse)
            self.prev = cur
            time.sleep(0.5)
        self.capturing_motion = False
        

    def stop(self):
        self.camera_started = False
        print("Stopping Camera")        
        self.stop_stream()
        while self.recording or self.capturing_motion:
            time.sleep(0.5)                        
        self.picam2.stop()        
        