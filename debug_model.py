import cv2
import numpy as np
import torch
from ultralytics import YOLO

MODEL_PATH = 'model/train_yolo11L/weights/best.mlpackage'

def debug_inference():
    print(f"Loading model: {MODEL_PATH}")
    try:
        model = YOLO(MODEL_PATH, task='segment')
        print("Model loaded successfully.")
        print(f"Model Names: {model.names}")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Create a dummy image (black) 640x640
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    
    # Draw a white circle to simulate "something"
    cv2.circle(img, (320, 320), 50, (255, 255, 255), -1)
    
    print("\n--- Running Inference on Dummy Image (640x640) ---")
    results = model(img)
    
    for r in results:
        boxes = r.boxes
        if boxes is None:
            print("No boxes detected.")
            continue
            
        print(f"Detected {len(boxes)} boxes:")
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            print(f" - Class: {cls_id} (Label: {model.names.get(cls_id, 'UNKNOWN')}), Conf: {conf:.4f}")

if __name__ == "__main__":
    debug_inference()
