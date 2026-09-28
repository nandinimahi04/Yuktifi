from typing import List, Optional
from pydantic import BaseModel, Field

class LocationInfo(BaseModel):
    district: str
    state: str
    country: str

class Competitor(BaseModel):
    name: str
    latitude: float
    longitude: float
    distance_km: float

class MarketReach(BaseModel):
    estimated_target_customer_base: int

class CompetitorMarketData(BaseModel):
    competitor_count: int
    competitor_list: List[Competitor]
    market_reach: MarketReach
    daily_footfall: int
    confidence: str

class PricingBand(BaseModel):
    lowest: int
    highest: int
    currency: str

class PricingMargins(BaseModel):
    pricing_band: PricingBand
    average_margin_percentage: float

class InitialSetupCosts(BaseModel):
    shop_deposit: int
    equipment_and_furniture: int
    initial_inventory: int
    total_setup_cost: int
    currency: str

class UtilitiesCost(BaseModel):
    electricity: int
    water: int

class MonthlyRunningCosts(BaseModel):
    rent: int
    utilities: UtilitiesCost
    salaries: int
    total_fixed_costs: int
    currency: str

class UnitEconomics(BaseModel):
    expected_monthly_revenue: int
    variable_costs: int
    net_operating_income: int
    currency: str

class QualitativeInsights(BaseModel):
    opportunity_gaps: List[str]
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]

class RiskRating(BaseModel):
    level: str
    reasoning: str

class CategoryData(BaseModel):
    category_name: str
    competitor_market_data: CompetitorMarketData
    pricing_margins: PricingMargins
    initial_setup_costs: InitialSetupCosts
    monthly_running_costs: MonthlyRunningCosts
    unit_economics: UnitEconomics
    qualitative_insights: QualitativeInsights
    sub_segments: Optional[List[str]] = None
    seasonality_and_demand_trend: Optional[dict] = None
    licenses_and_registrations_required: Optional[List[str]] = None
    applicable_government_schemes: Optional[List[str]] = None
    key_input_suppliers: Optional[List[str]] = None
    recommended_locations_within_district: Optional[List[str]] = None
    risk_rating: Optional[RiskRating] = None

class DistrictOverview(BaseModel):
    district_name: str
    state: str
    country: str
    headquarters: str
    administrative_division: str
    geography: dict
    demographics: dict
    talukas: List[dict]
    key_economic_sectors: List[str]
    connectivity: dict
    financial_institutions_present: List[str]
    msme_support_infrastructure: dict
    geographical_indication_tagged_products: List[dict]
    notes_on_data_sourcing: str

class CombinedDataset(BaseModel):
    location: LocationInfo
    district_overview: Optional[DistrictOverview] = None
    categories: dict[str, CategoryData]
