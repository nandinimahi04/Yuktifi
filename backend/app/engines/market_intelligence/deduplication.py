"""
Deduplication Engine for Overture Maps Places + OpenStreetMap (Phase 1).

Deterministically reconciles spatial Points of Interest from Overture and OSM:
- Uses geospatial proximity (<= 50m)
- Normalized string similarity (SequenceMatcher >= 0.75)
- Prevents naive double-counting (never overture_count + osm_count)
- Produces true unique_mapped_count with complete multi-source lineage.
"""
from __future__ import annotations

import re
import math
import difflib
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088

NOISE_WORDS = {
    "store", "shop", "shopping", "centre", "center", "market", "bazaar", "mart", 
    "hotel", "restaurant", "tea", "chai", "stall", "corner", "peth", 
    "road", "solapur", "sholapur", "bazar", "retail", "super", "depot",
    "snack", "snacks"
}

def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two coordinates."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * 1000.0 * math.asin(math.sqrt(a))

def normalize_poi_name(name: str) -> str:
    """Normalize POI name for fuzzy matching by removing noise and punctuation."""
    if not name:
        return ""
    s = name.lower()
    # Remove parenthetical details
    s = re.sub(r"\([^)]*\)", "", s)
    # Remove non-alphanumerics
    s = re.sub(r"[^\w\s]", " ", s)
    tokens = [w for w in s.split() if w and w not in NOISE_WORDS]
    return " ".join(tokens) if tokens else s.strip()

def are_pois_duplicate(poi1: Dict[str, Any], poi2: Dict[str, Any], max_dist_meters: float = 50.0) -> Tuple[bool, float, float]:
    """
    Check if two POIs represent the same physical business.
    Returns: (is_duplicate, distance_meters, name_similarity)
    """
    lat1, lon1 = float(poi1.get("latitude") or poi1.get("lat", 0)), float(poi1.get("longitude") or poi1.get("lon", 0))
    lat2, lon2 = float(poi2.get("latitude") or poi2.get("lat", 0)), float(poi2.get("longitude") or poi2.get("lon", 0))

    if lat1 == 0 or lat2 == 0 or lon1 == 0 or lon2 == 0:
        return False, 999999.0, 0.0

    dist_m = haversine_meters(lat1, lon1, lat2, lon2)
    if dist_m > max_dist_meters:
        return False, dist_m, 0.0

    name1 = normalize_poi_name(poi1.get("name", ""))
    name2 = normalize_poi_name(poi2.get("name", ""))

    if not name1 or not name2:
        # If one is unnamed but sits within 15 meters, treat as duplicate
        if dist_m <= 15.0:
            return True, dist_m, 0.5
        return False, dist_m, 0.0

    # Substring match
    if name1 == name2 or name1 in name2 or name2 in name1:
        return True, dist_m, 1.0

    # Sequence matcher ratio
    sim = difflib.SequenceMatcher(None, name1, name2).ratio()
    if sim >= 0.75:
        return True, dist_m, sim

    # Very close proximity (<= 20m) with modest similarity
    if dist_m <= 20.0 and sim >= 0.55:
        return True, dist_m, sim

    return False, dist_m, sim

def deduplicate_places(
    overture_places: List[Dict[str, Any]], 
    osm_places: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge Overture and OSM places deterministically.
    Returns:
      {
        "overture_count": int,
        "osm_count": int,
        "duplicate_count": int,
        "unique_mapped_count": int,
        "competitors": List[Dict[str, Any]],
        "deduplication_method": str
      }
    """
    unique_places: List[Dict[str, Any]] = []
    matched_osm_indices = set()
    duplicate_count = 0

    # Process Overture places first
    for ovt in overture_places:
        matched = False
        ovt_copy = {
            "id": ovt.get("id"),
            "name": ovt.get("name"),
            "category": ovt.get("category"),
            "latitude": ovt.get("latitude") or ovt.get("lat"),
            "longitude": ovt.get("longitude") or ovt.get("lon"),
            "distance_km": ovt.get("distance_km"),
            "sources": ["overture"],
            "is_duplicate_resolved": False,
        }

        # Check against OSM places
        for idx, osm in enumerate(osm_places):
            if idx in matched_osm_indices:
                continue
            is_dup, dist_m, sim = are_pois_duplicate(ovt_copy, osm)
            if is_dup:
                matched = True
                matched_osm_indices.add(idx)
                duplicate_count += 1
                ovt_copy["sources"].append("osm")
                ovt_copy["is_duplicate_resolved"] = True
                ovt_copy["osm_matched_id"] = osm.get("id")
                ovt_copy["reconciliation_note"] = f"Resolved duplicate within {dist_m:.1f}m (name similarity: {sim:.2f})"
                # Prefer longer/cleaner name if available
                if len(osm.get("name", "")) > len(ovt_copy["name"]):
                    ovt_copy["name"] = osm["name"]
                break

        unique_places.append(ovt_copy)

    # Add remaining unmatched OSM places
    for idx, osm in enumerate(osm_places):
        if idx not in matched_osm_indices:
            unique_places.append({
                "id": osm.get("id"),
                "name": osm.get("name"),
                "category": osm.get("category"),
                "latitude": osm.get("latitude") or osm.get("lat"),
                "longitude": osm.get("longitude") or osm.get("lon"),
                "distance_km": osm.get("distance_km"),
                "sources": ["osm"],
                "is_duplicate_resolved": False,
            })

    # Sort merged competitors by distance
    unique_places.sort(key=lambda x: x.get("distance_km", 999.0))

    return {
        "overture_count": len(overture_places),
        "osm_count": len(osm_places),
        "duplicate_count": duplicate_count,
        "unique_mapped_count": len(unique_places),
        "competitors": unique_places,
        "deduplication_method": "Geospatial proximity (<=50m) + fuzzy token string matching (>=0.75 ratio)",
    }
