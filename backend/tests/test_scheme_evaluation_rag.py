"""
Tests for RAG-grounded multi-scheme evaluator.
Verifies demographic targeting, subsidy calculations, and official RAG citations.
"""
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engines.scheme_evaluator import evaluate_applicant_schemes
from app.core.db import Base, get_db
from app.main import app as fastapi_app
from app.models import Session as SessionModel, User
from app.models.core import uid


def test_pmegp_rural_special_category_35_percent():
    res = evaluate_applicant_schemes(
        social_category="OBC",
        gender="Female",
        location_type="Rural",
        category_id="food_processing",
        project_cost=500_000.0,
        own_contribution=25_000.0
    )
    pmegp = next(s for s in res["eligible_schemes"] if s["scheme_id"] == "PMEGP")
    assert pmegp["is_eligible"] is True
    assert pmegp["subsidy_pct"] == 35.0
    assert pmegp["subsidy_amount"] == 175_000.0
    assert pmegp["equity_pct"] == 5.0
    assert pmegp["rag_citation"]["grounding_status"] in {"RAG_GROUNDED_VERIFIED", "VERIFIED_OFFICIAL_CORPUS"}


def test_pmegp_urban_general_15_percent():
    res = evaluate_applicant_schemes(
        social_category="General",
        gender="Male",
        location_type="Urban",
        category_id="retail_kirana",
        project_cost=400_000.0,
    )
    pmegp = next(s for s in res["eligible_schemes"] if s["scheme_id"] == "PMEGP")
    assert pmegp["subsidy_pct"] == 15.0
    assert pmegp["subsidy_amount"] == 60_000.0
    assert pmegp["equity_pct"] == 10.0


def test_pmfme_food_processing_35_percent_subsidy():
    res = evaluate_applicant_schemes(
        social_category="General",
        gender="Male",
        location_type="Rural",
        category_id="bakery",
        project_cost=600_000.0,
    )
    pmfme = next(s for s in res["eligible_schemes"] if s["scheme_id"] == "PMFME")
    assert pmfme["is_eligible"] is True
    assert pmfme["subsidy_pct"] == 35.0
    assert pmfme["subsidy_amount"] == 210_000.0
    assert pmfme["portal_url"] == "https://pmfme.mofpi.gov.in/"


def test_nsfdc_sc_women_mahila_samriddhi():
    res = evaluate_applicant_schemes(
        social_category="SC",
        gender="Female",
        location_type="Rural",
        category_id="tailoring",
        project_cost=100_000.0,
    )
    msy = next(s for s in res["eligible_schemes"] if s["scheme_id"] == "NSFDC_MSY")
    assert msy["is_eligible"] is True
    assert "4.0%" in msy["interest_rate"]
    assert msy["rag_citation"]["grounding_status"] in {"RAG_GROUNDED_VERIFIED", "VERIFIED_OFFICIAL_CORPUS"}


def test_pm_svanidhi_street_vendor():
    res = evaluate_applicant_schemes(
        social_category="General",
        gender="Male",
        location_type="Urban",
        category_id="vada_pav",
        project_cost=30_000.0,
    )
    svanidhi = next(s for s in res["eligible_schemes"] if s["scheme_id"] == "PM_SVANIDHI")
    assert svanidhi["is_eligible"] is True
    assert svanidhi["max_loan"] == 50000.0
    assert "7%" in svanidhi["special_benefit"]


def test_scheme_evaluate_api_endpoint():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    user = User(id=uid(), name="Meera", language_pref="en", social_category="SC", gender="Female")
    session = SessionModel(id="sess-rag-eval", user_id=user.id, location_id="solapur", category_id="bakery", margin_capital=50000.0)
    db.add_all([user, session])
    db.commit()

    def override():
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override
    try:
        client = TestClient(fastapi_app)
        r = client.post("/schemes/evaluate", json={
            "session_id": "sess-rag-eval",
            "project_cost": 500000.0
        })
        assert r.status_code == 200
        body = r.json()
        assert body["applicant_profile"]["social_category"] == "SC"
        assert body["applicant_profile"]["gender"] == "Female"
        assert body["total_eligible_count"] >= 3
        # Must have PMEGP, PMFME, and NSFDC/MUDRA
        scheme_ids = [s["scheme_id"] for s in body["eligible_schemes"]]
        assert "PMEGP" in scheme_ids
        assert "PMFME" in scheme_ids
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
