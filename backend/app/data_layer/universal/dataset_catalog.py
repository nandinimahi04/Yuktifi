"""
Dataset Catalog Schema and Registry (UYDF-1.0).
Provides a comprehensive schema for official and project datasets discovered in Documents SIH 26.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DatasetCatalogEntry(BaseModel):
    dataset_id: str
    dataset_name: str
    organization: str
    source_type: str
    source_url: Optional[str] = None
    original_filename: str
    original_format: str
    version: str = "1.0"
    reference_year: Optional[int] = None
    reference_date: Optional[str] = None
    update_frequency: str = "DECENNIAL"  # ANNUAL, MONTHLY, STATIC, REALTIME, ADHOC
    geographic_scope: str = "INDIA"
    geographic_resolution: str = "DISTRICT"  # NATIONAL, STATE, DISTRICT, SUBDISTRICT, VILLAGE, GRID_1KM
    coverage: str = "OFFICIAL_COMPREHENSIVE"
    description: str
    license: str = "Open Government Data (OGD) / Public"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checksum: str
    parser: str
    schema_version: str = "UYDF-1.0"
    status: str = "VERIFIED_ACTIVE"
    limitations: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
