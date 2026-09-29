"""
Unit tests for Consumer Affairs Retail Price Provider and Engine (Phase 2).
"""
import pytest
from app.data_layer.providers.consumer_affairs_provider import consumer_affairs_provider
from app.engines.market_intelligence.retail_price_engine import (
    get_commodity_retail_metrics, get_retail_basket_for_category, get_retail_timeseries
)

def test_consumer_affairs_provider_metrics():
    # Test rice metrics in Solapur
    metrics = consumer_affairs_provider.compute_retail_metrics("rice", "Solapur")
    assert metrics["status"] == "VALID"
    assert metrics["commodity_id"] == "rice"
    assert metrics["current_price"] > 0
    assert metrics["avg_7d"] is not None
    assert metrics["avg_30d"] is not None
    assert metrics["avg_90d"] is not None
    assert metrics["change_30d_pct"] is not None
    assert metrics["volatility_cv"] is not None
    assert metrics["observation_count"] >= 3

def test_consumer_affairs_missing_commodity():
    metrics = consumer_affairs_provider.compute_retail_metrics("non_existent_item_xyz", "Solapur")
    assert metrics["status"] == "INSUFFICIENT_DATA"
    assert metrics["current_price"] is None
    assert metrics["evidence_state"] == "MISSING"

def test_retail_basket_kirana():
    basket = get_retail_basket_for_category("retail_kirana", "Solapur")
    assert basket["total_basket_items"] >= 5
    assert basket["valid_items_count"] > 0
    assert len(basket["items"]) == basket["total_basket_items"]
    assert "retail_price_rice" in basket["evidence"]

def test_retail_timeseries():
    ts = get_retail_timeseries("wheat", "Solapur", days=30)
    assert ts["commodity_id"] == "wheat"
    assert ts["points_count"] > 0
    assert len(ts["series"]) > 0
    assert "date" in ts["series"][0]
    assert "price" in ts["series"][0]
