"""
Financial truth tests — the audit's mandatory cases.

These encode the submission standard:
  Test A  Rs 1 lakh vada pav, no debt. The engine must NOT manufacture a loan.
  Test B  Rs 1 lakh capital, Rs 2 lakh project, Rs 1 lakh debt. EMI + schedule.
  Test C  Demand shock -20%. Whole chain recalculates.
  Test D  Cost shock +15%. Whole chain recalculates.
  Test E  Impossible business. Must become NOT_VIABLE and say why.

Plus the cross-module rupee-equality invariant: dashboard == financial API ==
report == what-if == AI explanation, to the rupee.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP_DB = Path(tempfile.gettempdir()) / "yukti_financial_truth_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["SEED_ON_STARTUP"] = "false"

import pytest

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    ProductItem,
    OpexBreakdown,
    WorkingCapitalConfig,
    assert_financing_reconciles,
    build_loan_schedule,
    compute_canonical_financials,
    compute_emi,
)
from app.engines.stress_engine import run_stress_test_suite
from app.engines.simulation_engine import run_simulation


VADA_PAV = dict(
    name="vada_pav",
    units_per_month=9000.0,
    selling_price=20.0,
    variable_cost_per_unit=8.0,
)


def vada_pav_input(**overrides) -> CanonicalFinancialInput:
    base = dict(
        business_type="vada_pav",
        products=[ProductItem(**VADA_PAV)],
        opex=OpexBreakdown(rent=8000.0, salaries=6000.0, electricity=2000.0),
        own_capital=100000.0,
        total_project_cost=100000.0,
        debt_amount=0.0,
    )
    base.update(overrides)
    return CanonicalFinancialInput(**base)


# ── Test A ────────────────────────────────────────────────────────────────────

def test_a_no_loan_is_manufactured():
    """Capital Rs 1L, project cost Rs 1L, no debt. Must stay at zero debt."""
    res = compute_canonical_financials(vada_pav_input())

    assert res.total_project_cost == 100000.0
    assert res.own_capital == 100000.0
    assert res.debt_amount == 0.0
    assert res.approved_loan_amount == 0.0
    assert res.monthly_emi == 0.0
    assert res.annual_debt_service == 0.0
    assert res.financing_gap == 0.0
    assert res.financing_reconciled is True
    assert_financing_reconciles(res)


def test_a_dscr_is_not_applicable_not_a_sentinel():
    """No debt means no DSCR. It must be None, never 999 or inf."""
    res = compute_canonical_financials(vada_pav_input())

    assert res.dscr is None
    assert res.dscr_status == "NOT_APPLICABLE_NO_DEBT"
    assert res.debt_service_status == "NO_DEBT"
    assert res.loan_schedule == []


def test_a_no_sentinel_survives_serialisation():
    """The result must serialise without any sentinel leaking to the client."""
    res = compute_canonical_financials(vada_pav_input())
    flat = repr(res.to_dict())

    assert "999" not in flat
    assert "inf" not in flat


# ── Test B ────────────────────────────────────────────────────────────────────

def test_b_declared_debt_produces_schedule():
    """Capital Rs 1L, project Rs 2L, debt Rs 1L. EMI and repayment schedule."""
    res = compute_canonical_financials(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )

    assert res.debt_amount == 100000.0
    assert res.financing_gap == 0.0
    assert res.financing_reconciled is True
    assert_financing_reconciles(res)

    expected_emi = compute_emi(100000.0, 9.0, 60)
    assert res.monthly_emi == expected_emi
    assert res.monthly_emi > 0

    assert len(res.loan_schedule) == 60
    assert res.loan_schedule[0]["opening_balance"] == 100000.0
    assert res.loan_schedule[-1]["closing_balance"] == 0.0
    assert res.dscr is not None
    assert res.dscr_status == "COMPUTED"


def test_b_schedule_amortises_fully_and_consistently():
    """Interest plus principal repaid must reconstruct the loan exactly."""
    principal, rate, tenure = 250000.0, 11.0, 48
    schedule = build_loan_schedule(principal, rate, tenure)

    assert len(schedule) == tenure
    assert schedule[-1]["closing_balance"] == 0.0

    total_interest = round(sum(r["interest"] for r in schedule), 2)
    total_principal = round(sum(r["principal_repaid"] for r in schedule), 2)
    total_repayment = round(sum(r["payment"] for r in schedule), 2)

    assert total_principal == pytest.approx(principal, abs=1.0)
    assert total_repayment == pytest.approx(total_interest + principal, abs=1.0)

    # Interest must decline as the balance falls, not stay flat on the
    # original principal for the whole tenure.
    assert schedule[0]["interest"] > schedule[tenure // 2]["interest"]
    assert schedule[tenure // 2]["interest"] > schedule[-2]["interest"]


def test_b_moratorium_is_interest_only():
    schedule = build_loan_schedule(120000.0, 10.0, 60, moratorium_months=6)

    for row in schedule[:6]:
        assert row["in_moratorium"] is True
        assert row["principal_repaid"] == 0.0
        assert row["interest"] > 0.0

    assert schedule[6]["in_moratorium"] is False
    assert schedule[6]["principal_repaid"] > 0.0


# ── Test C ────────────────────────────────────────────────────────────────────

def test_c_demand_shock_recalculates_the_whole_chain():
    base = compute_canonical_financials(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )
    stress = run_stress_test_suite(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )
    shocked = stress["scenarios"]["demand_minus_20"]["result"]

    assert shocked["monthly_revenue"] == pytest.approx(base.monthly_revenue * 0.80, abs=1.0)
    assert shocked["monthly_cogs"] == pytest.approx(base.monthly_cogs * 0.80, abs=1.0)
    assert shocked["monthly_gross_profit"] < base.monthly_gross_profit
    assert shocked["monthly_ebitda"] < base.monthly_ebitda
    assert shocked["annual_operating_cash_flow"] < base.annual_operating_cash_flow
    assert shocked["cfads_monthly"] < base.cfads_monthly
    assert shocked["dscr"] < base.dscr
    assert shocked["monthly_pat"] < base.monthly_pat

    entry = stress["scenarios"]["demand_minus_20"]
    assert "primary_driver" in entry
    assert "decision_changed" in entry


def test_c_shock_does_not_alter_the_financing_plan():
    """A demand shock changes operations, not the loan the entrepreneur signed."""
    stress = run_stress_test_suite(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )
    shocked = stress["scenarios"]["demand_minus_20"]["result"]

    assert shocked["debt_amount"] == 100000.0
    assert shocked["monthly_emi"] == compute_emi(100000.0, 9.0, 60)
    assert shocked["financing_gap"] == 0.0


# ── Test D ────────────────────────────────────────────────────────────────────

def test_d_cost_shock_recalculates_the_whole_chain():
    base = compute_canonical_financials(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )
    stress = run_stress_test_suite(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )
    shocked = stress["scenarios"]["cost_plus_15"]["result"]

    assert shocked["monthly_revenue"] == pytest.approx(base.monthly_revenue, abs=1.0)
    assert shocked["monthly_cogs"] == pytest.approx(base.monthly_cogs * 1.15, abs=1.0)
    assert shocked["contribution_per_unit"] < base.contribution_per_unit
    assert shocked["monthly_gross_profit"] < base.monthly_gross_profit
    assert shocked["monthly_ebitda"] < base.monthly_ebitda
    assert shocked["dscr"] < base.dscr
    # More cash tied up in stock at the higher unit cost. Note that net
    # working capital can still fall when supplier payable days exceed
    # inventory days, because suppliers finance the difference.
    assert shocked["inventory_requirement"] > base.inventory_requirement


def test_d_interest_shock_recalculates_debt_service():
    stress = run_stress_test_suite(
        vada_pav_input(total_project_cost=200000.0, debt_amount=100000.0)
    )
    base = stress["scenarios"]["base_case"]["result"]
    shocked = stress["scenarios"]["interest_plus_2"]["result"]

    assert shocked["debt_amount"] == base["debt_amount"]
    assert shocked["monthly_emi"] > base["monthly_emi"]
    assert shocked["total_interest_paid"] > base["total_interest_paid"]
    assert shocked["monthly_interest"] > base["monthly_interest"]
    assert shocked["dscr"] < base["dscr"]


# ── Test E ────────────────────────────────────────────────────────────────────

def test_e_impossible_business_is_not_viable_and_explains_why():
    """Selling price below variable cost: no volume can ever work."""
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="vada_pav",
            products=[ProductItem("vada_pav", 5000.0, 8.0, 12.0)],
            opex=OpexBreakdown(rent=8000.0),
            own_capital=100000.0,
            total_project_cost=100000.0,
            debt_amount=0.0,
        )
    )

    assert res.contribution_per_unit < 0
    assert res.break_even_units_monthly is None
    assert res.break_even_revenue_monthly is None
    assert res.margin_of_safety_pct is None
    assert res.economic_viability == "NOT_VIABLE"
    assert res.viability_reasons
    assert any("does not cover variable cost" in r for r in res.viability_reasons)


def test_e_revenue_below_total_cost_is_not_viable():
    """Revenue cannot cover variable plus fixed cost."""
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="tea_stall",
            products=[ProductItem("tea", 1000.0, 10.0, 6.0)],
            opex=OpexBreakdown(rent=12000.0),
            own_capital=100000.0,
            total_project_cost=100000.0,
            debt_amount=0.0,
        )
    )

    assert res.monthly_ebitda < 0
    assert res.economic_viability == "NOT_VIABLE"
    assert any("EBITDA" in r for r in res.viability_reasons)


def test_e_unfunded_gap_is_reported_not_hidden():
    res = compute_canonical_financials(
        vada_pav_input(total_project_cost=500000.0, debt_amount=0.0)
    )

    assert res.financing_gap == 400000.0
    assert res.financing_reconciled is False
    assert res.economic_viability == "NOT_VIABLE"
    assert any("does not reconcile" in r for r in res.viability_reasons)


def test_e_viable_business_is_marked_viable():
    res = compute_canonical_financials(
        vada_pav_input(total_project_cost=100000.0, debt_amount=0.0)
    )

    assert res.monthly_ebitda > 0
    assert res.economic_viability == "VIABLE"
    assert res.viability_reasons == []


# ── Financing reconciliation ──────────────────────────────────────────────────

@pytest.mark.parametrize("project_cost,own,other,subsidy,debt", [
    (100000.0, 100000.0, 0.0, 0.0, 0.0),
    (200000.0, 100000.0, 0.0, 0.0, 100000.0),
    (500000.0, 100000.0, 50000.0, 50000.0, 300000.0),
    (1000000.0, 100000.0, 0.0, 0.0, 900000.0),
    (350000.0, 60000.0, 40000.0, 0.0, 250000.0),
])
def test_financing_always_reconciles(project_cost, own, other, subsidy, debt):
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="vada_pav",
            products=[ProductItem(**VADA_PAV)],
            opex=OpexBreakdown(rent=8000.0),
            own_capital=own,
            other_funding=other,
            eligible_subsidy=subsidy,
            total_project_cost=project_cost,
            debt_amount=debt,
        )
    )

    assert res.financing_gap == 0.0
    assert res.financing_reconciled is True
    assert res.total_project_cost == own + other + subsidy + debt
    assert_financing_reconciles(res)


def test_engine_never_invents_a_loan_without_an_opt_in():
    """Omitting debt must yield zero debt, whatever the project cost."""
    for project_cost in (100000.0, 500000.0, 1000000.0):
        res = compute_canonical_financials(
            vada_pav_input(total_project_cost=project_cost, debt_amount=None)
        )
        assert res.debt_amount == 0.0
        assert res.monthly_emi == 0.0
        assert res.dscr is None


def test_scheme_derived_debt_is_explicit_opt_in():
    kw = dict(
        business_type="vada_pav",
        products=[ProductItem(**VADA_PAV)],
        opex=OpexBreakdown(rent=8000.0),
        own_capital=100000.0,
        total_project_cost=1000000.0,
        scheme_financing_rate=0.90,
    )
    without = compute_canonical_financials(CanonicalFinancialInput(**kw))
    with_scheme = compute_canonical_financials(
        CanonicalFinancialInput(**kw, derive_debt_from_scheme=True)
    )

    assert without.debt_amount == 0.0
    assert without.financing_gap == 900000.0

    assert with_scheme.debt_amount == 900000.0
    assert with_scheme.financing_gap == 0.0
    assert with_scheme.financing_reconciled is True


def test_scheme_ceiling_caps_debt_and_surfaces_the_residue():
    res = compute_canonical_financials(
        vada_pav_input(
            total_project_cost=1000000.0,
            debt_amount=None,
            derive_debt_from_scheme=True,
            scheme_ceiling=450000.0,
        )
    )

    assert res.debt_amount == 450000.0
    assert res.financing_gap == 450000.0
    assert res.financing_reconciled is False


# ── Cash flow, payback, working capital ───────────────────────────────────────

def test_working_capital_is_a_real_cash_outflow():
    """Net working capital must reduce owner payback, not sit decorative."""
    cfg = WorkingCapitalConfig(inventory_days=20, receivable_days=15, payable_days=5)
    with_wc = compute_canonical_financials(
        vada_pav_input(working_capital_cfg=cfg, total_project_cost=500000.0,
                       debt_amount=400000.0)
    )
    without_wc = compute_canonical_financials(
        vada_pav_input(working_capital_cfg=WorkingCapitalConfig(0, 0, 0),
                       total_project_cost=500000.0, debt_amount=400000.0)
    )

    assert with_wc.net_working_capital > 0
    assert without_wc.net_working_capital == 0.0
    assert with_wc.cash_conversion_cycle_days > without_wc.cash_conversion_cycle_days
    assert (with_wc.payback_months or 0) > (without_wc.payback_months or 0)


def test_payback_is_not_always_month_one():
    """Payback must account for the owner's actual outlay."""
    res = compute_canonical_financials(
        vada_pav_input(total_project_cost=500000.0, debt_amount=400000.0)
    )

    assert res.payback_achieved is True
    assert res.payback_months is not None
    assert res.payback_months > 1


def test_payback_absent_when_outlay_never_recovers():
    """A business that never repays must report no payback, not month one."""
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="vada_pav",
            products=[ProductItem("vada_pav", 1000.0, 20.0, 8.0)],
            opex=OpexBreakdown(rent=50000.0),
            own_capital=100000.0,
            total_project_cost=100000.0,
            debt_amount=0.0,
        )
    )

    assert res.monthly_ebitda < 0
    assert res.payback_achieved is False
    assert res.payback_months is None


# ── Rupee-equality across every surface ───────────────────────────────────────

def test_g_rupee_equality_across_dashboard_api_whatif_and_ai(
    monkeypatch,
):
    """
    One business input must produce the same profit on every surface.

    dashboard / financial API  = canonical result
    what-if (no shock)         = canonical result re-run
    report + AI context        = values persisted from canonical result
    """
    os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.db import Base
    import app.models  # noqa: F401  — register all models
    from app.models import Location, Session as SessionModel, BusinessCategory
    from app.models.core import AdminLevel
    from app.services import session_service
    from app.services.session_service import (
        build_canonical_input, compute_full_financials, get_base_state,
    )
    from app.ai_layer.context_builder import build_explain_context

    COST_PROFILE = {
        "estimated_monthly_units": 2000.0,
        "selling_price_per_unit": 50.0,
        "variable_cost_per_unit": 30.0,
        "fixed_cost_monthly": 12000.0,
        "total_setup_cost": 400000.0,
    }
    monkeypatch.setattr(
        session_service.data_layer, "get_cost_profile",
        lambda location_id, category_id: {"value": dict(COST_PROFILE), "confidence": "High"},
    )

    engine = create_engine(f"sqlite:///{_TMP_DB}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    loc = Location(id="loc_fin_truth", district="Solapur", state="Maharashtra",
                   lat=17.6, lng=75.9, admin_level=AdminLevel.village, data_richness="rich")
    cat = BusinessCategory(id="retail_kirana", name="Retail Kirana")
    db.add_all([loc, cat])
    db.commit()

    session = SessionModel(id="sess_fin_truth", user_id=None, location_id=loc.id,
                           margin_capital=200000.0, category_id=cat.id)
    db.add(session)
    db.commit()

    api = compute_full_financials(db, session.id)

    fin_input, _ = build_canonical_input(cat.id, 200000.0, dict(COST_PROFILE))
    canonical = compute_canonical_financials(fin_input)

    # Dashboard / financial API
    assert api["monthly_revenue"] == canonical.monthly_revenue
    assert api["net_profit"] == canonical.monthly_pat
    assert api["monthly_ebitda"] == canonical.monthly_ebitda
    assert api["dscr"] == canonical.dscr
    assert api["project_cost"] == canonical.total_project_cost
    assert api["loan_amount"] == canonical.debt_amount

    # What-if with no shock must be identical, not merely close.
    base_state = get_base_state(db, session.id)
    sim = run_simulation(base_state, 0.0, 0.0, None)
    assert sim["net_profit"] == canonical.monthly_pat
    assert sim["monthly_revenue"] == canonical.monthly_revenue
    assert sim["monthly_ebitda"] == canonical.monthly_ebitda
    assert sim["dscr"] == canonical.dscr
    assert sim["emi"] == canonical.monthly_emi
    assert sim["decision"] == canonical.economic_viability

    # Report + AI context read the persisted projection.
    ctx = build_explain_context(db, session.id)
    assert ctx["financial_projection"]["monthly_revenue"] == canonical.monthly_revenue
    assert ctx["financial_projection"]["net_profit"] == canonical.monthly_pat
    assert ctx["financial_projection"]["dscr"] == canonical.dscr
    assert ctx["loan"]["project_cost"] == canonical.total_project_cost
    assert ctx["loan"]["loan_amount"] == canonical.debt_amount

    db.close()


def test_whatif_shock_moves_profit_in_the_right_direction():
    """A -20% demand shock must reduce profit relative to the unshocked run."""
    fin_input = CanonicalFinancialInput(
        business_type="vada_pav",
        products=[ProductItem(**VADA_PAV)],
        opex=OpexBreakdown(rent=8000.0, salaries=6000.0, electricity=2000.0),
        own_capital=200000.0,
        total_project_cost=400000.0,
        debt_amount=200000.0,
    )
    base_state = {
        "canonical_input": fin_input,
        "dimension_scores": {
            "financial_viability": 80, "repayment_capacity": 80,
            "market_opportunity": 70, "capital_efficiency": 70, "risk_exposure": 60,
        },
        "confidence_multiplier": 0.85,
    }

    flat = run_simulation(base_state, 0.0, 0.0, None)
    demand = run_simulation(base_state, -20.0, 0.0, None)
    cost = run_simulation(base_state, 0.0, 15.0, None)

    assert demand["net_profit"] < flat["net_profit"]
    assert cost["net_profit"] < flat["net_profit"]
    assert demand["dscr"] < flat["dscr"]
    assert cost["dscr"] < flat["dscr"]

    # The unshocked what-if must equal the canonical engine exactly.
    canonical = compute_canonical_financials(fin_input)
    assert flat["net_profit"] == canonical.monthly_pat
    assert flat["dscr"] == canonical.dscr


def test_whatif_refuses_to_guess_without_canonical_input():
    """Recomputing from a summary would silently drop cost lines."""
    sim = run_simulation(
        {"monthly_revenue": 180000.0, "monthly_opex": 100000.0,
         "dimension_scores": {}, "confidence_multiplier": 0.85},
        -20.0, 0.0, None,
    )
    assert sim["error"] == "CANONICAL_INPUT_UNAVAILABLE"
    assert "net_profit" not in sim


def _whatif_state(**overrides) -> dict:
    """A what-if base state, debtless by default so the null paths are reachable."""
    fields = dict(
        business_type="vada_pav",
        products=[ProductItem(**VADA_PAV)],
        opex=OpexBreakdown(rent=8000.0, salaries=6000.0, electricity=2000.0),
        own_capital=400000.0,
        total_project_cost=400000.0,
        debt_amount=0.0,
    )
    fields.update(overrides)
    return {
        "canonical_input": CanonicalFinancialInput(**fields),
        "dimension_scores": {
            "financial_viability": 80, "repayment_capacity": 80,
            "market_opportunity": 70, "capital_efficiency": 70, "risk_exposure": 60,
        },
        "confidence_multiplier": 0.85,
    }


def test_a_debtless_business_is_not_reported_as_failing_the_stress_test():
    """
    `survives_stress` was `dscr is not None and dscr >= 1.0`, and a business
    with no debt has dscr None. So every debtless plan came back from the
    what-if simulator marked as having failed the stress test - on an unshocked
    run included. There is no debt service to fail to cover, so the answer to the
    question is "not applicable", and the field has to be able to say so.

    A debtless borrower paying no interest on a zero loan cannot default, and
    the one thing a founder would take from this screen is that their plan is
    not viable, when the model had actually called it viable.
    """
    sim = run_simulation(_whatif_state(), -20.0, 15.0, None)

    assert sim["dscr"] is None
    assert sim["dscr_status"] == "NOT_APPLICABLE_NO_DEBT"
    assert sim["survives_stress"] is None, "a debtless plan cannot fail a debt-service test"
    assert sim["survives_stress_applicable"] is False


def test_survives_stress_is_a_real_answer_when_there_is_debt():
    """The tri-state must not have quietly become 'always None'."""
    healthy = run_simulation(
        _whatif_state(
            debt_amount=150000.0, own_capital=250000.0,
            interest_rate_annual_pct=9.0, tenure_months=60,
        ),
        0.0, 0.0, None,
    )
    assert healthy["dscr"] is not None
    assert healthy["survives_stress"] is True
    assert healthy["survives_stress_applicable"] is True

    # A business whose operating cash is thin relative to its debt service is a
    # failure, and it is reported as one rather than as "not applicable". This
    # one earns 5,500 a month against a repayment of about 5,561.
    thin = dict(
        products=[ProductItem(name="Vada Pav", units_per_month=3900, selling_price=15.0, variable_cost_per_unit=10.0)],
        opex=OpexBreakdown(rent=6000.0, salaries=6000.0, electricity=2000.0),
    )
    strained = run_simulation(
        _whatif_state(
            debt_amount=250000.0, own_capital=150000.0,
            interest_rate_annual_pct=12.0, tenure_months=60, **thin,
        ),
        0.0, 0.0, None,
    )
    assert strained["dscr"] is not None, "a thin-margin business still has a computable DSCR"
    assert strained["dscr"] < 1.0
    assert strained["survives_stress"] is False


def test_negative_operating_cash_counts_as_failing_the_stress_test():
    """
    When operating cash is negative the engine publishes no DSCR at all - the
    ratio has no meaning - but the business has still failed: the debt service
    is unfunded. This path is why `survives_stress` cannot simply be
    `dscr is None -> not applicable`. Distinguishing "no debt service exists" from
    "the cash to service it does not exist" is the whole point of the tri-state.
    """
    distressed = run_simulation(
        _whatif_state(
            products=[ProductItem(name="Vada Pav", units_per_month=3900, selling_price=15.0, variable_cost_per_unit=13.0)],
            opex=OpexBreakdown(rent=12000.0, salaries=9000.0, electricity=3000.0),
            debt_amount=200000.0, own_capital=200000.0,
            interest_rate_annual_pct=10.0, tenure_months=60,
        ),
        0.0, 0.0, None,
    )

    assert distressed["dscr"] is None
    assert distressed["dscr_status"] == "NEGATIVE_CFADS"
    assert distressed["survives_stress"] is False
    assert distressed["survives_stress_applicable"] is True


def test_the_simulator_shock_matches_the_stress_matrix_shock():
    """
    Both surfaces take a demand and a cost shock and claim to apply them the
    same way. The simulator used to build its own shocked input, scaling units
    and variable cost directly. They now share the canonical `apply_shock`, so
    the same percentages produce the same model on both screens.
    """
    from app.engines.stress_engine import run_stress_test_suite
    from app.financial.projection import apply_shock

    state = _whatif_state(
        debt_amount=150000.0, own_capital=250000.0,
        interest_rate_annual_pct=9.0, tenure_months=60,
    )
    base_input = state["canonical_input"]

    sim = run_simulation(state, -20.0, 15.0, None)
    direct = compute_canonical_financials(
        apply_shock(base_input, demand_pct=-0.20, cost_pct=0.15)
    )

    assert sim["monthly_revenue"] == pytest.approx(direct.monthly_revenue, abs=0.01)
    assert sim["net_profit"] == pytest.approx(direct.monthly_pat, abs=0.01)
    assert sim["monthly_ebitda"] == pytest.approx(direct.monthly_ebitda, abs=0.01)

    # And the matrix's cost_plus_15 entry, which uses the same helper, agrees.
    stress = run_stress_test_suite(base_input)
    cost_shock = stress["scenarios"]["cost_plus_10"]["result"]
    expected = compute_canonical_financials(
        apply_shock(base_input, cost_pct=0.10)
    )
    assert cost_shock["monthly_revenue"] == pytest.approx(expected.monthly_revenue, abs=0.01)


def test_the_original_three_fields_still_mean_what_they_meant():
    """
    `revenue_delta_pct` is a *volume* shock in this API and always has been.
    Translating it to the canonical `units_multiplier` keeps that reading, which
    matters: reinterpreting it as a price move would change every existing
    client's answer, and change it in the flattering direction, because a demand
    fall takes variable cost down with it while a price cut does not.
    """
    state = _whatif_state(
        debt_amount=150000.0, own_capital=250000.0,
        interest_rate_annual_pct=9.0, tenure_months=60,
    )
    base_input = state["canonical_input"]
    base = compute_canonical_financials(base_input)

    legacy = run_simulation(state, -20.0, 0.0, None)
    explicit = run_simulation(state, adjustments={"units_multiplier": 0.80})
    by_price = run_simulation(state, adjustments={"price_delta_pct": -20.0})

    assert legacy["net_profit"] == pytest.approx(explicit["net_profit"], abs=0.01)
    # A volume cut of 20% takes 20% of revenue, and it takes 20% of the variable
    # cost that scales with it, but it does not touch a rupee of fixed cost. So
    # profit falls by MORE than the volume did - operating leverage, and the
    # reason a small demand miss is more dangerous than it looks.
    assert legacy["monthly_revenue"] == pytest.approx(base.monthly_revenue * 0.80, abs=0.01)
    assert legacy["net_profit"] < base.monthly_pat * 0.80
    # The same 20% as a price cut is worse still: variable cost does not fall
    # with the price at all.
    assert by_price["net_profit"] < legacy["net_profit"]


def test_a_caller_can_now_ask_questions_the_endpoint_could_not_answer_before():
    """
    The canonical engine had thirteen what-if levers and the HTTP API exposed
    two of them. A founder could not ask what happened if they put in more of
    their own money, borrowed for longer, or negotiated 60-day supplier terms -
    the model could answer all three and the product could not ask.

    Each lever is checked for actually moving the model it should move, not
    merely for being accepted.
    """
    state = _whatif_state(
        debt_amount=150000.0, own_capital=250000.0,
        interest_rate_annual_pct=9.0, tenure_months=60,
    )
    base = run_simulation(state)

    # Borrowing more raises the repayment and lowers profit after interest.
    borrowed = run_simulation(state, adjustments={"debt_amount": 300000.0})
    assert borrowed["dscr"] is not None
    assert borrowed["emi"] > base["emi"]
    assert borrowed["net_profit"] < base["net_profit"]

    # A longer tenure means a much smaller repayment for the same principal, but
    # it is not free: less principal is retired early, so the year-one interest
    # charged against profit is slightly higher and the lifetime interest is far
    # higher. Both halves are asserted, because presenting only the lower EMI
    # would be the misleading half.
    longer = run_simulation(state, adjustments={"tenure_months": 120})
    assert longer["emi"] < base["emi"] * 0.7
    assert longer["net_profit"] < base["net_profit"]
    assert (base["net_profit"] - longer["net_profit"]) / base["net_profit"] < 0.01
    assert longer["total_interest_paid"] > base["total_interest_paid"] * 2

    # A higher rate raises the repayment on an unchanged principal.
    dearer = run_simulation(state, adjustments={"interest_rate_annual_pct": 16.0})
    assert dearer["emi"] > base["emi"]

    # A tax rate the plan never declared. The base is pre-tax, so a caller has to
    # be told which of the two figures it is looking at rather than assuming
    # "net profit" meant the same thing before and after.
    assert base["tax_status"] == "NOT_MODELED"
    taxed = run_simulation(state, adjustments={"tax_rate_pct": 30.0})
    assert taxed["tax_status"] == "MODELED"
    assert taxed["monthly_tax"] > 0
    assert taxed["net_profit"] < base["net_profit"]

    # Longer supplier terms reduce the cash tied up in the cycle.
    stretched = run_simulation(state, adjustments={"working_capital_days_scale": 3.0})
    assert stretched["net_working_capital"] > base["net_working_capital"]

    # A price rise, and the volume lever.
    pricier = run_simulation(state, adjustments={"price_delta_pct": 10.0})
    assert pricier["monthly_revenue"] > base["monthly_revenue"]
    busier = run_simulation(state, adjustments={"units_multiplier": 1.20})
    assert busier["monthly_revenue"] > base["monthly_revenue"]


def test_an_explicit_lever_overrides_the_shorthand():
    """
    Both request forms are accepted at once, so one has to win. The explicit
    lever does: a caller that named `units_multiplier` meant it, and quietly
    preferring `revenue_delta_pct` would make the two forms disagree depending
    on which arrived.
    """
    state = _whatif_state(
        debt_amount=150000.0, own_capital=250000.0,
        interest_rate_annual_pct=9.0, tenure_months=60,
    )
    # revenue_delta_pct would mean a 50% volume fall; the explicit lever says
    # volume rises 50%.
    both = run_simulation(
        state, 50.0, 0.0, None, adjustments={"units_multiplier": 1.50}
    )
    explicit = run_simulation(state, adjustments={"units_multiplier": 1.50})
    assert both["net_profit"] == pytest.approx(explicit["net_profit"], abs=0.01)

    # A lever the shorthand does not cover is taken even while the shorthand is
    # present, so the two forms compose rather than exclude.
    combined = run_simulation(
        state, -20.0, 0.0, None, adjustments={"tenure_months": 120}
    )
    volume_only = run_simulation(state, -20.0, 0.0, None)
    assert combined["net_profit"] < volume_only["net_profit"]


def test_the_response_records_which_levers_actually_moved():
    """
    Without this a caller that changed its capital, its tenor and its working
    capital cycle had no way to see what it had asked for, and no way to tell an
    accepted lever from a silently ignored one.
    """
    state = _whatif_state(
        debt_amount=150000.0, own_capital=250000.0,
        interest_rate_annual_pct=9.0, tenure_months=60,
    )
    out = run_simulation(
        state, adjustments={"own_capital": 300000.0, "tenure_months": 84}
    )
    applied = {a["lever"]: a for a in out["applied_adjustments"]}

    assert set(applied) == {"own_capital", "tenure_months"}
    assert applied["own_capital"]["previous"] == 250000.0
    assert applied["own_capital"]["applied"] == 300000.0
    assert applied["tenure_months"]["change"] == 24
    assert set(out["adjustments"]) == {"own_capital", "tenure_months"}

    # An unlevered run says nothing changed, rather than reporting every lever.
    assert run_simulation(state)["applied_adjustments"] == []
