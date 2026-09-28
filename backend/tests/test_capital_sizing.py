"""
Capital sizing and return calculations.

Regression guard for the defect where a session's revenue was a hardcoded
fallback (Rs 10,000/month) while fixed costs were derived from the user's own
margin capital. That combination reported a loss for every business and made
profit fall as capital rose.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.session_service import build_canonical_input
from app.financial.canonical_engine import (
    CanonicalFinancialInput, compute_canonical_financials,
    resolve_financing,
)
from app.templates.business_templates import TEMPLATES, get_business_template

CATEGORIES = sorted(TEMPLATES)


def _run(category, margin, cost=None):
    fin_input, derived = build_canonical_input(category, margin, cost)
    return compute_canonical_financials(fin_input), derived


# --- The reported defect ---------------------------------------------------

def test_revenue_does_not_stay_flat_while_costs_grow():
    """
    The old fallback pinned revenue at Rs 10,000/month for every session and
    set fixed costs to 10% of the user's own margin, so a larger deposit
    produced a larger loss.
    """
    small, _ = _run("retail_kirana", 50_000)
    large, _ = _run("retail_kirana", 500_000)

    assert large.monthly_revenue > small.monthly_revenue * 5
    assert large.monthly_pat > small.monthly_pat


def test_more_capital_never_reduces_profit():
    for category in CATEGORIES:
        previous = None
        for margin in (25_000, 100_000, 400_000, 1_000_000):
            result, _ = _run(category, margin)
            if previous is not None:
                assert result.monthly_pat >= previous, (
                    f"{category}: profit fell when capital rose from "
                    f"{margin // 4:,} to {margin:,}"
                )
            previous = result.monthly_pat


def test_a_plain_capital_deposit_is_not_guaranteed_to_be_a_loss():
    """No category should be structurally unprofitable at a sane deposit."""
    for category in CATEGORIES:
        result, _ = _run(category, 200_000)
        assert result.monthly_pat > 0, f"{category} is loss-making at Rs 2L"
        assert result.economic_viability == "VIABLE", (
            f"{category}: {result.viability_reasons}"
        )


# --- Capital must size the business ---------------------------------------

def test_project_cost_scales_with_the_declared_contribution_share():
    for category in CATEGORIES:
        tmpl = get_business_template(category)
        margin = 120_000.0
        fin_input, derived = build_canonical_input(category, margin, None)
        expected = margin / (tmpl.promoter_contribution_pct / 100.0)
        assert fin_input.total_project_cost == pytest.approx(expected)
        assert derived["has_setup_cost"] is False


def test_revenue_follows_the_declared_capital_turnover_ratio():
    for category in CATEGORIES:
        tmpl = get_business_template(category)
        margin = 250_000.0
        result, derived = build_canonical_input(category, margin, None)
        result = compute_canonical_financials(result)
        expected_annual = result.total_project_cost * tmpl.annual_revenue_per_invested_rupee
        assert result.annual_revenue == pytest.approx(expected_annual, rel=0.01)
        assert derived["capital_turnover_ratio"] == tmpl.annual_revenue_per_invested_rupee


def test_units_are_reported_in_real_transactions():
    for category in CATEGORIES:
        tmpl = get_business_template(category)
        result, _ = _run(category, 200_000)
        expected_units = result.monthly_revenue / tmpl.typical_unit_value
        assert result.break_even_units_monthly is not None
        # Volumes must be plausible counts, not rupee totals.
        assert 0 < result.break_even_units_monthly < expected_units * 100


# --- Depreciation must actually be charged ---------------------------------

def test_depreciation_is_charged_on_the_asset_base():
    result, _ = _run("retail_kirana", 200_000)
    assert result.monthly_depreciation > 0
    assert result.monthly_ebitda - result.monthly_depreciation == pytest.approx(
        result.monthly_ebit, abs=1.0
    )


def test_depreciation_matches_the_declared_share_and_life():
    tmpl = get_business_template("dairy")
    fin_input, _ = build_canonical_input("dairy", 300_000.0, None)
    result = compute_canonical_financials(fin_input)

    assert fin_input.asset_cost == pytest.approx(
        fin_input.total_project_cost * tmpl.depreciable_asset_share
    )
    expected_annual = fin_input.asset_cost / tmpl.asset_useful_life_years
    assert result.annual_depreciation == pytest.approx(expected_annual, rel=0.01)


def test_pat_is_never_above_ebitda_when_there_is_depreciation():
    for category in CATEGORIES:
        result, _ = _run(category, 300_000)
        assert result.monthly_pat < result.monthly_ebit, (
            f"{category}: depreciation is not reaching profit"
        )


def test_fixed_costs_are_not_invented_as_a_rent_salary_and_electricity_split():
    """
    The opex block was filled out by splitting the declared fixed cost 50/30/20
    across rent, salaries and electricity. No one had declared any of the three.
    The total was right and the composition was fiction, so the cost breakdown,
    the AI explanation and the report all repeated three numbers a founder had
    never stated - and the only figure they could check was the one that matched.

    Only lines that were actually declared may appear as declared.
    """
    tmpl = get_business_template("dairy")
    fin_input, _ = build_canonical_input("dairy", 300_000.0, None)

    assert fin_input.opex.rent == 0.0
    assert fin_input.opex.salaries == 0.0
    assert fin_input.opex.electricity == 0.0

    # The total is preserved, so the model's arithmetic is unaffected.
    expected_monthly = fin_input.total_project_cost * tmpl.annual_revenue_per_invested_rupee / 12.0
    expected_monthly *= tmpl.typical_opex_pct / 100.0
    assert fin_input.opex.total_monthly_opex == pytest.approx(expected_monthly, rel=0.01)
    assert fin_input.opex.total_monthly_opex == pytest.approx(
        fin_input.opex.rent + fin_input.opex.salaries + fin_input.opex.electricity
        + fin_input.opex.transport + fin_input.opex.maintenance + fin_input.opex.marketing
        + fin_input.opex.insurance + fin_input.opex.admin + fin_input.opex.other,
        abs=0.01,
    )


def test_a_cost_profile_keeps_its_fixed_cost_total_intact():
    """
    The change above must not move the model's arithmetic. The declared
    `fixed_cost_monthly` from a real cost profile still reaches the opex total
    unchanged, whether it arrives from an observed profile or from the template.
    """
    fin_input, derived = build_canonical_input(
        "retail_kirana", 200_000.0,
        {
            "estimated_monthly_units": 1000,
            "selling_price_per_unit": 50.0,
            "variable_cost_per_unit": 20.0,
            "fixed_cost_monthly": 10_000.0,
            "total_setup_cost": 400_000.0,
        },
    )
    assert derived["revenue_source"] == "cost_profile"
    assert fin_input.opex.total_monthly_opex == pytest.approx(10_000.0, abs=0.01)
    # Observed data wins for the operating lines, and the project cost is the
    # declared setup cost rather than a figure inferred from the margin.
    assert fin_input.products[0].units_per_month == 1000
    assert fin_input.products[0].selling_price == 50.0
    assert fin_input.total_project_cost == pytest.approx(400_000.0)


# --- Debt funds the real gap ----------------------------------------------

def test_scheme_debt_funds_the_gap_and_never_a_percentage_of_cost():
    project_cost = 1_000_000.0
    resolved = resolve_financing(CanonicalFinancialInput(
        business_type="retail_kirana",
        products=[],
        opex=None,
        own_capital=250_000.0,
        total_project_cost=project_cost,
        derive_debt_from_scheme=True,
    ))
    assert resolved["debt_amount"] == pytest.approx(750_000.0)
    assert resolved["financing_gap"] == pytest.approx(0.0)


def test_scheme_debt_is_capped_by_the_scheme_ceiling():
    resolved = resolve_financing(CanonicalFinancialInput(
        business_type="retail_kirana",
        products=[],
        opex=None,
        own_capital=100_000.0,
        total_project_cost=5_000_000.0,
        derive_debt_from_scheme=True,
        scheme_ceiling=1_250_000.0,
    ))
    assert resolved["debt_amount"] == pytest.approx(1_250_000.0)
    # The part the scheme cannot fund stays visible as an unfunded gap.
    assert resolved["financing_gap"] == pytest.approx(3_650_000.0)


def test_debt_is_never_derived_without_an_explicit_opt_in():
    resolved = resolve_financing(CanonicalFinancialInput(
        business_type="retail_kirana",
        products=[],
        opex=None,
        own_capital=250_000.0,
        total_project_cost=1_000_000.0,
        derive_debt_from_scheme=False,
    ))
    assert resolved["debt_amount"] == 0.0
    assert resolved["financing_gap"] == pytest.approx(750_000.0)


def test_capital_sized_sessions_reconcile():
    """Every capital-sized session must fully fund its own project cost."""
    for category in CATEGORIES:
        result, _ = _run(category, 200_000)
        assert result.financing_reconciled is True, (
            f"{category}: gap of {result.financing_gap:,.0f}"
        )
        assert result.financing_gap == pytest.approx(0.0, abs=1.0)


# --- Return figures -------------------------------------------------------

def test_returns_are_in_a_plausible_band_for_every_category():
    """
    ROI on project cost above ~150% means the declared turnover and margin
    assumptions are mutually inconsistent for that sector.
    """
    for category in CATEGORIES:
        result, _ = _run(category, 200_000)
        assert 0 < result.roi_on_total_project_pct < 150, (
            f"{category}: {result.roi_on_total_project_pct}% on project cost"
        )


def test_equity_return_exceeds_project_return_only_because_equity_is_thinner():
    result, _ = _run("retail_kirana", 200_000)
    assert result.roi_on_owner_equity_pct > result.roi_on_total_project_pct
    implied = result.roi_on_total_project_pct * (
        result.total_project_cost / result.own_capital
    )
    assert result.roi_on_owner_equity_pct == pytest.approx(implied, rel=0.01)


def test_roi_is_scale_invariant_for_the_same_category():
    """Doubling the deposit doubles profit, so the percentage must not move."""
    for category in CATEGORIES:
        small, _ = _run(category, 100_000)
        large, _ = _run(category, 200_000)
        assert large.monthly_pat == pytest.approx(small.monthly_pat * 2, rel=0.02)
        assert large.roi_on_total_project_pct == pytest.approx(
            small.roi_on_total_project_pct, rel=0.02
        )


# --- Scenario band must agree with the headline ---------------------------
#
# The scenario table used to subtract the full EMI and ignore depreciation, so
# its "realistic" row reported a pre-depreciation cash figure that disagreed
# with the headline PAT. Two distinct measures are now published: profit
# (after interest, before principal) and cash (after the full EMI).

def _scenario_band(result):
    from app.engines.financial_engine import compute_revenue_scenarios
    return compute_revenue_scenarios(
        monthly_revenue=result.monthly_revenue,
        monthly_variable_cost=result.monthly_cogs,
        monthly_fixed_cost=result.monthly_opex,
        emi=result.monthly_emi,
        total_investment=result.total_project_cost,
        monthly_interest=result.monthly_interest,
        monthly_depreciation=result.monthly_depreciation,
    )


def test_revenue_scenarios_reconcile_to_the_headline_result():
    result, _ = _run("dairy", 200_000)
    realistic = _scenario_band(result)["realistic"]

    assert realistic["monthly_ebitda"] == pytest.approx(result.monthly_ebitda, abs=1.0)
    assert realistic["monthly_net_profit"] == pytest.approx(result.monthly_pat, abs=1.0)
    assert realistic["roi_pct"] == pytest.approx(
        round(result.roi_on_total_project_pct, 1), abs=0.2
    )


def test_scenario_profit_excludes_principal_but_cash_includes_it():
    result, _ = _run("dairy", 200_000)
    realistic = _scenario_band(result)["realistic"]
    assert realistic["monthly_cash_after_debt_service"] < realistic["monthly_net_profit"]
    principal = result.monthly_emi - result.monthly_interest
    # Cash exceeds profit by the non-cash depreciation charge and falls short
    # by the principal that must be repaid: profit - cash = principal - dep.
    gap = realistic["monthly_net_profit"] - realistic["monthly_cash_after_debt_service"]
    assert gap == pytest.approx(principal - result.monthly_depreciation, abs=1.0)


def test_revenue_scenarios_are_ordered_and_hold_fixed_costs():
    result, _ = _run("retail_kirana", 200_000)
    band = _scenario_band(result)
    assert (
        band["pessimistic"]["monthly_net_profit"]
        < band["realistic"]["monthly_net_profit"]
        < band["optimistic"]["monthly_net_profit"]
    )
    for label in band:
        assert band[label]["monthly_fixed_cost"] == pytest.approx(result.monthly_opex)
