from pydantic import BaseModel
from typing import Optional, Any, List, Dict

class DataProvenance(BaseModel):
    source_type: str
    source_name: str
    source_url: Optional[str] = None
    dataset_name: Optional[str] = None
    last_updated: Optional[str] = None
    confidence: str
    methodology: Optional[str] = None

class MetricWithProvenance(BaseModel):
    value: Any
    provenance: DataProvenance

class MarketRequest(BaseModel):
    session_id: str
    location_id: str
    category_id: str
    category_name: Optional[str] = None
    budget: Optional[int] = None
    experience: Optional[str] = None
    idea_details: Optional[str] = None

class MarketResponse(BaseModel):
    location_id: str
    category_id: str
    category_name: str
    market_reach: MetricWithProvenance
    competitors: MetricWithProvenance
    pricing: MetricWithProvenance
    opportunity_gaps: MetricWithProvenance
    swot: MetricWithProvenance
    threats: MetricWithProvenance
    overall_confidence: str

# ─── Market Intelligence Phase 1 Schemas ─────────────────────────────────────

class LocationInfo(BaseModel):
    state: str
    district: str
    subdistrict: Optional[str] = None
    village: Optional[str] = None
    latitude: float
    longitude: float
    formatted_address: str

class CategoryInfo(BaseModel):
    category_id: str
    display_name: str
    primary_radius_km: float
    extended_radius_km: float
    selected_radius_km: float
    description: Optional[str] = ""

class PopulationInfo(BaseModel):
    catchment_population: int
    catchment_households: int
    radius_km: float
    area_sq_km: float
    density_per_sq_km: float
    density_classification: str
    is_estimate: bool = True
    source: str

class CensusReferenceInfo(BaseModel):
    district_population_2011: int
    district_households_2011: int
    literacy_rate_pct: float
    reference_year: int = 2011
    is_estimate: bool = False
    source: str

class CompetitorItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: Optional[float] = None
    sources: Optional[List[str]] = None
    is_duplicate_resolved: Optional[bool] = False
    osm_matched_id: Optional[str] = None
    reconciliation_note: Optional[str] = None

class CompetitionInfo(BaseModel):
    unique_mapped_count: int
    overture_count: int
    osm_count: int
    duplicate_count: int
    competitors: List[CompetitorItem]
    note: str

class CompetitorDensityInfo(BaseModel):
    competitors_per_1000_people: float
    population_per_competitor: Optional[int] = None
    is_estimate: bool = True

class AccessibilityItem(BaseModel):
    name: str
    type: str
    importance: Optional[str] = None
    distance_km: float
    latitude: float
    longitude: float

class AccessibilityInfo(BaseModel):
    mapped_infrastructure_count: int
    infrastructure: List[AccessibilityItem]
    source: str

# ─── Market Intelligence Phase 2 Schemas ─────────────────────────────────────

class ConsumerProfileInfo(BaseModel):
    status: str
    state: str
    sector: str
    survey_year: str
    benchmark_label: str
    report_number: Optional[str] = None
    survey_period: Optional[str] = None
    mpce_inr: Optional[float] = None
    food_share_pct: Optional[float] = None
    non_food_share_pct: Optional[float] = None
    avg_household_size: Optional[float] = None
    monthly_household_expenditure_inr: Optional[float] = None
    commodity_shares_pct: Optional[Dict[str, float]] = None
    quantity_consumption: Optional[Dict[str, float]] = None
    business_category_id: Optional[str] = None
    relevant_spending_groups: Optional[List[str]] = None
    relevant_category_share_pct: Optional[float] = None
    estimated_per_capita_category_spend_inr: Optional[float] = None
    estimated_household_category_spend_inr: Optional[float] = None
    limitations: List[str]

class RetailPriceItem(BaseModel):
    commodity_id: str
    commodity_name: str
    market_centre: str
    unit: str
    status: str
    current_price: Optional[float] = None
    avg_7d: Optional[float] = None
    avg_30d: Optional[float] = None
    avg_90d: Optional[float] = None
    change_30d_pct: Optional[float] = None
    yoy_pct: Optional[float] = None
    volatility_cv: Optional[float] = None
    observation_count: int
    latest_observed_at: Optional[str] = None
    limitations: Optional[str] = None

class RetailPricesInfo(BaseModel):
    category_id: str
    market_centre: str
    total_basket_items: int
    valid_items_count: int
    items: List[RetailPriceItem]
    source: str
    limitations: List[str]

class MandiPriceItem(BaseModel):
    commodity_id: str
    commodity_name: str
    market_name: str
    distance_km: Optional[float] = None
    status: str
    latest_arrival_date: Optional[str] = None
    variety: Optional[str] = None
    grade: Optional[str] = None
    unit: str = "INR/quintal"
    unit_kg: str = "INR/kg"
    modal_price_quintal: Optional[float] = None
    min_price_quintal: Optional[float] = None
    max_price_quintal: Optional[float] = None
    modal_price_kg: Optional[float] = None
    avg_7d_modal: Optional[float] = None
    avg_30d_modal: Optional[float] = None
    avg_90d_modal: Optional[float] = None
    change_30d_pct: Optional[float] = None
    volatility_cv: Optional[float] = None
    observation_count: int
    limitations: Optional[str] = None

class MandiPricesInfo(BaseModel):
    category_id: str
    primary_mandi: str
    primary_mandi_distance_km: Optional[float] = None
    label: str = "Nearest mapped mandi price"
    total_basket_items: int
    valid_items_count: int
    items: List[MandiPriceItem]
    source: str
    limitations: List[str]

class CostDriverItem(BaseModel):
    commodity_id: str
    commodity_name: str
    weight_pct: float
    source_type: str
    current_price: Optional[float] = None
    unit: str
    change_30d_pct: Optional[float] = None
    volatility_cv: Optional[float] = None
    weighted_contribution_pct: Optional[float] = None
    status: str

class InputCostPressureInfo(BaseModel):
    status: str
    category_id: str
    weighted_30d_change_pct: Optional[float] = None
    weighted_volatility_cv: Optional[float] = None
    pressure_level: str
    coverage_pct: float
    cost_drivers: List[CostDriverItem]
    input_breakdown: List[CostDriverItem]
    limitations: List[str]

class MarketSnapshotResponse(BaseModel):
    location: LocationInfo
    category: CategoryInfo
    population: PopulationInfo
    census_reference: CensusReferenceInfo
    competition: CompetitionInfo
    competitor_density: CompetitorDensityInfo
    accessibility: AccessibilityInfo
    # Phase 2 blocks
    consumer_profile: Optional[ConsumerProfileInfo] = None
    retail_prices: Optional[RetailPricesInfo] = None
    mandi_prices: Optional[MandiPricesInfo] = None
    input_cost_pressure: Optional[InputCostPressureInfo] = None
    evidence: Dict[str, Any]
    limitations: List[str]
    overall_confidence: str
