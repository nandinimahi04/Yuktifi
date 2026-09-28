import httpx
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class GeocodingClient:
    """
    Client for OpenStreetMap's Nominatim geocoding service.
    Converts a place name (e.g. 'Pune, Maharashtra') into Latitude and Longitude.
    """
    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        # Nominatim requires a valid user agent
        self.headers = {
            "User-Agent": "YuktiFi-Market-Intelligence/1.0 (contact@yukti.gov.in)"
        }

    def get_coordinates(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Returns (lat, lon) for the given query, or None if not found.
        """
        try:
            with httpx.Client(headers=self.headers) as client:
                response = client.get(
                    self.BASE_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    logger.info(f"Geocoded '{query}' to {lat}, {lon}")
                    return (lat, lon)
                
                logger.warning(f"Could not geocode '{query}'")
                return None
        except Exception as e:
            logger.error(f"Geocoding API error for '{query}': {e}")
            return None
