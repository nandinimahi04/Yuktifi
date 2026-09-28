"""
Auditable Decision Dossier.

This is the document a promoter, a bank officer or a scheme officer reads, so it
carries the highest burden of proof in the product: a figure in here is treated
as measured.

The previous generator failed that in two independent ways, and the first one
caused the second.

1. Wrong key names. It read `total_project_cost`, `own_capital`,
   `approved_loan_amount`, `monthly_pat`, `monthly_cogs`, `monthly_opex` and
   `monthly_depreciation`. The advisory financial result publishes
   `project_cost`, `promoter_margin`, `loan_amount`, `operating_profit`,
   `variable_cost` and `fixed_cost`. None of those names matched, so the
   `.get(key, 0)` fallbacks fired and the dossier printed **0** for the project
   cost, the owner's capital, the loan amount, EBITDA, PAT, DSCR, ROI and the
   whole cost waterfall - a full set of zeroes on a document intended to prove
   the numbers.

2. Wrong nesting for the decision block. It looked for
   `feasibility_result["breakdown"]["demand"]` and `["breakdown"]["risk"]`, but
   `report.py` passes `result["decision"]`, which has no `breakdown` key. Both
   lookups therefore missed and fell back to **50**. Every dossier consequently
   reported demand 50/100, risk 50/100 and evidence coverage 50% - the exact
   "measured, average, trustworthy" appearance that the abstention rules exist
   to prevent.

The specific harm of the defaults:

* `dscr: 0` reads as a computed catastrophic ratio rather than "not applicable,
  the business carries no debt" or "negative cash".
* `eligible_subsidy: 0` reads as an eligibility determination rather than "no
  scheme evaluated".
* `approved_loan_amount: 0` reads as a lending decision rather than "no loan
  modelled".
* `demand_proxy_score: 50` and `risk_score: 50` are fabricated mid-scores that
  then feed `confidence: "MEDIUM"`.

The generator now reads the fields that exist, and represents every unknown as
`null` with a named reason in `unavailable_fields`. `null` in an auditable
document means "this was not measured", which is the only safe default for a
field that is being used to justify a loan.
"""
from __future__ import annotations

from typing import Any

LEGAL_DISCLAIMER = """
DISCLAIMER & LEGAL NOTICE:
YUKT provides analytical decision support based on available data and declared assumptions.
It does NOT act as a financial adviser, lender, or guaranteed subsidy approval authority.
Final credit decisions and scheme approvals remain strictly with the competent lender, government department, or institution.
DATA ATTRIBUTION:
- Population & Demographic Data: Census of India / Government Open Data License (OGD Platform).
- Geospatial & Map Data: (c) OpenStreetMap contributors.
"""

#: Keys that must never be defaulted to a number. A missing value stays null.
_NO_DEFAULTS = (
    "monthly_revenue",
    "annual_revenue",
    "variable_cost",
    "fixed_cost",
    "operating_profit",
    "project_cost",
    "promoter_margin",
    "loan_amount",
    "monthly_emi",
    "annual_debt_service",
    "dscr",
    "cash_available_for_debt_service_monthly",
    "break_even_units",
    "break_even_revenue",
    "margin_of_safety_pct",
    "roi_on_total_project_pct",
    "roi_on_owner_equity_pct",
    "payback_months",
    "financing_gap",
    "estimated_demand_units_monthly",
    "mapped_competitors",
    "eligible_subsidy",
    "experience_years",
    "applicant_capital",
)


class _Dossier:
    """Collects values and records every one that was unavailable."""

    def __init__(self) -> None:
        self.unavailable: list[dict[str, str]] = []

    def get(
        self,
        source: dict[str, Any],
        *keys: str,
        reason: str = "not present in the pipeline result",
    ) -> Any:
        """First present, non-None value among `keys`, else null + a record."""
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
        label = keys[0] if keys else "?"
        self.unavailable.append({"field": label, "reason": reason})
        return None


def generate_auditable_dossier(
    profile: Dict[str, Any],
    location: Dict[str, Any],
    business_template: Dict[str, Any],
    financial_result: Dict[str, Any],
    stress_result: Dict[str, Any],
    feasibility_result: Dict[str, Any],
    why_not_result: list,
    schemes: list,
) -> Dict[str, Any]:
    fin = financial_result or {}
    decision = feasibility_result or {}
    d = _Dossier()

    confidence = decision.get("confidence") or {}
    gates = decision.get("gates") or []
    gate_by_name = {g.get("gate"): g for g in gates if isinstance(g, dict)}

    demand_gate = gate_by_name.get("demand_evidence") or {}
    risk_gate = gate_by_name.get("stress_resilience") or {}

    dscr_status = fin.get("dscr_status") or "UNAVAILABLE"

    dossier_sections = {
        "1_entrepreneur_profile": {
            # No default: an applicant's capital is a declared fact about a real
            # person, and inventing one puts a fabricated number in a document
            # used to request finance.
            "applicant_capital": d.get(
                profile, "own_capital", "promoter_margin",
                reason="the applicant's declared capital was not supplied",
            ),
            "experience_years": d.get(
                profile, "experience_years",
                reason="the applicant's experience was not supplied",
            ),
            "category_preference": profile.get("category_id"),
        },
        "2_location_resolution": location,
        "3_business_template": {
            "name": business_template.get("name"),
            "sector": business_template.get("sector"),
            "catchment_radius_km": business_template.get("default_catchment_km"),
            "template_assumptions": business_template.get("assumptions"),
        },
        "4_market_evidence": {
            "competition_note": decision.get("competition_note"),
            "mapped_competitors": d.get(
                decision, "mapped_competitors",
                reason="no competitor survey was supplied to this run",
            ),
            "demand_evidence_status": demand_gate.get("status", "UNKNOWN"),
            "demand_evidence_detail": demand_gate.get("detail"),
            "estimated_demand_units_monthly": d.get(
                decision, "estimated_units_monthly",
                reason="demand was not estimated, so no figure is asserted",
            ),
        },
        "5_assumptions_provenance": fin.get("assumptions") or fin.get("assumptions_provenance") or [],
        "6_project_cost": {
            "total_project_cost": d.get(
                fin, "project_cost", "total_project_cost",
                reason="no declared or reconciled project cost",
            ),
            "own_capital": d.get(
                fin, "promoter_margin", "own_capital",
                reason="no declared own capital",
            ),
            "loan_amount": d.get(
                fin, "loan_amount", "approved_loan_amount",
                reason="no loan was modelled",
            ),
            "financing_gap": d.get(fin, "financing_gap"),
            "financing_reconciled": fin.get("financing_reconciled"),
            # Null, never 0: a zero subsidy reads as an eligibility decision
            # that was made and found to be nil.
            "eligible_subsidy": d.get(
                fin, "eligible_subsidy",
                reason="no scheme eligibility evaluation was performed",
            ),
        },
        "7_revenue_model": {
            "monthly_revenue": d.get(fin, "monthly_revenue"),
            "monthly_units": d.get(fin, "monthly_units"),
            "price_per_unit": d.get(fin, "price_per_unit"),
        },
        "8_cost_waterfall": {
            "variable_cost_monthly": d.get(fin, "variable_cost", "monthly_cogs"),
            "fixed_cost_monthly": d.get(fin, "fixed_cost", "monthly_opex"),
            "note": (
                "This pipeline models a single-variable-cost business, so the waterfall is "
                "volume x price less variable cost less fixed operating cost. Depreciation is "
                "not separately modelled in this engine."
            ),
        },
        "9_profit_waterfall": {
            "operating_profit_monthly": d.get(fin, "operating_profit", "monthly_pat"),
            "economic_viability": fin.get("economic_viability"),
            "viability_reasons": fin.get("viability_reasons") or [],
            "assessability_unknowns": fin.get("assessability_unknowns") or [],
        },
        "10_financing_structure": {
            "modeled_loan_requirement": d.get(fin, "modeled_loan_requirement"),
            "loan_amount": d.get(fin, "loan_amount"),
            "interest_rate_annual_pct": _rate_from_assumptions(fin),
            "tenure_months": _assumed(fin, "tenure_months"),
            "moratorium_months": _assumed(fin, "moratorium_months"),
        },
        "11_debt_service": {
            "monthly_emi": d.get(fin, "monthly_emi"),
            "annual_debt_service": d.get(fin, "annual_debt_service"),
        },
        "12_dscr_analysis": {
            # Null means not applicable or not computable, per dscr_status. A
            # 0 here would read as a computed catastrophic ratio.
            "dscr": d.get(fin, "dscr", reason=f"DSCR status: {dscr_status}"),
            "dscr_status": dscr_status,
            "dscr_interpretation": _dscr_note(fin, dscr_status),
        },
        "13_break_even_analysis": {
            "break_even_units": d.get(
                fin, "break_even_units", "break_even_units_monthly"
            ),
            "break_even_revenue": d.get(
                fin, "break_even_revenue", "break_even_revenue_monthly"
            ),
            "basis": _assumed(fin, "break_even_basis")
            or "Break-even is a cash measure, so non-cash depreciation is excluded.",
        },
        "14_roi_metrics": {
            "roi_on_total_project_pct": d.get(fin, "roi_on_total_project_pct"),
            "roi_on_owner_equity_pct": d.get(fin, "roi_on_owner_equity_pct"),
        },
        "15_payback_analysis": {
            "payback_months": d.get(fin, "payback_months"),
            "payback_achieved": fin.get("payback_achieved"),
            "payback_status": fin.get("payback_status"),
            "payback_basis": _assumed(fin, "payback_basis"),
        },
        "16_decision": {
            "decision": decision.get("decision"),
            "why": decision.get("why") or [],
            "what_would_change_it": decision.get("what_would_change_it") or [],
            "gates": gates,
            "failed_gates": decision.get("failed_gates") or [],
            "unevaluated_gates": decision.get("unevaluated_gates") or [],
            "decision_basis": decision.get("decision_basis"),
        },
        "17_scheme_router": {
            "schemes": schemes or [],
            "status_note": (
                "Scheme status is 'Potentially eligible' at most. This system does not approve "
                "anything; eligibility is confirmed by the issuing authority."
            ),
        },
        "18_stress_tests": stress_result.get("scenarios") or stress_result or {},
        "19_risk_exposure": {
            "stress_resilience_status": risk_gate.get("status", "UNKNOWN"),
            "stress_resilience_detail": risk_gate.get("detail"),
            "worst_case_dscr": (stress_result.get("worst_case_dscr")
                                if isinstance(stress_result, dict) else None),
        },
        "20_confidence_propagation": {
            "overall_confidence": confidence.get("overall"),
            "evidence_coverage": confidence.get("evidence_coverage"),
            "calculation_integrity": confidence.get("calculation_integrity"),
            "evidence_inputs": confidence.get("inputs"),
            "thresholds": decision.get("thresholds"),
        },
        "21_evidence_registry": decision.get("evidence") or [],
        "22_why_this_business": decision.get("why") or [],
        "23_why_not_alternatives": why_not_result or [],
        "24_legal_disclaimer_attribution": LEGAL_DISCLAIMER.strip(),
    }

    return {
        "title": (
            f"YUKTIFI AUDITABLE DECISION DOSSIER - "
            f"{business_template.get('name') or 'Enterprise'}"
        ),
        "version": "2.0-abstaining",
        "sections": dossier_sections,
        # Every field printed as null in the document above is listed here with
        # the reason. A reader can audit the gaps instead of inferring them.
        "unavailable_fields": d.unavailable,
        "unavailable_field_count": len(d.unavailable),
        "reading_note": (
            "A null value in this dossier means the figure was not measured, not that it was "
            "zero. Absence of evidence is recorded as absence and is never substituted with a "
            "neutral or zero figure."
        ),
    }


def _assumed(fin: dict[str, Any], name: str) -> Any:
    """Read a named assumption from the provenance list."""
    for row in fin.get("assumptions") or fin.get("assumptions_provenance") or []:
        if isinstance(row, dict) and row.get("name") == name:
            return row.get("value")
    return None


def _rate_from_assumptions(fin: dict[str, Any]) -> Any:
    return _assumed(fin, "interest_rate_annual_pct")


def _dscr_note(fin: dict[str, Any], status: str) -> str:
    if status == "NEGATIVE_CFADS":
        return (
            "DSCR is not reported because operating cash is negative. A ratio with a negative "
            "numerator has no financial meaning and moves backwards, so the shortfall is stated "
            "in rupees in viability_reasons instead."
        )
    if status == "NOT_APPLICABLE_NO_DEBT":
        return "The business carries no debt obligation, so there is no DSCR to compute."
    if status == "COMPUTED":
        return "DSCR is measured against the debt service actually due in the first year."
    if status == "NOT_COMPUTABLE":
        return "No debt service schedule was available, so DSCR could not be computed."
    return "DSCR was not produced by this run."
