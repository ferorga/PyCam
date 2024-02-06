#!/usr/bin/python3

import time
import threading
import numpy as np

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

class CameraManager:

    video_config = {
        "main": {"size": (1280, 720), "format": "YUV420"},
        "lores": {"size": (320, 240), "format": "YUV420"}  # Assuming default low-resolution size
    }

    def __init__(self, motion_callback=None):
        self.picam2 = Picamera2()
        self.stream = None
        self.stop_camera = False
        self.prev = None
        self.motion_callback = motion_callback
        self.motion_threshold = 7
        self.encoder = None        
        self.streaming = False
        #self.lock = threading.Lock()

    def start(self):        
        config = self.picam2.create_video_configuration(main={"size": (1280, 720), "format": "YUV420"},
                                                 lores={"size": (320, 240), "format": "YUV420"})

        self.picam2.configure(config)        
        self.encoder = H264Encoder(1000000)
        self.picam2.encoders = self.encoder
        self.picam2.start()
        capture_motion_thread = threading.Thread(target=self._capture_motion_th)
        capture_motion_thread.start()

    def set_stream(self, stream):        
        if self.streaming:
            self.picam2.stop_encoder()                    
        print("Starting encoder")
        self.encoder.output = FileOutput(stream)
        self.picam2.start_encoder(self.encoder)
        self.streaming = True

    def stop_stream(self):
        if self.streaming:
            print("Stopping encoder")
            self.picam2.stop_encoder()
            self.streaming = False        

    def start_stream(self):
        if not self.streaming:
            print("Start streaming")
            self.picam2.start_encoder(self.encoder)
            self.streaming = True

    def is_streaming(self):
        return self.streaming

    def get_lux(self):
        metadata = self.picam2.capture_metadata()
        return metadata["Lux"]

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
        #self.picam2.stop_encoder()
        self.picam2.stop()        
        