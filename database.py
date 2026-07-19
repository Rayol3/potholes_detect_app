from pymongo import MongoClient
from datetime import datetime

# Provide a fallback if user doesn't have Mongo running locally
# We will use a flag or try/except block.

DB_URI = "mongodb://localhost:27017/"
DB_NAME = "potholes"
COLLECTION_NAME = "detections"

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.connect()

    def connect(self):
        try:
            self.client = MongoClient(DB_URI, serverSelectionTimeoutMS=2000)
            # Trigger connection to check if it's live
            self.client.server_info()
            self.db = self.client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
            print("Connected to MongoDB")
        except Exception as e:
            print(f"Could not connect to MongoDB: {e}")
            self.client = None

    def insert_pothole(self, lat, lon, confidence, image_path=None, size=None, fps=None):
        if self.collection is None:
            return
        
        doc = {
            "timestamp": datetime.now(),
            "location": {
                "type": "Point",
                "coordinates": [lon, lat] # GeoJSON format: [longitude, latitude]
            },
            "lat": lat,
            "lon": lon,
            "confidence": float(confidence),
            "image_path": image_path,
            "size_m": size,
            "fps": fps
        }
        try:
            self.collection.insert_one(doc)
            print(f"Saved pothole at {lat}, {lon}")
        except Exception as e:
            print(f"Error saving to DB: {e}")

    def get_all_potholes(self):
        if self.collection is None:
            return []
        try:
            # Return list of [lat, lon, weight] for heatmap
            cursor = self.collection.find({}, {"lat": 1, "lon": 1, "confidence": 1})
            data = []
            for doc in cursor:
                if "lat" in doc and "lon" in doc:
                    data.append([doc["lat"], doc["lon"], doc.get("confidence", 1.0)])
            return data
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []

    def get_all_potholes_raw(self):
        """Returns all pothole documents as a list of dicts for reporting."""
        if self.collection is None:
            return []
        try:
            return list(self.collection.find().sort("timestamp", -1))
        except Exception as e:
            print(f"Error fetching raw data: {e}")
            return []

    def clear_database(self):
        """Deletes all documents in the collection."""
        if self.collection is None:
            return False
        try:
            self.collection.delete_many({})
            print("Database cleared.")
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False

    def is_duplicate(self, lat, lon, radius_m=5):
        """
        Check if a pothole exists within radius_m meters of (lat, lon).
        """
        if self.collection is None:
            return False
            
        # Haversine function
        def haversine_dist(lat1, lon1, lat2, lon2):
            import math
            R = 6371000 # Earth radius in meters
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c

        # Retrieve all coordinates (optimized projection)
        # Note: For very large DBs, use MongoDB $near or $geoWithin.
        # For this app, Python iteration is fine and robust.
        existing = self.collection.find({}, {'lat': 1, 'lon': 1})
        
        for p in existing:
            try:
                d = haversine_dist(lat, lon, p['lat'], p['lon'])
                if d < radius_m:
                    return True # Duplicate found
            except Exception:
                continue
                
                
        return False
