"""
Universal Yukti Evidence Contract (UYEC-1.0).
Provides a unified, traceable envelope over all heterogeneous project datasets,
guaranteeing complete provenance, confidence scoring, geography resolution, and time normalization.
"""
from __future__ import annotations
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ValueOrigin(str, Enum):
    USER_PROVIDED = "USER_PROVIDED"
    DATASET_DERIVED = "DATASET_DERIVED"
    CALCULATED = "CALCULATED"
    ASSUMED = "ASSUMED"
    MODELLED_ESTIMATE = "MODELLED_ESTIMATE"

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    ESTIMATED = "ESTIMATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class SourceCategory(str, Enum):
    OFFICIAL_STATISTICAL = "OFFICIAL_STATISTICAL"
    OFFICIAL_GEOGRAPHIC = "OFFICIAL_GEOGRAPHIC"
    OFFICIAL_MARKET = "OFFICIAL_MARKET"
    OFFICIAL_SCHEME = "OFFICIAL_SCHEME"
    OFFICIAL_INFRASTRUCTURE = "OFFICIAL_INFRASTRUCTURE"
    REMOTE_SENSING = "REMOTE_SENSING"
    OPEN_GEOSPATIAL = "OPEN_GEOSPATIAL"
    SURVEY = "SURVEY"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    RESEARCH = "RESEARCH"
    USER_PROVIDED = "USER_PROVIDED"
    CALCULATED = "CALCULATED"
    ASSUMED = "ASSUMED"
    UNKNOWN = "UNKNOWN"

class EntityContext(BaseModel):
    type: str = "ADMINISTRATIVE_BOUNDARY"  # DISTRICT, SUBDISTRICT, VILLAGE, TOWN, PINCODE, CATCHMENT
    name: str
    country: str = "India"
    state: Optional[str] = None
    district: Optional[str] = None
    subdistrict: Optional[str] = None
    village: Optional[str] = None
    town: Optional[str] = None
    lgd_code: Optional[str] = None
    census_code_2011: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geometry: Optional[Dict[str, Any]] = None

class ObservationPayload(BaseModel):
    metric: str
    value: Optional[float | int | str | Dict[str, Any]] = None
    unit: str
    category: Optional[str] = None
    original_value: Optional[Any] = None
    original_unit: Optional[str] = None
    normalized_value: Optional[float | int] = None
    normalized_unit: Optional[str] = None
    conversion_method: Optional[str] = None

class TimeContext(BaseModel):
    reference_year: Optional[int] = None
    observed_at: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    survey_period: Optional[str] = None

class ProvenanceContext(BaseModel):
    source: str
    source_url: Optional[str] = None
    original_file: str
    sheet: Optional[str] = None
    page: Optional[int] = None
    table: Optional[str] = None
    row: Optional[int] = None
    column: Optional[str] = None
    method: str = "DIRECT_MEASUREMENT"
    version: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class QualityContext(BaseModel):
    source_type: SourceCategory = SourceCategory.OFFICIAL_STATISTICAL
    origin: ValueOrigin = ValueOrigin.DATASET_DERIVED
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    coverage: str = "FULL"  # FULL, PARTIAL, SAMPLE, BENCHMARK
    is_estimate: bool = False
    is_assumption: bool = False

class BusinessContext(BaseModel):
    business_categories: List[str] = Field(default_factory=list)
    relevance: str = "DIRECT"  # DIRECT, PROXY, MACRO_INDICATOR

class UniversalEvidenceRecord(BaseModel):
    """
    Canonical Universal Yukti Evidence Contract (UYEC-1.0).
    Every fact, demographic count, consumption benchmark, price, and competitor finding
    conforms to this contract.
    """
    evidence_id: str = Field(default_factory=lambda: f"evi_{uuid.uuid4().hex[:16]}")
    dataset_id: str
    entity: EntityContext
    observation: ObservationPayload
    time: TimeContext
    provenance: ProvenanceContext
    quality: QualityContext
    business_context: BusinessContext = Field(default_factory=BusinessContext)
    limitations: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
