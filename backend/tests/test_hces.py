"""
Unit tests for HCES 2023-24 Data Provider and Consumer Profile Engine (Phase 2).
"""
import pytest
from app.data_layer.providers.hces_provider import hces_provider
from app.engines.market_intelligence.consumer_profile_engine import compute_consumer_profile
from app.evidence.schema import EvidenceState

def test_hces_provider_state_benchmark():
    # Maharashtra rural benchmark
    bench_rural = hces_provider.get_state_benchmark("Maharashtra", "rural")
    assert bench_rural is not None
    assert bench_rural["mpce_inr"] == 4830.0
    assert bench_rural["food_expenditure_share_pct"] == 46.5
    assert bench_rural["non_food_expenditure_share_pct"] == 53.5
    assert bench_rural["survey_year"] == "2023-24"
    assert "rural" in bench_rural["benchmark_label"].lower()

    # Maharashtra urban benchmark
    bench_urban = hces_provider.get_state_benchmark("Maharashtra", "urban")
    assert bench_urban is not None
    assert bench_urban["mpce_inr"] == 7380.0
    assert bench_urban["food_expenditure_share_pct"] == 39.2
    assert bench_urban["non_food_expenditure_share_pct"] == 60.8

def test_hces_mpce_evidence_record():
    rec = hces_provider.get_mpce_record("Maharashtra", "rural")
    assert rec.usable is True
    assert rec.value == 4830.0
    assert rec.state == EvidenceState.VERIFIED
    assert rec.is_estimate is False
    assert rec.source_id == "hces_2023_24"
    assert rec.geography_level == "state/sector"
    assert rec.reference_date == "2023-24"

def test_compute_consumer_profile_kirana():
    res = compute_consumer_profile(state="Maharashtra", sector="rural", category_id="retail_kirana")
    assert res["status"] == "VALID"
    assert res["mpce_inr"] == 4830.0
    assert res["food_share_pct"] == 46.5
    assert res["relevant_category_share_pct"] > 0
    assert res["estimated_per_capita_category_spend_inr"] > 0
    assert res["estimated_household_category_spend_inr"] > 0
    assert "State/Sector Benchmark" in res["benchmark_label"]
    assert len(res["limitations"]) > 0

def test_compute_consumer_profile_tea_snacks():
    res = compute_consumer_profile(state="Maharashtra", sector="urban", category_id="tea_snacks")
    assert res["status"] == "VALID"
    assert res["mpce_inr"] == 7380.0
    assert res["sector"] == "urban"
    assert res["relevant_category_share_pct"] > 0
    assert "beverages_refreshments_processed" in res["relevant_spending_groups"]
