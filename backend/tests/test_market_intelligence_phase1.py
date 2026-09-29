"""
Unit & Integration Tests for Market Intelligence Phase 1
Sources: Census India 2011 + WorldPop + Overture Maps Places + OpenStreetMap
Pilot Geography: Solapur District, Maharashtra
Pilot Businesses: Kirana / Grocery Store & Tea & Snacks Shop
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.base_provider import BaseDataProvider
from app.providers.census_provider import CensusProvider
from app.providers.worldpop_provider import WorldPopProvider
from app.providers.overture_provider import OvertureProvider
from app.providers.osm_provider import OSMProvider
from app.providers.taxonomy import (
    resolve_category_taxonomy,
    TAXONOMIES,
    CategoryTaxonomy,
)
from app.engines.market_intelligence.deduplication import (
    deduplicate_places,
    are_pois_duplicate,
    normalize_poi_name,
)
from app.engines.market_intelligence.snapshot_engine import compute_market_snapshot
from app.evidence.schema import EvidenceState, Confidence

client = TestClient(app)


# ─── 1. Provider Interface & Taxonomy Tests ───────────────────────────────────

def test_providers_inherit_base():
    """All 4 providers must implement BaseDataProvider contract."""
    assert issubclass(CensusProvider, BaseDataProvider)
    assert issubclass(WorldPopProvider, BaseDataProvider)
    assert issubclass(OvertureProvider, BaseDataProvider)
    assert issubclass(OSMProvider, BaseDataProvider)


def test_taxonomy_kirana_and_tea_snacks():
    """Verify distinct radii and taxonomy mapping for Kirana and Tea & Snacks."""
    kirana = resolve_category_taxonomy("retail_kirana")
    assert kirana.primary_radius_km == 2.0
    assert kirana.extended_radius_km == 5.0
    assert "grocery_store" in kirana.overture_categories
    assert any("convenience" in t for t in kirana.osm_tag_filters)

    tea = resolve_category_taxonomy("tea_snacks")
    assert tea.primary_radius_km == 1.0
    assert tea.extended_radius_km == 3.0
    assert "tea_house" in tea.overture_categories
    assert any("cafe" in t for t in tea.osm_tag_filters)


def test_taxonomy_alias_resolution():
    """Verify fuzzy and alias resolution for categories."""
    assert resolve_category_taxonomy("tea_stall").category_id == "tea_stall"
    assert resolve_category_taxonomy("chai").category_id == "tea_snacks"
    assert resolve_category_taxonomy("grocery").category_id == "retail_kirana"
    assert resolve_category_taxonomy("retail_shop").primary_radius_km == 2.0


# ─── 2. Census India Provider Tests ───────────────────────────────────────────

def test_census_provider_solapur_baseline():
    """Census provider returns verified 2011 baseline data."""
    provider = CensusProvider()
    res = provider.fetch_data({"district": "Solapur", "state": "Maharashtra"})
    
    assert "value" in res and "provenance" in res and "confidence" in res
    val = res["value"]
    prov = res["provenance"]
    
    # Official 2011 Solapur population
    assert val["total_population"] == 4317756
    assert val["census_reference_year"] == 2011
    
    # Provenance assertions
    assert prov["is_estimate"] is False
    assert prov["reference_date"] == "2011"
    assert prov["state"] == EvidenceState.VERIFIED.value
    assert prov["source_id"] == "census_pca_2011"


def test_census_provider_taluka_lookups():
    """Census provider resolves specific Solapur talukas and towns."""
    provider = CensusProvider()
    
    # Solapur City
    city_res = provider.fetch_data({"district": "Solapur", "village": "Solapur City"})
    assert city_res["value"]["total_population"] == 951558
    
    # Barshi Taluka
    barshi_res = provider.fetch_data({"district": "Solapur", "subdistrict": "Barshi"})
    assert barshi_res["value"]["total_population"] == 372711


# ─── 3. WorldPop Provider Tests ───────────────────────────────────────────────

def test_worldpop_provider_catchment_calculation():
    """WorldPop provider returns modeled spatial population."""
    provider = WorldPopProvider()
    res = provider.fetch_data({"lat": 17.6599, "lon": 75.9064, "radius_km": 2.0})
    
    val = res["value"]
    prov = res["provenance"]
    
    assert val["radius_km"] == 2.0
    assert val["catchment_population"] > 0
    assert val["catchment_households"] > 0
    assert val["area_sq_km"] > 0
    
    # Provenance assertions
    assert prov["is_estimate"] is True
    assert prov["state"] == EvidenceState.ESTIMATED.value
    assert prov["source_id"] == "worldpop_grid"


def test_worldpop_radius_scaling():
    """Larger radius increases catchment population monotonically."""
    provider = WorldPopProvider()
    r1 = provider.fetch_data({"lat": 17.6599, "lon": 75.9064, "radius_km": 1.0})["value"]["catchment_population"]
    r2 = provider.fetch_data({"lat": 17.6599, "lon": 75.9064, "radius_km": 2.0})["value"]["catchment_population"]
    r5 = provider.fetch_data({"lat": 17.6599, "lon": 75.9064, "radius_km": 5.0})["value"]["catchment_population"]
    
    assert r1 < r2 < r5


# ─── 4. Overture & OSM Providers Tests ─────────────────────────────────────────

def test_overture_provider_poi_extraction():
    """Overture provider extracts commercial POIs matching category."""
    provider = OvertureProvider()
    res = provider.fetch_data({"lat": 17.6599, "lon": 75.9064, "category_id": "retail_kirana", "radius_km": 2.0})
    
    val = res["value"]
    assert val["count"] > 0
    assert len(val["records"]) == val["count"]
    for rec in val["records"]:
        assert rec["source"] == "overture"
        assert rec["distance_km"] <= 2.0


def test_osm_provider_pois_and_accessibility():
    """OSM provider extracts POIs and accessibility infrastructure."""
    provider = OSMProvider()
    res = provider.fetch_data({"lat": 17.6599, "lon": 75.9064, "category_id": "tea_snacks", "radius_km": 1.5})
    
    val = res["value"]
    assert val["count"] > 0
    assert len(val["accessibility"]) > 0
    
    # Accessibility infrastructure assertions
    infra_names = [i["name"] for i in val["accessibility"]]
    assert any("Solapur Junction" in n for n in infra_names)


# ─── 5. Deduplication Engine Tests ────────────────────────────────────────────

def test_poi_name_normalization():
    """Verify name normalization strips noise words and symbols."""
    assert normalize_poi_name("Yashoda Shopping Centre (Navi Peth)") == "yashoda"
    assert normalize_poi_name("Yewale Amruttulya Tea & Snacks") == "yewale amruttulya"


def test_duplicate_poi_detection():
    """Same place within 50m is flagged as duplicate."""
    p1 = {"name": "Yashoda Supermarket", "lat": 17.6605, "lon": 75.9070}
    p2 = {"name": "Yashoda Shopping Centre", "lat": 17.66055, "lon": 75.90705}
    is_dup, dist_m, sim = are_pois_duplicate(p1, p2)
    assert is_dup is True
    assert dist_m < 20.0
    assert sim > 0.5


def test_deduplicate_places_deterministic():
    """Deduplication ensures unique_mapped_count = overture + osm - duplicates."""
    ovt_places = [
        {"id": "ovt_1", "name": "Yashoda Supermarket", "category": "grocery", "lat": 17.6605, "lon": 75.9070, "distance_km": 0.2},
        {"id": "ovt_2", "name": "Modi Bazaar", "category": "supermarket", "lat": 17.6470, "lon": 75.9110, "distance_km": 1.5},
    ]
    osm_places = [
        {"id": "osm_1", "name": "Yashoda Shopping Centre", "category": "convenience", "lat": 17.6605, "lon": 75.9070, "distance_km": 0.2}, # duplicate of ovt_1
        {"id": "osm_2", "name": "Navi Peth Store", "category": "general", "lat": 17.6640, "lon": 75.9095, "distance_km": 0.6}, # unique
    ]
    
    dedup = deduplicate_places(ovt_places, osm_places)
    
    assert dedup["overture_count"] == 2
    assert dedup["osm_count"] == 2
    assert dedup["duplicate_count"] == 1
    assert dedup["unique_mapped_count"] == 3  # 2 + 2 - 1 = 3 (Never 4!)


# ─── 6. Snapshot Engine & Metrics Calculation Tests ───────────────────────────

def test_market_snapshot_kirana_solapur():
    """Full snapshot for Kirana in Solapur."""
    snapshot = compute_market_snapshot(
        location_query="Solapur City",
        category_id="retail_kirana",
        radius_km=2.0
    )
    
    assert snapshot["location"]["district"] == "Solapur"
    assert snapshot["category"]["primary_radius_km"] == 2.0
    assert snapshot["population"]["catchment_population"] > 0
    assert snapshot["census_reference"]["district_population_2011"] == 951558  # Solapur City Census 2011
    assert snapshot["competition"]["unique_mapped_count"] > 0
    assert snapshot["competitor_density"]["competitors_per_1000_people"] > 0
    assert snapshot["competitor_density"]["population_per_competitor"] > 0
    assert len(snapshot["accessibility"]["infrastructure"]) > 0
    assert len(snapshot["limitations"]) >= 4


def test_market_snapshot_tea_snacks_solapur():
    """Full snapshot for Tea & Snacks in Solapur (1.0 km radius)."""
    snapshot = compute_market_snapshot(
        location_query="Solapur City",
        category_id="tea_snacks",
        radius_km=1.0
    )
    
    assert snapshot["category"]["display_name"] == "Tea & Snacks Shop"
    assert snapshot["category"]["primary_radius_km"] == 1.0
    assert snapshot["competition"]["unique_mapped_count"] > 0
    assert snapshot["population"]["radius_km"] == 1.0


def test_market_snapshot_zero_competitor_graceful_abstention():
    """Zero competitor scenario must abstain safely without ZeroDivisionError."""
    # Remote point with 0 competitors
    snapshot = compute_market_snapshot(
        lat=19.9999,
        lon=79.9999,
        category_id="retail_kirana",
        radius_km=0.5
    )
    
    assert snapshot["competition"]["unique_mapped_count"] == 0
    assert snapshot["competitor_density"]["competitors_per_1000_people"] == 0.0
    assert snapshot["competitor_density"]["population_per_competitor"] is None
    assert "No mapped competitors were found" in snapshot["competition"]["note"]


# ─── 7. API Endpoints Integration Tests ───────────────────────────────────────

def test_api_get_market_snapshot_kirana():
    """Test GET /api/market/snapshot for Kirana."""
    response = client.get("/api/market/snapshot?category_id=retail_kirana&location=Solapur+City")
    assert response.status_code == 200
    data = response.json()
    assert data["category"]["category_id"] == "retail_kirana"
    assert data["population"]["catchment_population"] > 0
    assert data["competition"]["unique_mapped_count"] > 0
    assert "census_reference" in data["evidence"]


def test_api_get_market_snapshot_tea_snacks():
    """Test GET /api/market/snapshot for Tea & Snacks."""
    response = client.get("/api/market/snapshot?category_id=tea_snacks&location=Barshi")
    assert response.status_code == 200
    data = response.json()
    assert data["category"]["category_id"] == "tea_snacks"
    assert data["location"]["subdistrict"] == "Barshi"


def test_api_post_market_snapshot():
    """Test POST /api/market/snapshot."""
    response = client.post("/api/market/snapshot?category_id=retail_kirana&lat=17.6599&lon=75.9064")
    assert response.status_code == 200
    data = response.json()
    assert data["competition"]["unique_mapped_count"] > 0
