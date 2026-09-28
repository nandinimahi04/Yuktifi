"""
Comprehensive Test Suite for YuktiFi Analytics & Opportunity Engine.
Tests all 4 dashboard metrics:
1. Market Opportunity
2. Financial Viability
3. Risk Exposure
4. Capital Efficiency
Verifies deterministic math, boundary conditions, sensitivity, and endpoint responses.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    compute_canonical_financials,
    ProductItem,
    OpexBreakdown,
)
from app.engines.analytics_opportunity_engine import (
    compute_market_opportunity,
    compute_financial_viability,
    compute_risk_exposure,
    compute_capital_efficiency,
    compute_all_opportunity_analytics,
    normalize_score,
    determine_status,
)


def _create_vada_pav_financials(
    project_cost: float = 200000.0,
    own_capital: float = 60000.0,
    monthly_units: float = 7500.0,
    selling_price: float = 20.0,
    var_cost: float = 8.0,
    monthly_opex: float = 18000.0,
    interest_rate: float = 9.5,
    tenure_months: int = 36,
):
    loan_amount = max(0.0, project_cost - own_capital)
    inp = CanonicalFinancialInput(
        business_type="vada_pav",
        products=[ProductItem(name="Vada Pav", units_per_month=monthly_units, selling_price=selling_price, variable_cost_per_unit=var_cost)],
        opex=OpexBreakdown(rent=monthly_opex * 0.4, salaries=monthly_opex * 0.4, electricity=monthly_opex * 0.2),
        own_capital=own_capital,
        total_project_cost=project_cost,
        debt_amount=loan_amount,
        asset_cost=project_cost * 0.65,
        useful_life_years=5.0,
        interest_rate_annual_pct=interest_rate,
        tenure_months=tenure_months,
    )
    return compute_canonical_financials(inp)


def test_market_opportunity_deterministic():
    """Verify Market Opportunity computation from population and competitors."""
    res = compute_market_opportunity(
        category_id="vada_pav",
        population=48500,
        competitor_count=4,
        selling_price_override=20.0,
    )
    assert res.score is not None
    assert 0 <= res.score <= 100
    assert res.value > 0
    assert res.unit == "₹ / month"
    assert res.status in ["HIGH", "MODERATE", "LOW"]
    assert len(res.drivers) >= 3
    assert len(res.sources) >= 2
    assert "Census of India" in res.sources[0]
    assert res.inputs["population"] == 48500
    assert res.inputs["competitor_count"] == 4


def test_market_opportunity_missing_data():
    """Verify missing population returns INSUFFICIENT_DATA."""
    res = compute_market_opportunity(
        category_id="vada_pav",
        population=None,
        competitor_count=4,
    )
    assert res.status == "INSUFFICIENT_DATA"
    assert res.score is None
    assert res.value is None


def test_competitor_density_reduces_market_opportunity_and_increases_risk():
    """Verify increasing competitor density reduces opportunity score and increases risk."""
    opp_low_comp = compute_market_opportunity("vada_pav", population=50000, competitor_count=2)
    opp_high_comp = compute_market_opportunity("vada_pav", population=50000, competitor_count=20)
    
    assert opp_low_comp.score > opp_high_comp.score

    fin = _create_vada_pav_financials()
    risk_low_comp = compute_risk_exposure(fin, competitor_density_per_1k=0.5)
    risk_high_comp = compute_risk_exposure(fin, competitor_density_per_1k=8.0)
    
    assert risk_high_comp.score > risk_low_comp.score


def test_financial_viability_sensitivity():
    """Verify changing revenue and expenses alters viability score deterministically."""
    # Base viable scenario
    fin_base = _create_vada_pav_financials(monthly_units=7500.0, monthly_opex=18000.0)
    viab_base = compute_financial_viability(fin_base)
    assert viab_base.score >= 70
    assert viab_base.status in ["HIGH", "GOOD"]

    # Higher expenses scenario reduces net margin and viability
    fin_high_exp = _create_vada_pav_financials(monthly_units=7500.0, monthly_opex=60000.0)
    viab_high_exp = compute_financial_viability(fin_high_exp)
    assert viab_high_exp.score < viab_base.score
    assert viab_high_exp.value < viab_base.value

    # Loss making scenario MUST NOT receive favorable viability score
    fin_loss = _create_vada_pav_financials(monthly_units=1000.0, monthly_opex=50000.0)
    viab_loss = compute_financial_viability(fin_loss)
    assert viab_loss.score <= 30
    assert viab_loss.status == "LOW"


def test_selling_price_changes_contribution_and_breakeven():
    """Verify changing selling price modifies contribution margin and break-even revenue."""
    fin_price_20 = _create_vada_pav_financials(selling_price=20.0, var_cost=8.0)
    fin_price_30 = _create_vada_pav_financials(selling_price=30.0, var_cost=8.0)

    assert fin_price_30.break_even_revenue_monthly < fin_price_20.break_even_revenue_monthly
    assert fin_price_30.monthly_pat > fin_price_20.monthly_pat


def test_capital_efficiency_sensitivity():
    """Verify changing project cost changes capital efficiency, ROCE and ROI."""
    fin_low_cost = _create_vada_pav_financials(project_cost=150000.0)
    fin_high_cost = _create_vada_pav_financials(project_cost=500000.0)

    cap_low = compute_capital_efficiency(fin_low_cost)
    cap_high = compute_capital_efficiency(fin_high_cost)

    assert cap_low.inputs["roi_pct"] > cap_high.inputs["roi_pct"]
    assert cap_low.score >= cap_high.score
    assert cap_low.inputs["capital_turnover"] > cap_high.inputs["capital_turnover"]


def test_increasing_debt_service_increases_financial_risk():
    """Verify high debt and tight DSCR increases risk exposure score."""
    fin_no_debt = _create_vada_pav_financials(project_cost=200000.0, own_capital=200000.0)
    fin_heavy_debt = _create_vada_pav_financials(project_cost=200000.0, own_capital=20000.0, tenure_months=12)

    risk_no_debt = compute_risk_exposure(fin_no_debt)
    risk_heavy_debt = compute_risk_exposure(fin_heavy_debt)

    assert risk_heavy_debt.score > risk_no_debt.score


def test_unified_opportunity_suite_output():
    """Verify compute_all_opportunity_analytics returns complete 4-metric schema."""
    fin = _create_vada_pav_financials()
    res = compute_all_opportunity_analytics(
        fin_result=fin,
        population=45000,
        competitor_count=3,
        category_id="vada_pav",
    )

    assert "market_opportunity" in res
    assert "financial_viability" in res
    assert "risk_exposure" in res
    assert "capital_efficiency" in res

    for key, metric in res.items():
        assert metric["score"] is not None
        assert 0 <= metric["score"] <= 100
        assert metric["status"] in ["HIGH", "MODERATE", "LOW", "GOOD", "WARNING", "ALERT"]
        assert len(metric["drivers"]) > 0
        assert len(metric["sources"]) > 0
        assert len(metric["formula"]) > 0
        assert len(metric["inputs"]) > 0
        assert "timestamp" in metric


def test_get_opportunity_analytics_api_endpoint():
    """Verify FastAPI GET /api/analytics/opportunity endpoint returns valid analytics."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/analytics/opportunity?category_id=retail_kirana&district=Solapur")
    assert resp.status_code == 200
    data = resp.json()

    assert "market_opportunity" in data
    assert "financial_viability" in data
    assert "risk_exposure" in data
    assert "capital_efficiency" in data

    assert data["market_opportunity"]["score"] > 0
    assert data["market_opportunity"]["unit"] == "₹ / month"
    assert data["financial_viability"]["unit"] == "% Net Margin"
    assert data["risk_exposure"]["unit"] == "/ 100"
    assert data["capital_efficiency"]["unit"] == "% ROI"

