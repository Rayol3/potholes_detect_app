import os
import sys
import time
import asyncio
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import cv2

# Import our backend components
from detection_thread import DetectionThread
from database import Database
from gps_helper import GPSHelper
from edge_sensing_system.server import config

app = FastAPI(title="Pothole Detector & Labeler API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
db = Database()
gps = GPSHelper()
detection_thread = None
MODEL_PATH = config.MODEL_PATH

# Ensure captures and labels directories exist
os.makedirs("captures", exist_ok=True)
os.makedirs("labels", exist_ok=True)

# ---------------------------------------------------------
# Detection API
# ---------------------------------------------------------

@app.get("/api/cameras")
def get_cameras():
    """Scan and return available cameras"""
    available = []
    available.append({"id": "tcp", "name": "Auto Connect (Edge Sensor/iPhone)"})
    available.append({"id": "record3d", "name": "Record3D App (USB)"})
    
    # Local Webcams
    for i in range(2):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available.append({"id": str(i), "name": f"Local USB Webcam {i}"})
            cap.release()
    return available

@app.post("/api/start")
async def start_detection(request: Request):
    global detection_thread
    data = await request.json()
    cam_id = data.get("camera_id")
    
    if detection_thread and detection_thread.is_alive():
        return {"status": "error", "message": "Already running"}
        
    # Convert cam_id back to int if it's a digit
    if str(cam_id).isdigit():
        cam_id = int(cam_id)
        
    detection_thread = DetectionThread(MODEL_PATH, camera_index=cam_id, db=db, gps=gps)
    detection_thread.start()
    return {"status": "started"}

@app.post("/api/stop")
def stop_detection():
    global detection_thread
    if detection_thread:
        detection_thread.stop()
        detection_thread = None
    return {"status": "stopped"}

@app.get("/api/stats")
def get_stats():
    global detection_thread
    if detection_thread and detection_thread.is_alive():
        return detection_thread.latest_stats
    return {"fps": 0.0, "detections": 0, "vibration": 0.0, "depth_val": 0.0, "status": "stopped"}

# ---------------------------------------------------------
# Streaming API (MJPEG)
# ---------------------------------------------------------

async def frame_generator(feed_type="rgb"):
    global detection_thread
    while True:
        if not detection_thread or not detection_thread.is_alive():
            await asyncio.sleep(0.5)
            continue
            
        frame = detection_thread.latest_frame if feed_type == "rgb" else detection_thread.latest_depth
        
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(1/30.0) # Limit stream to ~30 FPS

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(frame_generator("rgb"), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/depth_feed")
async def depth_feed():
    return StreamingResponse(frame_generator("depth"), media_type="multipart/x-mixed-replace; boundary=frame")

# ---------------------------------------------------------
# Map & DB API
# ---------------------------------------------------------

@app.get("/api/incidents")
def get_incidents():
    incidents = db.get_all_potholes()
    return {"incidents": incidents}

@app.get("/api/route")
def get_route():
    if gps:
        lat, lon = gps.get_location()
        return {"lat": lat, "lon": lon}
    return {"lat": 0, "lon": 0}

@app.post("/api/clear")
def clear_db():
    db.clear_database()
    return {"status": "cleared"}

# ---------------------------------------------------------
# FastLabel Module API
# ---------------------------------------------------------

@app.get("/api/labeler/images")
def list_images():
    """List all images in the captures directory"""
    images = []
    for file in os.listdir("captures"):
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            images.append(file)
    return {"images": sorted(images)}

@app.get("/api/labeler/image/{filename}")
def get_image(filename: str):
    """Serve specific image for labeling"""
    path = os.path.join("captures", filename)
    if os.path.exists(path):
         with open(path, "rb") as f:
             return Response(content=f.read(), media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Image not found")

@app.post("/api/labeler/save")
async def save_annotation(request: Request):
    """Save YOLO annotation"""
    data = await request.json()
    filename = data.get("filename") # e.g. "image.jpg"
    content = data.get("content")   # The YOLO txt content
    
    if not filename or content is None:
         raise HTTPException(status_code=400, detail="Invalid data")
         
    basename = os.path.splitext(filename)[0]
    txt_filename = f"{basename}.txt"
    txt_path = os.path.join("labels", txt_filename)
    
    with open(txt_path, "w") as f:
        f.write(content)
        
    return {"status": "saved", "path": txt_path}

# Mount frontend (Assuming we build Vite to frontend/dist)
# Fallback to serving raw html if needed
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
else:
    print("WARNING: frontend/dist not found. Build the react app first.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
