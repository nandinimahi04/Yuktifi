"""
Input-Cost Pressure Engine (Phase 2).

Computes business-specific input cost inflation pressure and procurement risk.
Answers Question 4: How do price movements affect the selected business?

Mathematical Specification:
- Input weights w_i obtained from commodity_taxonomy.yaml
- Weighted 30D Price Change = sum(w_i * delta_p_i_30d)
- Weighted Volatility Index = sum(w_i * cv_i)
- If weights are missing or inputs have insufficient data -> INSUFFICIENT_DATA
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
import logging

from app.data_layer.normalization.commodity_mapper import commodity_mapper
from app.data_layer.providers.consumer_affairs_provider import consumer_affairs_provider
from app.data_layer.providers.agmarknet_provider import agmarknet_provider
from app.evidence.schema import EvidenceRecord, EvidenceState

logger = logging.getLogger(__name__)

def compute_input_cost_pressure(
    category_id: str = "retail_kirana",
    market_centre: Optional[str] = "Solapur",
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes business-specific weighted input cost pressure index.
    """
    cat_key = category_id.lower().strip()
    weights_dict = commodity_mapper.get_business_input_profile(cat_key)

    if not weights_dict:
        return {
            "status": "INSUFFICIENT_DATA",
            "category_id": cat_key,
            "weighted_30d_change_pct": None,
            "weighted_volatility_cv": None,
            "pressure_level": "UNKNOWN",
            "cost_drivers": [],
            "input_breakdown": [],
            "coverage_pct": 0.0,
            "evidence_state": EvidenceState.MISSING.value,
            "limitations": [f"No input cost weighting profile defined in commodity_taxonomy.yaml for category '{cat_key}'."]
        }

    total_weight = sum(weights_dict.values())
    if total_weight <= 0:
        return {
            "status": "INSUFFICIENT_DATA",
            "category_id": cat_key,
            "weighted_30d_change_pct": None,
            "weighted_volatility_cv": None,
            "pressure_level": "UNKNOWN",
            "cost_drivers": [],
            "input_breakdown": [],
            "coverage_pct": 0.0,
            "evidence_state": EvidenceState.MISSING.value,
            "limitations": [f"Input weights sum to zero for category '{cat_key}'."]
        }

    # Normalize weights so they sum to 1.0
    norm_weights = {k: v / total_weight for k, v in weights_dict.items()}

    input_breakdown: List[Dict[str, Any]] = []
    weighted_change_sum = 0.0
    weighted_volatility_sum = 0.0
    usable_weight_sum = 0.0

    for cid, weight in norm_weights.items():
        cinfo = commodity_mapper.get_commodity_info(cid) or {}
        canon_name = cinfo.get("canonical_name", cid.replace("_", " ").title())
        unit = cinfo.get("unit", "INR/kg")

        # First check retail price from DCA
        ret_metrics = consumer_affairs_provider.compute_retail_metrics(cid, market_centre)
        if ret_metrics.get("status") == "VALID":
            curr_p = ret_metrics.get("current_price")
            chg_30d = ret_metrics.get("change_30d_pct") or 0.0
            vol_cv = ret_metrics.get("volatility_cv") or 0.0
            src_type = "retail_dca"
        else:
            # Fallback to APMC mandi price
            mandi_metrics = agmarknet_provider.compute_mandi_metrics(cid, lat, lon)
            if mandi_metrics.get("status") == "VALID":
                curr_p = mandi_metrics.get("modal_price_kg")
                chg_30d = mandi_metrics.get("change_30d_pct") or 0.0
                vol_cv = mandi_metrics.get("volatility_cv") or 0.0
                src_type = "wholesale_mandi"
            else:
                curr_p = None
                chg_30d = None
                vol_cv = None
                src_type = "none"

        if curr_p is not None and chg_30d is not None:
            weighted_contrib = round(weight * chg_30d, 3)
            weighted_change_sum += weighted_contrib
            weighted_volatility_sum += (weight * (vol_cv or 0.0))
            usable_weight_sum += weight
            status_item = "VALID"
        else:
            weighted_contrib = None
            status_item = "INSUFFICIENT_DATA"

        input_breakdown.append({
            "commodity_id": cid,
            "commodity_name": canon_name,
            "weight_pct": round(weight * 100.0, 1),
            "source_type": src_type,
            "current_price": curr_p,
            "unit": unit,
            "change_30d_pct": chg_30d,
            "volatility_cv": vol_cv,
            "weighted_contribution_pct": weighted_contrib,
            "status": status_item
        })

    coverage_pct = round(usable_weight_sum * 100.0, 1)

    if coverage_pct < 50.0:
        return {
            "status": "INSUFFICIENT_DATA",
            "category_id": cat_key,
            "weighted_30d_change_pct": None,
            "weighted_volatility_cv": None,
            "pressure_level": "UNKNOWN",
            "cost_drivers": [],
            "input_breakdown": input_breakdown,
            "coverage_pct": coverage_pct,
            "evidence_state": EvidenceState.MISSING.value,
            "limitations": [f"Insufficient commodity price coverage ({coverage_pct}% < 50% threshold) for category '{cat_key}'."]
        }

    # Normalize weighted change by usable weight
    final_weighted_change = round(weighted_change_sum / usable_weight_sum, 2)
    final_weighted_volatility = round(weighted_volatility_sum / usable_weight_sum, 4)

    # Classify pressure level
    if final_weighted_change < 2.0:
        pressure_level = "LOW"
    elif final_weighted_change < 5.0:
        pressure_level = "MODERATE"
    elif final_weighted_change < 10.0:
        pressure_level = "HIGH"
    else:
        pressure_level = "SEVERE"

    # Identify top cost drivers
    valid_items = [item for item in input_breakdown if item.get("weighted_contribution_pct") is not None]
    cost_drivers = sorted(valid_items, key=lambda x: x["weighted_contribution_pct"], reverse=True)

    return {
        "status": "VALID",
        "category_id": cat_key,
        "weighted_30d_change_pct": final_weighted_change,
        "weighted_volatility_cv": final_weighted_volatility,
        "pressure_level": pressure_level,
        "coverage_pct": coverage_pct,
        "cost_drivers": cost_drivers[:3],
        "input_breakdown": input_breakdown,
        "evidence_state": EvidenceState.VERIFIED.value,
        "limitations": [
            "Input cost pressure represents weighted average price movement of primary business inputs.",
            "Weights reflect typical sector cost composition from commodity_taxonomy.yaml.",
            "Actual shop-level procurement terms depend on distributor relationships and volume discounts."
        ]
    }
