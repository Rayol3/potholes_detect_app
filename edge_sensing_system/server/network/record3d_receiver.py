import numpy as np
import cv2
import time
from record3d import Record3DStream

from threading import Lock

class Record3DReceiver:
    def __init__(self):
        self.stream = None
        self.running = False
        self.lock = Lock()
        self.latest_rgb = None
        self.latest_depth = None
        self.read_count = 0
        
    def _on_new_frame(self):
        # printf debug to verify callback is working
        # print("RX Frame") 
        with self.lock:
            self.stream.get_rgb_frame() # Must call to clear buffer? or just get? usage varies.
            # actually if we are event driven, maybe valid frame is passed in?
            # Documentation says "Method called upon receiving new frame."
            # It usually doesn't pass args.
            
            self.latest_rgb = self.stream.get_rgb_frame()
            self.latest_depth = self.stream.get_depth_frame()
            
            if self.latest_rgb is not None:
                 pass # got it
        
    def open(self):
        try:
            self.stream = Record3DStream()
            self.stream.on_new_frame = self._on_new_frame
            
            devices = self.stream.get_connected_devices()
            print(f"Record3D Devices found: {devices}")
            if not devices:
                print("No iPhone found via USB. Please open Record3D app and connect USB.")
                return False
            
            self.stream.connect(devices[0]) # Connect to first device
            self.running = True
            print("Record3D Stream created. Waiting for frames...")
            return True
        except Exception as e:
            print(f"Error creating Record3D stream: {e}")
            self.running = False
            return False

    def isOpened(self):
        return self.running

    def read(self):
        """
        Returns: (ret, frame_rgb, frame_depth, accel_data)
        """
        if not self.running:
            return False, None, None, None

        self.read_count += 1
        
        try:
            rgb = None
            depth = None
            
            with self.lock:
                if self.latest_rgb is not None:
                    rgb = self.latest_rgb.copy()
                if self.latest_depth is not None:
                    depth = self.latest_depth.copy()
            
            # Debug empty frames
            if rgb is None:
                if self.read_count % 100 == 0:
                     print(f"Record3D: Waiting for frames... (Attempts: {self.read_count})")
                return False, None, None, None
            
            if getattr(rgb, 'size', 0) == 0:
                 return False, None, None, None

            # Record3D RGB is usually (H, W, 3) RGB. OpenCV wants BGR.
            if rgb is not None and getattr(rgb, 'size', 0) > 0:
                # Convert RGB to BGR for OpenCV compatibility
                rgb = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            else:
                return False, None, None, None
                
            # Depth is usually metric float (meters)
            
            # No IMU/Accel support in standard pyrecord3d public API straightforwardly
            # We will return None for accel for now.
            accel = None
            
            if rgb is not None and depth is not None:
                return True, rgb, depth, accel
            else:
                 return False, None, None, None

        except Exception as e:
            print(f"Record3D Read Error: {e}")
            return False, None, None, None
            
    def release(self):
        self.running = False
        self.stream = None
