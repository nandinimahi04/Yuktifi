"""
Consistency between the compatibility layer and the canonical engine.

`app.engines.financial_engine` still exists because routes, the ranking service
and older tests import from it. That is a legitimate reason for the module to
exist and not a reason for it to contain arithmetic. These tests hold the line:
every model-level figure reached through the legacy import path must equal the
one the canonical engine produces for the same plan.

A failure here means the product is capable of showing two different numbers for
the same business - one from an analysis screen and one from a business plan -
which is the failure mode this refactor exists to remove. It is a much more
expensive defect to find in production than in this file.
"""
import pytest

from app.engines.financial_engine import (
    SEASONAL_INDEX,
    SEASONAL_INDEX_RAW,
    compute_cashflow_projection,
    compute_revenue_scenarios,
    compute_seasonal_revenue,
    run_financial_engine,
)
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)
from app.financial.projection import normalise_seasonality


# A representative plan, expressed in the shape the legacy helpers take.
MONTHLY_REVENUE = 58500.0
MONTHLY_VARIABLE_COST = 27300.0
MONTHLY_FIXED_COST = 17500.0
TOTAL_INVESTMENT = 100000.0


def canonical_plan(**overrides) -> CanonicalFinancialInput:
    # Mirrors what the dataset route builds, so the two can be compared figure
    # for figure: the plant and equipment is depreciable, and the working capital
    # it funds is not. Without the asset_cost line the canonical model applies no
    # depreciation at all, so the dataset route's EBIT would be lower than the
    # canonical one for a reason that has nothing to do with the passthrough under
    # test.
    kwargs = dict(
        business_type="retail_kirana",
        products=[ProductItem(
            name="Vada Pav",
            units_per_month=3900,
            selling_price=15.0,
            variable_cost_per_unit=7.0,
        )],
        opex=OpexBreakdown(other=MONTHLY_FIXED_COST),
        own_capital=TOTAL_INVESTMENT,
        total_project_cost=TOTAL_INVESTMENT,
        debt_amount=0.0,
        asset_cost=TOTAL_INVESTMENT - 9872.87,
        useful_life_years=10.0,
    )
    kwargs.update(overrides)
    return CanonicalFinancialInput(**kwargs)


# ── Seasonality ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("category", sorted(SEASONAL_INDEX_RAW))
def test_every_seasonal_table_means_one_after_normalisation(category):
    """
    The tables are hand-written, so their raw means are not 1.0. If normalisation
    is skipped or done differently in the compat layer, a category silently
    loses or gains a slice of its annual revenue - and the loss lands on EBITDA,
    which is a small residual, so the error in profit is several times the error
    in revenue.
    """
    normalised = SEASONAL_INDEX[category]

    assert len(normalised) == 12
    assert sum(normalised) / 12 == pytest.approx(1.0, abs=1e-9)
    assert normalised == pytest.approx(normalise_seasonality(SEASONAL_INDEX_RAW[category]))


def test_the_raw_tables_are_preserved_so_the_correction_stays_visible():
    """
    The un-normalised tables are kept deliberately. Normalising them in place
    would hide the fact that they needed correcting, and the next person to edit
    one would not know a correction was expected.
    """
    for category, raw in SEASONAL_INDEX_RAW.items():
        assert sum(raw) / 12 != pytest.approx(1.0, abs=1e-6) or category
        assert SEASONAL_INDEX[category] != raw or sum(raw) / 12 == pytest.approx(1.0, abs=1e-6)


# ── Seasonal revenue reads the canonical forecast ────────────────────────────
@pytest.mark.parametrize("category", ["dairy", "retail_kirana", "tailoring", "poultry"])
def test_seasonal_revenue_sums_back_to_the_annual_revenue(category):
    rows = compute_seasonal_revenue(MONTHLY_REVENUE, category)

    assert len(rows) == 12
    # Seasonality redistributes a year; it does not create or destroy one.
    assert sum(r["revenue"] for r in rows) == pytest.approx(MONTHLY_REVENUE * 12, abs=0.1)


def test_seasonal_revenue_matches_the_canonical_forecast_month_for_month():
    """
    The seasonal table and the monthly forecast are the same claim about the
    same year. If they are computed separately they will eventually disagree,
    and a user comparing a revenue table with a cash-flow chart gets no way to
    tell which one is right.
    """
    profile = SEASONAL_INDEX["dairy"]
    canonical = compute_canonical_financials(canonical_plan(seasonality_index=list(profile)))
    legacy = compute_seasonal_revenue(MONTHLY_REVENUE, "dairy")

    for i, row in enumerate(legacy):
        assert row["revenue"] == pytest.approx(canonical.monthly_forecast[i]["revenue"], abs=0.01)
        assert row["index"] == pytest.approx(canonical.seasonality_applied[i], abs=1e-9)


# ── Cash flow projection ─────────────────────────────────────────────────────
def test_the_cash_flow_projection_sums_to_its_own_year():
    """
    The legacy projection is a single, self-contained arithmetic path rather
    than a second full model, so the guarantee available for it is internal
    consistency: the twelve months must add up to what they claim, and fixed
    cost must not move with the season.
    """
    rows = compute_cashflow_projection(
        monthly_revenue=MONTHLY_REVENUE,
        monthly_fixed_cost=MONTHLY_FIXED_COST,
        monthly_variable_cost=MONTHLY_VARIABLE_COST,
        emi=0.0,
        category_id="dairy",
    )

    assert len(rows) == 12
    assert sum(r["revenue"] for r in rows) == pytest.approx(MONTHLY_REVENUE * 12, abs=0.1)
    for row in rows:
        assert row["fixed_cost"] == pytest.approx(MONTHLY_FIXED_COST, abs=0.01), (
            "a seasonal profile redistributes sales, it does not change the rent"
        )
        expected = row["revenue"] - row["variable_cost"] - row["fixed_cost"] - row["emi_payment"]
        assert row["net_cash"] == pytest.approx(expected, abs=0.01)


def test_the_cash_flow_projection_cumulative_agrees_with_its_own_months():
    rows = compute_cashflow_projection(
        monthly_revenue=MONTHLY_REVENUE,
        monthly_fixed_cost=MONTHLY_FIXED_COST,
        monthly_variable_cost=MONTHLY_VARIABLE_COST,
        emi=0.0,
    )

    running = 0.0
    for row in rows:
        running += row["net_cash"]
        assert row["cumulative"] == pytest.approx(running, abs=0.01)


# ── Revenue scenarios ────────────────────────────────────────────────────────
def test_the_realistic_scenario_reconciles_to_the_headline():
    """
    The `realistic` row is the plan as declared. If it does not tie back to the
    headline EBITDA, the scenario table and the headline are measuring
    different businesses - which is the discrepancy that made this table
    untrustworthy in the first place.
    """
    scenarios = compute_revenue_scenarios(
        monthly_revenue=MONTHLY_REVENUE,
        monthly_variable_cost=MONTHLY_VARIABLE_COST,
        monthly_fixed_cost=MONTHLY_FIXED_COST,
        emi=0.0,
        total_investment=TOTAL_INVESTMENT,
    )

    realistic = scenarios["realistic"]
    headline_ebitda = MONTHLY_REVENUE - MONTHLY_VARIABLE_COST - MONTHLY_FIXED_COST
    assert realistic["monthly_ebitda"] == pytest.approx(headline_ebitda, abs=0.01)
    assert realistic["monthly_revenue"] == pytest.approx(MONTHLY_REVENUE, abs=0.01)


def test_scenarios_are_ordered_pessimistic_realistic_optimistic():
    """
    A scenario table out of order, or with the optimistic case below the base,
    reads as a forecast of what will happen rather than a range of what could.
    """
    scenarios = compute_revenue_scenarios(
        monthly_revenue=MONTHLY_REVENUE,
        monthly_variable_cost=MONTHLY_VARIABLE_COST,
        monthly_fixed_cost=MONTHLY_FIXED_COST,
        emi=0.0,
        total_investment=TOTAL_INVESTMENT,
    )

    ebitdas = [scenarios[k]["monthly_ebitda"] for k in ("pessimistic", "realistic", "optimistic")]
    assert ebitdas == sorted(ebitdas)
    assert scenarios["pessimistic"]["monthly_revenue"] < scenarios["realistic"]["monthly_revenue"]


def test_fixed_cost_does_not_scale_with_the_scenario():
    """
    Variable cost moves with volume because it is per unit. Rent does not, and a
    table that scales both is showing a business that got a rent discount
    exactly when sales fell.
    """
    scenarios = compute_revenue_scenarios(
        monthly_revenue=MONTHLY_REVENUE,
        monthly_variable_cost=MONTHLY_VARIABLE_COST,
        monthly_fixed_cost=MONTHLY_FIXED_COST,
        emi=0.0,
        total_investment=TOTAL_INVESTMENT,
    )

    fixed = {k: v["monthly_fixed_cost"] for k, v in scenarios.items()}
    assert len(set(fixed.values())) == 1


# ── The compatibility entry point itself ─────────────────────────────────────
def dataset_plan(**overrides):
    """The shape the dataset-driven entry point actually reads."""
    unit_economics = {
        "expected_monthly_revenue": MONTHLY_REVENUE,
        "variable_costs": MONTHLY_VARIABLE_COST,
        "net_operating_income": MONTHLY_REVENUE - MONTHLY_VARIABLE_COST - MONTHLY_FIXED_COST,
    }
    unit_economics.update(overrides.pop("unit_economics", {}))
    kwargs = dict(
        user_capital=TOTAL_INVESTMENT,
        setup_costs={"total_setup_cost": TOTAL_INVESTMENT},
        pricing_margins={"average_margin_percentage": 46.7},
        monthly_costs={"total_fixed_costs": MONTHLY_FIXED_COST},
        unit_economics=unit_economics,
    )
    kwargs.update(overrides)
    return run_financial_engine(**kwargs)


def test_the_legacy_entry_point_reports_canonical_figures():
    """
    Whatever the legacy signature is, the arithmetic it hands back has to be the
    canonical arithmetic. This is the assertion the whole module exists to
    satisfy: a caller reaching the old import path must not get a different
    answer from a caller reaching the canonical one.
    """
    out = dataset_plan()

    assert out["financial_data_available"] is True
    assert out["monthly_revenue"] == pytest.approx(MONTHLY_REVENUE, abs=0.01)
    assert out["monthly_opex"] == pytest.approx(MONTHLY_FIXED_COST, abs=0.01)
    assert out["monthly_cogs"] == pytest.approx(MONTHLY_VARIABLE_COST, abs=0.01)
    assert out["monthly_ebitda"] == pytest.approx(
        MONTHLY_REVENUE - MONTHLY_VARIABLE_COST - MONTHLY_FIXED_COST, abs=0.01
    )


def test_the_legacy_entry_point_passes_the_canonical_verdicts_through():
    """
    The engine's gates, stress cases and cash profile used to be dropped here,
    so a route using this entry point had no verdict to show and no way to get
    one short of re-running the model. The blocks travel now.
    """
    out = dataset_plan()

    assert out["decision_gates"], "no gates reached the caller"
    assert out["financial_status"]["value"] in ("GO", "CONDITIONAL", "NO_GO", "INSUFFICIENT_EVIDENCE")
    assert "demand_minus_10" in out["stress_scenarios"]
    assert len(out["monthly_forecast"]) == 12
    assert out["explainability"]["ebitda"]["formula"]
    assert out["gate_benchmarks"]["min_dscr"] > 0


def test_the_legacy_entry_point_refuses_an_incomplete_dataset():
    """
    A dataset missing its revenue has no financials. The engine says so instead
    of substituting a number, and the abstention travels as a flag a client can
    branch on rather than as an empty dict.
    """
    out = run_financial_engine(
        user_capital=TOTAL_INVESTMENT,
        setup_costs={},
        pricing_margins={},
        monthly_costs={},
    )

    assert out["financial_data_available"] is False
    assert out["reason"], "an abstention without a reason cannot be acted on"
    assert "monthly_revenue" not in out


# The client contract. The financials screen used to rebuild the P&L, the working
# capital position and the loan totals from whatever the engine handed it: COGS
# came from back-solving a rounded gross margin, EBIT was net profit plus an EMI
# (principal included), tax was a literal 0, the cash float was opex divided by
# 30 and 4, and the totals were EMI times the post-moratorium month count. The
# screen now reads these fields instead, so they are part of the contract and a
# silent removal would show up as a blank dashboard rather than a failed test.


def test_the_client_contract_carries_the_full_waterfall():
    """
    Every line the P&L screen prints has to arrive computed. A missing key here
    renders as a dash; a key present but wrong renders as a confident number,
    which is the failure that matters.
    """
    out = dataset_plan()
    res = compute_canonical_financials(canonical_plan())

    for field in (
        "monthly_revenue",
        "monthly_cogs",
        "monthly_gross_profit",
        "monthly_opex",
        "monthly_ebitda",
        "monthly_depreciation",
        "monthly_ebit",
        "monthly_interest",
        "monthly_pbt",
        "monthly_tax",
        "monthly_pat",
        "tax_status",
        "net_margin_pct",
        "operating_days_per_month",
    ):
        assert field in out, f"{field} missing from the client contract"

    # The compatibility layer reports, it does not re-derive: the waterfall it
    # publishes has to be the canonical one.
    assert out["monthly_gross_profit"] == pytest.approx(res.monthly_gross_profit, abs=0.01)
    assert out["monthly_ebitda"] == pytest.approx(res.monthly_ebitda, abs=0.01)
    assert out["monthly_ebit"] == pytest.approx(res.monthly_ebit, abs=0.01)
    assert out["monthly_pbt"] == pytest.approx(res.monthly_pbt, abs=0.01)
    assert out["monthly_pat"] == pytest.approx(res.monthly_pat, abs=0.01)
    # Published to one decimal for display; the value is the canonical one
    # rounded, not a separate division by the client's own revenue figure.
    assert out["net_margin_pct"] == pytest.approx(round(res.net_margin_pct, 1), abs=0.001)
    assert out["net_margin_pct"] != pytest.approx(
        out["monthly_pat"] / out["monthly_revenue"] * 100, abs=0.01
    )

    # The waterfall has to close. A screen that prints these lines in a column
    # invites the reader to add them up, so the steps are asserted to reconcile
    # rather than merely to exist.
    assert out["monthly_ebitda"] == pytest.approx(
        out["monthly_gross_profit"] - out["monthly_opex"], abs=0.01
    )
    assert out["monthly_ebit"] == pytest.approx(
        out["monthly_ebitda"] - out["monthly_depreciation"], abs=0.01
    )
    assert out["monthly_pbt"] == pytest.approx(
        out["monthly_ebit"] - out["monthly_interest"], abs=0.01
    )
    assert out["monthly_pat"] == pytest.approx(
        out["monthly_pbt"] - out["monthly_tax"], abs=0.01
    )


def test_a_zero_tax_is_distinguishable_from_an_unmodelled_tax():
    """
    The P&L tab prints a tax line. With tax status NOT_MODELED the figure is zero
    because no tax was computed, not because the business owes none - and the two
    deserve different words on screen. This pins the flag that tells them apart.
    """
    out = dataset_plan()

    assert out["tax_status"] == "NOT_MODELED"
    assert out["monthly_tax"] == 0.0


def test_the_client_contract_states_how_many_days_it_assumed():
    """
    The screen used to divide monthly break-even by a hardcoded 26 working days.
    It has to receive the plan's actual figure, and receive null when there is
    none, so the per-day line can say "not declared" instead of assuming.
    """
    out = dataset_plan()

    assert out["operating_days_per_month"] == 30
    assert out["margin_of_safety_pct"] is not None


def test_the_client_contract_carries_the_cycle_days_behind_the_working_capital():
    """
    The working-capital tab used to show inventory, receivables and payables all
    as 0 with invented 15/0/0-day cycles. The engine's own block travels now,
    cycle days included, so a card can label a cycle that was actually assumed.
    """
    out = dataset_plan()
    wc = out["working_capital"]

    assert set(wc) >= {
        "monthly_working_capital",
        "net_working_capital",
        "daily_cash_needed",
        "weekly_cash_needed",
        "inventory_requirement",
        "receivables",
        "payables",
        "recommended_buffer",
        "receivable_days",
        "payable_days",
        "inventory_days",
    }
    # Inventory, receivables and payables are the three the screen used to fake
    # as zero. Each must now follow from the declared cycle rather than be zero.
    assert wc["inventory_requirement"] > 0
    assert wc["receivables"] > 0
    assert wc["payables"] > 0

    # The block reports the model's own figures. It used to be produced by a
    # second private calculation, so a change to the working-capital treatment
    # could move the payback and cash tables while this card kept showing the
    # old numbers.
    res = compute_canonical_financials(canonical_plan())
    assert wc["net_working_capital"] == pytest.approx(res.net_working_capital, abs=0.01)
    assert wc["inventory_requirement"] == pytest.approx(res.inventory_requirement, abs=0.01)
    assert wc["receivables"] == pytest.approx(res.receivables_requirement, abs=0.01)
    assert wc["payables"] == pytest.approx(res.payables_requirement, abs=0.01)

    # Daily and weekly cash are the operating cash flow per day and per week -
    # the day's money out and back - using the declared trading days. They are
    # not net working capital divided by a month, and not opex divided by 30.
    assert wc["daily_cash_needed"] == pytest.approx(
        res.monthly_operating_cash_flow / res.operating_days_per_month, abs=0.01
    )
    # Both are rounded from the same unrounded daily figure, hence a paise of
    # tolerance rather than an exact match.
    assert wc["weekly_cash_needed"] == pytest.approx(wc["daily_cash_needed"] * 7, abs=0.05)


def test_a_declared_working_capital_cycle_changes_the_requirement():
    """
    A dairy business collecting in 7 days and a shop selling for cash hold
    different amounts of money, and the tab is the screen a founder uses to size
    that float. Passing a cycle in has to actually reach the model - otherwise
    the configuration is accepted and quietly discarded, and the screen shows
    the same float for every business.
    """
    default = dataset_plan()["working_capital"]["monthly_working_capital"]
    longer = dataset_plan(
        working_capital_cfg={"receivable_days": 60, "inventory_days": 45, "payable_days": 60}
    )["working_capital"]["monthly_working_capital"]

    assert longer > default
    assert dataset_plan(
        working_capital_cfg={"receivable_days": 0, "inventory_days": 0, "payable_days": 0}
    )["working_capital"]["monthly_working_capital"] == pytest.approx(0.0, abs=0.01)


def test_contribution_per_unit_is_withheld_when_there_is_only_an_aggregate():
    """
    The dataset route is handed a monthly revenue total, not a price and a cost
    per unit. Divided out, that "yields" a single unit selling at the whole
    month's revenue - so a contribution of 31,200 "per unit", which is just
    gross profit wearing a costume. Break-even units is withheld for the same
    reason; this asserts the sibling field is too.
    """
    out = dataset_plan()

    assert out["contribution_per_unit"] is None
    assert out["break_even_units"] is None
    # The revenue-based break-even survives, because it needs no unit price.
    assert out["break_even_monthly_revenue"] == pytest.approx(
        MONTHLY_FIXED_COST / (1 - MONTHLY_VARIABLE_COST / MONTHLY_REVENUE), abs=0.01
    )


def test_loan_totals_come_from_the_schedule_not_a_recomputed_guessed_schedule():
    """
    Total repayable used to be emi * (tenure - moratorium) on the client, which
    ignores that a moratorium is interest-only and that the final instalment is
    smaller than the rest. The published totals must be the schedule's own, and
    must reconcile: principal repaid across the schedule is the amount borrowed,
    and the total is the principal plus the interest.
    """
    out = dataset_plan(
        user_capital=25000.0,
        setup_costs={"total_setup_cost": 100000.0},
        unit_economics={
            "expected_monthly_revenue": 120000.0,
            "variable_costs": 40000.0,
            "net_operating_income": 30000.0,
        },
    )
    schedule = out["loan_schedule"]
    assert schedule, "no amortisation schedule to total"

    principal = sum(row["principal_repaid"] for row in schedule)
    interest = sum(row["interest"] for row in schedule)

    assert principal == pytest.approx(out["loan_amount"], abs=1.0)
    assert out["total_interest_paid"] == pytest.approx(interest, abs=1.0)
    assert out["total_repayment"] == pytest.approx(principal + interest, abs=1.0)
    # The naive client formula, pinned so the replacement is visibly better.
    naive = out["emi"] * (out["tenure_months"] - out["moratorium_months"])
    assert out["total_repayment"] != pytest.approx(naive, abs=1.0)
