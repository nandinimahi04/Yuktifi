import math
from typing import List, Dict, Any, Tuple

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371.0088 # Radius of earth in kilometers.
    return c * r

def filter_within_radius(center_lat: float, center_lon: float, points: List[Dict[str, Any]], radius_km: float) -> List[Dict[str, Any]]:
    """
    Filters a list of dictionaries with 'latitude' and 'longitude' keys,
    returning only those within radius_km of the center.
    Also adds a 'distance_km' field to the dictionaries.
    """
    filtered = []
    for pt in points:
        lat = pt.get("latitude")
        lon = pt.get("longitude")
        if lat is None or lon is None:
            continue
            
        try:
            lat = float(lat)
            lon = float(lon)
            dist = haversine_km(center_lat, center_lon, lat, lon)
            if dist <= radius_km:
                pt_copy = dict(pt)
                pt_copy["distance_km"] = round(dist, 2)
                filtered.append(pt_copy)
        except (ValueError, TypeError):
            continue
            
    return filtered
