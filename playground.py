import sys
import cv2
import numpy as np
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

# Reuse existing modules
from edge_sensing_system.server.processing.detector import Detector

class VideoThread(QThread):
    change_pixmap_signal = Signal(QImage)
    
    def __init__(self, detector):
        super().__init__()
        self.detector = detector
        self.running = True
        self.source = None # File path
    
    def set_file_mode(self, filepath):
        self.source = filepath
        self.running = True

    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        cap = cv2.VideoCapture(self.source)

        while self.running:
            if cap is None: break
            ret, frame = cap.read()
            if not ret: 
                # Loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            # Simulation speed for file
            time.sleep(0.03) 

            if frame is not None:
                # Predict
                annotated_frame = self.detector.predict(frame)
                self.emit_image(annotated_frame)
        
        if cap:
            cap.release()
            
    def emit_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 480, Qt.KeepAspectRatio)
        self.change_pixmap_signal.emit(p)

class Playground(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pothole Detector Playground (Video Only)")
        self.setGeometry(100, 100, 800, 600)
        
        # UI Setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Video Label
        self.video_label = QLabel("Carga un video para probar el modelo")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setFixedSize(640, 480)
        self.layout.addWidget(self.video_label, alignment=Qt.AlignCenter)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("📂 Cargar Video")
        self.btn_load.clicked.connect(self.load_video)
        btn_layout.addWidget(self.btn_load)
        
        self.btn_stop = QPushButton("⏹ Detener")
        self.btn_stop.clicked.connect(self.stop_video)
        btn_layout.addWidget(self.btn_stop)
        
        self.layout.addLayout(btn_layout)
        
        # Logic
        print("Initializing Detector...")
        self.detector = Detector() # Load model once
        self.thread = None

    def load_video(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir Video", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_name:
            self.stop_video()
            self.thread = VideoThread(self.detector)
            self.thread.change_pixmap_signal.connect(self.update_image)
            self.thread.set_file_mode(file_name)
            self.thread.start()

    def stop_video(self):
        if self.thread:
            self.thread.stop()
            self.thread = None
        self.video_label.setText("Detenido")

    def update_image(self, q_img):
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

    def closeEvent(self, event):
        self.stop_video()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Playground()
    window.show()
    sys.exit(app.exec())
