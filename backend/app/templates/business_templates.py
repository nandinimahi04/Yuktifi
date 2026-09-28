"""
YuktiFi Business Template Engine (Phase 5).
Provides sector-tailored business models, default parameters, working capital days, and catchment radii.
"""
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class BusinessTemplate:
    category_id: str
    name: str
    sector: str
    catchment_radius_min_km: float
    catchment_radius_max_km: float
    default_inventory_days: int
    default_receivable_days: int
    default_payable_days: int
    typical_cogs_pct: float
    typical_opex_pct: float
    key_cost_drivers: List[str]
    description: str
    # --- Capital sizing parameters -------------------------------------------
    # The promoter's own share of total project cost, as a percentage. This is
    # the scheme contribution norm for the sector, not a financial output.
    promoter_contribution_pct: float = 25.0
    # Annual sales generated per rupee of total project cost (capital turnover).
    # This is the bridge from capital to revenue: without it, capital has no
    # effect on earning capacity and every return figure is meaningless.
    annual_revenue_per_invested_rupee: float = 4.0
    # Average transaction value, so volumes are reported in real units rather
    # than as an abstract rupee total.
    typical_unit_value: float = 100.0
    # Share of project cost that is depreciable equipment/fixtures. The balance
    # is inventory, deposits and working capital, which are not depreciated.
    depreciable_asset_share: float = 0.75
    # Useful life of that equipment, used to charge depreciation.
    asset_useful_life_years: float = 10.0

TEMPLATES: Dict[str, BusinessTemplate] = {
    "retail_kirana": BusinessTemplate(
        category_id="retail_kirana",
        annual_revenue_per_invested_rupee=2.2,
        depreciable_asset_share=0.7,
        asset_useful_life_years=10,
        name="Retail Kirana / Grocery Store",
        sector="Retail",
        catchment_radius_min_km=1.0,
        catchment_radius_max_km=3.0,
        default_inventory_days=10,
        default_receivable_days=7,
        default_payable_days=14,
        typical_cogs_pct=75.0,
        typical_opex_pct=15.0,
        key_cost_drivers=["Inventory / Stock Purchase", "Shop Rent", "Electricity & Shrinkage"],
        description="Fast-moving consumer goods retail store with short receivable cycle and regular local footfall.",
        promoter_contribution_pct=25,
        typical_unit_value=250,
    ),
    "tea_stall": BusinessTemplate(
        category_id="tea_stall",
        annual_revenue_per_invested_rupee=2.5,
        depreciable_asset_share=0.65,
        asset_useful_life_years=5,
        name="Tea & Snacks Stall",
        sector="Food & Beverage",
        catchment_radius_min_km=0.5,
        catchment_radius_max_km=1.5,
        default_inventory_days=2,
        default_receivable_days=1,
        default_payable_days=7,
        typical_cogs_pct=40.0,
        typical_opex_pct=30.0,
        key_cost_drivers=["Milk & Tea Leaves", "LPG Fuel", "Stall Location Rent"],
        description="High-frequency daily cash sales business with minimal receivables.",
        promoter_contribution_pct=50.0,
        typical_unit_value=20,
    ),
    "dairy": BusinessTemplate(
        category_id="dairy",
        annual_revenue_per_invested_rupee=3.2,
        depreciable_asset_share=0.75,
        asset_useful_life_years=10,
        name="Dairy & Milk Collection Centre",
        sector="Dairy",
        catchment_radius_min_km=2.0,
        catchment_radius_max_km=8.0,
        default_inventory_days=1,
        default_receivable_days=10,
        default_payable_days=15,
        typical_cogs_pct=80.0,
        typical_opex_pct=12.0,
        key_cost_drivers=["Raw Milk Procurement", "Chilling & Refrigeration Electricity", "Transport / Can Logistics"],
        description="Perishable dairy aggregation enterprise reliant on daily collection and local dairy cooperative cycles.",
        promoter_contribution_pct=30,
        typical_unit_value=60,
    ),
    "tailoring": BusinessTemplate(
        category_id="tailoring",
        annual_revenue_per_invested_rupee=2.5,
        depreciable_asset_share=0.8,
        asset_useful_life_years=10,
        name="Tailoring & Garment Works",
        sector="Service",
        catchment_radius_min_km=1.0,
        catchment_radius_max_km=5.0,
        default_inventory_days=5,
        default_receivable_days=3,
        default_payable_days=7,
        typical_cogs_pct=25.0,
        typical_opex_pct=40.0,
        key_cost_drivers=["Thread & Accessories", "Machine Maintenance", "Labor / Helper Wages"],
        description="Labor-intensive service enterprise with high profit margin and localized custom orders.",
        promoter_contribution_pct=25,
        typical_unit_value=1200,
    ),
    "diagnostic": BusinessTemplate(
        category_id="diagnostic",
        annual_revenue_per_invested_rupee=2,
        depreciable_asset_share=0.85,
        asset_useful_life_years=7,
        name="Diagnostic & Clinical Collection Centre",
        sector="Health Service",
        catchment_radius_min_km=5.0,
        catchment_radius_max_km=15.0,
        default_inventory_days=15,
        default_receivable_days=15,
        default_payable_days=30,
        typical_cogs_pct=35.0,
        typical_opex_pct=35.0,
        key_cost_drivers=["Reagents & Testing Kits", "Calibrated Medical Devices", "Qualified Technician Salary"],
        description="Specialized healthcare service requiring wider geographical catchment and clinical accuracy.",
        promoter_contribution_pct=35,
        typical_unit_value=800,
    ),
    "agri_machinery": BusinessTemplate(
        category_id="agri_machinery",
        annual_revenue_per_invested_rupee=1.4,
        depreciable_asset_share=0.9,
        asset_useful_life_years=10,
        name="Agricultural Machinery & Equipment Dealer / Hiring Centre",
        sector="Agriculture",
        catchment_radius_min_km=10.0,
        catchment_radius_max_km=30.0,
        default_inventory_days=30,
        default_receivable_days=20,
        default_payable_days=30,
        typical_cogs_pct=65.0,
        typical_opex_pct=20.0,
        key_cost_drivers=["Equipment Financing & Maintenance", "Diesel Fuel", "Operator Wages"],
        description="Capital-intensive agricultural service serving multiple villages across rural block/district.",
        promoter_contribution_pct=25,
        typical_unit_value=25000,
    ),
    "food_processing": BusinessTemplate(
        category_id="food_processing",
        annual_revenue_per_invested_rupee=2.4,
        depreciable_asset_share=0.8,
        asset_useful_life_years=10,
        name="Micro Food Processing (Atta Chakki / Spices Unit)",
        sector="Food Processing",
        catchment_radius_min_km=3.0,
        catchment_radius_max_km=10.0,
        default_inventory_days=12,
        default_receivable_days=7,
        default_payable_days=15,
        typical_cogs_pct=60.0,
        typical_opex_pct=20.0,
        key_cost_drivers=["Raw Grains / Spices Procurement", "3-Phase Commercial Power", "Packaging Material"],
        description="Value-addition manufacturing enterprise converting local farm produce into processed goods.",
        promoter_contribution_pct=30,
        typical_unit_value=400,
    ),
    "repair_services": BusinessTemplate(
        category_id="repair_services",
        annual_revenue_per_invested_rupee=3,
        depreciable_asset_share=0.7,
        asset_useful_life_years=7,
        name="Auto / Electronics Repair Works",
        sector="Repair",
        catchment_radius_min_km=2.0,
        catchment_radius_max_km=8.0,
        default_inventory_days=10,
        default_receivable_days=5,
        default_payable_days=15,
        typical_cogs_pct=40.0,
        typical_opex_pct=35.0,
        key_cost_drivers=["Spare Parts Inventory", "Specialized Tooling", "Mechanic Wages"],
        description="Service & repair enterprise combining spare part sales with technical repair labor.",
        promoter_contribution_pct=25,
        typical_unit_value=1500,
    ),
    "small_hospitality": BusinessTemplate(
        category_id="small_hospitality",
        annual_revenue_per_invested_rupee=3,
        depreciable_asset_share=0.75,
        asset_useful_life_years=10,
        name="Dhaba / Small Restaurant",
        sector="Hospitality",
        catchment_radius_min_km=3.0,
        catchment_radius_max_km=12.0,
        default_inventory_days=4,
        default_receivable_days=2,
        default_payable_days=10,
        typical_cogs_pct=45.0,
        typical_opex_pct=35.0,
        key_cost_drivers=["Ration & Perishables", "Cook & Service Staff", "LPG & Electricity"],
        description="Highway/town hospitality business combining quick food service with daily footfall.",
        promoter_contribution_pct=30,
        typical_unit_value=250,
    )
}

def get_business_template(category_id: str) -> BusinessTemplate:
    if not category_id or category_id not in TEMPLATES:
        raise ValueError(f"Unknown or missing category_id: {category_id}")
    return TEMPLATES[category_id]
