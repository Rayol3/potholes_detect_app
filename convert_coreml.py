from ultralytics import YOLO

# Load the working PyTorch model
model = YOLO('model/train_yolo11L/weights/best.pt')

print("Exporting to CoreML (Standard, nms=False)...")
# Export without NMS (Ultralytics handles post-processing for Segmentation models)
model.export(format='coreml', nms=False)
