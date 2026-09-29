"""
Business Category Taxonomy for Market Intelligence Phase 1.

Maps YuktiFi business categories to:
- Primary and extended catchment radius (in km)
- Overture Maps Places category taxonomy
- OpenStreetMap / Overpass query tags
- Display metadata
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass(frozen=True)
class CategoryTaxonomy:
    category_id: str
    display_name: str
    primary_radius_km: float
    extended_radius_km: float
    overture_categories: List[str]
    osm_tag_filters: List[str]
    description: str = ""
    typical_footfall_daily: int = 200

# Canonical Phase 1 Business Categories & Fallbacks
TAXONOMIES: Dict[str, CategoryTaxonomy] = {
    # ── 1. Kirana / Grocery Store ─────────────────────────────────────────────
    "retail_kirana": CategoryTaxonomy(
        category_id="retail_kirana",
        display_name="Kirana / Grocery Store",
        primary_radius_km=2.0,
        extended_radius_km=5.0,
        overture_categories=[
            "grocery_store",
            "supermarket",
            "convenience_store",
            "food_store",
            "general_store",
            "retail",
            "market"
        ],
        osm_tag_filters=[
            '["shop"="convenience"]',
            '["shop"="supermarket"]',
            '["shop"="general"]',
            '["shop"="groceries"]',
            '["shop"="grocery"]',
            '["shop"="kiosk"]',
        ],
        description="Daily essential FMCG, packaged foods, spices, grains, and household supplies.",
        typical_footfall_daily=250,
    ),
    "retail_shop": CategoryTaxonomy(
        category_id="retail_shop",
        display_name="Retail & Kirana Store",
        primary_radius_km=2.0,
        extended_radius_km=5.0,
        overture_categories=[
            "grocery_store",
            "supermarket",
            "convenience_store",
            "food_store",
            "general_store",
            "retail",
            "department_store"
        ],
        osm_tag_filters=[
            '["shop"="convenience"]',
            '["shop"="supermarket"]',
            '["shop"="general"]',
            '["shop"="groceries"]',
            '["shop"="department_store"]',
        ],
        description="General retail and neighborhood provisioning.",
        typical_footfall_daily=300,
    ),

    # ── 2. Tea & Snacks Shop ──────────────────────────────────────────────────
    "tea_snacks": CategoryTaxonomy(
        category_id="tea_snacks",
        display_name="Tea & Snacks Shop",
        primary_radius_km=1.0,
        extended_radius_km=3.0,
        overture_categories=[
            "cafe",
            "tea_house",
            "snack_bar",
            "fast_food_restaurant",
            "restaurant",
            "bakery",
            "food_stand"
        ],
        osm_tag_filters=[
            '["amenity"="cafe"]',
            '["amenity"="fast_food"]',
            '["amenity"="restaurant"]',
            '["shop"="bakery"]',
            '["shop"="tea"]',
            '["amenity"="food_court"]',
        ],
        description="Chai, tea stalls, local breakfast items (poha, vadapav, samosa), and quick refreshments.",
        typical_footfall_daily=350,
    ),
    "tea_stall": CategoryTaxonomy(
        category_id="tea_stall",
        display_name="Tea Stall & Snacks",
        primary_radius_km=1.0,
        extended_radius_km=3.0,
        overture_categories=[
            "cafe",
            "tea_house",
            "snack_bar",
            "fast_food_restaurant",
            "food_stand"
        ],
        osm_tag_filters=[
            '["amenity"="cafe"]',
            '["amenity"="fast_food"]',
            '["shop"="tea"]',
        ],
        description="Micro tea stall and snacks point.",
        typical_footfall_daily=350,
    ),
    "food_beverage": CategoryTaxonomy(
        category_id="food_beverage",
        display_name="Food & Beverage / Snacks",
        primary_radius_km=1.0,
        extended_radius_km=3.0,
        overture_categories=[
            "cafe",
            "tea_house",
            "snack_bar",
            "fast_food_restaurant",
            "restaurant",
            "bakery"
        ],
        osm_tag_filters=[
            '["amenity"="cafe"]',
            '["amenity"="fast_food"]',
            '["amenity"="restaurant"]',
            '["shop"="bakery"]',
        ],
        description="Food, dining, and snack corners.",
        typical_footfall_daily=300,
    ),

    # ── Compatibility fallbacks for existing categories ───────────────────────
    "dairy": CategoryTaxonomy(
        category_id="dairy",
        display_name="Dairy Farm & Milk Products",
        primary_radius_km=3.0,
        extended_radius_km=7.0,
        overture_categories=["dairy_store", "dairy_farm", "food_store"],
        osm_tag_filters=['["shop"="dairy"]', '["amenity"="marketplace"]'],
        description="Fresh milk collection, curd, paneer, and ghee distribution.",
        typical_footfall_daily=120,
    ),
    "tailoring": CategoryTaxonomy(
        category_id="tailoring",
        display_name="Tailoring & Boutique",
        primary_radius_km=2.0,
        extended_radius_km=5.0,
        overture_categories=["clothing_store", "tailor", "apparel_services"],
        osm_tag_filters=['["craft"="tailor"]', '["shop"="tailor"]', '["shop"="clothes"]'],
        description="Custom stitching, alteration, and local boutique services.",
        typical_footfall_daily=50,
    ),
    "flour_mill": CategoryTaxonomy(
        category_id="flour_mill",
        display_name="Flour Mill / Atta Chakki",
        primary_radius_km=2.0,
        extended_radius_km=4.0,
        overture_categories=["grain_mill", "food_processing", "general_store"],
        osm_tag_filters=['["craft"="mill"]', '["shop"="convenience"]'],
        description="Custom flour milling, spices grinding, and grain processing.",
        typical_footfall_daily=90,
    ),
    "poultry": CategoryTaxonomy(
        category_id="poultry",
        display_name="Poultry Farming",
        primary_radius_km=5.0,
        extended_radius_km=15.0,
        overture_categories=["farm", "poultry_farm", "meat_shop"],
        osm_tag_filters=['["landuse"="farm"]["farm"="poultry"]', '["shop"="butcher"]'],
        description="Broiler/layer poultry production and egg supply.",
        typical_footfall_daily=40,
    ),
}

# Aliases for normalized resolution
CATEGORY_ALIASES = {
    "kirana": "retail_kirana",
    "grocery": "retail_kirana",
    "supermarket": "retail_kirana",
    "retail": "retail_shop",
    "tea": "tea_snacks",
    "tea_stall": "tea_snacks",
    "chai": "tea_snacks",
    "chai_snacks": "tea_snacks",
    "snacks": "tea_snacks",
    "hotel": "food_beverage",
    "restaurant": "food_beverage",
}

def resolve_category_taxonomy(category_id_or_name: str) -> CategoryTaxonomy:
    """Resolve a raw category ID or name into a canonical CategoryTaxonomy."""
    key = str(category_id_or_name).lower().strip().replace(" ", "_").replace("-", "_")
    
    # Check direct match
    if key in TAXONOMIES:
        return TAXONOMIES[key]
    
    # Check alias
    if key in CATEGORY_ALIASES:
        target = CATEGORY_ALIASES[key]
        return TAXONOMIES[target]
    
    # Check fuzzy substring match
    for tax_key, tax in TAXONOMIES.items():
        if tax_key in key or key in tax_key:
            return tax
        if any(term in key for term in ["tea", "snack", "chai", "cafe"]):
            return TAXONOMIES["tea_snacks"]
        if any(term in key for term in ["kirana", "grocery", "provision", "shop", "retail", "store"]):
            return TAXONOMIES["retail_kirana"]

    # Fallback to Kirana default
    return TAXONOMIES["retail_kirana"]
