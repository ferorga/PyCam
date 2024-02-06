#!/usr/bin/python3

import time

from mqtt_manager import MQTTManager
from tcp_server import TCPServer
from camera_manager import CameraManager


def motion_cb(mse):
    a = 0 

def stream_cb(stream):
    camera.set_stream(stream)
    print("New stream received!")

def message_cb(topic, payload):    
    print("New MQTT message received!")
    if topic == "homeassistant/piz2/control/rtsp" and payload == "off":        
        print("RTSP control turned off")
        camera.stop_stream()
    if topic == "homeassistant/piz2/control/rtsp" and payload == "on":        
        print("RTSP control turned on")
        camera.start_stream()

camera = CameraManager(motion_callback=motion_cb)
camera.start()

tpc_server = TCPServer(stream_callback=stream_cb)
tpc_server.start()

mqtt_manager = MQTTManager(message_callback=message_cb)

force_stop = False

try:
    while not force_stop:        
        mqtt_manager.publish_message("homeassistant/piz2/camera/rtsp", payload = "on" if camera.is_streaming() else "off")
        mqtt_manager.publish_message("homeassistant/piz2/camera/lux", payload = camera.get_lux())
        time.sleep(1) 
except KeyboardInterrupt:
    force_stop = True
    tpc_server.stop()
    camera.stop()
    mqtt_manager.stop()
    print("Exit")