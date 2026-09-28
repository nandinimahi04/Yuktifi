"""
Phase 1 decision service.

Combines the declared financials, the market evidence and the risk assessment
into one verdict with a reason attached.

The financial block here is NOT a calculation. It is a translation of the
caller's declared figures into the canonical engine's vocabulary, plus a
delegation to `app.financial.canonical_engine`. Every arithmetic result in the
response - EMI, DSCR, break-even, ROI, payback, gates - comes from that engine
and from nowhere else. Writing the waterfall again here is exactly how two
implementations of the same number come to disagree, and the disagreement is
always discovered by a user rather than by a test.

The one judgement this module does make is the verdict, and it is explicit
about its inputs: `GO` only when every gate passed, `CONDITIONAL` when the
business survives but a gate is unknown or advisory-failed, and `NO-GO` when a
fatal gate failed. It never reports a decision without the reasons behind it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    WorkingCapitalConfig,
    compute_canonical_financials,
)
from app.phase2.service import list_evidence


#: Project cost assumed by the dairy demo scenario. It is a SCENARIO PARAMETER,
#: not a measurement, and `build_dairy_demo` publishes it as an assumption.
DAIRY_SCENARIO_PROJECT_COST = 1_000_000.0
DAIRY_SCENARIO_MARGIN_CAPITAL = 100_000.0
DAIRY_SCENARIO_MONTHLY_REVENUE = 180_000.0
DAIRY_SCENARIO_MONTHLY_OPEX = 100_000.0


def _build_financial_input(fin: Dict[str, Any]) -> CanonicalFinancialInput:
    """
    Translate the declared financial block into a canonical input.

    Two deliberate choices:

    * `total_project_cost` is used only when the caller supplied it. It is never
      derived from margin capital, because inflating a project cost to match a
      loan is how an unviable plan acquires a healthy EMI.
    * Revenue and cost are declared as a single aggregate line. The payload has
      no volume and no per-unit price, so per-unit metrics are not derivable
      from it and the engine reports them as not modelled.
    """
    margin = fin.get("margin_capital")
    margin = float(margin) if margin is not None else 0.0
    project_cost = fin.get("total_project_cost")
    project_cost = float(project_cost) if project_cost is not None else None

    revenue = float(fin.get("monthly_revenue") or 0.0)
    opex = float(fin.get("monthly_opex") or 0.0)

    declared_debt = fin.get("debt_amount")
    debt = float(declared_debt) if declared_debt is not None else None

    return CanonicalFinancialInput(
        business_type=str(fin.get("business_type") or "unspecified"),
        products=[ProductItem(
            name=str(fin.get("business_type") or "service"),
            units_per_month=1.0,
            selling_price=revenue,
            variable_cost_per_unit=0.0,
        )],
        opex=OpexBreakdown(other=opex),
        own_capital=margin,
        total_project_cost=project_cost,
        debt_amount=debt,
        interest_rate_annual_pct=float(fin.get("annual_interest_rate_pct") or 9.0),
        tenure_months=int(fin.get("tenure_months") or 60),
        moratorium_months=int(fin.get("moratorium_months") or 0),
        working_capital_cfg=WorkingCapitalConfig(
            inventory_days=int(fin.get("inventory_days") or 10),
            receivable_days=int(fin.get("receivable_days") or 7),
            payable_days=int(fin.get("payable_days") or 14),
        ),
        field_provenance={
            "own_capital": "USER_PROVIDED" if margin else "MODEL_ASSUMPTION",
            "monthly_revenue": "USER_PROVIDED" if revenue else "MODEL_ASSUMPTION",
            "monthly_opex": "USER_PROVIDED" if opex else "MODEL_ASSUMPTION",
            "total_project_cost": "USER_PROVIDED" if project_cost is not None else "MODEL_ASSUMPTION",
            "debt_amount": "USER_PROVIDED" if debt is not None else "MODEL_ASSUMPTION",
        },
    )


def _financial_block(inp: CanonicalFinancialInput) -> Dict[str, Any]:
    """Canonical results, shaped for the historical response contract."""
    res = compute_canonical_financials(inp)
    return {
        "project_cost": res.total_project_cost,
        "loan_amount": res.debt_amount,
        "financing_gap": res.financing_gap,
        "financing_reconciled": res.financing_reconciled,
        "own_capital": res.own_capital,
        "monthly_revenue": res.monthly_revenue,
        "monthly_opex": res.monthly_opex,
        "monthly_ebitda": res.monthly_ebitda,
        "monthly_pat": res.monthly_pat,
        "annual_pat": res.annual_pat,
        "emi": res.monthly_emi,
        "annual_debt_service": res.annual_debt_service,
        "dscr": res.dscr,
        "dscr_status": res.dscr_status,
        "break_even_revenue_monthly": res.break_even_revenue_monthly,
        "break_even_units_monthly": res.break_even_units_monthly,
        "contribution_per_unit": res.contribution_per_unit,
        "roi_pct": res.roi_on_total_project_pct,
        "roi_on_owner_equity_pct": res.roi_on_owner_equity_pct,
        "payback_months": res.payback_months,
        "payback_status": res.payback_status,
        "net_working_capital": res.net_working_capital,
        "minimum_cash_balance": res.minimum_cash_balance,
        "ending_cash_balance": res.ending_cash_balance,
        "npv": res.npv,
        "irr_pct": res.irr_pct,
        "economic_viability": res.economic_viability,
        "viability_reasons": res.viability_reasons,
        "assessability_unknowns": res.assessability_unknowns,
        "financial_status": res.financial_status,
        "decision_gates": res.decision_gates,
        "gate_benchmarks": res.gate_benchmarks,
        "financial_confidence": res.financial_confidence,
        "explainability": res.explainability,
        "stress_scenarios": res.stress_scenarios,
        "monthly_forecast": res.monthly_forecast,
        "validation_issues": res.validation_issues,
        "loan_schedule": res.loan_schedule,
    }


#: The gate status vocabulary is inherited verbatim from the canonical engine.
#: No translation layer here, because a translation is a place for the two
#: vocabularies to drift apart.
from app.financial.gates import (  # noqa: E402
    GATE_FAIL,
    STATUS_CONDITIONAL,
    STATUS_GO,
    STATUS_NO_GO,
    STATUS_INSUFFICIENT,
)


def _public_decision(status: str) -> str:
    """
    Map the canonical status onto the three-value vocabulary this endpoint has
    always published.

    The distinction between CONDITIONAL and INSUFFICIENT_EVIDENCE is preserved
    inside the nested `financial_status` block and in the reasons; only the top
    level is collapsed, because clients of this older endpoint have three states
    and returning a fourth would be a silent breaking change.
    """
    return {
        STATUS_GO: "GO",
        STATUS_CONDITIONAL: "CONDITIONAL",
        STATUS_INSUFFICIENT: "CONDITIONAL",
        STATUS_NO_GO: "NO-GO",
    }.get(status, "CONDITIONAL")


def run_decision(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce one decision with its evidence, its reasons and its limits.
    """
    if not isinstance(payload, dict):
        raise ValueError("Decision payload must be a dict.")

    business_id = str(payload.get("business_id") or "").strip()
    if not business_id:
        raise ValueError("`business_id` is required.")

    fin = dict(payload.get("financial") or {})
    market = dict(payload.get("market") or {})
    risk_score = payload.get("risk_score")

    inp = _build_financial_input(fin)
    financial = _financial_block(inp)

    status = financial["financial_status"]["value"]
    decision = _public_decision(status)

    # A missing risk score is reported as missing. It is not replaced with a
    # neutral 50, because a neutral risk score is indistinguishable from a
    # measured one and would let an unassessed business look assessed.
    if risk_score is None:
        risk_known = False
        risk_reasons = ["No risk score was supplied, so the risk dimension was not assessed."]
        risk_display: Optional[int] = None
    else:
        risk_known = True
        risk_display = int(risk_score)
        risk_reasons = []

    evidence = list_evidence(geography=market.get("geography") or None, limit=20)
    evidence_ids = [e["id"] for e in evidence if e.get("id")]

    reasons: List[str] = list(financial["financial_status"]["reasons"])
    conditions: List[str] = list(financial["financial_status"]["conditions"])
    unknowns: List[str] = list(financial["financial_status"]["unknowns"])
    reasons.extend(risk_reasons)

    return {
        "business_id": business_id,
        "business_name": payload.get("business_name"),
        "location": payload.get("location"),
        "decision": decision,
        "financial_status": financial["financial_status"],
        "reasons": reasons,
        "conditions": conditions,
        "unknowns": unknowns,
        "financial": financial,
        "market": {
            **market,
            "population": market.get("population"),
            "evidence_count": market.get("evidence_count"),
            "risk_score": risk_display,
            "risk_assessed": risk_known,
        },
        "evidence_ids": evidence_ids,
        "confidence": financial["financial_confidence"],
        "limitations": [
            "Figures are computed by the canonical financial engine from the declared inputs "
            "only. They are not a substitute for a quotation, a valuation or a lender's assessment.",
            "Evidence not marked High confidence is carried as ESTIMATED and should be verified "
            "before it is relied on.",
        ],
    }
