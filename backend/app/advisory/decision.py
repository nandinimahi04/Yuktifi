"""
Decision gate: GO / CONDITIONAL GO / NO-GO / INSUFFICIENT EVIDENCE.

This replaces a four-line gate that compared `fin["dscr"] >= 1.25` directly. A
project with no debt has `dscr = None`, and `None >= 1.25` raises
`TypeError: '>=' not supported between instances of 'NoneType' and 'float'` -
so the single most common real case, an entrepreneur funding their business
from savings, crashed the decision endpoint.

The deeper problem was the binary outcome. A verdict of NO-GO was issued when
evidence was merely absent, which tells a first-time entrepreneur their business
is a bad idea when the truth is that nobody has measured it yet. So:

* Every gate reports its own status: PASS, FAIL, or UNKNOWN.
* UNKNOWN is never silently treated as FAIL, and never as PASS.
* NO-GO requires at least one gate to have actually FAILED on evidence.
* When a required gate is UNKNOWN, the decision is INSUFFICIENT EVIDENCE and
  the response says precisely which evidence would change it.

`INSUFFICIENT EVIDENCE` is not a soft NO-GO. It is a request for data, and it
carries the same weight in the UI: a plan cannot be recommended on unknown.
"""
from __future__ import annotations

from typing import Any, Optional

# ── Thresholds ──────────────────────────────────────────────────────────────
BASE_DSCR_TARGET = 1.25      # comfortable margin on debt service
BASE_DSCR_FLOOR = 1.0        # cash flow must at minimum cover debt service
STRESS_DSCR_FLOOR = 1.0      # must survive the worst modelled stress

#: DSCR required only when the business actually carries debt.
BASE_DSCR_CONDITIONAL = 1.0

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

GO = "GO"
CONDITIONAL_GO = "CONDITIONAL_GO"
NO_GO = "NO-GO"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _status_from_value(value: Optional[float], target: float, floor: float) -> str:
    if value is None:
        return UNKNOWN
    if value >= target:
        return PASS
    if value >= floor:
        # Above the floor but below target: viable, conditionally.
        return "PASS_WITH_CAVEAT"
    return FAIL


def _gates(fin: dict, market: dict, risk: dict) -> list[dict[str, Any]]:
    """Evaluate every gate and record what it actually knew."""
    has_debt = bool(fin.get("debt_amount")) or fin.get("dscr") is not None
    dscr = fin.get("dscr")
    worst = risk.get("worst_case_dscr")

    gates: list[dict[str, Any]] = []

    # ── Repayment capacity ──────────────────────────────────────────────────
    if not has_debt:
        gates.append({
            "gate": "repayment_capacity",
            "status": NOT_APPLICABLE,
            "value": None,
            "detail": (
                "The business carries no debt obligation, so there is no repayment capacity to "
                "test. This is a pass, not a gap in evidence."
            ),
            "counts_as_failure": False,
        })
    else:
        status = _status_from_value(dscr, BASE_DSCR_TARGET, BASE_DSCR_FLOOR)
        gates.append({
            "gate": "repayment_capacity",
            "status": status,
            "value": dscr,
            "detail": (
                f"Base DSCR is {dscr}, against a comfort target of {BASE_DSCR_TARGET} and an "
                f"absolute floor of {BASE_DSCR_FLOOR}."
                if dscr is not None else
                "The project carries debt but no DSCR was computed, so repayment capacity "
                "cannot be tested."
            ),
            "counts_as_failure": status == FAIL,
        })

    # ── Stress resilience ───────────────────────────────────────────────────
    gates.append({
        "gate": "stress_resilience",
        "status": UNKNOWN if worst is None else (PASS if worst >= STRESS_DSCR_FLOOR else FAIL),
        "value": worst,
        "detail": (
            f"Worst modelled stress DSCR is {worst}, against a floor of {STRESS_DSCR_FLOOR}."
            if worst is not None else
            "No stress test result was supplied, so resilience to a demand, cost or rate shock "
            "is untested."
        ),
        "counts_as_failure": worst is not None and worst < STRESS_DSCR_FLOOR,
    })

    # ── Demand evidence ─────────────────────────────────────────────────────
    units = market.get("estimated_units_monthly")
    gates.append({
        "gate": "demand_evidence",
        "status": PASS if units is not None else UNKNOWN,
        "value": units,
        "detail": (
            f"A demand estimate exists ({units} units/month)."
            if units is not None else
            "No supported local demand estimate is available, so the market side of the "
            "decision has not been tested."
        ),
        "counts_as_failure": False,
    })

    # ── Unit economics ──────────────────────────────────────────────────────
    margin = fin.get("net_margin_pct")
    gates.append({
        "gate": "unit_economics",
        "status": UNKNOWN if margin is None else (PASS if margin > 0 else FAIL),
        "value": margin,
        "detail": (
            f"Net margin is {margin}%, after variable cost, fixed operating cost, interest and "
            f"depreciation."
            if margin is not None else
            "Net margin was not computed, so it is unknown whether revenue covers all costs."
        ),
        "counts_as_failure": margin is not None and margin <= 0,
    })

    # ── Financing reconciliation ────────────────────────────────────────────
    gap = fin.get("financing_gap")
    reconciled = fin.get("financing_reconciled")
    gates.append({
        "gate": "financing",
        "status": UNKNOWN if reconciled is None else (PASS if reconciled else FAIL),
        "value": gap,
        "detail": (
            f"Funding reconciles to project cost."
            if reconciled else
            f"Funding does not reconcile: an unfunded gap of {abs(gap or 0):,.0f} remains."
        ),
        "counts_as_failure": reconciled is False,
    })

    return gates


def decide(
    fin: dict,
    market: dict,
    competitors: dict,
    risk: dict,
    schemes: list[dict],
) -> dict[str, Any]:
    """
    Produce a decision, its reasons, and what evidence would change it.

    Order of resolution:
      1. Any gate FAILED on evidence            -> NO-GO
      2. Gates pass or do not apply, none unknown -> GO
      3. Gates pass with caveats, none unknown    -> CONDITIONAL GO
      4. A required gate is UNKNOWN               -> INSUFFICIENT EVIDENCE
    """
    gates = _gates(fin, market, risk)
    failures = [g for g in gates if g["counts_as_failure"]]
    unknowns = [g for g in gates if g["status"] == UNKNOWN]
    caveats = [g for g in gates if g["status"] == "PASS_WITH_CAVEAT"]

    if failures:
        decision = NO_GO
    elif unknowns:
        decision = INSUFFICIENT_EVIDENCE
    elif caveats:
        decision = CONDITIONAL_GO
    else:
        decision = GO

    why: list[str] = []
    changes: list[str] = []

    for g in failures:
        why.append(f"Failed check - {g['gate']}: {g['detail']}")

    for g in caveats:
        why.append(f"Passes with a caveat - {g['gate']}: {g['detail']}")

    for g in unknowns:
        why.append(f"Could not be evaluated - {g['gate']}: {g['detail']}")

    # What would change the outcome, mapped to the specific missing input.
    change_actions: dict[str, str] = {
        "repayment_capacity": (
            "Obtain actual loan terms (principal, rate, tenure) so DSCR can be computed against "
            "the real repayment schedule."
        ),
        "stress_resilience": (
            "Run the stress matrix (demand down 10% and 20%, costs up 10% and 15%, interest up "
            "2%, and the combined case) so resilience is measured rather than assumed."
        ),
        "demand_evidence": (
            "Supply catchment population evidence and a business-specific demand assumption so "
            "the achievable sales volume is grounded."
        ),
        "unit_economics": (
            "Enter actual prices and costs - from quotations and bills, not sector averages - so "
            "net margin can be computed."
        ),
        "financing": (
            "Reconcile the funding stack: project cost must equal own capital plus other funding "
            "plus subsidy plus debt."
        ),
    }
    for g in failures + unknowns:
        action = change_actions.get(g["gate"])
        if action:
            changes.append(action)

    if not why:
        why.append(
            "Every applicable check passed on available evidence: repayment capacity, stress "
            "resilience, demand, unit economics and financing reconciliation."
        )

    # Evidence coverage over the specific inputs this decision depends on.
    evidence_inputs = {
        "catchment_population": market.get("population") is not None,
        "households": market.get("households") is not None,
        "demand_estimate": market.get("estimated_units_monthly") is not None,
        "competitor_survey": competitors.get("mapped_count") is not None,
        "repayment_capacity": any(
            g["gate"] == "repayment_capacity" and g["status"] != UNKNOWN for g in gates
        ),
        "stress_result": risk.get("worst_case_dscr") is not None,
        "net_margin": fin.get("net_margin_pct") is not None,
    }
    evidence_coverage = sum(evidence_inputs.values()) / len(evidence_inputs)
    calculation_integrity = float(fin.get("calculation_integrity", 1) or 1)
    confidence = round(
        min(1.0, 0.5 * evidence_coverage + 0.5 * (1.0 if calculation_integrity == 1 else 0.0)), 2
    )

    return {
        "decision": decision,
        "why": why,
        "what_would_change_it": changes,
        "confidence": {
            "overall": confidence,
            "evidence_coverage": round(evidence_coverage, 2),
            "calculation_integrity": calculation_integrity,
            "inputs": evidence_inputs,
        },
        "gates": gates,
        "failed_gates": [g["gate"] for g in failures],
        "unevaluated_gates": [g["gate"] for g in unknowns],
        "thresholds": {
            "base_dscr_target": BASE_DSCR_TARGET,
            "base_dscr_floor": BASE_DSCR_FLOOR,
            "stress_dscr_floor": STRESS_DSCR_FLOOR,
        },
        "decision_basis": (
            "A NO-GO requires at least one check to have actually failed on evidence. Absent "
            "evidence produces INSUFFICIENT EVIDENCE, which is a request for data rather than a "
            "negative judgement about the business."
        ),
        "scheme_status": {x["scheme"]: x["status"] for x in schemes or []},
    }
