"""
End-to-End Tests for Market Intelligence Phase 2.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.engines.market_intelligence.snapshot_engine import compute_market_snapshot

client = TestClient(app)

def test_unified_market_snapshot_engine():
    snapshot = compute_market_snapshot(
        location_query="Solapur City",
        category_id="retail_kirana"
    )
    # Check Phase 1 elements
    assert "location" in snapshot
    assert "population" in snapshot
    assert "census_reference" in snapshot
    assert "competition" in snapshot
    assert "accessibility" in snapshot

    # Check Phase 2 elements
    assert "consumer_profile" in snapshot
    assert snapshot["consumer_profile"]["status"] == "VALID"
    assert snapshot["consumer_profile"]["mpce_inr"] == 4830.0 or snapshot["consumer_profile"]["mpce_inr"] == 7380.0

    assert "retail_prices" in snapshot
    assert snapshot["retail_prices"]["valid_items_count"] > 0

    assert "mandi_prices" in snapshot
    assert snapshot["mandi_prices"]["valid_items_count"] > 0
    assert "Nearest mapped mandi price" in snapshot["mandi_prices"]["label"]

    assert "input_cost_pressure" in snapshot
    assert snapshot["input_cost_pressure"]["status"] == "VALID"

def test_api_consumer_profile():
    response = client.get("/api/market/consumer-profile?state=Maharashtra&sector=rural&category_id=retail_kirana")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALID"
    assert data["state"] == "Maharashtra"
    assert data["mpce_inr"] == 4830.0

def test_api_retail_prices():
    response = client.get("/api/market/retail-prices?category_id=retail_kirana&market_centre=Solapur")
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == "retail_kirana"
    assert len(data["items"]) > 0

def test_api_mandi_prices():
    response = client.get("/api/market/mandi-prices?category_id=retail_kirana&lat=17.6599&lon=75.9064")
    assert response.status_code == 200
    data = response.json()
    assert "Nearest mapped mandi price" in data["label"]
    assert len(data["items"]) > 0

def test_api_price_trends():
    response = client.get("/api/market/price-trends?commodity=rice&market_centre=Solapur&days=30")
    assert response.status_code == 200
    data = response.json()
    assert data["commodity_id"] == "rice"
    assert len(data["series"]) > 0

def test_api_input_cost_pressure():
    response = client.get("/api/market/input-cost-pressure?category_id=retail_kirana&market_centre=Solapur")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VALID"
    assert data["pressure_level"] in ("LOW", "MODERATE", "HIGH", "SEVERE")

def test_api_snapshot_full():
    response = client.get("/api/market/snapshot?location=Solapur%20City&category_id=retail_kirana")
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "population" in data
    assert "consumer_profile" in data
    assert "retail_prices" in data
    assert "mandi_prices" in data
    assert "input_cost_pressure" in data
