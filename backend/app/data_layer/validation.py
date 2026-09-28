import re
from typing import Dict, Any, List

def clean_competitor_name(name: str) -> str:
    """Normalizes whitespace and casing for competitor names."""
    if not name:
        return "Unknown Business"
    # Remove extra spaces and title case
    cleaned = re.sub(r'\s+', ' ', str(name)).strip().title()
    return cleaned

def validate_coordinates(lat: Any, lon: Any) -> bool:
    """Checks if coordinates are valid floats within bounds."""
    try:
        lat = float(lat)
        lon = float(lon)
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return True
        return False
    except (ValueError, TypeError):
        return False

def clean_competitor_list(competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleans a list of competitors, removing those without valid coordinates
    and normalizing names.
    """
    cleaned = []
    for comp in competitors:
        lat = comp.get("latitude")
        lon = comp.get("longitude")
        if validate_coordinates(lat, lon):
            comp_copy = dict(comp)
            comp_copy["name"] = clean_competitor_name(comp.get("name"))
            comp_copy["latitude"] = float(lat)
            comp_copy["longitude"] = float(lon)
            cleaned.append(comp_copy)
    return cleaned
