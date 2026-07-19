import time
import argparse
import sys
import os
import cv2
import numpy as np

# Ensure we can import from parent directories
sys.path.append(os.getcwd())

from edge_sensing_system.server.network.tcp_server import TCPServer
# Conditionally import Detector to avoid loading heavy models in lighter modes if possible,
# or just instantiation control. We import it but only instantiate if needed.
from edge_sensing_system.server.processing.detector import Detector

class BenchmarkHandler:
    def __init__(self, mode='full'):
        self.mode = mode
        # Only load Detector (YOLO) if we are doing full processing
        if mode == 'full':
            self.detector = Detector()
        else:
            self.detector = None
            
        self.frame_count = 0
        self.start_time = time.time()
        self.interval_start = time.time()
        self.frames_in_interval = 0
        
        # Stats tracking
        self.data_bytes_received = 0
        self.latency_samples = []

    def process_packet(self, data):
        packet_start = time.time()
        self.data_bytes_received += len(data)
        
        # 2. Decoding (if needed)
        frame = None
        if self.mode != 'network_only':
            frame, depth = self.decode(data)
        
        # 3. Inference (if needed)
        if self.mode == 'full' and frame is not None:
             _ = self.detector.predict(frame)

        # Metrics
        self.frame_count += 1
        self.frames_in_interval += 1
        
        current_time = time.time()
        interval_duration = current_time - self.interval_start
        
        if interval_duration >= 1.0:
            fps = self.frames_in_interval / interval_duration
            mbps = (self.data_bytes_received / (1024*1024)) / interval_duration
            print(f"[{self.mode.upper()}] FPS: {fps:.2f} | Bandwidth: {mbps:.2f} MB/s | Total Frames: {self.frame_count}")
            
            # Reset interval stats
            self.interval_start = current_time
            self.frames_in_interval = 0
            self.data_bytes_received = 0

    def decode(self, packet_data):
        """
        Decodes TCP packet (Image + Depth).
        Duplicate logic from Detector to allow 'decode_only' without loading YOLO.
        """
        offset = 0
        total_len = len(packet_data)
        
        # 1. Parse Image Length
        if total_len < 4: return None, None
        img_len = int.from_bytes(packet_data[offset:offset+4], 'big')
        offset += 4
        
        # 2. Extract Image Bytes
        if total_len < offset + img_len: return None, None
        image_bytes = packet_data[offset:offset+img_len]
        offset += img_len
        
        # 3. Parse Depth Length (if present)
        depth_bytes = None
        if total_len >= offset + 4:
            depth_len = int.from_bytes(packet_data[offset:offset+4], 'big')
            offset += 4
            if total_len >= offset + depth_len:
                depth_bytes = packet_data[offset:offset+depth_len]

        # 4. Decode Image
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return frame, depth_bytes

def main():
    parser = argparse.ArgumentParser(description="Benchmark System FPS")
    parser.add_argument("--mode", choices=['network_only', 'decode_only', 'full'], default='full',
                        help="Benchmark mode: 'network_only' (TCP throughput), 'decode_only' (TCP+JPEG Decode), 'full' (TCP+Decode+YOLO)")
    args = parser.parse_args()

    print(f"Starting Edge Sensing FPS Benchmark...")
    print(f"Mode: {args.mode}")
    print("Press Ctrl+C to stop.")
    
    server = TCPServer()
    handler = BenchmarkHandler(args.mode)
    
    # TCPServer.start is blocking, so we pass the method
    server.start(handler.process_packet)

if __name__ == "__main__":
    main()
