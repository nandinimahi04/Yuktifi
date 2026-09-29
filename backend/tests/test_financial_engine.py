"""
Tests for the financial engine compatibility shim.

The shim must never reimplement financial math. These tests assert that it
delegates correctly, refuses to invent values, and that its display helpers
report honest numbers.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engines import financial_engine as fe
from app.financial.canonical_engine import compute_emi as canonical_emi


def test_emi_delegates_to_canonical_engine():
    for principal, rate, tenure, moratorium in [
        (100000.0, 9.0, 60, 0),
        (250000.0, 11.0, 48, 0),
        (120000.0, 10.0, 60, 6),
        (50000.0, 6.5, 36, 3),
    ]:
        assert fe.compute_emi(principal, rate, tenure, moratorium) == \
            canonical_emi(principal, rate, tenure, moratorium)


def test_emi_is_zero_without_principal_and_never_raises():
    assert fe.compute_emi(0.0, 10.0, 60) == 0.0
    assert fe.compute_emi(100000.0, 10.0, 6, 6) == 0.0


def test_dscr_is_none_without_debt_service():
    assert fe.compute_dscr(50000.0, 0.0) is None
    assert fe.compute_dscr(50000.0, None) is None


def test_dscr_matches_canonical_ratio():
    assert fe.compute_dscr(50000.0, 20000.0) == 2.5


def test_loan_amount_never_exceeds_the_funding_gap():
    """A loan larger than the gap would make the structure impossible."""
    assert fe.compute_loan_amount(200000.0, None, own_contribution=100000.0) == 100000.0
    assert fe.compute_loan_amount(200000.0, None, own_contribution=200000.0) == 0.0
    assert fe.compute_loan_amount(200000.0, None, own_contribution=500000.0) == 0.0


def test_loan_amount_respects_other_funding_and_ceiling():
    assert fe.compute_loan_amount(
        500000.0, None, own_contribution=100000.0, other_funding=50000.0
    ) == 350000.0
    assert fe.compute_loan_amount(
        1000000.0, 450000.0, own_contribution=100000.0
    ) == 450000.0


def test_break_even_is_none_when_contribution_is_not_positive():
    assert fe.compute_break_even_units(10000.0, 20.0, 25.0) is None
    assert fe.compute_break_even_units(10000.0, 20.0, 20.0) is None


def test_break_even_units_are_computed_from_contribution():
    assert fe.compute_break_even_units(10000.0, 20.0, 12.0) == 1250.0


def test_net_profit_subtracts_variable_cost():
    """Revenue minus fixed cost alone is not profit."""
    assert fe.compute_net_profit(100000.0, 20000.0, 30000.0) == 50000.0
    assert fe.compute_net_profit(100000.0, 20000.0) == 80000.0


def test_pnl_statement_has_no_default_cogs_or_tax():
    pnl = fe.compute_pnl_statement(
        monthly_revenue=100000.0, monthly_variable_cost=40000.0, monthly_fixed_cost=20000.0
    )
    assert pnl["cogs"] == 40000.0
    assert pnl["gross_profit"] == 60000.0
    assert pnl["tax"] == 0.0
    assert pnl["tax_status"] == "NOT_MODELED"
    assert pnl["net_profit"] == 40000.0


def test_pnl_statement_models_tax_only_when_a_rate_is_given():
    pnl = fe.compute_pnl_statement(
        monthly_revenue=100000.0, monthly_variable_cost=40000.0,
        monthly_fixed_cost=20000.0, tax_rate_pct=25.0,
    )
    assert pnl["tax_status"] == "MODELED"
    assert pnl["tax"] == 10000.0
    assert pnl["net_profit"] == 30000.0


def test_pnl_waterfall_is_internally_consistent():
    pnl = fe.compute_pnl_statement(
        monthly_revenue=200000.0, monthly_variable_cost=80000.0,
        monthly_fixed_cost=40000.0, monthly_depreciation=10000.0,
        monthly_interest=5000.0, tax_rate_pct=20.0,
    )
    assert pnl["ebitda"] == pnl["gross_profit"] - pnl["operating_expenses"]
    assert pnl["ebit"] == pnl["ebitda"] - pnl["depreciation"]
    assert pnl["pbt"] == pnl["ebit"] - pnl["interest"]
    assert pnl["net_profit"] == pnl["pbt"] - pnl["tax"]


def test_working_capital_responds_to_actual_variable_cost():
    """The old implementation hardcoded 45% and ignored its own argument."""
    cheap = fe.compute_working_capital(100000.0, 20000.0)
    dear = fe.compute_working_capital(100000.0, 80000.0)

    assert dear["inventory_requirement"] > cheap["inventory_requirement"]
    assert dear["payables"] > cheap["payables"]
    assert dear["net_working_capital"] != cheap["net_working_capital"]


def test_working_capital_payables_can_exceed_inventory_requirement():
    """Suppliers financing the business is a legitimate, visible outcome."""
    wc = fe.compute_working_capital(
        100000.0, 60000.0, receivable_days=7, payable_days=30, inventory_days=5
    )
    assert wc["net_working_capital"] < 0


def test_cashflow_seasonality_must_not_cancel_out():
    """Indexing revenue and opex by the same factor makes seasonality a no-op."""
    rows = fe.compute_cashflow_projection(
        monthly_revenue=100000.0, monthly_fixed_cost=30000.0,
        monthly_variable_cost=20000.0, emi=0.0, category_id="dairy",
    )
    margins = {
        round((r["revenue"] - r["variable_cost"] - r["fixed_cost"]) / r["revenue"] * 100, 4)
        for r in rows
    }
    assert len(margins) > 1, "seasonality must change profitability, not just scale it"

    fixed = {r["fixed_cost"] for r in rows}
    assert len(fixed) == 1, "fixed cost must not scale with season"


def test_cashflow_moratorium_suppresses_emi():
    rows = fe.compute_cashflow_projection(
        100000.0, 30000.0, 20000.0, 5000.0, moratorium_months=3, category_id="kirana"
    )
    assert rows[0]["emi_payment"] == 0.0
    assert rows[2]["emi_payment"] == 0.0
    assert rows[3]["emi_payment"] == 5000.0


def test_payback_subtracts_the_investment():
    """Without subtracting it, every profitable business pays back in month 1."""
    args = dict(
        monthly_revenue=50000.0,
        monthly_variable_cost=20000.0,
        monthly_fixed_cost=20000.0,
        emi=0.0,
        total_investment=500000.0,
        category_id="dairy",
    )
    result = fe.compute_payback_period(**args)

    outlay = result["total_outlay"]
    assert outlay > args["total_investment"], "working capital must be part of the outlay"

    # Independently locate the crossing month from the projected cash flows.
    rows = fe.compute_cashflow_projection(
        args["monthly_revenue"], args["monthly_fixed_cost"],
        args["monthly_variable_cost"], args["emi"], category_id="dairy",
        num_months=60,
    )
    cumulative = 0.0
    expected = None
    for row in rows:
        cumulative += row["net_cash"]
        if cumulative >= outlay:
            expected = row["month_num"]
            break

    assert expected is not None
    assert result["payback_months"] == expected
    assert result["payback_months"] > 1


def test_payback_reports_failure_when_outlay_never_recovers():
    result = fe.compute_payback_period(
        monthly_revenue=10000.0, monthly_variable_cost=6000.0,
        monthly_fixed_cost=8000.0, emi=0.0, total_investment=500000.0,
        category_id="dairy", max_months=24,
    )
    assert result["payback_achieved"] is False
    assert result["payback_months"] is None
    assert "not recovered" in result["note"]


def test_revenue_scenarios_hold_fixed_cost_constant():
    """Fixed cost scaling with revenue is not a fixed cost."""
    s = fe.compute_revenue_scenarios(
        monthly_revenue=100000.0, monthly_variable_cost=40000.0,
        monthly_fixed_cost=20000.0, emi=0.0, total_investment=500000.0,
    )
    assert s["pessimistic"]["monthly_fixed_cost"] == s["optimistic"]["monthly_fixed_cost"]
    assert s["pessimistic"]["monthly_net_profit"] < s["optimistic"]["monthly_net_profit"]


def test_run_financial_engine_abstains_when_dataset_is_incomplete():
    result = fe.run_financial_engine(
        user_capital=100000.0,
        setup_costs={},
        pricing_margins={},
        monthly_costs={},
        category_id="retail_kirana",
        unit_economics={},
    )
    assert result["financial_data_available"] is False
    assert "reason" in result
    assert "project_cost" not in result


def test_run_financial_engine_uses_dataset_setup_cost_not_margin_multiple():
    result = fe.run_financial_engine(
        user_capital=100000.0,
        setup_costs={"total_setup_cost": 400000.0},
        pricing_margins={"average_margin_percentage": 40.0},
        monthly_costs={"total_fixed_costs": 15000.0},
        unit_economics={
            "expected_monthly_revenue": 200000.0,
            "variable_costs": 90000.0,
            "net_operating_income": 95000.0,
        },
        category_id="dairy",
    )

    assert result["financial_data_available"] is True
    assert result["project_cost"] == 400000.0
    assert result["own_contribution"] == 100000.0
    assert result["financing_gap"] == 0.0
    assert result["financing_reconciled"] is True
    assert result["loan_amount"] > 0
    assert result["dscr"] is not None


def test_run_financial_engine_surfaces_dataset_variance():
    """A disagreement with the dataset's own NOI must be visible, not hidden."""
    result = fe.run_financial_engine(
        user_capital=100000.0,
        setup_costs={"total_setup_cost": 400000.0},
        pricing_margins={"average_margin_percentage": 40.0},
        monthly_costs={"total_fixed_costs": 15000.0},
        unit_economics={
            "expected_monthly_revenue": 200000.0,
            "variable_costs": 90000.0,
            "net_operating_income": 1.0,
        },
        category_id="dairy",
    )
    assert result["dataset_net_operating_income"] == 1.0
    assert result["dataset_noi_variance"] != 0.0
