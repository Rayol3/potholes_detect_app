import sys
import os
import cv2
import time
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QComboBox, 
                               QTabWidget, QSplitter, QMessageBox)
from PySide6.QtGui import QPixmap, QImage, QAction, QKeyEvent
from PySide6.QtCore import Qt, Slot, QTimer

# Matplotlib for Vibration Graph
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Custom Modules
from styles import DARK_THEME
from detection_thread import DetectionThread
from database import Database
from gps_helper import GPSHelper
from map_view import MapView
import report_generator
from edge_sensing_system.server import config

MODEL_PATH = config.MODEL_PATH

class DepthLiveView(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        self.header = QLabel("ESCANER PROFUNDIDAD (PSEUDO-LIDAR)")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("background-color: #222; color: #ff9900; font-weight: bold; font-size: 10px;")
        self.layout.addWidget(self.header)
        
        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: #111; border: 1px solid #333;")
        self.image_label.setScaledContents(True)
        self.layout.addWidget(self.image_label)
        
    @Slot(QImage)
    def update_image(self, qt_img):
        self.image_label.setPixmap(QPixmap.fromImage(qt_img))

class LivePanel(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Camera Controls
        controls = QHBoxLayout()
        self.camera_combo = QComboBox()
        self.btn_refresh = QPushButton("Refrescar Lista")
        self.btn_refresh.clicked.connect(self.refresh_cameras)
        
        controls.addWidget(QLabel("Cámara:"))
        controls.addWidget(self.camera_combo)
        controls.addWidget(self.btn_refresh)
        self.layout.addLayout(controls)
        
        buttons = QHBoxLayout()
        self.btn_start = QPushButton("Iniciar Detección")
        self.btn_stop = QPushButton("Detener")
        self.btn_stop.setEnabled(False)
        self.btn_session = QPushButton("Finalizar y Reporte") # Reporting Button
        self.btn_session.setStyleSheet("background-color: #007acc; color: white;")
        
        # Clear Data Button
        self.btn_clear = QPushButton("Limpiar BD")
        self.btn_clear.setStyleSheet("background-color: #d9534f; color: white;")
        self.btn_clear.clicked.connect(parent_app.clear_data)

        buttons.addWidget(self.btn_start)
        buttons.addWidget(self.btn_stop)
        buttons.addWidget(self.btn_session)
        buttons.addWidget(self.btn_clear)
        self.layout.addLayout(buttons)
        
        # Video Feed
        self.video_label = QLabel("Cámara Apagada")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border: 2px solid #444;")
        self.video_label.setMinimumSize(640, 480)
        self.layout.addWidget(self.video_label)
        
        # Connect
        self.btn_start.clicked.connect(parent_app.start_detection)
        self.btn_stop.clicked.connect(parent_app.stop_detection)
        self.btn_session.clicked.connect(parent_app.end_session)
        
        self.available_cameras = []
        self.refresh_cameras()

    def refresh_cameras(self):
        self.camera_combo.clear()
        self.available_cameras = self.parent_app.scan_cameras()
        if not self.available_cameras:
            self.camera_combo.addItem("No se encontró cámara")
            self.btn_start.setEnabled(False)
        else:
            for idx, name in self.available_cameras:
                self.camera_combo.addItem(f"{name} (Índice {idx})")
            self.btn_start.setEnabled(True)

class PotholeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Detector de Baches - Panel de Control")
        self.resize(1200, 800)
        self.setStyleSheet(DARK_THEME)

        self.db = Database()
        self.gps = GPSHelper()
        self.thread = None
        self.pothole_cache = [] # Cache for current session
        
        # Main Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Info Header
        self.lbl_info = QLabel("Presione 'ESPACIO' para marcar incidente manual. | Estado: Listo")
        self.lbl_info.setStyleSheet("font-size: 14px; color: #aaa; padding: 5px;")
        main_layout.addWidget(self.lbl_info)
        
        # Splitter Layout (3-Panel)
        splitter_h = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter_h)
        
        # 1. Left Panel: Video
        self.live_panel = LivePanel(self)
        splitter_h.addWidget(self.live_panel)
        
        # Right Splitter (Vertical)
        splitter_v = QSplitter(Qt.Vertical)
        splitter_h.addWidget(splitter_v)
        
        # 2. Right Top: Map
        self.map_view = MapView(self.db)
        splitter_v.addWidget(self.map_view)
        
        # 3. Right Bottom: Depth View (Replaces Vibration Graph)
        self.depth_view = DepthLiveView()
        splitter_v.addWidget(self.depth_view)
        
        # Set Splitter ratios
        splitter_h.setStretchFactor(0, 2) # Video wider
        splitter_h.setStretchFactor(1, 1) # Map column
        splitter_v.setStretchFactor(0, 2) # Map taller
        splitter_v.setStretchFactor(1, 1) # Graph smaller
        
        # Timer for Real-time Map Update
        self.map_timer = QTimer()
        self.map_timer.timeout.connect(self.update_map_periodic)
        self.map_timer.start(2000) # Every 2 seconds

    def scan_cameras(self):
        import subprocess
        # Basic scanning
        available = []
        
        # 0. Edge Sensor Option (First)
        available.append(("tcp", "📱 iPhone Edge Sensor"))
        
        # Attempt to find all via OpenCV
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append((i, f"Cámara USB/Webcam {i}"))
                cap.release()
        return available

    @Slot()
    def start_detection(self):
        combo_idx = self.live_panel.camera_combo.currentIndex()
        if combo_idx < 0: return
        cam_idx = self.live_panel.available_cameras[combo_idx][0]
        
        self.live_panel.btn_start.setEnabled(False)
        self.live_panel.btn_stop.setEnabled(True)
        self.live_panel.camera_combo.setEnabled(False)
        self.live_panel.btn_session.setEnabled(True)
        
        self.pothole_cache = [] # Reset session cache
        
        self.thread = DetectionThread(MODEL_PATH, camera_index=cam_idx, db=self.db, gps=self.gps)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.stats_signal.connect(self.update_stats)
        self.thread.depth_signal.connect(self.depth_view.update_image) # Connect Depth
        self.thread.start()
        self.lbl_info.setText("Estado: Ejecutando | Presione ESPACIO para Marcado Manual")

    @Slot()
    def stop_detection(self):
        if self.thread:
            self.thread.stop()
            self.thread = None
        
        self.live_panel.btn_start.setEnabled(True)
        self.live_panel.btn_stop.setEnabled(False)
        self.live_panel.camera_combo.setEnabled(True)
        self.lbl_info.setText("Estado: Detenido")

    @Slot(QImage)
    def update_image(self, qt_img):
        self.live_panel.video_label.setPixmap(QPixmap.fromImage(qt_img))

    @Slot(dict)
    def update_stats(self, stats):
        # Update Vibration Graph
        vib = stats.get("vibration", 0.0)
        # self.vib_graph.update_val(vib) # Disabled for Depth View
        
    def update_map_periodic(self):
        # Update Route & Refresh if Auto-Refresh ON
        if self.gps:
            lat, lon = self.gps.get_location()
            self.map_view.update_route(lat, lon)
            
            if self.map_view.cb_auto_refresh.isChecked():
                self.map_view.refresh_map(current_location=[lat, lon])

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Space:
            self.handle_manual_trigger()
        else:
            super().keyPressEvent(event)

    def handle_manual_trigger(self):
        # Manual Incident
        lat, lon = self.gps.get_location()
        print(f"Marcado Manual en {lat}, {lon}")
        
        # Save to DB as Manual
        self.db.insert_pothole(lat, lon, 1.0, image_path=None) # 1.0 confidence
        
        # Flash or Feedback
        self.lbl_info.setText(f"MARCADOR MANUAL GUARDADO @ {lat:.4f}, {lon:.4f}")
        QTimer.singleShot(2000, lambda: self.lbl_info.setText("Estado: Ejecutando (Espacio para Manual)"))

    def end_session(self):
        self.stop_detection()
        
        # Capture Map Screenshot
        map_img_path = "captures/map_snapshot.png"
        # Ensure map is visible before grabbing
        pixmap = self.map_view.grab() 
        pixmap.save(map_img_path)
        
        # Generate Report
        potholes = self.db.get_all_potholes_raw()
        
        fname = "Orden_Trabajo_Sesion.pdf"
        report_generator.generate_report(potholes, fname, map_image_path=map_img_path)
        
        msg = QMessageBox()
        msg.setWindowTitle("Sesión Finalizada")
        msg.setText(f"Orden de Trabajo PDF Generada.\nArchivo: {fname}")
        msg.exec()

    def closeEvent(self, event):
        self.stop_detection()
        if self.thread:
             self.thread.wait()
        event.accept()

    def clear_data(self):
        confirm = QMessageBox.question(self, "Confirmar Limpieza", 
                                     "¿Está seguro de que desea borrar TODOS los datos de baches?",
                                     QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            success = self.db.clear_database()
            if success:
                self.map_view.refresh_map() # Clear map
                QMessageBox.information(self, "Éxito", "Base de datos limpiada correctamente.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo limpiar la base de datos.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PotholeApp()
    window.show()
    sys.exit(app.exec())
