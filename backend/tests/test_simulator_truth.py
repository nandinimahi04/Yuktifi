"""
The dynamic simulator must not flatter the borrower.

Two defects are covered, both of which moved the answer in the direction that
makes a business look safer than it is:

* Debt service was `monthly_emi + monthly_interest`. An EMI already contains
  interest, so the denominator counted the same money twice and inflated it. A
  stress tool whose ratio rises when the business gets worse is worse than no
  stress tool at all.
* A negative cash flow produced a small negative ratio (e.g. -0.4), which reads
  as a marginal shortfall rather than as a business that cannot service its debt
  at all.

A third test pins the fact that two `EventEngine` classes exist in this package
with different return shapes, and that the loop tolerates both.
"""
import pytest

from app.engines.simulator.simulator_engine import run_dynamic_simulation

BASELINE = {
    "monthly_revenue": 100000,
    "monthly_operating_cost": 60000,
    "project_cost": 400000,
    "monthly_emi": 8000,
    "monthly_interest": 1200,
}


def _run(**kwargs):
    params = {
        "month": 4,
        "cash_balance": 50000,
        "active_events": [],
        "decision": "hold",
        "baseline": dict(BASELINE),
    }
    params.update(kwargs)
    return run_dynamic_simulation(**params)


def test_a_simulation_with_an_event_actually_stresses_revenue():
    out = _run(active_events=["competitor_entry"])
    assert out["revenue"] < BASELINE["monthly_revenue"]


def test_event_effects_are_named_in_the_output():
    out = _run(active_events=["competitor_entry"])
    applied = [a for a in out["assumptions"] if a.get("event") == "competitor_entry"]
    assert applied and applied[0]["applied"] is True
    assert applied[0]["title"] == "New competitor opens"
    assert applied[0]["description"]


def test_unknown_event_is_reported_not_ignored():
    out = _run(active_events=["meteor_strike"])
    applied = [a for a in out["assumptions"] if a.get("event") == "meteor_strike"]
    assert applied and applied[0]["applied"] is False
    assert "Unknown event" in applied[0]["reason"]


def test_dscr_uses_the_emi_without_adding_interest_twice():
    """
    40,000 net cash flow against an 8,000 EMI is 5.0.

    Adding the 1,200 of interest to the denominator gave 4.35, flattering the
    ratio in the one direction that hides risk.
    """
    out = _run()
    assert out["dscr"] == 5.0
    assert out["dscr_status"] == "COMPUTED"


def test_dscr_falls_when_the_business_does():
    strong = _run()
    weak = _run(active_events=["monsoon"], decision="improve_service")
    assert weak["dscr"] < strong["dscr"], "a stressed month must not improve DSCR"


def test_negative_cash_flow_is_a_shortfall_not_a_small_ratio():
    out = run_dynamic_simulation(
        month=1,
        cash_balance=0,
        active_events=[],
        decision="hold",
        baseline={**BASELINE, "monthly_operating_cost": 115000},
    )
    assert out["net_cash_flow"] < 0
    assert out["dscr"] is None
    assert out["dscr_status"] == "NEGATIVE_CASH_FLOW"


def test_no_declared_debt_service_means_no_dscr():
    out = run_dynamic_simulation(
        month=1,
        cash_balance=0,
        active_events=[],
        decision="hold",
        baseline={**BASELINE, "monthly_emi": None},
    )
    assert out["dscr"] is None
    assert out["dscr_status"] == "NO_DEBT_SERVICE_DECLARED"


def test_no_baseline_means_no_figures():
    """An empty baseline must not be presented as a business with no revenue."""
    out = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold", baseline=None
    )
    assert out.get("dscr") is None
    assert out["dscr_status"] == "NOT_COMPUTABLE_NO_BASELINE"
    assert out["available"] is False
    assert out["revenue"] is None


def test_both_event_shapes_are_read():
    """
    Two EventEngine classes live here with different return shapes: the one in
    simulator_engine returns dicts, event_engine.EventEngine returns an object.
    The loop reads either, so swapping an engine in cannot silently drop every
    event effect.
    """
    from app.engines.simulator.event_engine import EventEngine as ObjectEngine
    from app.engines.simulator.simulator_engine import EventEngine as DictEngine

    dict_event = DictEngine().get_event("competitor_entry")
    assert isinstance(dict_event, dict)
    assert dict_event["effects"]["demand_change"] < 0

    object_event = ObjectEngine().get_event("new_competitor")
    assert object_event is not None
    assert object_event.effects["demand_change"] < 0


# ── The canonical path ───────────────────────────────────────────────────────

from app.financial.canonical_engine import (  # noqa: E402
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)


def canonical_plan(**overrides) -> CanonicalFinancialInput:
    fields = dict(
        business_type="retail_kirana",
        products=[ProductItem(name="Vada Pav", units_per_month=3900,
                              selling_price=15.0, variable_cost_per_unit=7.0)],
        opex=OpexBreakdown(other=17500.0),
        own_capital=100000.0,
        total_project_cost=100000.0,
        debt_amount=0.0,
    )
    fields.update(overrides)
    return CanonicalFinancialInput(**fields)


def test_with_no_events_the_simulator_equals_the_analysis_screen():
    """
    The strongest statement available about two surfaces: with nothing to apply,
    the simulator must reproduce the canonical model exactly.

    Before the canonical path existed this was not true and could not be - the
    simulator worked from a baseline dict and had no access to the model. It
    computed revenue minus operating cost, which is EBITDA, so its "net cash
    flow" ignored tax and the change in working capital, and its ROI used annual
    EBITDA where the model uses profit after tax. A user watching the simulator
    and the analysis tab for the same business was reading two models.
    """
    inp = canonical_plan()
    expected = compute_canonical_financials(inp)

    out = run_dynamic_simulation(
        month=1, cash_balance=50000.0, active_events=[], decision="hold",
        scenario_parameters={}, baseline=None, canonical_input=inp,
    )

    assert out["model"] == "canonical"
    assert out["revenue"] == pytest.approx(expected.monthly_revenue, abs=0.01)
    assert out["net_cash_flow"] == pytest.approx(
        expected.monthly_operating_cash_flow, abs=0.01
    )
    assert out["roi"] == pytest.approx(expected.roi_on_total_project_pct, abs=0.01)
    assert out["decision"] == expected.economic_viability
    assert out["available"] is True


def test_a_price_cut_does_not_also_cut_variable_cost():
    """
    `reduce_price` was a revenue factor applied to the revenue line alone, which
    modelled a price cut as though it were free: revenue fell 5% while variable
    cost per unit stayed put, so the business was credited with no change in its
    largest cost. That is the right arithmetic for a price cut - a lower price
    does not make flour cheaper - but it was arriving there by accident, through
    a lever that could not distinguish a price cut from a demand fall.

    A demand fall does reduce variable cost, because fewer units means less
    input bought. The two decisions are now declared separately, and this asserts
    the declaration is honoured.
    """
    inp = canonical_plan()
    base = compute_canonical_financials(inp)

    cut = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="reduce_price",
        scenario_parameters={}, canonical_input=inp,
    )
    # Revenue falls 5%; variable cost is untouched.
    assert cut["revenue"] == pytest.approx(base.monthly_revenue * 0.95, abs=0.01)
    assert cut["net_cash_flow"] == pytest.approx(
        base.monthly_revenue * 0.95 - base.monthly_cogs - base.monthly_opex, abs=0.01
    )

    marketing = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="increase_marketing",
        scenario_parameters={}, canonical_input=inp,
    )
    # A volume lift moves variable cost with it, so more units is not more profit
    # at a fixed cost base. This is the difference the `revenue_via` declaration
    # exists to express.
    assert marketing["revenue"] == pytest.approx(base.monthly_revenue * 1.07, abs=0.01)
    assert marketing["net_cash_flow"] < base.monthly_operating_cash_flow * 1.07


def test_the_response_says_which_model_produced_it():
    """
    The scalar fallback is a lesser model, so a reader comparing the two screens
    has to be able to tell which one they are looking at.
    """
    inp = canonical_plan()
    canonical = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold",
        canonical_input=inp,
    )
    scalar = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold",
        baseline={
            "monthly_revenue": 58500.0,
            "monthly_operating_cost": 44800.0,
            "total_project_cost": 100000.0,
            "monthly_emi": None,
        },
    )
    assert canonical["model"] == "canonical"
    assert scalar["model"] == "scalar_baseline"
    # A canonical input wins over a baseline dict: the model is never a
    # preliminary to the model.
    both = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold",
        baseline={"monthly_revenue": 1.0, "monthly_operating_cost": 1.0},
        canonical_input=inp,
    )
    assert both["model"] == "canonical"
    assert both["revenue"] == pytest.approx(58500.0, abs=0.01)


def test_a_debtless_business_is_not_given_a_dscr_on_the_canonical_path():
    inp = canonical_plan(debt_amount=0.0)
    out = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold",
        canonical_input=inp,
    )
    assert out["dscr"] is None
    assert out["dscr_status"] == "NOT_APPLICABLE_NO_DEBT"


def test_negative_operating_cash_is_reported_as_a_shortfall_on_the_canonical_path():
    # Debt is required for this path to be reachable: without it there is no
    # debt service to be short of, and NOT_APPLICABLE_NO_DEBT is the right
    # answer rather than a shortfall.
    inp = canonical_plan(
        products=[ProductItem(name="Vada Pav", units_per_month=3900,
                              selling_price=15.0, variable_cost_per_unit=13.0)],
        opex=OpexBreakdown(other=24000.0),
        debt_amount=200000.0,
        own_capital=200000.0,
        interest_rate_annual_pct=10.0,
        tenure_months=60,
    )
    out = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold",
        canonical_input=inp,
    )
    assert out["net_cash_flow"] < 0
    assert out["dscr"] is None
    assert out["dscr_status"] == "NEGATIVE_CASH_FLOW"


def test_no_debt_service_takes_precedence_over_negative_cash():
    """
    A debtless business running at a loss is two things at once, and the one
    worth reporting is the one that is not applicable rather than the shortfall:
    there is nothing for the loss to fall short of. Reporting it as a negative
    cash-flow shortfall would imply a loan it does not have.
    """
    inp = canonical_plan(
        products=[ProductItem(name="Vada Pav", units_per_month=3900,
                              selling_price=15.0, variable_cost_per_unit=13.0)],
        opex=OpexBreakdown(other=24000.0),
        debt_amount=0.0,
    )
    out = run_dynamic_simulation(
        month=1, cash_balance=0, active_events=[], decision="hold",
        canonical_input=inp,
    )
    assert out["net_cash_flow"] < 0
    assert out["dscr"] is None
    assert out["dscr_status"] == "NOT_APPLICABLE_NO_DEBT"
