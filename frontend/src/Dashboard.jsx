import { useState, useEffect } from 'react';
import { Play, Square, RefreshCw, Camera } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';

// Fix Leaflet icon issue in React
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const API_BASE = 'http://localhost:8000';

export default function Dashboard() {
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [stats, setStats] = useState({ fps: 0, detections: 0, vibration: 0, depth_val: 0 });
  const [location, setLocation] = useState([0, 0]);
  const [incidents, setIncidents] = useState([]);
  
  useEffect(() => {
    fetchCameras();
    
    // Polling for stats and map data
    const interval = setInterval(() => {
      if (isRunning) {
        fetch(`${API_BASE}/api/stats`)
          .then(res => res.json())
          .then(data => setStats(data))
          .catch(err => console.error("Stats Error:", err));
          
        fetch(`${API_BASE}/api/route`)
          .then(res => res.json())
          .then(data => {
              if (data.lat !== 0) setLocation([data.lat, data.lon]);
          })
          .catch(err => console.error(err));
          
        fetch(`${API_BASE}/api/incidents`)
          .then(res => res.json())
          .then(data => setIncidents(data.incidents || []))
          .catch(err => console.error(err));
      }
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isRunning]);

  const fetchCameras = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/cameras`);
      const data = await res.json();
      setCameras(data);
      if (data.length > 0) setSelectedCamera(data[0].id);
    } catch (error) {
      console.error("Failed to fetch cameras:", error);
    }
  };

  const handleStart = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: selectedCamera })
      });
      const data = await res.json();
      if (data.status === 'started') setIsRunning(true);
    } catch (error) {
      console.error("Start error:", error);
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/api/stop`, { method: 'POST' });
      setIsRunning(false);
    } catch (error) {
      console.error("Stop error:", error);
    }
  };

  return (
    <div className="dashboard-grid">
      {/* Left Column: Video & Map */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        <div className="video-container">
          {isRunning ? (
            <img 
              src={`${API_BASE}/video_feed`} 
              className="video-feed" 
              alt="Live Feed"
              onError={(e) => { e.target.src = ''; console.log('Video feed lost'); }}
            />
          ) : (
            <div style={{ color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <Camera size={48} opacity={0.5} />
              <span>Camera Offline</span>
            </div>
          )}
        </div>
        
        <div className="map-container">
          <MapContainer center={location[0] !== 0 ? location : [40.7128, -74.0060]} zoom={15} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {location[0] !== 0 && <Marker position={location}><Popup>Current Location</Popup></Marker>}
            {incidents.map((inc, idx) => (
              <Marker key={idx} position={[inc.lat, inc.lon]}>
                <Popup>
                  Pothole Detected<br/>Conf: {inc.confidence}<br/>Size: {inc.size}m
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      </div>

      {/* Right Column: Controls & Stats */}
      <div className="glass-panel controls-panel">
        <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Control Center</h2>
        
        <div className="input-group">
          <label>Camera Source</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <select 
              value={selectedCamera} 
              onChange={(e) => setSelectedCamera(e.target.value)}
              disabled={isRunning}
              style={{ flex: 1 }}
            >
              {cameras.map(cam => (
                <option key={cam.id} value={cam.id}>{cam.name}</option>
              ))}
            </select>
            <button className="btn" style={{ background: 'rgba(255,255,255,0.1)' }} onClick={fetchCameras} disabled={isRunning}>
              <RefreshCw size={18} />
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
          <button 
            className="btn btn-primary" 
            style={{ flex: 1 }} 
            onClick={handleStart} 
            disabled={isRunning}
          >
            <Play size={18} /> Start
          </button>
          <button 
            className="btn btn-danger" 
            style={{ flex: 1 }} 
            onClick={handleStop} 
            disabled={!isRunning}
          >
            <Square size={18} /> Stop
          </button>
        </div>

        <div className="stats-grid">
          <div className="stat-box">
            <span className="stat-label">FPS</span>
            <span className="stat-value">{stats.fps.toFixed(1)}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Detections</span>
            <span className="stat-value">{stats.detections}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Vibration</span>
            <span className="stat-value">{stats.vibration.toFixed(2)}</span>
          </div>
          <div className="stat-box">
            <span className="stat-label">Depth Value</span>
            <span className="stat-value">{stats.depth_val.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
