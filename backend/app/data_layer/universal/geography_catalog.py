"""
Geography Catalog & Administrative Hierarchy Schema.
Maps hierarchical locations with Local Government Directory (LGD) codes,
Census 2011 codes, GPS centroids, and historical name aliases (e.g., Ahmadnagar <-> Ahilyanagar).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class GeographyEntry(BaseModel):
    geography_id: str
    lgd_code: Optional[str] = None
    census_2011_code: Optional[str] = None
    level: str  # STATE, DISTRICT, SUBDISTRICT, VILLAGE, TOWN, WARD, GRAM_PANCHAYAT
    name: str
    normalized_name: str
    aliases: List[str] = Field(default_factory=list)
    country: str = "India"
    state: str
    district: Optional[str] = None
    subdistrict: Optional[str] = None
    village: Optional[str] = None
    town: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geometry: Optional[Dict[str, Any]] = None
    source: str = "Local Government Directory (MoPR) & Census 2011"
    reference_year: int = 2011
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    status: str = "ACTIVE"
