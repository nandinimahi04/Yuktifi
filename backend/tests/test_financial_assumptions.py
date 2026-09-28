import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_db, Base, engine
from app.models.session import Session
from app.models.financial_assumptions import ProjectFinancialAssumptions
from app.models.location import Location
from app.models.business_category import BusinessCategory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


def create_test_session():
    import uuid
    db = next(get_db())
    loc_id = f"loc_{uuid.uuid4().hex[:8]}"
    cat_id = "vada_pav"
    sess_id = f"sess_{uuid.uuid4().hex[:8]}"

    # Add location & category if not existing
    loc = db.query(Location).filter(Location.id == loc_id).first()
    if not loc:
        loc = Location(id=loc_id, district="Solapur", state="Maharashtra", lat=17.6715, lng=75.9080)
        db.add(loc)

    cat = db.query(BusinessCategory).filter(BusinessCategory.id == cat_id).first()
    if not cat:
        cat = BusinessCategory(id=cat_id, name="Vada Pav & Street Food", parent_category="Food & Beverage")
        db.add(cat)

    sess = Session(id=sess_id, location_id=loc_id, category_id=cat_id, margin_capital=100000.0)
    db.add(sess)
    db.commit()
    return sess_id


def test_get_financial_assumptions_initializes_defaults():
    sess_id = create_test_session()
    response = client.get(f"/api/financials/{sess_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("success", "warning")
    assert "assumptions" in data
    assert "financials" in data
    assert data["assumptions"]["session_id"] == sess_id
    assert data["assumptions"]["version"] == 1
    assert data["financials"]["monthly_revenue"] > 0
    assert data["financials"]["monthly_cogs"] > 0
    assert data["financials"]["pnl_statement"]["gross_profit"] > 0


def test_recalculate_vada_pav_business_end_to_end():
    sess_id = create_test_session()
    
    # Initialize version 1 via GET
    init_res = client.get(f"/api/financials/{sess_id}")
    assert init_res.status_code == 200
    assert init_res.json()["assumptions_version"] == 1

    # Define ₹1,00,000 Vada Pav business parameters
    payload = {
        "session_id": sess_id,
        "assumptions": {
            "project_cost": 150000.0,
            "own_capital": 50000.0,
            "loan_amount": 100000.0,
            "is_direct_revenue_mode": False,
            "selling_price": 20.0,
            "units_per_day": 250.0,
            "operating_days": 30,
            "variable_cost_per_unit": 8.0,
            "monthly_expenses": 18000.0,
            "interest_rate_annual_pct": 9.0,
            "loan_tenure_months": 36,
            "moratorium_months": 0,
            "version": 1
        },
        "changed_by": "test_suite"
    }
    
    res = client.post("/api/financials/recalculate", json=payload)
    assert res.status_code == 200
    data = res.json()
    
    assump = data["assumptions"]
    fin = data["financials"]
    pnl = fin["pnl_statement"]
    
    # 1. Revenue = 20 * 250 * 30 = 1,50,000
    assert assump["version"] == 2
    assert fin["monthly_revenue"] == 150000.0
    
    # 2. Variable Cost / COGS = 8 * 250 * 30 = 60,000
    assert fin["monthly_cogs"] == 60000.0
    
    # 3. Gross Profit = 1,50,000 - 60,000 = 90,000 (Gross margin 60%)
    assert pnl["gross_profit"] == 90000.0
    assert pnl["gross_margin_pct"] == 60.0
    
    # 4. EBITDA = 90,000 - 18,000 = 72,000
    assert pnl["ebitda"] == 72000.0
    
    # 5. Loan Amount = 1,00,000 @ 9% for 36 months -> EMI approx 3180
    assert fin["monthly_emi"] > 3100.0 and fin["monthly_emi"] < 3300.0
    
    # 6. Break-even: Contribution = 20 - 8 = 12. Break-even units = 18000 / 12 = 1500 units/mo
    assert fin["break_even_units"] == 1500.0
    assert fin["break_even_revenue"] == 30000.0
    
    # 7. DSCR > 1.5 (very healthy cash coverage)
    assert fin["dscr"] is not None and fin["dscr"] > 1.5


def test_direct_revenue_mode_override():
    sess_id = create_test_session()
    
    payload = {
        "session_id": sess_id,
        "assumptions": {
            "project_cost": 200000.0,
            "own_capital": 50000.0,
            "loan_amount": 150000.0,
            "is_direct_revenue_mode": True,
            "monthly_revenue": 220000.0,
            "selling_price": 20.0,
            "units_per_day": 200.0,
            "operating_days": 30,
            "variable_cost_per_unit": 8.0,
            "monthly_expenses": 30000.0,
            "interest_rate_annual_pct": 8.5,
            "loan_tenure_months": 60,
            "version": 1
        }
    }
    
    res = client.post("/api/financials/recalculate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["financials"]["monthly_revenue"] == 220000.0


def test_validation_rejects_own_capital_greater_than_project_cost():
    sess_id = create_test_session()
    
    payload = {
        "session_id": sess_id,
        "assumptions": {
            "project_cost": 100000.0,
            "own_capital": 150000.0, # invalid
            "loan_amount": 0.0,
            "is_direct_revenue_mode": False,
            "selling_price": 20.0,
            "units_per_day": 100.0,
            "operating_days": 30,
            "variable_cost_per_unit": 8.0,
            "monthly_expenses": 10000.0,
        }
    }
    
    res = client.post("/api/financials/recalculate", json=payload)
    assert res.status_code == 422


def test_optimistic_concurrency_conflict():
    sess_id = create_test_session()
    
    # Initialize version 1 via GET
    init_res = client.get(f"/api/financials/{sess_id}")
    assert init_res.status_code == 200
    assert init_res.json()["assumptions_version"] == 1

    # Save once -> advances from v1 to v2
    payload1 = {
        "session_id": sess_id,
        "assumptions": {
            "project_cost": 200000.0,
            "own_capital": 50000.0,
            "loan_amount": 150000.0,
            "is_direct_revenue_mode": False,
            "selling_price": 20.0,
            "units_per_day": 100.0,
            "operating_days": 30,
            "variable_cost_per_unit": 8.0,
            "monthly_expenses": 10000.0,
            "version": 1
        }
    }
    res1 = client.post("/api/financials/recalculate", json=payload1)
    assert res1.status_code == 200
    assert res1.json()["assumptions_version"] == 2

    # Second request with stale version 1 -> must 409
    payload2 = {
        "session_id": sess_id,
        "assumptions": {
            "project_cost": 250000.0,
            "own_capital": 50000.0,
            "loan_amount": 200000.0,
            "is_direct_revenue_mode": False,
            "selling_price": 20.0,
            "units_per_day": 100.0,
            "operating_days": 30,
            "variable_cost_per_unit": 8.0,
            "monthly_expenses": 10000.0,
            "version": 1 # Stale!
        }
    }
    res2 = client.post("/api/financials/recalculate", json=payload2)
    assert res2.status_code == 409


def test_unseeded_session_auto_initialization():
    import uuid
    new_sess_id = f"auto_{uuid.uuid4().hex}"
    
    # 1. GET /api/financials/{new_sess_id} should auto-create session and return 200 (not 404)
    get_res = client.get(f"/api/financials/{new_sess_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["assumptions"]["session_id"] == new_sess_id
    assert data["assumptions"]["version"] == 1
    assert data["financials"]["monthly_revenue"] > 0

    # 2. POST /api/financials/recalculate with a brand new unseeded session id should auto-create and return 200
    another_sess_id = f"auto_{uuid.uuid4().hex}"
    payload = {
        "session_id": another_sess_id,
        "category_id": "vada_pav",
        "assumptions": {
            "project_cost": 200000.0,
            "own_capital": 50000.0,
            "loan_amount": 150000.0,
            "is_direct_revenue_mode": False,
            "selling_price": 25.0,
            "units_per_day": 200.0,
            "operating_days": 30,
            "variable_cost_per_unit": 10.0,
            "monthly_expenses": 20000.0,
            "interest_rate_annual_pct": 9.5,
            "loan_tenure_months": 48,
            "version": 1
        }
    }
    recalc_res = client.post("/api/financials/recalculate", json=payload)
    assert recalc_res.status_code == 200
    recalc_data = recalc_res.json()
    assert recalc_data["assumptions"]["session_id"] == another_sess_id
    assert recalc_data["assumptions"]["version"] == 1

    # 3. Subsequent POST advances version to 2
    payload["assumptions"]["version"] = 1
    payload["assumptions"]["monthly_expenses"] = 22000.0
    recalc_res2 = client.post("/api/financials/recalculate", json=payload)
    assert recalc_res2.status_code == 200
    assert recalc_res2.json()["assumptions"]["version"] == 2


