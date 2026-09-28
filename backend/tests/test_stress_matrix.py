"""
Stress matrix: full coverage, shock direction, and driver attribution.

The existing suite only proved three scenarios worked. These tests pin the
matrix the specification actually requires, and check the properties that make
a stress test meaningful rather than decorative.
"""
import pytest

from app.engines.stress_engine import run_stress_test_suite
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)
from app.financial.projection import STRESS_SCENARIOS

# The suite this file exercises is a presentation layer over the canonical
# matrix, so the expected scenario set is read from that matrix rather than
# restated. It used to be a hardcoded literal here, which is how the two drifted
# apart in the first place: the canonical matrix grew a price shock and this
# copy of the list did not, so the suite quietly stopped covering a scenario the
# product shipped. Deriving it means adding a scenario to the matrix updates
# these expectations instead of requiring someone to remember.
REQUIRED_SCENARIOS = {s.key for s in STRESS_SCENARIOS}

#: The matrix must keep covering the product's required shocks. This is the one
#: list worth pinning by hand, because it is a product requirement rather than
#: an implementation detail.
_MUST_COVER = {
    "demand_minus_10",
    "demand_minus_20",
    "cost_plus_10",
    "cost_plus_15",
    "interest_plus_2",
    "combined_severe",
}
assert _MUST_COVER <= REQUIRED_SCENARIOS, (
    f"canonical stress matrix dropped a required shock: {_MUST_COVER - REQUIRED_SCENARIOS}"
)


def viable_input(**overrides) -> CanonicalFinancialInput:
    """A business that comfortably covers its debt service."""
    base = dict(
        business_type="test_stress",
        products=[
            ProductItem(name="unit", units_per_month=1000, selling_price=20, variable_cost_per_unit=8)
        ],
        opex=OpexBreakdown(rent=2000, salaries=1500, electricity=300),
        own_capital=80000,
        total_project_cost=200000,
        debt_amount=120000,
        interest_rate_annual_pct=9.0,
        tenure_months=60,
        tax_rate_pct=25.0,
    )
    base.update(overrides)
    return CanonicalFinancialInput(**base)


def lossmaking_input(**overrides) -> CanonicalFinancialInput:
    """A business whose operating cash is negative, so DSCR has no meaning."""
    base = dict(
        business_type="test_stress_loss",
        products=[
            ProductItem(name="unit", units_per_month=200, selling_price=20, variable_cost_per_unit=15)
        ],
        opex=OpexBreakdown(rent=1500, salaries=1200, electricity=200),
        own_capital=50000,
        total_project_cost=200000,
        debt_amount=150000,
        interest_rate_annual_pct=11.0,
        tenure_months=48,
        tax_rate_pct=25.0,
    )
    base.update(overrides)
    return CanonicalFinancialInput(**base)


# ── Matrix coverage ──────────────────────────────────────────────────────────

def test_e_matrix_contains_every_required_shock():
    """Demand -10/-20, cost +10/+15, rate +2, and a combined case."""
    out = run_stress_test_suite(viable_input())
    assert REQUIRED_SCENARIOS <= set(out["scenarios"])
    assert out["matrix"]["includes_combined"] is True


def test_e_matrix_metadata_is_published():
    out = run_stress_test_suite(viable_input())
    m = out["matrix"]
    assert m["demand_shocks_pct"] == [-10, -20]
    assert m["cost_shocks_pct"] == [10, 15]
    assert m["interest_shock_points"] == 2.0


def test_e_every_scenario_reports_decision_and_driver():
    """A stress test that does not say what changed is just a number."""
    out = run_stress_test_suite(viable_input())
    for key, scen in out["scenarios"].items():
        assert "decision" in scen, key
        assert "decision_changed" in scen, key
        assert "primary_driver" in scen, key
        assert "breaches" in scen, key
        assert scen["primary_driver"].strip(), key


# ── Shock direction: shocks must move the model the correct way ──────────────

def test_e_demand_shock_reduces_revenue_not_cost():
    base = compute_canonical_financials(viable_input())
    out = run_stress_test_suite(viable_input())
    for key, pct in (("demand_minus_10", 0.90), ("demand_minus_20", 0.80)):
        r = out["scenarios"][key]["result"]
        # Volume-driven: revenue falls with units, and unit economics are unchanged.
        assert r["monthly_revenue"] == pytest.approx(base.monthly_revenue * pct, abs=1.0)
        assert r["contribution_per_unit"] == pytest.approx(base.contribution_per_unit, abs=0.01)
        # A demand fall must not reduce debt service: the loan was signed already.
        assert r["monthly_emi"] == pytest.approx(base.monthly_emi, abs=0.01)


def test_e_cost_shock_raises_cogs_not_revenue():
    base = compute_canonical_financials(viable_input())
    out = run_stress_test_suite(viable_input())
    for key, mult in (("cost_plus_10", 1.10), ("cost_plus_15", 1.15)):
        r = out["scenarios"][key]["result"]
        # Price-driven: units and revenue hold, unit cost rises.
        assert r["monthly_revenue"] == pytest.approx(base.monthly_revenue, abs=1.0)
        assert r["monthly_cogs"] == pytest.approx(base.monthly_cogs * mult, abs=1.0)
        assert r["contribution_per_unit"] < base.contribution_per_unit
        assert r["monthly_emi"] == pytest.approx(base.monthly_emi, abs=0.01)


def test_e_interest_shock_raises_debt_service_only():
    base = compute_canonical_financials(viable_input())
    out = run_stress_test_suite(viable_input())
    r = out["scenarios"]["interest_plus_2"]["result"]
    assert r["monthly_revenue"] == pytest.approx(base.monthly_revenue, abs=1.0)
    assert r["monthly_cogs"] == pytest.approx(base.monthly_cogs, abs=1.0)
    assert r["monthly_emi"] > base.monthly_emi
    assert r["total_interest_paid"] > base.total_interest_paid
    assert r["dscr"] < base.dscr


def test_e_combined_shock_is_worse_than_any_single_shock():
    """The whole point of a combined case: the effects compound."""
    out = run_stress_test_suite(viable_input())
    combined = out["scenarios"]["combined_severe"]["result"]
    worst_single = min(
        (
            s["result"]
            for k, s in out["scenarios"].items()
            if k not in ("base_case", "combined_severe")
        ),
        key=lambda r: r["monthly_ebitda"],
    )
    assert combined["monthly_ebitda"] < worst_single["monthly_ebitda"]
    assert combined["dscr"] < worst_single["dscr"]


def test_e_shocks_never_mutate_the_base_input():
    """Re-running the suite must give an identical result: no in-place leakage."""
    inp = viable_input()
    first = run_stress_test_suite(inp)
    second = run_stress_test_suite(inp)
    assert first["scenarios"]["base_case"]["result"] == second["scenarios"]["base_case"]["result"]
    assert inp.products[0].units_per_month == 1000
    assert inp.interest_rate_annual_pct == 9.0


# ── The negative-CFADS case ──────────────────────────────────────────────────

def test_f_negative_cash_reports_no_dscr_rather_than_a_negative_ratio():
    """
    A negative DSCR is directionally wrong: a higher EMI pushes a negative
    ratio toward zero, so a rate hike would appear to improve coverage.
    """
    result = compute_canonical_financials(lossmaking_input())
    assert result.dscr is None
    assert result.dscr_status == "NEGATIVE_CFADS"
    assert result.economic_viability == "NOT_VIABLE"
    # The shortfall is stated in rupees instead.
    assert any("negative by" in r for r in result.viability_reasons)


def test_f_rate_hike_never_improves_reported_coverage():
    """Guards the specific artifact that motivated the guard above."""
    out = run_stress_test_suite(lossmaking_input())
    base_dscr = out["scenarios"]["base_case"]["result"]["dscr"]
    shocked_dscr = out["scenarios"]["interest_plus_2"]["result"]["dscr"]
    assert base_dscr is None
    assert shocked_dscr is None
    # And the case is still correctly flagged as a breach.
    assert out["scenarios"]["interest_plus_2"]["dscr_breached"] is True
    assert out["resilience"]["survives_all"] is False


def test_f_negative_cash_still_reports_the_breach():
    out = run_stress_test_suite(lossmaking_input())
    for key in REQUIRED_SCENARIOS:
        assert out["scenarios"][key]["dscr_breached"] is True, key
    assert out["resilience"]["scenarios_failed"]


# ── Resilience summary ───────────────────────────────────────────────────────

def test_g_resilience_summary_matches_the_scenarios():
    out = run_stress_test_suite(viable_input())
    res = out["resilience"]
    assert res["survives_all"] == (not res["scenarios_failed"])
    assert set(res["scenarios_survived"]) | set(res["scenarios_failed"]) == REQUIRED_SCENARIOS
    assert not (set(res["scenarios_survived"]) & set(res["scenarios_failed"]))


def test_g_worst_case_dscr_is_the_minimum_across_scenarios():
    out = run_stress_test_suite(viable_input())
    dscrs = [
        s["result"]["dscr"]
        for s in out["scenarios"].values()
        if s["result"]["dscr"] is not None
    ]
    assert out["resilience"]["worst_case_dscr"] == min(dscrs)


def test_g_debtless_business_reports_no_breach_possible():
    """No debt means no DSCR breach is possible, and that is stated, not hidden."""
    out = run_stress_test_suite(
        viable_input(debt_amount=0, own_capital=200000, total_project_cost=200000)
    )
    base = out["scenarios"]["base_case"]["result"]
    assert base["dscr"] is None
    assert base["dscr_status"] == "NOT_APPLICABLE_NO_DEBT"
    assert out["resilience"]["worst_case_dscr"] is None
    assert "No debt service applies" in out["resilience"]["summary"]


# ── The two stress surfaces must be the same stress test ─────────────────────


def test_the_suite_and_the_canonical_matrix_agree_shock_for_shock():
    """
    There are two places a user can be shown a stressed number: the
    `stress_scenarios` block the canonical engine attaches to every result, and
    this suite. They used to be separate implementations with separate shock
    lists, and the `combined_severe` entries had already diverged - the
    canonical one also cut selling price 10% while this one did not. Both
    published a `monthly_ebitda` under the same name, so the two screens
    disagreed about the worst case for the same business and neither said which
    was the approximation.

    This compares them on every shared scenario. It is the test that would have
    caught the drift, and it is what keeps the two presentations from becoming
    two opinions again.
    """
    inp = viable_input()
    suite = run_stress_test_suite(inp)
    base = compute_canonical_financials(inp)
    canonical = base.stress_scenarios

    shared = set(suite["scenarios"]) & set(canonical) - {"base_case"}
    assert shared, "the two surfaces share no scenario keys"

    for key in sorted(shared):
        presented = suite["scenarios"][key]
        modelled = canonical[key]

        # The shock itself, not just the outcome: two different shocks can land
        # on a similar EBITDA by coincidence, and agreeing on the outcome while
        # disagreeing on the cause is the bug all over again.
        assert presented["applied_shocks"] == modelled["applied_shocks"], key
        assert presented["severity"] == modelled["severity"], key

        result = presented["result"]
        assert result["monthly_ebitda"] == pytest.approx(
            modelled["monthly_ebitda"], abs=0.01
        ), key
        assert result["monthly_pat"] == pytest.approx(modelled["monthly_pat"], abs=0.01), key
        assert result["monthly_revenue"] == pytest.approx(
            modelled["monthly_revenue"], abs=0.01
        ), key
        assert result["dscr"] == modelled["dscr"], key
        assert result["dscr_status"] == modelled["dscr_status"], key
        assert result["monthly_emi"] == pytest.approx(modelled["monthly_emi"], abs=0.01), key
        assert result["economic_viability"] == modelled["economic_viability"], key
        assert result["payback_months"] == modelled["payback_months"], key


def test_the_combined_case_really_is_worse_than_any_single_shock():
    """
    The combined entry exists to be the worst case. That only holds if every
    shock pushes in the same direction: a scenario described as combined-severe
    that scores better than one of its own components means a shock is being
    absorbed rather than compounding, and the "worst case" is not one.
    """
    inp = viable_input()
    out = run_stress_test_suite(inp)
    combined = out["scenarios"]["combined_severe"]["result"]["monthly_ebitda"]

    for key in REQUIRED_SCENARIOS - {"combined_severe"}:
        single = out["scenarios"][key]["result"]["monthly_ebitda"]
        assert combined <= single, (
            f"combined_severe ({combined}) is better than {key} ({single}); "
            f"the shocks are not compounding"
        )
