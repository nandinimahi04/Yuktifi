"""
Dynamic event simulator.

The financial impact of a decision must come from the session's own canonical
model. This module previously declared `revenue = 60000`, `operating_cost =
42000`, divided annual cash flow by a hardcoded `200000` to produce an ROI, and
divided monthly cash flow by a hardcoded "Assuming 8k EMI" to produce a DSCR.

A DSCR divided by an EMI that no lender agreed to is not a DSCR; it is a number
whose denominator was chosen to make the output look healthy. Both ratios are
now computed from declared inputs, and when those inputs are absent the ratios
are withheld rather than manufactured.

Two paths, in order of preference:

* When the caller supplies the session's `canonical_input`, the events and the
  decision are expressed as adjustments to that input and the full canonical
  model is re-run, so every figure on the response - DSCR, ROI, break-even,
  verdict - is the same number the analysis screen showed for the same business.
* Without it, the module falls back to a scalar model over a declared
  `baseline` dict. That fallback is a lesser model: it works from a revenue and
  a cost rather than from products, opex lines, capital and a loan, so its
  figures can legitimately differ from the canonical ones. The response says
  which path produced it, because a reader comparing the two screens should
  know whether they are comparing like with like.

Event effects are deterministic multipliers declared in the event table. User
decision effects are declared here as named assumptions, because the effect of
"increase marketing" on a given business genuinely cannot be known in advance -
which is why each carries a stated basis and can be overridden per scenario.

The mechanism matters, and was previously unstated. A revenue effect does not
say *which* part of revenue moves. A price cut takes revenue down while variable
cost per unit stays where it is; a marketing lift takes volume up, so it drags
variable cost up with it. Applying both to the revenue line alone, as this
module did, modelled the price cut as though it were free - profit fell by 5% of
revenue when it should have fallen by 5% of revenue with no offsetting saving at
all - and it gave the marketing lift credit for a cost reduction that never
happens. Each decision therefore declares `revenue_via`.
"""
from __future__ import annotations

import logging
from dataclasses import replace as _dc_replace
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: Declared effect of each user decision on the baseline. These are model
#: assumptions, not observations, and are reported as such.
#:
#: `revenue_via` states which part of the revenue line moves:
#:   "units" - volume moves, so variable cost per unit moves with it. Use for a
#:             demand or marketing change.
#:   "price" - the selling price moves, so variable cost per unit is unchanged
#:             and the whole reduction lands on profit. Use for a price cut.
DECISION_EFFECTS: dict[str, dict[str, Any]] = {
    "hold": {
        "revenue_factor": 1.0,
        "revenue_via": "units",
        "operating_cost_add": 0.0,
        "basis": "No change to trading. Baseline figures stand.",
    },
    "increase_marketing": {
        "revenue_factor": 1.07,
        "revenue_via": "units",
        "operating_cost_add": None,  # taken from scenario marketing_spend
        "basis": (
            "ASSUMPTION: a 7% volume lift from additional marketing spend, so revenue and "
            "variable cost per unit both rise. The true elasticity is unknown and varies by "
            "business; override with marketing_spend and an observed response."
        ),
    },
    "reduce_price": {
        "revenue_factor": 0.95,
        # A price cut, not a demand fall: variable cost per unit does not move,
        # so applying this to volume would credit the business with a saving it
        # does not get.
        "revenue_via": "price",
        "operating_cost_add": 0.0,
        "basis": (
            "ASSUMPTION: a 5% cut to the selling price, with volume held. Variable cost per "
            "unit is unchanged, so the full 5% of revenue is lost profit. This ignores any "
            "volume response, so it understates the benefit if the cut drives volume. Provide a "
            "volume assumption to model it properly."
        ),
    },
    "improve_service": {
        "revenue_factor": 1.02,
        "revenue_via": "units",
        "operating_cost_add": 2000.0,
        "basis": (
            "ASSUMPTION: a 2% volume lift for an additional Rs 2,000 monthly cost. "
            "Unvalidated."
        ),
    },
}

DEFAULT_MARKETING_SPEND = 5000.0


class EventEngine:
    """Deterministic event table. Effects are declared multipliers, not guesses."""

    def __init__(self) -> None:
        self.events: dict[str, dict[str, Any]] = {
            "monsoon": {
                "event_id": "monsoon",
                "title": "Monsoon season",
                "effects": {"demand_change": -0.25, "price_pressure": -0.10},
                "description": "Footfall and construction demand fall; input supply tightens.",
            },
            "festival": {
                "event_id": "festival",
                "title": "Festival season",
                "effects": {"demand_change": 0.30, "price_pressure": 0.05},
                "description": "Consumer spending peaks for several weeks.",
            },
            "drought": {
                "event_id": "drought",
                "title": "Drought",
                "effects": {"demand_change": -0.20, "price_pressure": 0.20},
                "description": "Input costs rise sharply on poor supply.",
            },
            "fuel_price_shock": {
                "event_id": "fuel_price_shock",
                "title": "Fuel price shock",
                "effects": {"demand_change": -0.10, "price_pressure": 0.15},
                "description": "Transport and logistics costs increase.",
            },
            "competitor_entry": {
                "event_id": "competitor_entry",
                "title": "New competitor opens",
                "effects": {"demand_change": -0.15, "price_pressure": -0.12},
                "description": "A comparable business opens nearby, taking share.",
            },
            "government_scheme": {
                "event_id": "government_scheme",
                "title": "Scheme approval received",
                "effects": {"demand_change": 0.05, "price_pressure": 0.0},
                "description": "Subsidy or loan support confirmed (conditional on actual approval).",
            },
        }

    def get_event(self, event_id: str) -> Optional[dict[str, Any]]:
        return self.events.get(event_id)

    def list_events(self) -> list[dict[str, Any]]:
        return list(self.events.values())


event_engine = EventEngine()


def _event_field(event: Any, name: str, default: Any = None) -> Any:
    """
    Two EventEngine classes exist in this package: the one defined in this module
    returns dicts, while `event_engine.EventEngine` returns a SimulatorEvent
    object. This handles either shape so the two cannot be swapped between
    without breaking every simulation.
    """
    if isinstance(event, dict):
        return event.get(name, default)
    return getattr(event, name, default)


def _collect_effects(
    active_events: list[str], decision: str, scenario_parameters: dict[str, Any]
) -> tuple[float, float, float, list[dict[str, Any]]]:
    """
    Reduce the events and the decision to three multipliers:
    (units_factor, price_factor, cost_addition), plus the audit trail.

    Events act on volume and price separately because they are separate things:
    a monsoon cuts footfall *and* squeezes prices, and one does not stand in for
    the other.
    """
    applied: list[dict[str, Any]] = []
    units_factor = 1.0
    price_factor = 1.0

    for event_id in active_events or []:
        event = event_engine.get_event(event_id)
        if not event:
            applied.append({"event": event_id, "applied": False, "reason": "Unknown event id."})
            continue
        effects = _event_field(event, "effects") or {}
        if "demand_change" in effects:
            units_factor *= 1 + effects["demand_change"]
        if "price_pressure" in effects:
            price_factor *= 1 + effects["price_pressure"]
        applied.append({
            "event": event_id,
            "title": _event_field(event, "title", event_id),
            "applied": True,
            "description": _event_field(event, "description", "") or "",
        })

    effect = DECISION_EFFECTS.get(decision)
    if effect is None:
        applied.append({"decision": decision, "applied": False, "reason": "Unknown decision."})
        effect = DECISION_EFFECTS["hold"]

    if effect["revenue_via"] == "price":
        price_factor *= effect["revenue_factor"]
    else:
        units_factor *= effect["revenue_factor"]

    cost_add = effect["operating_cost_add"]
    if cost_add is None:
        cost_add = scenario_parameters.get("marketing_spend", DEFAULT_MARKETING_SPEND)

    return units_factor, price_factor, float(cost_add or 0.0), applied


def run_dynamic_simulation(
    month: int,
    cash_balance: float,
    active_events: list[str],
    decision: str,
    scenario_parameters: Optional[dict[str, Any]] = None,
    baseline: Optional[dict[str, Any]] = None,
    canonical_input: Optional[Any] = None,
) -> dict[str, Any]:
    """
    Compute the cash impact of a decision under a set of events.

    Preferred path, when `canonical_input` is supplied: the events and the
    decision become adjustments to the session's own canonical input, and the
    full canonical model is re-run. Every figure below is then the same number
    the analysis screen produced for the same business.

    Fallback path, when it is not: a scalar model over a declared `baseline`.
    `baseline` supplies the business's own declared figures:
        monthly_revenue       required to compute anything
        monthly_operating_cost required to compute anything
        total_project_cost    required for ROI; None omits the ratio
        monthly_emi           required for DSCR; None omits the ratio
        monthly_interest      optional, for a more accurate debt-service view

    Every argument that is required and absent causes the affected ratio to be
    withheld with a reason. Nothing is assumed.
    """
    scenario_parameters = scenario_parameters or {}
    baseline = baseline or {}

    if canonical_input is not None:
        return _run_canonical(
            cash_balance, active_events, decision, scenario_parameters, canonical_input
        )

    monthly_revenue = baseline.get("monthly_revenue")
    monthly_operating_cost = baseline.get("monthly_operating_cost")

    if monthly_revenue is None or monthly_operating_cost is None:
        return {
            "revenue": None,
            "operating_cost": None,
            "net_cash_flow": None,
            "roi": None,
            "dscr": None,
            "dscr_status": "NOT_COMPUTABLE_NO_BASELINE",
            "roi_status": "NOT_COMPUTABLE_NO_BASELINE",
            "available": False,
            "model": "scalar_baseline",
            "reason": (
                "This simulation needs the business's own monthly revenue and operating cost. "
                "Run the financial analysis first so the canonical model can supply them. "
                "No figures are assumed."
            ),
            "assumptions": [],
        }

    units_factor, price_factor, cost_add, applied = _collect_effects(
        active_events, decision, scenario_parameters
    )

    # On the scalar path the two multipliers can only be combined, so a
    # simultaneous volume and price move is reported as one net revenue factor.
    # The canonical path keeps them apart, which is the whole reason to prefer it.
    revenue = float(monthly_revenue) * units_factor * price_factor
    operating_cost = float(monthly_operating_cost) + cost_add

    net_cash_flow = round(revenue - operating_cost, 2)

    # ROI only with a declared project cost. It is annual cash flow over total
    # project cost - not over an assumed investment.
    project_cost = baseline.get("total_project_cost")
    if net_cash_flow > 0 and project_cost:
        roi = round((net_cash_flow * 12) / float(project_cost) * 100, 2)
        roi_status = "COMPUTED"
    else:
        roi = None
        roi_status = (
            "NOT_COMPUTABLE" if net_cash_flow <= 0 else "NO_PROJECT_COST_DECLARED"
        )

    # DSCR only against a declared debt service. A DSCR against an assumed
    # payment is not a coverage ratio.
    #
    # The debt service is the EMI alone. This added the monthly interest on top
    # of it (`emi + interest`), which counts the same money twice: an EMI is
    # already principal plus interest. The inflated denominator made every
    # simulated scenario look safer than the declared loan - exactly backwards
    # for a stress tool, since the whole point is to find where the DSCR falls
    # below 1.0.
    emi = baseline.get("monthly_emi")
    if emi and emi > 0:
        debt_service = float(emi)
        if net_cash_flow <= 0:
            # A negative cash flow over a positive debt service is not a small
            # ratio; it is a shortfall, and reporting it as e.g. -0.4 invites it
            # to be read as a small number rather than as a business that cannot
            # service its debt at all.
            dscr = None
            dscr_status = "NEGATIVE_CASH_FLOW"
        else:
            dscr = round(net_cash_flow / debt_service, 2)
            dscr_status = "COMPUTED"
    else:
        dscr = None
        dscr_status = "NO_DEBT_SERVICE_DECLARED"

    effect = DECISION_EFFECTS.get(decision, DECISION_EFFECTS["hold"])
    assumptions = [{
        "decision": decision,
        "basis": effect["basis"],
        "revenue_factor_applied": effect["revenue_factor"],
        "revenue_applied_via": effect["revenue_via"],
        "operating_cost_added": cost_add,
    }] + applied

    return {
        "revenue": round(revenue, 2),
        "operating_cost": round(operating_cost, 2),
        "net_cash_flow": net_cash_flow,
        "roi": roi,
        "roi_status": roi_status,
        "dscr": dscr,
        "dscr_status": dscr_status,
        "ending_cash_balance": round(float(cash_balance) + net_cash_flow, 2),
        "starting_cash_balance": float(cash_balance),
        "monthly_emi": float(emi) if emi else None,
        "available": True,
        "model": "scalar_baseline",
        "reason": None,
        "assumptions": assumptions,
    }


def _run_canonical(
    cash_balance: float,
    active_events: list[str],
    decision: str,
    scenario_parameters: dict[str, Any],
    canonical_input: Any,
) -> dict[str, Any]:
    """
    Re-run the session's canonical model with the events and the decision applied.

    The events and the decision are translated into the canonical what-if levers
    and handed to `apply_what_if`, so the adjustment semantics are the same ones
    the what-if simulator uses. Nothing is recomputed here: this function reads
    the model's output.
    """
    from app.financial.canonical_engine import compute_canonical_financials
    from app.financial.projection import WhatIfAdjustments, apply_what_if

    units_factor, price_factor, cost_add, applied = _collect_effects(
        active_events, decision, scenario_parameters
    )

    adjustments = WhatIfAdjustments(
        units_multiplier=units_factor,
        price_delta_pct=(price_factor - 1.0) * 100.0,
    )
    # The declared decisions add an absolute monthly cost. The canonical lever is
    # a percentage of the opex line, so the addition is converted against the
    # plan's own opex. Expressed this way the canonical model owns the arithmetic
    # and the declared figure stays an absolute rupee amount.
    base_opex = canonical_input.opex.total_monthly_opex
    if cost_add and base_opex:
        adjustments = _dc_replace(
            adjustments, fixed_cost_delta_pct=cost_add / base_opex * 100.0
        )

    shocked_input, _applied = apply_what_if(canonical_input, adjustments)
    result = compute_canonical_financials(_dc_replace(shocked_input, include_scenarios=False))

    # The model's own cash flow, not a revenue-minus-opex reconstruction. On the
    # scalar path `net_cash_flow` is EBITDA, which ignores tax and the change in
    # working capital; here it is the figure the projection is built from.
    net_cash_flow = result.cfads_monthly if result.debt_amount else result.monthly_operating_cash_flow
    dscr = _dscr_for(result)

    effect = DECISION_EFFECTS.get(decision, DECISION_EFFECTS["hold"])
    assumptions = [{
        "decision": decision,
        "basis": effect["basis"],
        "revenue_factor_applied": effect["revenue_factor"],
        "revenue_applied_via": effect["revenue_via"],
        "operating_cost_added": cost_add,
    }] + applied

    return {
        "revenue": round(result.monthly_revenue, 2),
        "operating_cost": round(result.monthly_variable_costs + result.monthly_opex, 2),
        "net_cash_flow": round(net_cash_flow, 2),
        "roi": result.roi_on_total_project_pct,
        "roi_status": "COMPUTED" if result.roi_on_total_project_pct is not None else "NOT_COMPUTABLE",
        "dscr": dscr[0],
        "dscr_status": dscr[1],
        "ending_cash_balance": round(float(cash_balance) + net_cash_flow, 2),
        "starting_cash_balance": float(cash_balance),
        "monthly_emi": result.monthly_emi,
        "available": True,
        "model": "canonical",
        "reason": None,
        "assumptions": assumptions,
        # The verdict travels so the response is not a set of ratios with no
        # conclusion attached, and so it is the model's own wording.
        "decision": result.economic_viability,
        "viability_reasons": result.viability_reasons,
        "break_even_units": result.break_even_units_monthly,
    }


def _dscr_for(result: Any) -> tuple[Optional[float], str]:
    """
    The model's DSCR and why it is or is not available.

    Mirrors the what-if simulator's three-way answer: a value, "no debt service
    to cover", or "the cash to cover it does not exist". The scalar path
    reported a debtless business as having no debt service, which is right, and
    a negative-cash business as a small ratio, which was not.
    """
    if result.dscr_status == "NOT_APPLICABLE_NO_DEBT" or result.debt_service_status == "NOT_APPLICABLE_NO_DEBT":
        return None, "NOT_APPLICABLE_NO_DEBT"
    if result.dscr_status == "NEGATIVE_CFADS":
        return None, "NEGATIVE_CASH_FLOW"
    if result.dscr is None:
        return None, "NO_DEBT_SERVICE_DECLARED"
    return result.dscr, "COMPUTED"
