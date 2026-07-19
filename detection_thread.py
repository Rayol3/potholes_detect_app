import cv2
import time
import numpy as np
import os
import threading
from ultralytics import YOLO
import torch # Added import
import sys
import os

# Ensure we can import from the edge_sensing_system package
sys.path.append(os.getcwd())
try:
    from edge_sensing_system.server.network.tcp_receiver import TCPFrameReceiver
    from edge_sensing_system.server.network.record3d_receiver import Record3DReceiver
except ImportError:
    print("Warning: Could not import Receivers. Edge Sensing/Record3D will not work.")

class DetectionThread(threading.Thread):
    def __init__(self, model_path, camera_index=None, video_path=None, db=None, gps=None):
        super().__init__()
        self.daemon = True
        
        # State for Web Server
        self.latest_frame = None
        self.latest_depth = None
        self.latest_stats = {"fps": 0.0, "detections": 0, "vibration": 0.0, "depth_val": 0.0}
        self.model_path = model_path
        self.camera_index = camera_index 
        # Special flag for TCP Edge Sensor
        self.use_tcp = (self.camera_index == "tcp")
        self.use_record3d = (self.camera_index == "record3d")
        
        self.video_path = video_path 
        self.db = db
        self.gps = gps
        self._run_flag = True
        self.model = None
        
        # De-duplication
        self.last_save_time = 0
        self.last_alert_time = 0.0
        self.last_save_coords = (0.0, 0.0)
        self.processed_ids = set()
        
        # Optical Flow
        self.prev_gray = None
        self.frame_count = 0
        self.last_depth_result = None
        
        # --- DEPTH MODEL (MiDaS) ---
        self.depth_model = None
        self.depth_transform = None
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        print(f"Depth Inference Device: {self.device}")
        
        self.current_fps = 0.0 # Store FPS for usage during detection
        
        # Ensure captures directory exists
        if not os.path.exists("captures"):
            os.makedirs("captures")

    # ... (haversine and load_depth_model methods remain the same) ...
    def haversine(self, lat1, lon1, lat2, lon2):
        import math
        R = 6371000 # meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R*c

    def load_depth_model(self):
        try:
            print("Loading MiDaS (Pseudo-LiDAR)...")
            self.depth_model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
            self.depth_model.to(self.device)
            self.depth_model.eval()
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.depth_transform = midas_transforms.small_transform
            print("Depth Model Loaded.")
        except Exception as e:
            print(f"Error cargando MiDaS: {e}")
            self.depth_model = None

    def run(self):
        # Load the model
        if not self.model:
            print("Loading YOLO model...")
            try:
                self.model = YOLO(self.model_path, task='segment')
                print(f"Model loaded.")
            except Exception as e:
                print(f"Error loading model: {e}")
                return

        if not self.depth_model:
            self.load_depth_model()

        # Initialize Input
        cap = None
        tcp_receiver = None
        
        if self.use_tcp:
            print("Starting TCP Server Mode (Edge Sensor)...")
            tcp_receiver = TCPFrameReceiver()
            if not tcp_receiver.open():
                print("Failed to start TCP Server")
                return
        elif self.use_record3d:
            print("Starting Record3D USB Receiver...")
            tcp_receiver = Record3DReceiver() # Re-using variable name for polymorphic receiver
            if not tcp_receiver.open():
                print("Failed to connect to Record3D app via USB")
                return
        elif self.video_path:
            cap = cv2.VideoCapture(self.video_path)
        else:
            idx = self.camera_index if self.camera_index is not None else 0
            cap = cv2.VideoCapture(idx)
            # Request 60 FPS
            cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Check if opened (for local)
        if cap and not cap.isOpened():
             print(f"Cannot open input")
             return

        while self._run_flag:
            
            # READ FRAME
            ret = False
            cv_img = None
            
            if self.use_tcp:
                # TCP Read (Returns ret, frame, depth_bytes, accel_data)
                ret, cv_img, depth_bytes, accel_data = tcp_receiver.read()
                if not ret:
                    # Non-blocking check or no client yet
                    # Create "Waiting" screen
                    wait_img = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(wait_img, "Waiting for 'EdgeSensor'...", (180, 240), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(wait_img, "IP: 192.168.1.53 Port: 5005", (190, 280), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
                    
                    self.latest_frame = self.encode_jpeg(wait_img)
                    time.sleep(0.1)
                    continue
            elif self.use_record3d:
                # Record3D Read (Returns ret, frame, depth_bytes, accel_data)
                # Note: depth_bytes here is actually already a numpy array from our adapter
                ret, cv_img, depth_bytes, accel_data = tcp_receiver.read()
                if not ret:
                     time.sleep(0.01)
                     continue
            else:
                # Standard CV2 Read
                ret, cv_img = cap.read()
                depth_bytes = None
                accel_data = None

            if ret:
                start_time = time.time()
                self.frame_count += 1
                
                # ... (Pre-processing) ...
                
                depth_colormap = None
                depth_out = None # Store raw depth for pothole depth calculation
                pothole_depth_val = 0.0
                
                # --- DEPTH PROCESSING ---
                if depth_bytes is not None:
                     # REAL LIDAR DATA (from iOS)
                     if self.frame_count % 30 == 0:
                         print(f"🔵 LiDAR ACTIVE | Payload: {len(depth_bytes)} bytes") # Debug Log
                     
                     # iOS sends Float32 (4 bytes/pixel) usually, or Float16. 
                     # Given ARFrame.sceneDepth.depthMap consists of Float32 meters in ARKit
                     try:
                         # Check if already numpy (Record3D) or bytes (TCP)
                         if isinstance(depth_bytes, np.ndarray):
                            # If from pyrecord3d, it might be (H, W) already or flattened
                            # Usually get_depth_frame() returns 2D array
                            depth_out = depth_bytes # Assume it is already the depth map
                            # Skip the reshape/decode logic below if already 2D
                            if len(depth_out.shape) == 2:
                                depth_arr = depth_out.flatten() # Just for legacy compatibility if valid
                            else:
                                depth_arr = depth_out.flatten()
                         else:
                             # Assume Float32 for now based on CVPixelBuffer extraction
                             depth_arr = np.frombuffer(depth_bytes, dtype=np.float32)
                         
                         # Reshape logic (Only if depth_out not already set or invalid shape)
                         if depth_out is None or len(depth_out.shape) != 2:
                             # Reshape: ARKit depth is usually smaller resolution (e.g. 256x192 or similar)
                             # We need to know shape or infer it. 
                             # For now, let's just attempt a common aspect ratio or reshape to known size if possible.
                             # SAFEGUARD: If size doesn't match expected, skip.
                             # A common LiDAR depth map is 256x192 (49152 pixels * 4 bytes = 196608 bytes)
                             
                             if depth_arr.size == 256 * 192:
                                 depth_out = depth_arr.reshape((192, 256))
                             elif depth_arr.size == 640 * 480: # If it was resized
                                 depth_out = depth_arr.reshape((480, 640))
                             else:
                                 # Fallback: Treat as 1D or try to guess?
                                 # Let's just create a square aspect approx if valid
                                 side = int(np.sqrt(depth_arr.size * (4/3)))
                                 if side * int(side*0.75) == depth_arr.size:
                                     depth_out = depth_arr.reshape((int(side*0.75), side))
                                 else:
                                     depth_out = None # Unknown shape
                         
                         if depth_out is not None:
                             # Normalize for Viz [0-255]
                             # LiDAR usually 0-5m. Clip to 5m for viz
                             depth_viz = np.clip(depth_out, 0, 5.0)
                             depth_norm = (depth_viz / 5.0) # 0 to 1
                             depth_uint8 = (depth_norm * 255).astype(np.uint8)
                             depth_colormap = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_JET)
                             
                             # Resize to match Video for Overlay/logic if needed
                             depth_out = cv2.resize(depth_out, (cv_img.shape[1], cv_img.shape[0]))
                             
                     except Exception as e:
                         print(f"LiDAR Decode Error: {e}")
                         depth_out = None

                elif self.depth_model:
                    # SIMULATED LIDAR (MiDaS)
                    if self.frame_count % 30 == 0:
                         print(f"🟠 NO LIDAR - Using AI Depth Estimation") # Debug Log

                    # Only run if NO real LiDAR and model loaded
                    run_depth = (self.frame_count % 5 == 0) or (self.last_depth_result is None)
                    
                    if run_depth:
                        try:
                            # Transform input
                            input_batch = self.depth_transform(cv_img).to(self.device)
                            
                            # Inference
                            with torch.no_grad():
                                prediction = self.depth_model(input_batch)
                                self.last_depth_result = prediction # Cache prediction
                        except Exception as e:
                            print(f"Depth Inference Error: {e}")
                    
                    # Use cached prediction if available
                    if self.last_depth_result is not None:
                        try:
                            prediction = self.last_depth_result
                            
                            # Resize to original resolution
                            prediction = torch.nn.functional.interpolate(
                                prediction.unsqueeze(1),
                                size=cv_img.shape[:2],
                                mode="bicubic",
                                align_corners=False,
                            ).squeeze()
                            
                            # Normalize output
                            depth_out = prediction.cpu().numpy()
                            
                            # Normalize to 0-255 for visualization
                            depth_min = depth_out.min()
                            depth_max = depth_out.max()
                            
                            if depth_max - depth_min > 0:
                                depth_norm = (depth_out - depth_min) / (depth_max - depth_min)
                            else:
                                depth_norm = np.zeros_like(depth_out)
                                
                            depth_uint8 = (depth_norm * 255).astype(np.uint8)
                            
                            # Apply Heatmap
                            depth_colormap = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_MAGMA)
                            
                        except Exception as e:
                            print(f"Depth Viz Error: {e}")
                            depth_colormap = None
                            depth_out = None

                # Inference with TRACKING
                # persist=True keeps IDs across frames
                # Switching to botsort.yaml due to LinAlgError in ByteTrack on some platforms
                # Explicitly pass task='segment' just in case, though loading should handle it
                results = self.model.track(cv_img, persist=True, tracker="botsort.yaml", verbose=False, retina_masks=True)
                
                # Annotate (We will draw manually, but let's keep a copy for clean drawing)
                annotated_frame = cv_img.copy()
                overlay = annotated_frame.copy() # Buffer for mask filling
                labels_queue = [] # Queue for drawing text after blending

                current_size_m = 0.0
                detected_this_frame = False
                
                # Iterate through tracked objects
                if results[0].boxes and results[0].boxes.id is not None:
                     boxes = results[0].boxes.xyxy.cpu()
                     track_ids = results[0].boxes.id.int().cpu().tolist()
                     confs = results[0].boxes.conf.cpu().tolist()
                     
                     for i, (box, track_id, conf) in enumerate(zip(boxes, track_ids, confs)):
                         # Sanity Check for NaNs
                         if torch.isnan(box).any() or torch.isinf(box).any():
                             continue
                             
                         x1, y1, x2, y2 = map(int, box)
                         detected_this_frame = True
                         
                         # --- SIZE CALCULATION ---
                         box_w_px = x2 - x1
                         box_y_center = (y1 + y2) / 2
                         img_h, img_w = results[0].orig_shape[0], results[0].orig_shape[1]
                         
                         # Perspective sizing
                         norm_y = box_y_center / img_h
                         safe_y = max(0.3, min(1.0, norm_y))
                         fov_width_m = np.interp(safe_y, [0.3, 1.0], [12.0, 1.8])
                         current_size_m = round((box_w_px / img_w) * fov_width_m, 2)

                         # CALCULATE DEPTH INTENSITY for this pothole
                         # In MiDaS, higher value (lighter) = closer. Lower (darker) = further/deeper.
                         # Pothole might be "darker" (further) than road surface or "lighter" depending on texture.
                         # Let's just grab the mean value for "interest".
                         if depth_out is not None:
                             # Ensure ROI coordinates are within bounds
                             x1_roi = max(0, x1)
                             y1_roi = max(0, y1)
                             x2_roi = min(depth_out.shape[1], x2)
                             y2_roi = min(depth_out.shape[0], y2)

                             if x2_roi > x1_roi and y2_roi > y1_roi:
                                 roi = depth_out[y1_roi:y2_roi, x1_roi:x2_roi]
                                 avg_val = np.mean(roi)
                                 pothole_depth_val = round(avg_val, 1)
                         
                         # --- NEW VISUALIZATION: BLUE FILL ONLY (No Boxes) ---
                         if results[0].masks is not None:
                             if i < len(results[0].masks.xy):
                                 mask_poly = results[0].masks.xy[i]
                                 if len(mask_poly) > 0:
                                     int_poly = np.array(mask_poly, dtype=np.int32)
                                     # Blue Fill (BGR: 255, 0, 0)
                                     cv2.fillPoly(overlay, [int_poly], (255, 0, 0))
                             
                         # --- SAVE LOGIC (De-duplication) ---
                         # 1. Check if ID already processed in this session
                         if track_id not in self.processed_ids:
                             
                             if self.db and self.gps:
                                 lat, lon = self.gps.get_location()
                                 # Debug Print
                                 # print(f"DEBUG: Check Dup ID:{track_id} Lat:{lat:.5f} Lon:{lon:.5f}")
                                 
                                 # 2. Check Database for geospatial duplicate (Solution 3)
                                 # DISABLED for Patio Testing (Force Save)
                                 # if not self.db.is_duplicate(lat, lon, radius_m=1.0):
                                 if True:
                                      
                                      # Valid New Pothole!
                                      self.processed_ids.add(track_id)
                                      
                                      # Save Clean Image (before blend)
                                      current_time = time.time()
                                      filename = f"captures/pothole_{track_id}_{int(current_time)}.jpg"
                                      cv2.imwrite(filename, cv_img) 
                                      
                                      self.db.insert_pothole(lat, lon, conf, image_path=filename, size=current_size_m, fps=self.current_fps)
                                      print(f"✅ POTHOLE SAVED! ID: {track_id} | {current_size_m}m | Conf: {conf:.2f} | FPS: {self.current_fps:.1f}")
                                      
                                      # Trigger Alert
                                      self.last_alert_time = 0 # Reset to force alert

                         # Queue Text for Drawing (After Blend)
                         label_text = f"ID:{track_id} {current_size_m}m"
                         labels_queue.append( ( (x1, y1), label_text ) )


                # Calculate FPS
                fps = 1.0 / (time.time() - start_time)
                self.current_fps = fps # Update for next frame/save
                
                # Stats
                detections = len(results[0].boxes) if results[0].boxes else 0
                stats = {
                    "fps": round(fps, 1),
                    "detections": detections,
                    "vibration": 0.0, # Placeholder
                    "depth_val": pothole_depth_val # New metric
                }
                
                # Optical Flow (Vibration Proxy) - Kept simple
                # ... (Keeping existing vibration logic scope)
                vibration_metric = 0.0
                if self.prev_gray is None:
                     self.prev_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                else:
                     curr_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                     try:
                         small_gray = cv2.resize(curr_gray, (160, 120))
                         small_prev = cv2.resize(self.prev_gray, (160, 120))
                         flow = cv2.calcOpticalFlowFarneback(small_prev, small_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                         mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                         vibration_metric = float(np.mean(mag))
                         stats["vibration"] = round(vibration_metric, 2)
                     except Exception:
                         pass
                     self.prev_gray = curr_gray

                # Override Vibration with Real Accelerometer if available
                if accel_data:
                    ax, ay, az = accel_data
                    if self.frame_count % 30 == 0:
                         print(f"🟢 ACCELEROMETER ACTIVE | g-force: {ax:.2f}, {ay:.2f}, {az:.2f}") # Debug Log

                    # Magnitude in Gs
                    mag = (ax**2 + ay**2 + az**2)**0.5
                    # Simple deviation from 1.0 (Approx Gravity)
                    vibration_metric = abs(mag - 1.0)
                    stats["vibration"] = round(vibration_metric, 2)
                
                self.latest_stats = stats
                
                # Apply Transparency (Blue Glow) at end of loop over detections
                cv2.addWeighted(overlay, 0.4, annotated_frame, 0.6, 0, annotated_frame)

                # Draw Labels (Sharp, on top of blend)
                for (pt, text) in labels_queue:
                    lx, ly = pt
                    # Black Background for readability
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_frame, (lx, ly - 20), (lx + tw + 4, ly), (0, 0, 0), -1)
                    # White Text
                    cv2.putText(annotated_frame, text, (lx + 2, ly - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Draw Labels (Sharp, on top of blend)
                for (pt, text) in labels_queue:
                    lx, ly = pt
                    # Black Background for readability
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_frame, (lx, ly - 20), (lx + tw + 4, ly), (0, 0, 0), -1)
                    # White Text
                    cv2.putText(annotated_frame, text, (lx + 2, ly - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Audio Alert Logic (Global for any detection in frame)
                if detected_this_frame and (time.time() - self.last_alert_time) > 2.0:
                     try:
                         import subprocess
                         subprocess.Popen(['afplay', '/System/Library/Sounds/Ping.aiff'])
                         self.last_alert_time = time.time()
                     except Exception:
                         pass

                # Encode to JPEG and save state
                self.latest_frame = self.encode_jpeg(annotated_frame)

                # Emit Depth Map Signal
                if depth_colormap is not None:
                    self.latest_depth = self.encode_jpeg(depth_colormap)

            else:
                if self.video_path:
                    print("Video finished")
                    self.stop()
                else:
                    print("Failed to read frame")
                    time.sleep(0.1)

        # Shut down
        if self.use_tcp and tcp_receiver:
            tcp_receiver.release()
        elif cap:
            cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.join(timeout=2.0)

    def encode_jpeg(self, cv_img):
        """Convert from an opencv image to JPEG bytes"""
        resized = cv2.resize(cv_img, (640, 480))
        ret, buffer = cv2.imencode('.jpg', resized)
        if ret:
            return buffer.tobytes()
        return b''
