from ultralytics import YOLO
import cv2
import numpy as np
from .. import config

class Detector:
    def __init__(self):
        print(f"Loading YOLO model from {config.MODEL_PATH}...")
        # Explicitly set task='segment' because our CoreML model is a segmentation model
        self.model = YOLO(config.MODEL_PATH, task='segment')
        print("Model loaded.")

    def process_frame(self, packet_data):
        """
        Legacy wrapper: Decodes packet and runs prediction.
        """
        frame, depth_data = self.decode_packet(packet_data)
        if frame is None:
            return None
        return self.predict(frame)

    def decode_packet(self, packet_data):
        """
        Decodes TCP packet (Image + Depth).
        Returns: (frame, depth_bytes)
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

    def predict(self, frame, conf=config.CONF_THRESHOLD):
        """
        Runs YOLO inference on a raw frame.
        Returns: annotated frame (numpy array)
        """
        if frame is None:
            return None

        # Run inference
        results = self.model(frame, conf=conf, verbose=False)
        
        # Custom Plotting to avoid KeyErrors with CoreML/YOLO mismatches
        annotated_frame = frame.copy()
        
        try:
            boxes = results[0].boxes
            masks = results[0].masks
            names = results[0].names
            
            # 1. Draw Masks (Blue Fill)
            if masks is not None:
                overlay = annotated_frame.copy()
                # masks.xy is a list of polygon points for each detection
                for i, mask_poly in enumerate(masks.xy):
                    if i >= len(boxes): break # Safety check
                    
                    # Blue color for Potholes
                    color = (255, 0, 0) # BGR: Blue
                    
                    # Convert float polygon to int32
                    if len(mask_poly) > 0:
                        int_poly = np.array(mask_poly, dtype=np.int32)
                        cv2.fillPoly(overlay, [int_poly], color)
                
                # Apply transparency (0.4 opacity)
                cv2.addWeighted(overlay, 0.4, annotated_frame, 0.6, 0, annotated_frame)
            
            # (Boxes removed as requested)
                                
        except Exception as e:
            print(f"Manual Plot Error: {e}")
            import traceback
            traceback.print_exc()
            
        return annotated_frame
