import time
import threading
import objc
from CoreLocation import CLLocationManager, kCLLocationAccuracyBest, kCLDistanceFilterNone, kCLAuthorizationStatusAuthorizedAlways, kCLAuthorizationStatusAuthorizedWhenInUse
from Foundation import NSObject

class LocationDelegate(NSObject):
    def init(self):
        self = objc.super(LocationDelegate, self).init()
        if self is None: return None
        self.last_location = (0.0, 0.0)
        return self

    def locationManager_didUpdateLocations_(self, manager, locations):
        try:
            loc = locations[-1]
            lat = loc.coordinate().latitude
            lon = loc.coordinate().longitude
            self.last_location = (lat, lon)
        except Exception as e:
            print(f"Error parsing location: {e}")

    def locationManager_didFailWithError_(self, manager, error):
        print(f"CoreLocation Error: {error}")

class CoreLocationHelper:
    def __init__(self):
        self.delegate = LocationDelegate.alloc().init()
        self.manager = CLLocationManager.alloc().init()
        self.manager.setDelegate_(self.delegate)
        self.manager.setDesiredAccuracy_(kCLLocationAccuracyBest)
        self.manager.setDistanceFilter_(kCLDistanceFilterNone)
        
        # Request access
        self.manager.requestAlwaysAuthorization()
        self.manager.startUpdatingLocation()
        
    def get_location(self):
        return self.delegate.last_location
