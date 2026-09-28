"""
Contract tests for the canonical financial engine.

The engine is the single source of truth for every number the product shows, so
these tests pin the arithmetic, not just the shape of the response. Each block
below corresponds to a promise the rest of the codebase relies on:

  * a fixed Vada Pav teashop plan produces the same figures every time,
  * debt is never invented, and missing data stays missing rather than becoming 0,
  * the monthly forecast reconciles to the annual headline,
  * every stress case and what-if is the same engine run with different inputs,
  * a gate that could not be evaluated is reported unknown, not passed.

Where a value is asserted, it is asserted against a number worked out by hand in
the comment beside it. An assertion that restates the implementation is worth
very little: it changes when the implementation changes, which is precisely the
case where a test is needed.

Note on the reference plan: it declares `tax_rate_pct=0.0` and records provenance
for the capital figures. Both are deliberate. An undeclared tax rate is reported
as a condition, and unrecorded provenance caps confidence, so the same plan
without them is CONDITIONAL. That is the engine telling the truth about what it
was and was not told, and it is why the GO test below has to supply them.
"""
import pytest

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    WorkingCapitalConfig,
    compute_canonical_financials,
    run_what_if,
)
from app.financial.gates import (
    GATE_CASH_FLOW,
    GATE_DEBT_SERVICE,
    GATE_FINANCING,
    GATE_PASS,
    GATE_UNKNOWN,
    SEVERITY_ERROR,
    STATUS_GO,
    STATUS_NO_GO,
    GateBenchmark,
)
from app.financial.inputs import (
    FinancialValidationError,
    InputSource,
    validate_financial_input,
)
from app.financial.projection import (
    WhatIfAdjustments,
    normalise_seasonality,
    seasonality_or_flat,
)


# ── The reference plan ───────────────────────────────────────────────────────
# Vada Pav, from the spec: 150 plates a day over 26 days (3,900 a month), sold
# at 15 with a 7 rupee variable cost per plate, 17,500 of monthly fixed costs,
# 100,000 of the entrepreneur's own money and no loan.
CAPITAL_PROVENANCE = {
    "own_capital": InputSource.USER_PROVIDED,
    "total_project_cost": InputSource.USER_PROVIDED,
    "debt_amount": InputSource.USER_PROVIDED,
}


def vada_pav(**overrides) -> CanonicalFinancialInput:
    kwargs = dict(
        business_type="vada_pav_stall",
        products=[
            ProductItem(
                name="Vada Pav",
                units_per_month=150 * 26,      # 3,900
                selling_price=15.0,
                variable_cost_per_unit=7.0,    # bun + potato + oil + masala
            )
        ],
        opex=OpexBreakdown(
            rent=5000, salaries=8000, electricity=1500,
            marketing=1000, maintenance=500, other=1500,
        ),                                   # 5,000+8,000+1,500+1,000+500+1,500 = 17,500
        own_capital=100000.0,
        total_project_cost=100000.0,
        debt_amount=0.0,
        tax_rate_pct=0.0,                    # declared, so "no tax modelled" is a choice
        field_provenance=dict(CAPITAL_PROVENANCE),
        working_capital_cfg=WorkingCapitalConfig(
            inventory_days=10, receivable_days=7, payable_days=14
        ),
    )
    kwargs.update(overrides)
    return CanonicalFinancialInput(**kwargs)


def vada_pav_with_loan(loan: float = 200000.0) -> CanonicalFinancialInput:
    """The same stall, with the loan actually stated rather than inferred."""
    return vada_pav(
        own_capital=100000.0,
        total_project_cost=300000.0,
        debt_amount=loan,
        interest_rate_annual_pct=12.0,
        tenure_months=60,
    )


def gate_of(result, gate_id):
    return next(g for g in result.decision_gates if g["gate"] == gate_id)


# ── Headline arithmetic ──────────────────────────────────────────────────────
def test_vada_pav_headline_numbers():
    res = compute_canonical_financials(vada_pav())

    assert res.monthly_revenue == 58500.0            # 3,900 x 15
    assert res.monthly_variable_costs == 27300.0    # 3,900 x 7
    assert res.contribution_per_unit == 8.0          # 15 - 7
    assert res.monthly_gross_profit == 31200.0       # 3,900 x 8
    assert res.monthly_opex == 17500.0               # sum of the six lines
    assert res.monthly_ebitda == 13700.0             # 31,200 - 17,500
    assert res.annual_ebitda == 164400.0             # 13,700 x 12


def test_vada_pav_break_even_ignores_depreciation_by_design():
    """
    17,500 of fixed cost over an 8 rupee contribution is 2,187.5 plates, or 84
    a day across 26 days. The figure is below an accounting break-even because
    depreciation is not a cash cost, and `break_even_basis` says which basis was
    used rather than leaving the reader to guess why it disagrees with the P&L.
    """
    res = compute_canonical_financials(vada_pav())

    assert res.break_even_units_monthly == pytest.approx(17500 / 8, abs=1e-6)   # 2,187.5
    assert res.break_even_revenue_monthly == pytest.approx((17500 / 8) * 15, abs=1e-6)
    assert "depreciation" in res.break_even_basis.lower()


def test_vada_pav_is_a_go_with_full_confidence():
    res = compute_canonical_financials(vada_pav())

    assert res.financial_status["value"] == STATUS_GO
    assert res.financial_status["failed_gates"] == []
    assert res.financial_status["advisory_gates"] == []
    assert res.financial_status["conditions"] == []
    assert res.financial_confidence["band"] == "HIGH"


def test_annual_figures_are_twelve_times_the_monthly_ones():
    res = compute_canonical_financials(vada_pav())

    assert res.annual_revenue == res.monthly_revenue * 12
    assert res.annual_opex == res.monthly_opex * 12
    assert res.annual_ebitda == res.monthly_ebitda * 12


# ── Conditions are reported rather than assumed away ─────────────────────────
def test_an_undeclared_tax_rate_is_a_condition_not_a_silent_zero():
    """
    Post-tax figures are only post-tax if a rate was declared. Guessing zero
    would present pre-tax profit as a take-home figure.
    """
    res = compute_canonical_financials(vada_pav(tax_rate_pct=None))

    assert res.tax_status != "TAX_APPLIED"
    assert any("tax" in c.lower() for c in res.financial_status["conditions"])
    assert res.financial_status["value"] != STATUS_GO


def test_unrecorded_provenance_caps_confidence():
    """
    The engine cannot claim its inputs are user-supplied when nobody said so.
    Confidence has to drop, and the result has to say why.
    """
    with_prov = compute_canonical_financials(vada_pav())
    without = compute_canonical_financials(vada_pav(field_provenance={}))

    assert without.financial_confidence["score"] < with_prov.financial_confidence["score"]
    assert without.financial_confidence["fields_recorded"] == 0
    assert any("provenance" in c.lower() for c in without.financial_status["conditions"])


# ── Debt is never invented ───────────────────────────────────────────────────
def test_no_debt_means_no_emi_and_no_dscr():
    res = compute_canonical_financials(vada_pav(debt_amount=0.0))

    assert res.debt_amount == 0.0
    assert res.monthly_emi == 0.0
    assert res.dscr is None
    assert res.dscr_status == "NOT_APPLICABLE_NO_DEBT"


def test_the_debt_service_gate_is_unknown_without_debt_and_does_not_block():
    res = compute_canonical_financials(vada_pav(debt_amount=0.0))

    assert gate_of(res, GATE_DEBT_SERVICE)["status"] == GATE_UNKNOWN
    # A gate that could not be evaluated is not a gate that failed. Reporting an
    # unknown gate as a failure would make every self-funded business look
    # unviable for the sole reason that it did not need a loan.
    assert res.financial_status["value"] == STATUS_GO
    # ...but it is still reported. A gate that quietly vanished from the block
    # would leave a reader unable to tell "passed" from "never checked".
    assert GATE_DEBT_SERVICE in res.financial_status["unknown_gates"]
    assert GATE_DEBT_SERVICE in res.financial_status["not_applicable_gates"]
    assert GATE_DEBT_SERVICE not in res.financial_status["failed_gates"]


def test_a_stated_loan_is_honoured_exactly():
    res = compute_canonical_financials(vada_pav_with_loan())

    assert res.debt_amount == 200000.0
    assert res.financing_reconciled is True
    assert res.financing_gap == 0.0
    assert res.monthly_emi > 0
    assert res.dscr is not None
    assert res.dscr_status == "COMPUTED"
    # With a loan, the debt service gate is no longer not-applicable: it is
    # evaluated, and it is held to the benchmark.
    assert gate_of(res, GATE_DEBT_SERVICE)["status"] != GATE_UNKNOWN


def test_other_funding_is_not_quietly_turned_into_a_loan():
    """
    `other_funding` is a source of money that is not a borrowing. Treating it as
    a loan would produce an EMI against funds the entrepreneur was never asked
    to repay, which is the most consequential way a financing figure can be
    wrong.
    """
    res = compute_canonical_financials(
        vada_pav(total_project_cost=300000.0, other_funding=200000.0)
    )

    assert res.debt_amount == 0.0
    assert res.monthly_emi == 0.0
    assert res.dscr is None


def test_the_loan_schedule_repays_exactly_what_was_borrowed():
    """
    Total repayment is principal plus total interest and nothing else. A
    schedule that over- or under-repays is the commonest way a loan model
    misleads, and the difference surfaces years later as a balance that will
    not clear.
    """
    res = compute_canonical_financials(vada_pav_with_loan())

    assert res.total_repayment == pytest.approx(res.debt_amount + res.total_interest_paid, rel=1e-9)
    assert res.total_interest_paid > 0, "a 5-year loan at 12% costs interest; zero means the rate was ignored"
    assert len(res.loan_schedule) >= 60


def test_a_funding_gap_is_reported_and_no_loan_is_invented_to_close_it():
    """
    Own capital below the project cost is a real gap. It is reported as one
    rather than closed by quietly raising the project cost or inventing a loan.
    """
    res = compute_canonical_financials(vada_pav(total_project_cost=500000.0))

    assert res.financing_gap > 0
    assert res.debt_amount == 0.0
    assert res.financing_reconciled is False
    assert gate_of(res, GATE_FINANCING)["status"] != GATE_PASS
    assert res.financial_status["value"] in (STATUS_NO_GO, "CONDITIONAL")


# ── Missing data stays missing ───────────────────────────────────────────────
def test_an_unmodelled_price_yields_none_rather_than_zero():
    """
    Break-even cannot be computed from a price the caller did not state.
    Returning 0 would imply the business breaks even selling nothing, which is
    the most optimistic answer available.
    """
    res = compute_canonical_financials(vada_pav(products=[
        ProductItem(name="Unpriced", units_per_month=100, selling_price=0.0, variable_cost_per_unit=4.0)
    ]))

    assert res.break_even_units_monthly is None
    assert res.break_even_revenue_monthly is None
    assert res.break_even_basis
    assert any("selling_price" in w["field"] for w in res.validation_warnings)


def test_negative_inputs_are_reported_not_corrected():
    res = compute_canonical_financials(vada_pav(own_capital=-1000.0))

    assert res.validation_errors, "a negative own capital must be reported"
    assert not res.financing_reconciled
    assert any(i["field"] == "own_capital" for i in res.validation_errors)


def test_strict_validation_refuses_to_calculate_at_all():
    with pytest.raises(FinancialValidationError):
        compute_canonical_financials(vada_pav(own_capital=-1.0, strict_validation=True))


def test_provenance_is_carried_into_the_result():
    res = compute_canonical_financials(vada_pav())

    by_field = {p["field"]: p for p in res.input_provenance}
    assert by_field["own_capital"]["source"] == InputSource.USER_PROVIDED.value


def test_confidence_is_exposed_under_both_names():
    """
    `financial_confidence` is the field; `confidence` is the compatibility
    alias clients look for. Both must be the same object, not two computations.
    """
    res = compute_canonical_financials(vada_pav())

    assert res.confidence is res.financial_confidence


# ── Seasonality ──────────────────────────────────────────────────────────────
def test_seasonality_is_normalised_to_a_mean_of_one():
    """
    A raw index is only meaningful relative to its own average. A profile
    averaging 1.2 is scaled down, so seasonality redistributes a year's revenue
    without inflating or shrinking it.
    """
    raw = [0.5] + [1.0] * 10 + [4.5]
    norm = normalise_seasonality(raw)

    assert len(norm) == 12
    assert sum(norm) / len(norm) == pytest.approx(1.0, abs=1e-9)


def test_a_flat_index_is_left_alone():
    assert normalise_seasonality([1.0] * 12) == pytest.approx([1.0] * 12)


def test_no_declared_profile_means_flat():
    assert normalise_seasonality(None) == [1.0] * 12


@pytest.mark.parametrize("bad", [
    [1.0, 2.0, 3.0],                     # wrong length
    [0.0] + [1.0] * 11,                  # a month with no demand
    [-1.0] + [1.0] * 11,                 # negative demand
    ["a"] + [1.0] * 11,                  # not a number
])
def test_a_declared_but_unusable_profile_is_refused_not_flattened(bad):
    """
    Returning a flat profile for a profile the caller actually supplied would be
    a silent correction: the response would show twelve even months with nothing
    to indicate the profile had been discarded. The refusal is loud instead.
    """
    with pytest.raises(ValueError):
        normalise_seasonality(bad)


def test_the_engine_declines_to_model_a_bad_profile_and_says_so():
    """
    The engine must still return a result rather than crash, but the refusal has
    to be visible in `validation_errors`. Falling back to flat is acceptable
    precisely because it is not hidden.
    """
    res = compute_canonical_financials(vada_pav(seasonality_index=[1.0, 2.0, 3.0]))

    assert seasonality_or_flat(vada_pav(seasonality_index=[1.0, 2.0, 3.0])) == [1.0] * 12
    assert res.seasonality_applied == [1.0] * 12
    assert any("seasonality" in e["field"] for e in res.validation_errors)


# ── The monthly forecast ─────────────────────────────────────────────────────
def test_the_forecast_reconciles_to_the_annual_headline():
    """
    If the twelve forecast months did not add up to the annual revenue shown
    above them, one of the two would be a lie. This is the single most important
    invariant in the forecast.
    """
    res = compute_canonical_financials(vada_pav())

    assert len(res.monthly_forecast) == 12
    assert sum(m["revenue"] for m in res.monthly_forecast) == pytest.approx(res.annual_revenue, rel=1e-9)
    assert sum(m["ebitda"] for m in res.monthly_forecast) == pytest.approx(res.annual_ebitda, rel=1e-9)


def test_seasonality_moves_revenue_between_months_without_changing_the_year():
    """
    A profile of 2.0 against eleven 1.0s has a mean of 1.083, so the engine
    rescales it: the strong month keeps its shape (2/1.083 = 1.846) and the year
    still totals the same revenue. Without the rescale, seasonality would
    quietly add 8.3% to the year.
    """
    res = compute_canonical_financials(vada_pav(seasonality_index=[2.0] + [1.0] * 11))

    assert res.seasonality_applied[0] == pytest.approx(2.0 / (13 / 12), rel=1e-6)
    assert sum(res.seasonality_applied) == pytest.approx(12.0, abs=1e-9)
    revenues = [m["revenue"] for m in res.monthly_forecast]
    assert revenues[0] > res.monthly_revenue, "the strong month must be above average"
    # Each month is rounded to the nearest paisa, so twelve months can differ from
    # the annual headline by up to six paise. The bound is asserted rather than
    # an exact equality, because each month's own arithmetic also rounds and
    # promising more precision than the arithmetic delivers would be the same
    # overclaiming the test exists to catch.
    assert sum(revenues) == pytest.approx(res.annual_revenue, abs=0.06)


def test_price_growth_compounds_and_shows_up_in_the_year_total():
    res = compute_canonical_financials(vada_pav(annual_price_growth_pct=12.0))

    revenues = [m["revenue"] for m in res.monthly_forecast]
    assert revenues[-1] > revenues[0], "a 12% annual price rise must raise the last month"
    assert revenues[-1] == pytest.approx(res.monthly_revenue * 1.12, rel=0.01)
    assert sum(revenues) > res.annual_revenue, "growth must be visible in the year total"


def test_projection_length_is_configurable():
    res = compute_canonical_financials(vada_pav(projection_months=6))

    assert len(res.monthly_forecast) == 6
    assert res.ending_cash_balance is not None


def test_cash_shortfalls_are_counted_and_the_worst_month_is_named():
    """
    A stall selling 500 plates a month cannot cover 25,000 of fixed cost, so it
    runs out of cash. The engine has to say how many months, which month was
    worst, and how much working capital is missing - not merely report negative
    EBITDA and leave the reader to infer insolvency.
    """
    struggling = vada_pav(
        own_capital=20000.0,
        total_project_cost=20000.0,
        opex=OpexBreakdown(other=25000.0),
        products=[ProductItem(name="Vada Pav", units_per_month=500, selling_price=15.0, variable_cost_per_unit=7.0)],
    )
    res = compute_canonical_financials(struggling)

    assert res.monthly_ebitda < 0
    assert res.months_negative_cash >= 1
    assert res.minimum_cash_balance < 0
    assert res.lowest_cash_month is not None
    assert res.working_capital_funding_gap > 0


def test_a_sound_plan_reports_no_cash_shortfall():
    res = compute_canonical_financials(vada_pav())

    assert res.months_negative_cash == 0
    assert res.minimum_cash_balance > 0
    assert res.working_capital_funding_gap == 0


# ── Stress: the same engine, different inputs ────────────────────────────────
STRESS_KEYS = (
    "demand_minus_10", "demand_minus_20", "price_minus_10",
    "cost_plus_10", "cost_plus_15", "interest_plus_2", "combined_severe",
)


def test_every_stress_case_is_present_and_recomputed():
    res = compute_canonical_financials(vada_pav())

    assert "BASE" in res.stress_scenarios, "the unshocked case belongs beside the shocked ones"
    for key in STRESS_KEYS:
        assert key in res.stress_scenarios, f"missing stress case: {key}"
        assert res.stress_scenarios[key]["monthly_ebitda"] is not None
        assert res.stress_scenarios[key]["ebitda_change"] is not None


def test_the_base_case_is_the_plan_as_declared():
    res = compute_canonical_financials(vada_pav())
    base = res.stress_scenarios["BASE"]

    assert base["monthly_ebitda"] == res.monthly_ebitda
    assert base["ebitda_change"] == 0.0
    assert base["decision_changed"] is False


def test_a_demand_shock_lowers_revenue_and_leaves_unit_economics_alone():
    res = compute_canonical_financials(vada_pav())
    case = res.stress_scenarios["demand_minus_10"]

    assert case["monthly_revenue"] == pytest.approx(res.monthly_revenue * 0.9, rel=1e-9)
    # Fewer units sold does not make the ingredients cheaper, so variable cost
    # falls with volume while the fixed cost is untouched.
    assert case["monthly_variable_costs"] == pytest.approx(res.monthly_variable_costs * 0.9, rel=1e-9)
    assert case["monthly_opex"] == pytest.approx(res.monthly_opex, rel=1e-9)
    assert case["monthly_ebitda"] < res.monthly_ebitda


def test_a_price_shock_takes_the_full_hit_on_revenue():
    res = compute_canonical_financials(vada_pav())
    case = res.stress_scenarios["price_minus_10"]

    assert case["monthly_revenue"] == pytest.approx(res.monthly_revenue * 0.9, rel=1e-9)
    assert case["contribution_per_unit"] == pytest.approx(15 * 0.9 - 7, rel=1e-9)
    assert case["monthly_opex"] == pytest.approx(res.monthly_opex, rel=1e-9)


def test_input_cost_inflation_does_not_raise_the_rent():
    res = compute_canonical_financials(vada_pav())
    case = res.stress_scenarios["cost_plus_10"]

    assert case["monthly_variable_costs"] == pytest.approx(res.monthly_variable_costs * 1.1, rel=1e-9)
    assert case["monthly_opex"] == pytest.approx(res.monthly_opex, rel=1e-9)


def test_the_combined_shock_compounds_below_every_single_shock():
    res = compute_canonical_financials(vada_pav())
    scenarios = res.stress_scenarios
    combined = scenarios["combined_severe"]["monthly_ebitda"]

    for key in ("demand_minus_20", "price_minus_10", "cost_plus_15"):
        assert combined < scenarios[key]["monthly_ebitda"], (
            f"the combined shock should sit below {key}, not above it"
        )


def test_an_interest_shock_rebuilds_the_schedule():
    """
    A rate change is a different loan, not a different label on the old one: the
    EMI has to move with it, and the DSCR has to fall as it does.
    """
    base = compute_canonical_financials(vada_pav_with_loan())
    case = base.stress_scenarios["interest_plus_2"]

    assert case["monthly_emi"] > base.monthly_emi
    assert case["dscr"] < base.dscr


def test_a_stressed_run_does_not_carry_its_own_nested_stress_block():
    """
    Recursion guard. A stressed result that inherited `include_scenarios=True`
    would run seven scenarios, each of which runs seven, without end.
    """
    res = compute_canonical_financials(vada_pav())
    case = res.stress_scenarios["demand_minus_10"]

    assert "stress_scenarios" not in case
    assert case["severity"] == "moderate"


# ── What-if ──────────────────────────────────────────────────────────────────
def test_a_what_if_leaves_unspecified_levers_alone():
    res = run_what_if(vada_pav(), WhatIfAdjustments(price_delta_pct=-5.0))

    applied = {a["lever"] for a in res["applied_adjustments"]}
    assert len(applied) == 1
    assert "units_multiplier" not in applied, "an unspecified lever must not be moved"


def test_a_what_if_reports_the_change_not_only_the_answer():
    base = compute_canonical_financials(vada_pav())
    res = run_what_if(vada_pav(), WhatIfAdjustments(price_delta_pct=10.0))

    assert res["result"]["monthly_revenue"] == pytest.approx(base.monthly_revenue * 1.1, rel=1e-9)
    # +10% on price is +5,850 of revenue: 58,500 x 10%.
    assert res["delta"]["monthly_revenue"] == pytest.approx(5850.0, rel=1e-9)
    assert res["delta"]["monthly_ebitda"] == pytest.approx(5850.0, rel=1e-9)


def test_an_empty_what_if_changes_nothing():
    base = compute_canonical_financials(vada_pav())
    res = run_what_if(vada_pav(), WhatIfAdjustments())

    assert res["result"]["monthly_revenue"] == pytest.approx(base.monthly_revenue, rel=1e-9)
    assert res["decision_changed"] is False


def test_a_what_if_can_add_a_loan_and_rebuilds_the_schedule():
    res = run_what_if(vada_pav(), WhatIfAdjustments(debt_amount=200000.0, own_capital=0.0))

    assert res["result"]["debt_amount"] == 200000.0
    assert res["result"]["monthly_emi"] > 0
    assert res["result"]["dscr"] is not None

def test_a_what_if_that_breaks_the_plan_says_the_decision_changed():
    res = run_what_if(vada_pav(), WhatIfAdjustments(price_delta_pct=-60.0))

    assert res["result"]["monthly_ebitda"] < 0
    assert res["decision_changed"] is True
    assert res["result_decision"] != res["base_decision"]


# ── Gates ────────────────────────────────────────────────────────────────────
def test_thresholds_are_published_so_a_gate_can_be_audited():
    """
    A verdict that cannot be checked is an assertion. The benchmarks travel
    with the result so a reader can see what PASS was measured against.
    """
    res = compute_canonical_financials(vada_pav())

    benchmarks = res.gate_benchmarks
    assert benchmarks["min_dscr"] == GateBenchmark().min_dscr
    assert benchmarks["min_contribution_margin_pct"] == GateBenchmark().min_contribution_margin_pct
    assert "not legal" in benchmarks["basis"].lower(), (
        "the benchmarks must say they are this model's thresholds, not a lender's rules"
    )


def test_benchmarks_are_configurable():
    """
    A different lender's threshold is a different answer. A hard-coded benchmark
    would make the gate unfalsifiable.
    """
    res = compute_canonical_financials(vada_pav(gate_benchmark=GateBenchmark(min_dscr=2.5)))

    assert res.gate_benchmarks["min_dscr"] == 2.5


def test_every_gate_states_its_value_its_threshold_and_why():
    for gate in compute_canonical_financials(vada_pav()).decision_gates:
        assert gate["status"]
        assert gate["reason"], f"{gate['gate']} gave a verdict without a reason"
        assert "fatal" in gate


def test_a_cash_shortfall_is_flagged_rather_than_ignored():
    tight = vada_pav(
        own_capital=20000.0,
        total_project_cost=20000.0,
        opex=OpexBreakdown(other=22000.0),
    )
    res = compute_canonical_financials(tight)

    # A cash figure is available, so the gate has to have an opinion about it.
    assert gate_of(res, GATE_CASH_FLOW)["status"] != GATE_UNKNOWN


def test_explainability_covers_every_headline_number():
    """
    Each headline needs a sentence explaining how it was reached, so a user who
    disagrees with a number can find the assumption they disagree with. The
    formula is spelled out with the substituted values, not left as a label.
    """
    res = compute_canonical_financials(vada_pav())

    for key in ("revenue", "variable_cost", "contribution_per_unit", "ebitda", "break_even_units"):
        entry = res.explainability[key]
        assert entry["formula"], f"{key} has no formula to check"
        assert entry["value"] is not None, f"{key} has no value recorded"
        assert entry["source"], f"{key} does not say which engine produced it"


def test_an_unmodelled_metric_is_explained_as_unmodelled():
    """
    When a number could not be computed, the explanation says why instead of
    showing a formula for a value that does not exist.
    """
    res = compute_canonical_financials(vada_pav(products=[
        ProductItem(name="Unpriced", units_per_month=100, selling_price=0.0, variable_cost_per_unit=4.0)
    ]))

    assert res.break_even_units_monthly is None
    assert res.explainability["break_even_units"]["formula"]


# ── Validation API ───────────────────────────────────────────────────────────
def test_validate_input_accepts_the_reference_plan():
    issues = validate_financial_input(vada_pav())
    assert not [i for i in issues if i.severity == SEVERITY_ERROR]


def test_validation_issues_carry_a_field_and_an_explanation():
    issues = validate_financial_input(vada_pav(own_capital=-5.0))

    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    assert errors
    assert errors[0].field == "own_capital"
    assert errors[0].message, "an error nobody can act on is not a useful error"
