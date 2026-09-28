"""
Stress-test presentation over the canonical stress matrix.

This module used to carry its own copy of the shock matrix. That copy had
already drifted from the canonical one in `app.financial.projection`, and the
divergence was not cosmetic: the two `combined_severe` entries applied
*different* shocks. The canonical combined case also takes selling price down
10%, so it models a business facing a competitor who cuts price; this module's
combined case left price alone. Both were labelled "combined severe", and both
published a `monthly_ebitda` for it. A user comparing the stress tab against the
scenario tab on the business-plan screen was comparing two different worst cases
and neither was labelled as the approximation it was.

The matrix now comes from `app.financial.projection.STRESS_SCENARIOS` and the
shock is applied by its `apply_shock`, so the scenarios cannot drift again.

What remains here is presentation, which the canonical engine has no opinion
about: which thresholds a scenario crossed, why the verdict moved, and a
one-sentence reading of the matrix as a whole. It re-runs the canonical model
once per scenario to reach the full result, which is model execution rather than
a second implementation of the arithmetic.

Shock semantics, stated explicitly because they are not interchangeable:

* Demand shock scales UNITS SOLD. Revenue falls with volume while fixed costs
  and per-unit variable cost stay put, so EBITDA absorbs the full operating
  leverage. This is the honest reading of "demand falls": you sell less, your
  rent does not fall.
* Price shock scales SELLING PRICE. Unit volume is held, so the whole reduction
  lands on revenue while variable cost per unit is unchanged. A competitor
  undercutting on price is a different event from a demand fall, and the two
  reach the same EBITDA by different routes.
* Cost shock scales VARIABLE COST PER UNIT only. Fixed operating costs are not
  inflated, because an input price rise does not raise the rent.
* Interest shock adds to the declared rate and rebuilds the amortisation
  schedule, so it changes both EMI and total interest.
* The combined case applies all of the above simultaneously. It is the case that
  matters, because the effects compound: a demand fall and a cost rise hit the
  same contribution line, and a rate rise then lands on a thinner margin.
"""
from __future__ import annotations

from typing import Any, Optional

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    CanonicalFinancialResult,
    compute_canonical_financials,
)
from app.financial.projection import STRESS_SCENARIOS, apply_shock

# ── The matrix ──────────────────────────────────────────────────────────────

# Re-exported from the canonical matrix for callers that still read these
# module-level names. Derived rather than restated, so a change to the matrix
# cannot leave these describing a stress suite that is no longer run. Order
# follows the matrix's own declaration order - mildest shock first - so a
# reader scanning the published metadata sees them graded, not alphabetised.
def _declared_shocks(attr: str) -> tuple[float, ...]:
    seen: list[float] = []
    for spec in STRESS_SCENARIOS:
        value = getattr(spec, attr)
        if value and value not in seen:
            seen.append(value)
    return tuple(seen)


DEMAND_SHOCKS: tuple[float, ...] = _declared_shocks("demand_pct")
COST_SHOCKS: tuple[float, ...] = _declared_shocks("cost_pct")
INTEREST_SHOCK_POINTS: float = max(
    (s.rate_points for s in STRESS_SCENARIOS if s.rate_points), default=2.0
)

#: DSCR below this is treated as a coverage breach. A presentation threshold:
#: the canonical gate benchmarks are the model's own, and this only decides which
#: scenarios the resilience summary calls failures.
DSCR_BREACH_THRESHOLD = 1.1

#: EBIT margin below this is treated as an operating loss.
EBITDA_BREACH_THRESHOLD = 0.0



# ── Comparison helpers ──────────────────────────────────────────────────────

def _dscr_delta(stressed: CanonicalFinancialResult, base: CanonicalFinancialResult) -> Optional[float]:
    """
    DSCR change, or None when it is not measurable.

    A business with no debt has no DSCR in either scenario, and None correctly
    reports "not measurable" rather than 0.0, which would read as "the shock
    changed nothing".
    """
    if stressed.dscr is None or base.dscr is None:
        return None
    return round(stressed.dscr - base.dscr, 2)


def _dscr_breached(result: CanonicalFinancialResult) -> bool:
    """
    True when the scenario fails to cover its own debt service.

    Negative CFADS counts as a breach. It is reported with dscr=None rather
    than a negative ratio, so the breach has to be detected from the status, not
    from a comparison on dscr.
    """
    if result.debt_amount and result.dscr_status == "NEGATIVE_CFADS":
        return True
    return result.dscr is not None and result.dscr < DSCR_BREACH_THRESHOLD


def _breaches(result: CanonicalFinancialResult) -> list[str]:
    """Every threshold this scenario crosses. Empty list means it held."""
    out: list[str] = []
    if result.dscr is not None and result.dscr < DSCR_BREACH_THRESHOLD:
        out.append(
            f"DSCR fell to {result.dscr}, below the {DSCR_BREACH_THRESHOLD} coverage floor."
        )
    if result.dscr_status == "NEGATIVE_CFADS" and result.debt_amount:
        out.append(
            f"Annual operating cash is negative ({round(result.cfads_annual, 2)}), so debt service "
            f"of {round(result.annual_debt_service, 2)} is unfunded."
        )
    if result.monthly_ebitda < EBITDA_BREACH_THRESHOLD:
        out.append(
            f"Monthly EBITDA is {round(result.monthly_ebitda, 2)}, so the business does not "
            f"cover its own operating costs."
        )
    if not result.financing_reconciled:
        out.append(f"Financing gap of {abs(result.financing_gap):,.0f} is unreconciled.")
    return out


def _primary_driver(
    base: CanonicalFinancialResult, stressed: CanonicalFinancialResult
) -> str:
    """
    Which constraint actually moved, so the UI can say WHY the verdict changed
    rather than only that it did.
    """
    if stressed.economic_viability == base.economic_viability:
        return "No change in economic viability under this shock."

    cfads_delta = stressed.cfads_monthly - base.cfads_monthly
    emi_delta = stressed.monthly_emi - base.monthly_emi

    if emi_delta > 0.01 and abs(emi_delta) >= abs(cfads_delta):
        return (
            f"Debt service: the higher interest rate raised the monthly repayment by "
            f"{round(emi_delta, 2)}, which outweighed the change in operating cash."
        )
    if cfads_delta < 0:
        return (
            f"Operating cash generation fell by {round(abs(cfads_delta), 2)} per month, which is "
            f"the direct operating effect of the shock."
        )
    if (
        stressed.break_even_units_monthly
        and base.break_even_units_monthly
        and stressed.break_even_units_monthly > base.break_even_units_monthly
    ):
        return (
            f"Break-even volume rose from {base.break_even_units_monthly} to "
            f"{stressed.break_even_units_monthly} units per month."
        )
    return "Operating cost structure."


# ── Suite ───────────────────────────────────────────────────────────────────

def _summary(
    base: CanonicalFinancialResult,
    survived: list[str],
    failed: list[str],
    debtless: bool = False,
) -> str:
    """One sentence saying what the matrix means, in the reader's terms."""
    total = len(survived) + len(failed)
    held = (
        f"The business holds under {len(survived)} of {total} stress scenarios."
        if not failed else
        f"The business breaks down under {len(failed)} of {total} stress scenarios"
        + (f", first failing under {failed[0].replace('_', ' ')}." if failed else ".")
    )
    if debtless:
        return (
            f"{held} No debt service applies, so a DSCR breach is not possible: the question "
            f"tested here is whether the business keeps covering its own operating costs."
        )
    return held


def run_stress_test_suite(base_input: CanonicalFinancialInput) -> dict[str, Any]:
    """Run the base case and the full shock matrix."""
    base_result = compute_canonical_financials(base_input)

    scenarios: dict[str, Any] = {
        "base_case": {
            "scenario_name": "Base Case",
            "description": "Declared assumptions, unshocked.",
            "severity": "base",
            "applied_shocks": {"demand": 0.0, "cost": 0.0, "rate_points": 0.0},
            "result": base_result.to_dict(),
            "decision": base_result.economic_viability,
            "dscr_breached": _dscr_breached(base_result),
            "breaches": _breaches(base_result),
            "decision_changed": False,
            "dscr_delta": None,
            "primary_driver": "Baseline.",
        }
    }

    for spec in STRESS_SCENARIOS:
        shocked_input = apply_shock(
            base_input,
            demand_pct=spec.demand_pct,
            price_pct=spec.price_pct,
            cost_pct=spec.cost_pct,
            rate_points=spec.rate_points,
        )
        # Scenarios are one level deep. Without this the shocked input inherits
        # include_scenarios=True and each scenario recursively runs its own
        # seven, and so on.
        from dataclasses import replace as _replace

        stressed = compute_canonical_financials(
            _replace(shocked_input, include_scenarios=False)
        )

        scenarios[spec.key] = {
            "scenario_name": spec.name,
            "description": spec.description,
            "severity": spec.severity,
            # The canonical shock record, including the price dimension this
            # module previously had no way to express.
            "applied_shocks": spec.to_dict()["applied_shocks"],
            "result": stressed.to_dict(),
            "decision": stressed.economic_viability,
            "dscr_breached": _dscr_breached(stressed),
            "breaches": _breaches(stressed),
            "decision_changed": stressed.economic_viability != base_result.economic_viability,
            "dscr_delta": _dscr_delta(stressed, base_result),
            "dscr_after": stressed.dscr,
            "monthly_ebitda_after": stressed.monthly_ebitda,
            "monthly_emi_after": stressed.monthly_emi,
            "viability_reasons": stressed.viability_reasons,
            "primary_driver": _primary_driver(base_result, stressed),
        }

    survived = [
        k for k, v in scenarios.items()
        if k != "base_case"
        and not v["dscr_breached"]
        and not v["breaches"]
        and v["decision"] == base_result.economic_viability
    ]
    failed = [k for k, v in scenarios.items() if k != "base_case" and k not in survived]

    return {
        "business_type": base_input.business_type,
        "base_decision": base_result.economic_viability,
        "base_dscr": base_result.dscr,
        "scenarios": scenarios,
        "matrix": {
            "demand_shocks_pct": [round(d * 100) for d in DEMAND_SHOCKS],
            "cost_shocks_pct": [round(c * 100) for c in COST_SHOCKS],
            "interest_shock_points": INTEREST_SHOCK_POINTS,
            "includes_combined": True,
            "dscr_breach_threshold": DSCR_BREACH_THRESHOLD,
        },
        "resilience": {
            "scenarios_survived": survived,
            "scenarios_failed": failed,
            "survives_all": not failed,
            "worst_case_dscr": min(
                (s["result"]["dscr"] for s in scenarios.values() if s["result"]["dscr"] is not None),
                default=None,
            ),
            "summary": _summary(
                base_result, survived, failed, debtless=not base_result.debt_amount
            ),
        },
    }
