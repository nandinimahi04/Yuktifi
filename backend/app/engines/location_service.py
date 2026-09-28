"""
Location Service — resolves user input to a known location ID.
Integrates with the DataService to match against valid loaded datasets.
"""
from typing import Optional
from app.services.data_service import data_service


from app.api_clients.geocoding_client import GeocodingClient

def resolve_location(input_text: str) -> Optional[str]:
    """
    Match user's location input using Geocoding API.
    Returns the location_id string as 'lat,lon', or None if no match.
    """
    if not input_text:
        return None
        
    geocoder = GeocodingClient()
    coords = geocoder.get_coordinates(input_text)
    
    if coords:
        return f"{coords[0]},{coords[1]}"
        
    return None


def get_location_metadata(location_id: str) -> dict:
    """Return metadata for a given location_id string ('lat,lon')."""
    try:
        if "," in location_id:
            lat_str, lon_str = location_id.split(",")
            return {
                "id": location_id,
                "lat": float(lat_str),
                "lon": float(lon_str),
                "village": "Selected Location",
                "block": "",
                "district": "",
                "state": "Maharashtra", # Example default state for commodity searches
                "radius_km": 5
            }
    except Exception:
        pass
        
    return {}
