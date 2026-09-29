"""
Consumer Profile Engine (Phase 2).

Computes consumer spending and consumption benchmarks from MoSPI HCES 2023-24 (Report No. 592).
Answers Question 1: What do consumers spend and consume in this state/sector?

CRITICAL POLICY:
- Labeled 'State/Sector Benchmark (Rural/Urban)'.
- NEVER interpolated to village-level micro-demand.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import logging

from app.data_layer.providers.hces_provider import hces_provider
from app.evidence.schema import EvidenceRecord, EvidenceState

logger = logging.getLogger(__name__)

CATEGORY_RELEVANT_SPENDING_GROUPS = {
    "retail_kirana": ["cereals", "pulses", "edible_oil", "sugar_salt_spices", "milk_and_products", "vegetables"],
    "retail_shop": ["cereals", "pulses", "edible_oil", "sugar_salt_spices", "milk_and_products", "clothing_and_footwear"],
    "tea_snacks": ["beverages_refreshments_processed", "sugar_salt_spices", "milk_and_products"],
    "tea_stall": ["beverages_refreshments_processed", "sugar_salt_spices", "milk_and_products"],
    "dairy": ["milk_and_products"],
    "flour_mill": ["cereals"],
    "poultry": ["egg_fish_meat"],
    "tailoring": ["clothing_and_footwear"],
}

def compute_consumer_profile(
    state: str = "Maharashtra",
    sector: str = "rural",
    category_id: Optional[str] = "retail_kirana"
) -> Dict[str, Any]:
    """
    Computes HCES 2023-24 state/sector consumer spending benchmarks.
    """
    norm_state = state.strip().title() if state else "Maharashtra"
    norm_sector = sector.strip().lower() if sector else "rural"
    if norm_sector not in ("rural", "urban"):
        norm_sector = "rural"

    bench = hces_provider.get_state_benchmark(norm_state, norm_sector)
    if not bench:
        return {
            "status": "UNAVAILABLE",
            "state": norm_state,
            "sector": norm_sector,
            "survey_year": "2023-24",
            "benchmark_label": f"State/Sector Benchmark ({norm_state} {norm_sector.title()})",
            "mpce_inr": None,
            "food_share_pct": None,
            "non_food_share_pct": None,
            "monthly_household_expenditure_inr": None,
            "avg_household_size": None,
            "commodity_shares_pct": {},
            "relevant_category_share_pct": None,
            "estimated_per_capita_category_spend_inr": None,
            "quantity_consumption": {},
            "evidence": {},
            "limitations": [f"HCES 2023-24 benchmark unavailable for state '{norm_state}'."]
        }

    mpce_val = bench.get("mpce_inr", 0.0)
    food_share = bench.get("food_expenditure_share_pct", 0.0)
    non_food_share = bench.get("non_food_expenditure_share_pct", 0.0)
    hh_size = bench.get("avg_household_size", 4.0)
    hh_expenditure = bench.get("estimated_monthly_household_expenditure_inr", mpce_val * hh_size)
    commodity_shares = bench.get("commodity_group_shares_pct", {})
    quantity_data = bench.get("monthly_per_capita_quantity", {})

    # Calculate category relevant basket share
    cat_key = (category_id or "retail_kirana").lower().strip()
    relevant_groups = CATEGORY_RELEVANT_SPENDING_GROUPS.get(cat_key, ["cereals", "pulses", "edible_oil", "sugar_salt_spices"])
    relevant_share_sum = sum(commodity_shares.get(grp, 0.0) for grp in relevant_groups)
    est_category_spend_per_capita = round(mpce_val * (relevant_share_sum / 100.0), 2)
    est_category_spend_household = round(hh_expenditure * (relevant_share_sum / 100.0), 2)

    # Prepare evidence records
    mpce_rec = hces_provider.get_mpce_record(norm_state, norm_sector)
    food_rec = hces_provider.get_food_share_record(norm_state, norm_sector)

    return {
        "status": "VALID",
        "state": norm_state,
        "sector": norm_sector,
        "survey_year": "2023-24",
        "benchmark_label": f"State/Sector Benchmark ({norm_state} {norm_sector.title()})",
        "report_number": "MoSPI Report No. 592 (HCES 2023-24)",
        "survey_period": "August 2023 - July 2024",
        "mpce_inr": mpce_val,
        "food_share_pct": food_share,
        "non_food_share_pct": non_food_share,
        "avg_household_size": hh_size,
        "monthly_household_expenditure_inr": hh_expenditure,
        "commodity_shares_pct": commodity_shares,
        "quantity_consumption": quantity_data,
        "business_category_id": cat_key,
        "relevant_spending_groups": relevant_groups,
        "relevant_category_share_pct": round(relevant_share_sum, 2),
        "estimated_per_capita_category_spend_inr": est_category_spend_per_capita,
        "estimated_household_category_spend_inr": est_category_spend_household,
        "evidence": {
            "mpce": mpce_rec.to_dict(),
            "food_share": food_rec.to_dict(),
        },
        "limitations": [
            "HCES 2023-24 figures represent state/sector averages (MoSPI Report No. 592).",
            "Figures must not be treated as micro-level neighborhood or village demand."
        ]
    }
