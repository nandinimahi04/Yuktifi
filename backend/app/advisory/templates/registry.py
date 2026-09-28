from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class BusinessTemplate:
    id: str
    name: str
    category: str
    sales_unit: str
    default_catchment_km: float
    variable_cost_ratio: float
    fixed_cost_monthly: float
    startup_assets: float
    direct_competitor_tags: tuple[str, ...]
    substitute_tags: tuple[str, ...]
    questions: tuple[str, ...]
    assumptions: tuple[str, ...]
    default_monthly_units: float | None
    default_price_per_unit: float | None
    default_variable_cost_per_unit: float | None
    demand_rate_per_1000_people: float

TEMPLATES = {
    "dairy": BusinessTemplate(
        "dairy", "Small Dairy Farming & Collection", "agri-livestock", "litre", 5.0,
        0.60, 15000, 600000,
        ("dairy", "milk_booth", "milk_collection"), ("sweet_shop", "packaged_milk"),
        ("animals", "litres_per_animal_per_day", "selling_price_per_litre", "feed_cost_per_litre"),
        ("Sourced economics from livestock census & local market standards.", "Demand is modeled from local household consumption.", "OSM competitor coverage is tagged with confidence."),
        727, 55, 20, 20
    ),
    "kirana": BusinessTemplate(
        "kirana", "Kirana / General Retail Store", "retail", "basket", 3.0,
        0.78, 18000, 350000,
        ("convenience_store", "grocery", "supermarket"), ("weekly_market", "online_grocery"),
        ("customers_per_day", "average_basket", "gross_margin_pct", "rent_monthly"),
        ("Retail basket economics based on local FMCG turnover.", "Catchment radius 1-3km based on walkability."),
        900, 250, 195, 120
    ),
    "vada_pav": BusinessTemplate(
        "vada_pav", "Vada Pav / Fast Food & Tea Stall", "food-service", "unit", 1.5,
        0.45, 12000, 150000,
        ("fast_food", "snack_shop", "restaurant"), ("street_food", "bakery"),
        ("units_per_day", "selling_price", "ingredient_cost_per_unit", "rent_monthly"),
        ("High-frequency daily cash sales model.", "Catchment radius 0.5-1.5km based on footfall."),
        1800, 20, 9, 180
    ),
    "tailoring": BusinessTemplate(
        "tailoring", "Tailoring & Garment Works", "services", "order", 3.0,
        0.20, 10000, 120000,
        ("tailor", "clothing_repair"), ("ready_made", "home_tailor"),
        ("orders_per_day", "average_ticket", "materials_cost_ratio", "rent_monthly"),
        ("Labor-intensive service model with high profit margin.", "Localized custom tailoring demand."),
        350, 350, 70, 80
    ),
    "diagnostic": BusinessTemplate(
        "diagnostic", "Diagnostic & Clinical Collection Centre", "health-service", "test", 10.0,
        0.35, 35000, 800000,
        ("clinic", "hospital", "laboratory", "pharmacy"), ("diagnostic_center", "health_post"),
        ("tests_per_day", "average_test_fee", "reagent_cost_ratio", "technician_salary"),
        ("Healthcare service requiring wider geographical catchment (5-15km).", "Clinical sample collection model."),
        400, 600, 210, 30
    ),
    "agri_machinery": BusinessTemplate(
        "agri_machinery", "Agri Machinery & Equipment Hiring Centre", "agri-machinery", "hour", 20.0,
        0.35, 45000, 1500000,
        ("agricultural_service", "machinery_dealer", "tractor_hire"), ("manual_labour", "cooperative"),
        ("hiring_hours_per_month", "rate_per_hour", "diesel_cost_per_hour", "operator_wages"),
        ("Capital-intensive agricultural equipment hiring across block/district.", "Wide catchment radius 10-30km."),
        300, 1200, 420, 15
    ),
    "food_processing": BusinessTemplate(
        "food_processing", "Micro Food Processing (Atta Chakki / Spices)", "food-processing", "kg", 5.0,
        0.60, 20000, 500000,
        ("flour_mill", "spice_mill", "food_processing"), ("packaged_food", "wholesale_market"),
        ("kg_processed_per_day", "processing_fee_per_kg", "power_cost_per_kg", "machine_maintenance"),
        ("Value-addition manufacturing model converting local farm produce.", "Commercial 3-phase power requirement."),
        2500, 40, 24, 100
    ),
    "repair_services": BusinessTemplate(
        "repair_services", "Auto & Electronics Repair Works", "repair-service", "job", 5.0,
        0.40, 15000, 250000,
        ("car_repair", "motorcycle_repair", "electronics_repair"), ("spare_parts", "dealer_service"),
        ("jobs_per_day", "average_job_charge", "spare_parts_cost_ratio", "shop_rent"),
        ("Combined spare parts sales and technical repair service.", "Catchment radius 2-8km."),
        450, 400, 160, 60
    ),
    "small_hospitality": BusinessTemplate(
        "small_hospitality", "Dhaba & Small Restaurant", "hospitality", "meal", 8.0,
        0.45, 30000, 450000,
        ("restaurant", "dhaba", "fast_food"), ("hotel", "canteen"),
        ("meals_per_day", "average_meal_price", "food_ingredient_cost", "staff_salaries"),
        ("Highway/town hospitality business combining quick food service.", "Catchment radius 3-12km."),
        1200, 150, 67.5, 90
    ),
}

ALIAS_MAP = {
    "retail_kirana": "kirana",
    "grocery": "kirana",
    "tea_stall": "vada_pav",
    "snack_stall": "vada_pav",
    "fast_food": "vada_pav",
    "dairy_collection": "dairy",
    "dairy_farming": "dairy",
    "garment_works": "tailoring",
    "diagnostic_center": "diagnostic",
    "clinical_lab": "diagnostic",
    "agri_hiring": "agri_machinery",
    "atta_chakki": "food_processing",
    "auto_repair": "repair_services",
    "dhaba": "small_hospitality",
    "restaurant": "small_hospitality",
}

def get_template(business_id: str) -> BusinessTemplate:
    key = business_id.strip().lower().replace(" ", "_").replace("-", "_")
    key = ALIAS_MAP.get(key, key)
    if key not in TEMPLATES:
        return TEMPLATES["kirana"]  # Fallback to Kirana if unmapped
    return TEMPLATES[key]

def list_templates() -> list[dict]:
    return [asdict(v) for v in TEMPLATES.values()]
