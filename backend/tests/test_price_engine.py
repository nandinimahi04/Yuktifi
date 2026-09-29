"""
Unit tests for Input Cost Pressure Engine (Phase 2).
"""
import pytest
from app.engines.market_intelligence.input_cost_pressure_engine import compute_input_cost_pressure

def test_input_cost_pressure_kirana():
    res = compute_input_cost_pressure(category_id="retail_kirana", market_centre="Solapur")
    assert res["status"] == "VALID"
    assert res["category_id"] == "retail_kirana"
    assert res["weighted_30d_change_pct"] is not None
    assert res["weighted_volatility_cv"] is not None
    assert res["pressure_level"] in ("LOW", "MODERATE", "HIGH", "SEVERE")
    assert res["coverage_pct"] >= 50.0
    assert len(res["input_breakdown"]) > 0
    assert len(res["cost_drivers"]) > 0

def test_input_cost_pressure_tea_snacks():
    res = compute_input_cost_pressure(category_id="tea_snacks", market_centre="Solapur")
    assert res["status"] == "VALID"
    assert res["category_id"] == "tea_snacks"
    assert res["weighted_30d_change_pct"] is not None
    assert res["pressure_level"] in ("LOW", "MODERATE", "HIGH", "SEVERE")

def test_input_cost_pressure_missing_category():
    res = compute_input_cost_pressure(category_id="unmapped_nonexistent_category_123")
    assert res["status"] == "INSUFFICIENT_DATA"
    assert res["weighted_30d_change_pct"] is None
    assert res["pressure_level"] == "UNKNOWN"
