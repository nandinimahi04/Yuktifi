"""
Unit tests for AGMARKNET Mandi Price Provider and Engine (Phase 2).
"""
import pytest
from app.data_layer.providers.agmarknet_provider import agmarknet_provider
from app.engines.market_intelligence.mandi_price_engine import (
    get_commodity_mandi_metrics, get_mandi_basket_for_category
)

def test_agmarknet_provider_metrics():
    # Test onion in Solapur APMC
    metrics = agmarknet_provider.compute_mandi_metrics("onion", lat=17.6599, lon=75.9064)
    assert metrics["status"] == "VALID"
    assert metrics["commodity_id"] == "onion"
    assert metrics["modal_price_quintal"] > 0
    assert metrics["modal_price_kg"] == round(metrics["modal_price_quintal"] / 100.0, 2)
    assert metrics["avg_7d_modal"] is not None
    assert metrics["avg_30d_modal"] is not None
    assert metrics["change_30d_pct"] is not None
    assert metrics["volatility_cv"] is not None
    assert "Solapur" in metrics["market_name"]
    assert metrics["distance_km"] is not None

def test_agmarknet_nearest_market_resolution():
    # Barshi coordinates: 18.2333, 75.6967
    market, dist = agmarknet_provider.resolve_nearest_market(lat=18.2333, lon=75.6967)
    assert "barshi" in market.lower()
    assert dist < 1.0  # Very close to Barshi APMC

def test_mandi_basket_kirana():
    basket = get_mandi_basket_for_category("retail_kirana", lat=17.6599, lon=75.9064)
    assert basket["total_basket_items"] >= 5
    assert basket["valid_items_count"] > 0
    assert "Nearest mapped mandi price" in basket["label"]
    assert len(basket["items"]) == basket["total_basket_items"]
