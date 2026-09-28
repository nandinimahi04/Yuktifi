"""Section 15 — recalculation chain for the What-If Simulator.

The what-if must re-run the SAME canonical model as the dashboard, with the
requested changes applied. It never recomputes profit from a reduced summary
dict, because a summary drops cost lines and silently produces a different
answer to the one the user is looking at on screen.

Every change goes through the canonical `apply_what_if`, so the levers here are
the engine's own and this surface cannot drift from the model.
`revenue_delta_pct` / `cost_delta_pct` is the original API, retained for
compatibility and translated into levers; the full lever set sits alongside it
so a caller is not confined to a demand shock and a cost shock.
"""
from dataclasses import replace
from typing import Any, Dict, Optional

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    compute_canonical_financials,
)
from app.financial.projection import WhatIfAdjustments, apply_what_if
from app.engines.recommendation_engine import compute_yukti_score

#: DSCR below this is treated as failing the stress test. A presentation
#: threshold; the canonical gate benchmarks are the model's own.
DSCR_STRESS_GATE = 1.0


def _survives_stress(result) -> Optional[bool]:
    """
    Whether the scenario still covers its own debt service, or None when that
    question does not apply.

    This used to be `dscr is not None and dscr >= 1.0`, which reports False for
    a business with no debt. A borrower-free business cannot fail a debt-service
    coverage test - there is no debt service - so it was being shown as failing
    the stress test on every what-if run. That is the same mistake as reading a
    null as a zero, in the opposite direction: an unanswered question recorded
    as a bad answer. None lets the caller say "not applicable" instead.
    """
    if result.debt_service_status == "NOT_APPLICABLE_NO_DEBT" or result.dscr_status == "NOT_APPLICABLE_NO_DEBT":
        return None
    if result.dscr_status == "NEGATIVE_CFADS":
        # Operating cash is negative, so the debt service is unfunded whatever
        # the ratio says. The engine declines to publish a ratio here, and this
        # is the case the ratio would have reported as 0.
        return False
    if result.dscr is None:
        return None
    return result.dscr >= DSCR_STRESS_GATE


def run_simulation(
    base_state: Dict[str, Any],
    revenue_delta_pct: float = 0.0,
    cost_delta_pct: float = 0.0,
    tenure_override_years: Optional[int] = None,
    adjustments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Re-run the session's canonical model with the caller's changes applied.

    `base_state` must contain `canonical_input` (a CanonicalFinancialInput) so
    the changes are applied to the identical model the dashboard rendered, plus
    the scoring context: dimension_scores and confidence_multiplier.

    Two ways to ask the same question:

    * `adjustments` takes the canonical `WhatIfAdjustments` levers directly -
      units, price, variable cost, fixed cost, interest rate, tenure, own
      capital, debt, other funding, tax rate, working days, price growth and the
      working-capital cycle. The API exposes all of them, so a caller is not
      limited to the two shocks below.
    * `revenue_delta_pct` / `cost_delta_pct` / `tenure_override_years` are the
      original three fields, kept so existing clients keep working. They are
      translated into levers and applied through the same path, so the old and
      new ways of asking cannot answer differently.

    When both are supplied the explicit levers win, field by field, because a
    caller that named a specific lever meant it. Unnamed levers keep their
    legacy value.
    """
    base_input: Optional[CanonicalFinancialInput] = base_state.get("canonical_input")

    if base_input is None:
        return {
            "error": "CANONICAL_INPUT_UNAVAILABLE",
            "detail": (
                "The what-if simulator requires the canonical financial input. "
                "Recomputing from a summary would drop cost lines and produce a "
                "profit figure that disagrees with the dashboard."
            ),
            "revenue_delta_pct": revenue_delta_pct,
            "cost_delta_pct": cost_delta_pct,
        }

    levers = _legacy_levers(revenue_delta_pct, cost_delta_pct, tenure_override_years)
    if adjustments:
        for key, value in adjustments.items():
            if value is not None and hasattr(WhatIfAdjustments, key):
                levers[key] = value

    base_result = compute_canonical_financials(base_input)
    # Scenario results are one level deep; without this a what-if inherits
    # include_scenarios=True and re-runs the whole stress matrix.
    base_input = replace(base_input, include_scenarios=False)
    shocked_input, applied = apply_what_if(base_input, WhatIfAdjustments(**levers))
    result = compute_canonical_financials(shocked_input)

    emi = result.monthly_emi
    dscr = result.dscr
    net_profit = result.monthly_pat
    roi = result.roi_on_total_project_pct
    break_even = result.break_even_units_monthly
    decision = result.economic_viability
    decision_changed = result.economic_viability != base_result.economic_viability
    survives_stress = _survives_stress(result)

    score = compute_yukti_score(
        base_state["dimension_scores"], base_state["confidence_multiplier"], dscr
    )

    return {
        "emi": emi,
        "dscr": dscr,
        "dscr_status": result.dscr_status,
        "net_profit": net_profit,
        "monthly_revenue": result.monthly_revenue,
        "monthly_ebitda": result.monthly_ebitda,
        "cfads_monthly": result.cfads_monthly,
        "break_even_units": break_even,
        "verdict": score.verdict,
        "final_score": score.final_score,
        "simulated_roi": roi,
        "decision": decision,
        "decision_changed": decision_changed,
        "viability_reasons": result.viability_reasons,
        # None means the question does not apply (no debt service to cover), not
        # that the business failed. A caller that needs a boolean can branch on
        # this explicitly rather than being handed False for a debtless plan.
        "survives_stress": survives_stress,
        "survives_stress_applicable": survives_stress is not None,
        "applied_shocks": {
            "revenue_delta_pct": revenue_delta_pct,
            "cost_delta_pct": cost_delta_pct,
            "tenure_override_years": tenure_override_years,
        },
        # Which levers actually moved, with the value before and after. The
        # three-field form above cannot express a change of capital, a change of
        # tax rate or a longer working-capital cycle, so a caller that used them
        # had no way to see what it had really asked for.
        "adjustments": {k: v for k, v in levers.items() if v is not None},
        "applied_adjustments": applied,
        # Enough of the model for the caller to reconcile its screen without a
        # second request.
        "monthly_pat": result.monthly_pat,
        "monthly_opex": result.monthly_opex,
        "monthly_variable_costs": result.monthly_variable_costs,
        "net_working_capital": result.net_working_capital,
        "margin_of_safety_pct": result.margin_of_safety_pct,
        "total_repayment": result.total_repayment,
        "total_interest_paid": result.total_interest_paid,
        # Whether the profit figure above is actually after tax. A what-if can
        # set a tax rate the plan never declared, and a caller that assumed the
        # base was post-tax would otherwise be comparing a post-tax number with
        # a pre-tax one.
        "tax_status": result.tax_status,
        "monthly_tax": result.monthly_tax,
        "base_tax_status": base_result.tax_status,
        "base_decision": base_result.economic_viability,
        "base_net_profit": base_result.monthly_pat,
    }


def _legacy_levers(
    revenue_delta_pct: float, cost_delta_pct: float, tenure_override_years: Optional[int]
) -> Dict[str, Any]:
    """
    Translate the original three request fields into canonical levers.

    `revenue_delta_pct` has always been a volume shock here, so it becomes
    `units_multiplier`. Reinterpreting it as a price move would silently change
    the meaning of every existing client's call - and for the worse, because a
    demand fall reduces variable cost with it while a price cut does not.
    """
    levers: Dict[str, Any] = {}
    if revenue_delta_pct:
        levers["units_multiplier"] = 1.0 + revenue_delta_pct / 100.0
    if cost_delta_pct:
        levers["variable_cost_delta_pct"] = cost_delta_pct
    if tenure_override_years:
        levers["tenure_months"] = tenure_override_years * 12
    return levers
