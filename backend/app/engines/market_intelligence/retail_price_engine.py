"""
Retail Price Engine (Phase 2).

Computes consumer retail price analytics using Department of Consumer Affairs (PMS) data.
Answers Question 2: What are consumers paying for essential commodities?

Rules:
- Computes current_price, avg_7d, avg_30d, avg_90d, change_30d_pct, yoy_pct, volatility_cv.
- If fewer than 3 observations, flags INSUFFICIENT_DATA rather than returning 0.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

from app.data_layer.providers.consumer_affairs_provider import consumer_affairs_provider
from app.data_layer.normalization.commodity_mapper import commodity_mapper

logger = logging.getLogger(__name__)

CATEGORY_DEFAULT_COMMODITIES = {
    "retail_kirana": ["rice", "wheat", "atta", "tur_dal", "gram_dal", "sugar", "edible_oil", "milk", "tea", "salt"],
    "retail_shop": ["rice", "wheat", "atta", "tur_dal", "gram_dal", "sugar", "edible_oil", "milk", "tea", "salt"],
    "tea_snacks": ["milk", "sugar", "tea", "edible_oil", "atta", "salt", "potato", "onion"],
    "tea_stall": ["milk", "sugar", "tea", "edible_oil", "atta", "salt", "potato", "onion"],
    "dairy": ["milk", "sugar"],
    "flour_mill": ["wheat", "atta", "gram_dal"],
    "poultry": [],
    "tailoring": [],
}

def get_commodity_retail_metrics(
    commodity_id_or_name: str,
    market_centre: Optional[str] = "Solapur"
) -> Dict[str, Any]:
    """Returns calculated retail metrics for a specific commodity."""
    return consumer_affairs_provider.compute_retail_metrics(commodity_id_or_name, market_centre)

def get_retail_basket_for_category(
    category_id: str = "retail_kirana",
    market_centre: Optional[str] = "Solapur"
) -> Dict[str, Any]:
    """Returns retail metrics for all commodities relevant to the selected business category."""
    cat_key = category_id.lower().strip()
    commodities = CATEGORY_DEFAULT_COMMODITIES.get(cat_key, ["rice", "wheat", "atta", "sugar", "milk", "tea"])

    basket = []
    evidence_dict = {}
    valid_count = 0

    for cid in commodities:
        metrics = consumer_affairs_provider.compute_retail_metrics(cid, market_centre)
        basket.append(metrics)
        if metrics.get("status") == "VALID":
            valid_count += 1
            rec = consumer_affairs_provider.get_retail_price_record(cid, market_centre)
            evidence_dict[f"retail_price_{cid}"] = rec.to_dict()

    return {
        "category_id": cat_key,
        "market_centre": (market_centre or "Solapur").title(),
        "total_basket_items": len(commodities),
        "valid_items_count": valid_count,
        "items": basket,
        "evidence": evidence_dict,
        "source": "Department of Consumer Affairs (Price Monitoring Division)",
        "limitations": [
            "Official daily retail prices monitored at reporting market centres.",
            "Local village or corner kirana prices may vary due to transportation and micro-margins."
        ]
    }

def get_retail_timeseries(
    commodity_id_or_name: str,
    market_centre: Optional[str] = "Solapur",
    days: int = 90
) -> Dict[str, Any]:
    """Returns chronological time series data for frontend chart rendering."""
    cid = commodity_mapper.resolve_commodity(commodity_id_or_name, "consumer_affairs") or commodity_id_or_name.lower().strip()
    cinfo = commodity_mapper.get_commodity_info(cid) or {}
    canon_name = cinfo.get("canonical_name", cid.replace("_", " ").title())
    unit = cinfo.get("unit", "INR/kg")

    series = consumer_affairs_provider.get_price_series(cid, market_centre, days=days)
    chart_data = [{"date": r.get("observed_at"), "price": r.get("price")} for r in series]

    return {
        "commodity_id": cid,
        "commodity_name": canon_name,
        "market_centre": (market_centre or "Solapur").title(),
        "unit": unit,
        "days": days,
        "points_count": len(chart_data),
        "series": chart_data
    }
