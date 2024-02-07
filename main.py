#!/usr/bin/python3

import time
import asyncio

from mqtt_manager import MQTTManager
from tcp_server import TCPServer
from camera_manager import CameraManager
from pycamzero_bot import pycamzero_bot


def motion_cb(mse):
    global motion_detected_cnt    
    motion_detected_cnt = 5
    camera.start_recording(alarm_enabled)

def file_cb(path):
    if alarm_enabled:
        print("Sending file to telegram bot")
        # Create and run an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the pycamzero_bot coroutine within the event loop
        loop.run_until_complete(pycamzero_bot(path))

        # Close the event loop
        loop.close()

def stream_cb(stream):
    camera.set_stream(stream)
    print("New stream received!")

def message_cb(topic, payload):  

    global alarm_enabled
      
    print("New MQTT message received!")
    if topic == "homeassistant/piz2/control/rtsp" and payload == "off":        
        print("RTSP control turned off")
        camera.stop_stream()
    if topic == "homeassistant/piz2/control/rtsp" and payload == "on":        
        print("RTSP control turned on")
        camera.start_stream()
    if topic == "homeassistant/piz2/control/motion_recording" and payload == "on":    
        print("Enabling Motion Recording") 
        camera.set_motion_recording(True)
    if topic == "homeassistant/piz2/control/motion_recording" and payload == "off":    
        print("Disabling Motion Recording") 
        alarm_enabled = False
        camera.set_motion_recording(False)
    if topic == "homeassistant/piz2/control/alarm" and payload == "on":    
        print("Enabling Alarm") 
        alarm_enabled = True
        camera.set_motion_recording(True)
    if topic == "homeassistant/piz2/control/alarm" and payload == "off":    
        print("Disabling Alarm") 
        alarm_enabled = False
        camera.set_motion_recording(False)

def get_cpu_temp():
    temp_file = "/sys/class/thermal/thermal_zone0/temp"
    with open(temp_file, "r") as file:
        temp_str = file.readline().strip()
    temp = int(temp_str) / 1000  # Convert millidegrees Celsius to degrees Celsius
    return round(temp, 1)



camera = CameraManager(motion_callback=motion_cb, file_callback=file_cb)
camera.start()

tpc_server = TCPServer(stream_callback=stream_cb)
tpc_server.start()

mqtt_manager = MQTTManager(message_callback=message_cb)

force_stop = False
motion_detected_cnt = 0
alarm_enabled = False

try:
    while not force_stop:        
        
        mqtt_manager.publish_message("homeassistant/piz2/camera/status", payload = "online")

        mqtt_manager.publish_message("homeassistant/piz2/camera/temp", payload = get_cpu_temp())
        mqtt_manager.publish_message("homeassistant/piz2/camera/rtsp", payload = "on" if camera.is_streaming() else "off")
        mqtt_manager.publish_message("homeassistant/piz2/camera/lux", payload = camera.get_lux())
        mqtt_manager.publish_message("homeassistant/piz2/camera/motion", payload = "on" if motion_detected_cnt > 0 else "off")
        mqtt_manager.publish_message("homeassistant/piz2/camera/motion_recording", payload = "on" if camera.is_motion_recording_enabled() > 0 else "off")
        mqtt_manager.publish_message("homeassistant/piz2/camera/events_today", payload = camera.get_number_of_events_today())
        mqtt_manager.publish_message("homeassistant/piz2/camera/recording", payload = "on" if camera.is_recording() else "off")
        mqtt_manager.publish_message("homeassistant/piz2/camera/alarm", payload = "on" if alarm_enabled else "off")

        if motion_detected_cnt > 0:
            motion_detected_cnt -= 1

        time.sleep(1) 
except KeyboardInterrupt:
    force_stop = True
    tpc_server.stop()
    camera.stop()
    mqtt_manager.stop()
    print("Exit")