from core_location_helper import CoreLocationHelper
import geocoder # Keep as backup

class GPSHelper:
    def __init__(self):
        self.cl_helper = None
        self.use_real_gps = False
        
        try:
            self.cl_helper = CoreLocationHelper()
            self.use_real_gps = True
            print("Using Real-Time CoreLocation GPS")
        except Exception as e:
            print(f"Failed to init CoreLocation: {e}, falling back to IP/Sim")
            self.use_real_gps = False
            
        self.lat = 0.0
        self.lon = 0.0
        
        # Fallback Init
        if not self.use_real_gps:
            try:
                g = geocoder.ip('me')
                if g.latlng:
                    self.lat, self.lon = g.latlng
            except:
                pass

    def get_location(self):
        """
        Returns (lat, lon).
        """
        if self.use_real_gps and self.cl_helper:
            lat, lon = self.cl_helper.get_location()
            # If (0,0), it implies no update yet, maybe return last known or wait?
            if lat != 0.0 or lon != 0.0:
                self.lat, self.lon = lat, lon
            return self.lat, self.lon
        else:
            # Simulation fallback
            import random
            self.lat += random.uniform(-0.0001, 0.0001)
            self.lon += random.uniform(-0.0001, 0.0001)
            return self.lat, self.lon
