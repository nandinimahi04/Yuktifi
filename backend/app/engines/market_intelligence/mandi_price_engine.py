"""
Mandi Price Engine (Phase 2).

Computes wholesale agricultural mandi price dynamics from AGMARKNET / eNAM.
Answers Question 3: What are agricultural commodities trading for at wholesale markets?

Rules:
- Labeled "Nearest mapped mandi price".
- Reports distance to mapped mandi in km.
- Converts wholesale modal price from INR/quintal to INR/kg (price / 100).
- If insufficient data, flags INSUFFICIENT_DATA.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

from app.data_layer.providers.agmarknet_provider import agmarknet_provider
from app.data_layer.normalization.commodity_mapper import commodity_mapper

logger = logging.getLogger(__name__)

CATEGORY_DEFAULT_AGRI_COMMODITIES = {
    "retail_kirana": ["rice", "wheat", "tur_dal", "gram_dal", "urad_dal", "moong_dal", "onion", "potato", "sugar"],
    "retail_shop": ["rice", "wheat", "tur_dal", "gram_dal", "urad_dal", "moong_dal", "onion", "potato", "sugar"],
    "tea_snacks": ["sugar", "potato", "onion", "wheat", "gram_dal", "soyabean"],
    "tea_stall": ["sugar", "potato", "onion", "wheat", "gram_dal", "soyabean"],
    "food_beverage": ["sugar", "potato", "onion", "wheat", "gram_dal", "rice", "soyabean"],
    "food_stall": ["sugar", "potato", "onion", "wheat", "gram_dal", "rice", "soyabean"],
    "restaurant": ["sugar", "potato", "onion", "wheat", "gram_dal", "rice", "tur_dal", "soyabean"],
    "dairy": ["sugar", "soyabean", "wheat"],
    "flour_mill": ["wheat", "gram_dal", "jowar"],
    "poultry": ["soyabean", "wheat", "jowar"],
    "tailoring": ["rice", "wheat", "tur_dal", "gram_dal", "onion", "sugar"],
}

def get_commodity_mandi_metrics(
    commodity_id_or_name: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    preferred_market: Optional[str] = None
) -> Dict[str, Any]:
    """Returns calculated mandi metrics for a specific agricultural commodity."""
    return agmarknet_provider.compute_mandi_metrics(commodity_id_or_name, lat, lon, preferred_market)

def get_mandi_basket_for_category(
    category_id: str = "retail_kirana",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    preferred_market: Optional[str] = None
) -> Dict[str, Any]:
    """Returns wholesale mandi metrics for all agricultural commodities relevant to the category."""
    cat_key = category_id.lower().strip()
    commodities = CATEGORY_DEFAULT_AGRI_COMMODITIES.get(cat_key)
    if not commodities:
        if any(k in cat_key for k in ("food", "snack", "tea", "cafe", "dhaba", "sweet", "canteen")):
            commodities = CATEGORY_DEFAULT_AGRI_COMMODITIES["food_beverage"]
        elif any(k in cat_key for k in ("kirana", "shop", "grocery", "store", "retail")):
            commodities = CATEGORY_DEFAULT_AGRI_COMMODITIES["retail_kirana"]
        elif "dairy" in cat_key:
            commodities = CATEGORY_DEFAULT_AGRI_COMMODITIES["dairy"]
        elif any(k in cat_key for k in ("mill", "chakki", "flour")):
            commodities = CATEGORY_DEFAULT_AGRI_COMMODITIES["flour_mill"]
        else:
            commodities = ["rice", "wheat", "tur_dal", "gram_dal", "onion", "potato", "sugar", "jowar", "soyabean"]

    basket = []
    evidence_dict = {}
    valid_count = 0

    for cid in commodities:
        metrics = agmarknet_provider.compute_mandi_metrics(cid, lat, lon, preferred_market)
        basket.append(metrics)
        if metrics.get("status") == "VALID":
            valid_count += 1
            rec = agmarknet_provider.get_mandi_price_record(cid, lat, lon, preferred_market)
            evidence_dict[f"mandi_price_{cid}"] = rec.to_dict()

    # Determine primary nearest mandi info
    primary_market_name = basket[0]["market_name"] if basket else "Solapur APMC"
    primary_dist = basket[0].get("distance_km") if basket else None

    return {
        "category_id": cat_key,
        "primary_mandi": primary_market_name,
        "primary_mandi_distance_km": primary_dist,
        "label": "Nearest mapped mandi price",
        "total_basket_items": len(commodities),
        "valid_items_count": valid_count,
        "items": basket,
        "evidence": evidence_dict,
        "source": "AGMARKNET / eNAM (Ministry of Agriculture)",
        "limitations": [
            "Mandi modal prices represent official daily wholesale APMC arrivals.",
            "Distance to nearest mapped APMC is calculated from the selected location coordinates.",
            "Wholesale mandi rates exclude local transportation, handling, and trader margins."
        ]
    }
