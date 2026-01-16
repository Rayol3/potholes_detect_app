import cv2
import sys
import os

# Add local directory to path to allow imports
sys.path.append(os.getcwd())

from edge_sensing_system.server.network.tcp_server import TCPServer
from edge_sensing_system.server.processing.detector import Detector

def main():
    detector = Detector()
    server = TCPServer()

    def process_data(data):
        annotated_frame = detector.process_frame(data)
        if annotated_frame is not None:
            cv2.imshow("Edge Sensing Stream", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting...")
                sys.exit(0)

    print("Starting Edge Sensing Server...")
    print("Press 'q' in the window to quit.")
    server.start(process_data)

if __name__ == "__main__":
    main()
