from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
import folium
from folium.plugins import HeatMap, FastMarkerCluster
import io
import math

class MapView(QWidget):
    def __init__(self, db_handler):
        super().__init__()
        self.db = db_handler
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Controls Layer (Compact Horizontal Layout)
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cb_auto_refresh = QCheckBox("Auto-Actualizar")
        self.cb_auto_refresh.setChecked(True)
        controls_layout.addWidget(self.cb_auto_refresh)
        
        controls_layout.addStretch()
        
        self.lbl_stats = QLabel("Cercanos: -")
        self.lbl_stats.setStyleSheet("font-size: 12px; font-weight: bold; color: #ff5555;")
        controls_layout.addWidget(self.lbl_stats)
        
        self.layout.addLayout(controls_layout)
        
        self.route_path = [] # Store GPS history
        
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)
        
        self.refresh_map()

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371000 # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R*c

    def refresh_map(self, current_location=None):
        try:
            # Get data from DB
            data = self.db.get_all_potholes()
            
            # Determine center
            start_coords = [0, 0]
            if current_location and current_location[0] != 0:
                 start_coords = [current_location[0], current_location[1]]
            elif data:
                avg_lat = sum(d[0] for d in data) / len(data)
                avg_lon = sum(d[1] for d in data) / len(data)
                start_coords = [avg_lat, avg_lon]

            # Calculate Nearby Stats and Prepare Valid Points
            nearby_count = 0
            valid_points = []
            if current_location and current_location[0] != 0:
                current_lat, current_lon = current_location[0], current_location[1]
                for p in data:
                    if len(p) >= 2:
                        valid_points.append([p[0], p[1]])
                        dist = self.haversine(current_lat, current_lon, p[0], p[1])
                        if dist < 500: # 500 meters
                            nearby_count += 1
                self.lbl_stats.setText(f"Baches Cercanos (<500m): {nearby_count}")
            else:
                 self.lbl_stats.setText("Baches Cercanos (<500m): N/A (Sin GPS)")

            # Create Map
            m = folium.Map(location=start_coords, zoom_start=17, tiles="CartoDB dark_matter")
            
            # Add Current Location Marker (Person Icon)
            if current_location:
                folium.Marker(
                    current_location,
                    popup="Estás aquí",
                    icon=folium.Icon(color="red", icon="user", prefix="fa")
                ).add_to(m)

            # Add Hybrid Visualizations
            if valid_points:
                # 1. Heatmap
                HeatMap(data).add_to(m)
                
                # 2. FastMarkerCluster (Optimized for thousands of points)
                FastMarkerCluster(valid_points).add_to(m)
            
            # 3. Route Polyline
            if len(self.route_path) > 1:
                folium.PolyLine(self.route_path, color="blue", weight=3, opacity=0.7).add_to(m)

            # Save to Bytes
            data_io = io.BytesIO()
            m.save(data_io, close_file=False)
            html = data_io.getvalue().decode()
            
            self.web_view.setHtml(html)
            
        except Exception as e:
            print(f"Error refreshing map: {e}")
            self.lbl_stats.setText(f"Map Error: {e}")

    def update_route(self, lat, lon):
        # Only add if it moved slightly to avoid clutter
        if not self.route_path or (abs(self.route_path[-1][0]-lat) > 0.0001 or abs(self.route_path[-1][1]-lon) > 0.0001):
            self.route_path.append([lat, lon])
