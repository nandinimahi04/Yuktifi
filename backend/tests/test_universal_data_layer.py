"""
Comprehensive Test Suite for Universal Yukti Data & Evidence Layer (UYDF-1.0).
Verifies inventory, parsing, normalization, quality validation, evidence contract,
provenance, business mapping, RAG retrieval, and deterministic decision integration.
"""
import pytest
import sys
from pathlib import Path

# Add backend and root directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
repo_root = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from fastapi.testclient import TestClient
from app.main import app
from app.data_layer.universal.evidence_contract import (
    UniversalEvidenceRecord, EntityContext, ObservationPayload, TimeContext,
    ProvenanceContext, QualityContext, BusinessContext, ValueOrigin, ConfidenceLevel, SourceCategory
)
from app.data_layer.universal.business_mapping import (
    resolve_business_category, get_relevant_datasets_for_business, BUSINESS_TAXONOMY
)
from data_pipeline.normalizers.unit_normalizer import normalize_currency_and_period
from data_pipeline.normalizers.time_normalizer import normalize_time_context
from data_pipeline.normalizers.geography_normalizer import normalize_geography
from data_pipeline.validators.quality_validator import DataQualityValidator
from data_pipeline.validators.duplicate_detector import DuplicateDetector
from app.data_layer.universal.retrieval_service import (
    retrieve_evidence, retrieve_documents, get_dataset_catalog, get_data_quality_report
)

client = TestClient(app)

# 1. Unit Normalization Tests
def test_unit_normalization_currency():
    res = normalize_currency_and_period("₹75,000", "per month")
    assert res["normalized_value"] == 75000.0
    assert res["normalized_unit"] == "INR / month"

    res_lakh = normalize_currency_and_period("3.5 Lakh", "INR")
    assert res_lakh["normalized_value"] == 350000.0

    res_pct = normalize_currency_and_period("18.5%", "%")
    assert res_pct["normalized_value"] == 18.5
    assert res_pct["normalized_unit"] == "%"

# 2. Time Normalization Tests
def test_time_normalization():
    res = normalize_time_context("2022-23", filename="Factsheet_HCES_2022-23.pdf")
    assert res["reference_year"] == 2023
    assert res["survey_period"] == "2022-23"

    res_census = normalize_time_context(2011, filename="PCA_CDB_2730_F_Census.xls")
    assert res_census["reference_year"] == 2011

# 3. Geography Normalization & Alias Tests
def test_geography_normalization():
    # Alias test: Ahmadnagar -> Ahilyanagar
    geo = normalize_geography("Ahmadnagar")
    assert geo["normalized_name"] == "Ahilyanagar"

    # Solapur Taluka test: Akkalkot
    geo_ak = normalize_geography("Akkalkot")
    assert geo_ak["normalized_name"] == "Akkalkot"
    assert geo_ak["district"] == "Solapur"
    assert geo_ak["lgd_code"] == "04256"

# 4. Data Quality & Quarantine Tests
def test_data_quality_validation():
    validator = DataQualityValidator()
    mock_records = [
        {"District": "Solapur", "Population": 4317756, "Area": 14895},
        {"District": "Corrupt", "Population": -500}, # Negative impossible
        {} # Empty row
    ]
    valid, invalid, rep = validator.validate_dataset_records("test_ds", mock_records)
    assert len(valid) == 1
    assert len(invalid) == 2
    assert rep["status"] == "PARTIAL"

# 5. Duplicate Detection Tests
def test_duplicate_detection():
    detector = DuplicateDetector()
    h1 = "abc1234567890abcdef"
    assert detector.check_file("file1.csv", h1, 1024) is False
    assert detector.check_file("file1_copy.csv", h1, 1024) is True
    assert len(detector.get_duplicates_report()) == 1

# 6. Universal Evidence Contract Serialization
def test_universal_evidence_contract():
    record = UniversalEvidenceRecord(
        dataset_id="census_pca_2011",
        entity=EntityContext(name="Akkalkot", district="Solapur", state="Maharashtra", level="SUBDISTRICT"),
        observation=ObservationPayload(metric="population", value=314770, unit="Count"),
        time=TimeContext(reference_year=2011),
        provenance=ProvenanceContext(source="Census of India", original_file="PCA_CDB_2730_F_Census.xls"),
        quality=QualityContext(origin=ValueOrigin.DATASET_DERIVED, confidence=ConfidenceLevel.HIGH)
    )
    d = record.to_dict()
    assert d["dataset_id"] == "census_pca_2011"
    assert d["observation"]["value"] == 314770
    assert d["quality"]["origin"] == "DATASET_DERIVED"

# 7. Business Taxonomy & Mapping Tests
def test_business_taxonomy_mapping():
    kirana = resolve_business_category("kirana")
    assert kirana["category_id"] == "kirana"
    assert "census_pca_2011" in kirana["relevant_datasets"]

    dairy = resolve_business_category("doodh dairy")
    assert dairy["category_id"] == "dairy"
    assert "agmarknet_wholesale_prices" in dairy["relevant_datasets"]

    agri = resolve_business_category("farming")
    assert agri["category_id"] == "agriculture"
    assert "area_under_irrigation" in agri["relevant_datasets"]

# 8. Evidence & RAG Retrieval Tests
def test_evidence_retrieval_service():
    evi = retrieve_evidence(business_category="dairy", location="Solapur", limit=10)
    assert "results" in evi
    assert evi["confidence"] in ["HIGH", "MEDIUM"]

    docs = retrieve_documents(query="Solapur population and amenities", business_category="dairy", top_k=3)
    assert "results" in docs
    assert len(docs["results"]) > 0

# 9. API Endpoints Tests
def test_api_universal_evidence_endpoints():
    res = client.get("/api/evidence/datasets")
    assert res.status_code == 200
    assert "datasets" in res.json()

    res_search = client.get("/api/evidence/search?business_category=kirana&location=Solapur")
    assert res_search.status_code == 200
    assert "results" in res_search.json()

    res_catalog = client.get("/api/data/catalog")
    assert res_catalog.status_code == 200
    assert "catalog" in res_catalog.json()

    res_quality = client.get("/api/data/quality")
    assert res_quality.status_code == 200

    res_rag = client.get("/api/rag/search?query=Solapur+amenities")
    assert res_rag.status_code == 200

# 10. End-to-End Decision Integration Test
def test_end_to_end_decision_flow():
    """
    Scenario:
    User Location = Akkalkot, Solapur, Maharashtra
    Business = Dairy
    Capital = ₹100,000
    Verifies location resolution -> dataset mapping -> evidence retrieval -> financial engine -> decision object.
    """
    # 1. Location Normalization
    loc = normalize_geography("Akkalkot", raw_district="Solapur")
    assert loc["normalized_name"] == "Akkalkot"
    assert loc["lgd_code"] == "04256"

    # 2. Business Mapping
    biz = resolve_business_category("dairy")
    assert biz["category_id"] == "dairy"

    # 3. Evidence Retrieval
    evidence = retrieve_evidence(business_category="dairy", location="Solapur", limit=5)
    assert len(evidence["results"]) > 0

    # 4. RAG Retrieval
    docs = retrieve_documents(query="dairy livestock fodder Solapur", business_category="dairy", top_k=2)
    assert len(docs["results"]) > 0

    # 5. Financial & Decision Object Verification via Phase 1/2 services
    from app.phase1.service import run_decision
    payload = {
        "business_id": "dairy",
        "business_name": "Dairy Farm",
        "financial": {
            "total_project_cost": 300000.0,
            "margin_capital": 100000.0,
            "debt_amount": 200000.0,
            "monthly_revenue": 85000.0,
            "monthly_opex": 48000.0,
            "annual_interest_rate_pct": 9.0,
            "tenure_months": 60
        },
        "market": {
            "geography": "Solapur",
            "competitor_count": 2
        },
        "risk_score": 75
    }
    decision = run_decision(payload)
    assert decision is not None
    assert "decision" in decision
    assert "financial" in decision
    assert decision["financial"]["emi"] is not None
    assert decision["financial"]["dscr"] is not None
    assert decision["financial"]["project_cost"] == 300000.0
