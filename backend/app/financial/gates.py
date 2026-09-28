"""
Decision gates, financial status, confidence and explainability.

Part of the canonical engine (app.financial.*). Contains no arithmetic: every
number it reports has already been computed by canonical_engine. What this
module decides is what the numbers MEAN, and it is deliberately separate so
that the thresholds are auditable in one place and can be changed without
touching the model.

Two rules govern everything here:

    1. A gate that could not be evaluated is UNKNOWN, never PASS. Absence of
       evidence is not a pass and it is not a fail.
    2. Confidence in the NUMBERS is reported separately from the PERFECTION of
       the business. A well-evidenced loss is confidently a loss; a
       beautifully profitable projection built on template defaults is
       neither confident nor proven.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.financial.inputs import (
    FRESHNESS_HALFLIFE_DAYS,
    SEVERITY_ERROR,
    STALE_CONFIDENCE_MULTIPLIER,
    ProvenanceEntry,
    ValidationIssue,
)

# ── Status vocabularies ──────────────────────────────────────────────────────

STATUS_GO = "GO"
STATUS_CONDITIONAL = "CONDITIONAL"
STATUS_NO_GO = "NO_GO"
STATUS_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

GATE_PASS = "PASS"
GATE_FAIL = "FAIL"
GATE_UNKNOWN = "UNKNOWN"

GATE_FINANCING = "FINANCING_GATE"
GATE_UNIT_ECONOMICS = "UNIT_ECONOMICS_GATE"
GATE_BREAK_EVEN = "BREAK_EVEN_GATE"
GATE_CASH_FLOW = "CASH_FLOW_GATE"
GATE_DEBT_SERVICE = "DEBT_SERVICE_GATE"

ALL_GATES = (
    GATE_FINANCING,
    GATE_UNIT_ECONOMICS,
    GATE_BREAK_EVEN,
    GATE_CASH_FLOW,
    GATE_DEBT_SERVICE,
)


# ── Configurable thresholds ──────────────────────────────────────────────────

@dataclass
class GateBenchmark:
    """
    Thresholds a plan is measured against.

    These are MODEL BENCHMARKS, not legal or banking requirements. No
    universal DSCR minimum exists across Indian lending: lenders, schemes and
    sectors differ, and PMEGP, NSIC and state programmes each publish their own
    guidance. Every figure here is therefore a stated, changeable assumption,
    surfaced in the output so a reader can disagree with it, and never
    presented as a regulator's rule.
    """
    min_dscr: float = 1.25
    min_contribution_margin_pct: float = 20.0
    min_ebitda_margin_pct: float = 5.0
    min_roi_on_project_pct: float = 0.0
    max_payback_months: float = 60.0
    min_cash_buffer_months: float = 1.0
    require_financing_reconciled: bool = True
    #: A plan may be no more than this far into negative cash before the
    #: cash-flow gate fails. Working-capital gaps are normal in month 1.
    min_cash_balance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_dscr": self.min_dscr,
            "min_contribution_margin_pct": self.min_contribution_margin_pct,
            "min_ebitda_margin_pct": self.min_ebitda_margin_pct,
            "min_roi_on_project_pct": self.min_roi_on_project_pct,
            "max_payback_months": self.max_payback_months,
            "min_cash_buffer_months": self.min_cash_buffer_months,
            "require_financing_reconciled": self.require_financing_reconciled,
            "min_cash_balance": self.min_cash_balance,
            "basis": (
                "Internal appraisal benchmarks chosen by this model. They are not legal, "
                "regulatory or lender requirements; no universal DSCR minimum exists and each "
                "scheme and lender publishes its own guidance. Adjust per sector and per lender."
            ),
        }


DEFAULT_GATE_BENCHMARK = GateBenchmark()


@dataclass
class GateResult:
    gate: str
    status: str
    value: Optional[float]
    threshold: Optional[float]
    reason: str
    #: Whether a failing gate is fatal (NO_GO) or advisory (CONDITIONAL).
    fatal: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_gates(
    *,
    benchmark: GateBenchmark,
    financing_reconciled: bool,
    financing_gap: float,
    contribution_margin_pct: Optional[float],
    ebitda_margin_pct: Optional[float],
    break_even_units_monthly: Optional[float],
    modelled_units_monthly: Optional[float],
    monthly_ebitda: float,
    monthly_revenue: float,
    dscr: Optional[float],
    dscr_status: str,
    debt_amount: float,
    roi_on_total_project_pct: Optional[float],
    payback_months: Optional[float],
    payback_status: str,
    minimum_cash_balance: Optional[float],
    project_cost_known: bool,
) -> List[GateResult]:
    """
    Evaluate every gate. A gate is UNKNOWN when its input is missing, which is
    a different statement from FAIL and produces a different status.
    """
    gates: List[GateResult] = []

    # 6.15 FINANCING GATE - the declared funding stack must actually fund the plan.
    if not project_cost_known:
        gates.append(GateResult(
            GATE_FINANCING, GATE_UNKNOWN, None, None,
            "Project cost has not been established, so the funding requirement is unknown.",
        ))
    elif benchmark.require_financing_reconciled and not financing_reconciled:
        gates.append(GateResult(
            GATE_FINANCING, GATE_FAIL, abs(financing_gap), 0.0,
            f"The funding stack falls short of the project cost by {abs(financing_gap):,.0f}. "
            f"Either the shortfall is funded or the plan is not yet startable.",
        ))
    else:
        gates.append(GateResult(
            GATE_FINANCING, GATE_PASS, abs(financing_gap), 0.0,
            "Declared own capital, other funding, subsidy and debt together cover the project cost.",
        ))

    # 6.20 UNIT ECONOMICS GATE - each sale must contribute enough to matter.
    if contribution_margin_pct is None:
        gates.append(GateResult(
            GATE_UNIT_ECONOMICS, GATE_UNKNOWN, None, benchmark.min_contribution_margin_pct,
            "Contribution margin is not computable: there is no price or volume to measure against.",
        ))
    elif contribution_margin_pct <= 0:
        gates.append(GateResult(
            GATE_UNIT_ECONOMICS, GATE_FAIL, contribution_margin_pct, benchmark.min_contribution_margin_pct,
            f"Each unit sold loses {abs(round(100 - contribution_margin_pct, 2))} paise in the rupee. "
            f"Selling more makes the loss larger.",
        ))
    elif contribution_margin_pct < benchmark.min_contribution_margin_pct:
        gates.append(GateResult(
            GATE_UNIT_ECONOMICS, GATE_FAIL, contribution_margin_pct, benchmark.min_contribution_margin_pct,
            f"Contribution margin is {contribution_margin_pct}%, below the "
            f"{benchmark.min_contribution_margin_pct}% benchmark. Profit is highly sensitive to "
            f"any cost or price movement.",
            fatal=False,
        ))
    else:
        gates.append(GateResult(
            GATE_UNIT_ECONOMICS, GATE_PASS, contribution_margin_pct, benchmark.min_contribution_margin_pct,
            f"Contribution margin is {contribution_margin_pct}%, at or above the "
            f"{benchmark.min_contribution_margin_pct}% benchmark.",
        ))

    # 6.21 BREAK-EVEN GATE - is the modelled demand above break-even?
    if break_even_units_monthly is None:
        gates.append(GateResult(
            GATE_BREAK_EVEN, GATE_UNKNOWN, None, None,
            "Break-even volume is not computable because no unit has positive contribution.",
        ))
    elif not modelled_units_monthly:
        gates.append(GateResult(
            GATE_BREAK_EVEN, GATE_UNKNOWN, break_even_units_monthly, None,
            f"Break-even is {break_even_units_monthly:,.0f} units a month but no achievable volume "
            f"has been modelled, so the plan cannot be tested against it.",
        ))
    elif break_even_units_monthly > modelled_units_monthly:
        gates.append(GateResult(
            GATE_BREAK_EVEN, GATE_FAIL, break_even_units_monthly, modelled_units_monthly,
            f"Break-even needs {break_even_units_monthly:,.0f} units a month but only "
            f"{modelled_units_monthly:,.0f} are modelled as achievable.",
        ))
    else:
        gates.append(GateResult(
            GATE_BREAK_EVEN, GATE_PASS, break_even_units_monthly, modelled_units_monthly,
            f"Modelled volume of {modelled_units_monthly:,.0f} units a month clears break-even at "
            f"{break_even_units_monthly:,.0f}.",
        ))

    # 6.12 CASH FLOW GATE - EBITDA must be positive and cash must not go negative.
    if monthly_revenue <= 0:
        gates.append(GateResult(
            GATE_CASH_FLOW, GATE_UNKNOWN, monthly_ebitda, benchmark.min_ebitda_margin_pct,
            "There is no modelled revenue, so operating cash generation cannot be assessed.",
        ))
    elif monthly_ebitda <= 0:
        gates.append(GateResult(
            GATE_CASH_FLOW, GATE_FAIL, round(monthly_ebitda, 2), 0.0,
            f"Monthly EBITDA is {round(monthly_ebitda, 2)}. Revenue does not cover variable cost "
            f"plus fixed operating expenses, so the business consumes cash from the first month.",
        ))
    else:
        ebitda_margin = round(monthly_ebitda / monthly_revenue * 100, 2)
        if ebitda_margin < benchmark.min_ebitda_margin_pct:
            gates.append(GateResult(
                GATE_CASH_FLOW, GATE_FAIL, ebitda_margin, benchmark.min_ebitda_margin_pct,
                f"EBITDA margin is {ebitda_margin}%, below the {benchmark.min_ebitda_margin_pct}% "
                f"benchmark. The business is profitable on paper but leaves nothing for "
                f"unexpected costs.",
                fatal=False,
            ))
        elif minimum_cash_balance is not None and minimum_cash_balance < benchmark.min_cash_balance:
            gates.append(GateResult(
                GATE_CASH_FLOW, GATE_FAIL, round(minimum_cash_balance, 2), benchmark.min_cash_balance,
                f"Cash falls to {round(minimum_cash_balance, 2)} at its lowest point in the first "
                f"year. Working capital committed at commencement is not inside the declared "
                f"project cost, so it needs a separate contribution on top of the funding stack. "
                f"That is usually a small addition rather than a fatal flaw, so this is reported "
                f"as a condition.",
                fatal=False,
            ))
        else:
            gates.append(GateResult(
                GATE_CASH_FLOW, GATE_PASS, ebitda_margin, benchmark.min_ebitda_margin_pct,
                f"EBITDA margin is {ebitda_margin}% and the cash balance stays above the required "
                f"buffer through the first year.",
            ))

    # 6.19 DEBT SERVICE GATE - only applies when there is debt.
    if debt_amount <= 0:
        gates.append(GateResult(
            GATE_DEBT_SERVICE, GATE_UNKNOWN, None, benchmark.min_dscr,
            "There is no debt, so there is no debt service to cover. DSCR is not applicable.",
            fatal=False,
        ))
    elif dscr is None:
        gates.append(GateResult(
            GATE_DEBT_SERVICE, GATE_UNKNOWN, None, benchmark.min_dscr,
            f"Repayment capacity could not be expressed as a ratio (status: {dscr_status}).",
        ))
    elif dscr < benchmark.min_dscr:
        gates.append(GateResult(
            GATE_DEBT_SERVICE, GATE_FAIL, dscr, benchmark.min_dscr,
            f"DSCR is {dscr}x against a {benchmark.min_dscr}x benchmark, so operating cash does not "
            f"comfortably cover the loan. Lenders typically read anything below about 1.25x as thin.",
        ))
    else:
        gates.append(GateResult(
            GATE_DEBT_SERVICE, GATE_PASS, dscr, benchmark.min_dscr,
            f"DSCR is {dscr}x, at or above the {benchmark.min_dscr}x benchmark.",
        ))

    return gates


# ── Status ───────────────────────────────────────────────────────────────────

def derive_financial_status(
    gates: List[GateResult],
    *,
    validation_issues: Optional[List[ValidationIssue]] = None,
    roi_on_total_project_pct: Optional[float] = None,
    payback_months: Optional[float] = None,
    payback_status: str = "",
    project_cost_known: bool = True,
    monthly_revenue: float = 0.0,
) -> Dict[str, Any]:
    """
    Roll the gates up into one decision.

    NO_GO                 a fatal gate failed.
    INSUFFICIENT_EVIDENCE  nothing failed, but a gate that matters could not be
                          evaluated, or the inputs are too incomplete to decide.
    CONDITIONAL           nothing fatal failed, at least one advisory gate failed.
    GO                    every gate evaluated and passed.
    """
    issues = validation_issues or []
    has_input_error = any(i.severity == SEVERITY_ERROR for i in issues)
    warnings = [i for i in issues if i.severity != SEVERITY_ERROR]

    fatal_failures = [g for g in gates if g.status == GATE_FAIL and g.fatal]
    advisory_failures = [g for g in gates if g.status == GATE_FAIL and not g.fatal]
    unknown_all = [g for g in gates if g.status == GATE_UNKNOWN]
    # An unknown gate is not automatically fatal. DSCR cannot be evaluated for a
    # business that has no loan, and that is a fact about the plan rather than a
    # gap in it. These are reported separately from fatal unknowns so a self-funded
    # business is not demoted to INSUFFICIENT_EVIDENCE for having avoided debt -
    # and so the gate is still visible instead of disappearing from the block.
    unknowns = [g for g in unknown_all if g.fatal]
    not_applicable = [g for g in unknown_all if not g.fatal]

    reasons: List[str] = [g.reason for g in fatal_failures]
    conditions: List[str] = [g.reason for g in advisory_failures]
    unknowns_reasons: List[str] = [g.reason for g in unknowns]

    STATUS_INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"

    if has_input_error:
        status = STATUS_NO_GO
        reasons.insert(0, "One or more declared inputs are not usable, so no decision can be made from them.")
    elif not project_cost_known or monthly_revenue <= 0:
        status = STATUS_INSUFFICIENT_INPUT
        if not project_cost_known:
            reasons.append("Project Cost is missing.")
        if monthly_revenue <= 0:
            reasons.append("Monthly Revenue is missing.")
    elif fatal_failures:
        status = STATUS_NO_GO
    elif unknowns or roi_on_total_project_pct is None or payback_months is None:
        status = STATUS_INSUFFICIENT
        if roi_on_total_project_pct is None:
            unknowns_reasons.append(
                "Return on the project cannot be assessed because the capital base is unknown.")
        if payback_months is None and payback_status:
            unknowns_reasons.append(
                "Payback was not reached within the modelled horizon, so its length is unknown.")
    elif advisory_failures or warnings:
        status = STATUS_CONDITIONAL
        conditions.extend(w.message for w in warnings)
    else:
        status = STATUS_GO

    return {
        "value": status,
        "reasons": reasons,
        "conditions": conditions,
        "unknowns": unknowns_reasons,
        "failed_gates": [g.gate for g in fatal_failures],
        "advisory_gates": [g.gate for g in advisory_failures],
        "unknown_gates": [g.gate for g in unknown_all],
        "not_applicable_gates": [g.gate for g in not_applicable],
        "not_applicable_reasons": [g.reason for g in not_applicable],
        "gates_passed": [g.gate for g in gates if g.status == GATE_PASS],
    }


# ── Confidence ───────────────────────────────────────────────────────────────

CONF_HIGH = "HIGH"
CONF_MEDIUM = "MEDIUM"
CONF_LOW = "LOW"

_BANDS = ((0.75, CONF_HIGH), (0.50, CONF_MEDIUM), (0.0, CONF_LOW))


def assess_confidence(
    *,
    provenance: Dict[str, ProvenanceEntry],
    validation_issues: List[ValidationIssue],
    conflicts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    How much weight the NUMBERS deserve. Independent of whether the business
    is profitable: a confidently-measured loss is still a loss, and a
    profitable projection on template defaults is not evidence of anything.

    Deductions, each with its reason recorded:
        * inputs that are assumptions, estimates or demo data
        * inputs with no provenance recorded at all
        * stale inputs
        * inputs that contradict each other
        * input warnings
    """
    conflicts = list(conflicts or [])
    issues = validation_issues or []
    basis: List[str] = []

    total_fields = len(provenance)
    if total_fields == 0:
        score = 0.25
        basis.append(
            "No input provenance was recorded, so it is not known which figures are observed. "
            "Confidence is capped at LOW."
        )
    else:
        weights = [p.weight for p in provenance.values()]
        mean_weight = sum(weights) / len(weights)
        verified = sum(1 for p in provenance.values() if p.verified)
        score = mean_weight
        basis.append(
            f"{verified} of {total_fields} recorded inputs are user-provided or dataset-derived."
        )
        unverified = total_fields - verified
        if unverified:
            basis.append(
                f"{unverified} inputs are template defaults, estimates or model assumptions "
                f"({', '.join(sorted({p.source for p in provenance.values() if not p.verified}))})."
            )

    stale = [
        p.field for p in provenance.values()
        if p.freshness_days is not None and p.freshness_days > FRESHNESS_HALFLIFE_DAYS
    ]
    if stale:
        score *= STALE_CONFIDENCE_MULTIPLIER
        basis.append(
            f"Stale inputs older than {FRESHNESS_HALFLIFE_DAYS:g} days: "
            f"{', '.join(sorted(stale))}."
        )

    if conflicts:
        score *= max(0.0, 1.0 - 0.15 * len(conflicts))
        basis.append(f"Contradictory inputs: {', '.join(sorted(conflicts))}.")

    warnings = [i for i in issues if i.severity != SEVERITY_ERROR]
    if warnings:
        score *= max(0.0, 1.0 - 0.05 * len(warnings))
        basis.append(f"{len(warnings)} input fields are missing or not modelled.")

    if any(i.severity == SEVERITY_ERROR for i in issues):
        score = min(score, 0.05)
        basis.append("One or more inputs are not usable, so no figure derived from them is reportable.")

    score = round(max(0.0, min(1.0, score)), 2)
    band = next(name for threshold, name in _BANDS if score >= threshold)

    return {
        "band": band,
        "score": score,
        "basis": basis,
        "fields_recorded": total_fields,
        "fields_verified": sum(1 for p in provenance.values() if p.verified),
        "conflicts": conflicts,
        "note": (
            "Confidence describes the evidence behind these numbers. It is independent of "
            "performance: a well-evidenced business that loses money is high confidence and a "
            "profitable projection built on assumptions is low confidence."
        ),
    }


# ── Explainability ───────────────────────────────────────────────────────────

def build_explanations(
    *,
    monthly_revenue: float,
    monthly_variable_costs: float,
    monthly_opex: float,
    monthly_ebitda: float,
    contribution_per_unit: float,
    avg_price_per_unit: float,
    break_even_units_monthly: Optional[float],
    operating_days_per_month: int,
    dscr: Optional[float],
    dscr_status: str,
    annual_debt_service: float,
    cfads_annual: float,
    debt_amount: float,
    break_even_basis: str,
    roi_on_total_project_pct: Optional[float],
    total_project_cost: float,
    annual_pat: float,
    payback_months: Optional[float],
    payback_status: str,
    net_working_capital: float,
    min_cash_balance: Optional[float],
) -> Dict[str, Any]:
    """
    One entry per headline figure: the value, the arithmetic that produced it,
    why it matters to the entrepreneur, and where the inputs came from.

    The formula strings are generated from the actual numbers, so they cannot
    drift away from the result they describe.
    """
    rev = round(monthly_revenue, 2)
    vc = round(monthly_variable_costs, 2)
    opex = round(monthly_opex, 2)
    ebitda = round(monthly_ebitda, 2)

    def entry(value, formula, why) -> Dict[str, Any]:
        return {
            "value": value,
            "formula": formula,
            "why_it_matters": why,
            "source": "Canonical Financial Engine (app.financial.canonical_engine)",
        }

    out: Dict[str, Any] = {
        "revenue": entry(
            rev,
            f"Revenue = {avg_price_per_unit:,.2f} x units sold per month = {rev:,.2f}.",
            "The top line. Every profit figure below is a share of this number.",
        ),
        "variable_cost": entry(
            vc,
            f"Variable cost per unit x units sold per month = {vc:,.2f}.",
            "Costs that move with volume. This is what stops revenue from being profit.",
        ),
        "contribution_per_unit": entry(
            round(contribution_per_unit, 2),
            f"Contribution = price {avg_price_per_unit:,.2f} - variable cost "
            f"{round(avg_price_per_unit - contribution_per_unit, 2)} = "
            f"{contribution_per_unit:,.2f} per unit.",
            "What one more customer actually adds towards paying the bills. It is the number to "
            "watch when prices or input costs move.",
        ),
        "ebitda": entry(
            ebitda,
            f"EBITDA = revenue {rev:,.2f} - variable cost {vc:,.2f} - fixed operating cost "
            f"{opex:,.2f} = {ebitda:,.2f}.",
            "What the business earns before financing and tax. Negative here means every "
            "additional sale deepens the loss.",
        ),
    }

    if break_even_units_monthly is not None:
        be = break_even_units_monthly
        daily = round(be / operating_days_per_month, 1) if operating_days_per_month else None
        out["break_even_units"] = entry(
            be,
            f"Break-even = fixed operating cost {opex:,.2f} / contribution "
            f"{round(contribution_per_unit, 2)} = {be:,.1f} units a month"
            + (f", i.e. {daily:,.1f} units on each of {operating_days_per_month} working days."
               if daily is not None else "."),
            "The volume below which the business loses money. " + break_even_basis,
        )
    else:
        out["break_even_units"] = entry(
            None,
            "Not computable: no unit has a positive contribution, so no volume can ever cover "
            "fixed costs.",
            "Break-even is unavailable here. This is not the same as a break-even of zero.",
        )

    if debt_amount <= 0:
        out["dscr"] = entry(
            None,
            "Not applicable: the business has no loan, so there is no debt service to cover.",
            "DSCR is N/A for an unlevered business. It is not zero and not a perfect score.",
        )
    elif dscr is None:
        out["dscr"] = entry(
            None,
            f"Not computable (status: {dscr_status}). Annual debt service is "
            f"{annual_debt_service:,.2f} against annual cash available of {cfads_annual:,.2f}.",
            "Repayment capacity could not be expressed as a ratio. A ratio is withheld rather "
            "than reported negative, because a negative DSCR moves the wrong way when the loan "
            "gets more expensive.",
        )
    else:
        out["dscr"] = entry(
            dscr,
            f"DSCR = cash available for debt service {cfads_annual:,.2f} / annual debt service "
            f"{annual_debt_service:,.2f} = {dscr}x.",
            "How many times over the year's operating cash covers the loan repayments. Below "
            "1.0x the repayments are not covered at all.",
        )

    if roi_on_total_project_pct is None:
        out["roi"] = entry(
            None,
            "Not computable: ROI is a ratio and the project cost is unknown, so the "
            "denominator does not exist.",
            "Return on the investment is unknown, not zero.",
        )
    else:
        out["roi"] = entry(
            roi_on_total_project_pct,
            f"ROI = annual profit {annual_pat:,.2f} / total project cost "
            f"{total_project_cost:,.2f} x 100 = {roi_on_total_project_pct}%.",
            "The return on every rupee committed to the business, before the cost of financing.",
        )

    if payback_months is None:
        out["payback"] = entry(
            None,
            f"Not achieved within the modelled horizon (status: {payback_status}).",
            "Payback is undetermined in this horizon, not zero.",
        )
    else:
        out["payback"] = entry(
            payback_months,
            f"Payback = the month in which cumulative cash recovers own capital plus other "
            f"funding plus working capital of {net_working_capital:,.2f}.",
            "How long the money is at risk. Working capital is counted once, at commencement.",
        )

    if min_cash_balance is not None:
        out["minimum_cash_balance"] = entry(
            round(min_cash_balance, 2),
            "Lowest month-end cash balance across the 12-month projection, after debt service "
            "and working capital.",
            "The point at which the business is most exposed. Below zero it cannot pay the next "
            "bill without new money.",
        )

    return out
