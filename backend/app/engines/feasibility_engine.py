"""
YuktiFi Feasibility Engine, YUKTI Score & 'Why Not?' Analysis Engine (Phases 9 & 14).
Combines deterministic component scoring with configurable weights, confidence propagation, and comparative evaluation.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from app.financial.canonical_engine import CanonicalFinancialResult

@dataclass
class ScoreWeights:
    demand_weight: float = 0.25
    financial_weight: float = 0.30
    competition_weight: float = 0.15
    infrastructure_weight: float = 0.10
    operations_weight: float = 0.10
    risk_weight: float = 0.10

DEFAULT_WEIGHTS = ScoreWeights()

def compute_yukti_score(
    fin_result: CanonicalFinancialResult,
    mapped_competitors_count: int,
    competitor_coverage: str = "MEDIUM",
    infrastructure_score: float = 75.0,
    operations_score: float = 70.0,
    weights: ScoreWeights = DEFAULT_WEIGHTS
) -> Dict[str, Any]:
    """
    Computes YUKTI score deterministically from financial DSCR, ROI, Payback,
    competitor density, and operational readiness.
    """
    # 1. Financial Component (0 - 100)
    # DSCR >= 1.5 -> 100, 1.25 -> 80, 1.0 -> 50, <1.0 -> 20
    # A business with no debt has no DSCR. That is an absence of information,
    # not a perfect score, so it is scored as not-applicable rather than 100.
    dscr = fin_result.dscr
    if dscr is None:
        fin_dscr_score = 60.0
        dscr_note = "DSCR not applicable (no debt). Scored on repayment risk absent."
    elif dscr >= 1.5:
        fin_dscr_score = 100.0
        dscr_note = f"Modeled DSCR {dscr}x is strong."
    elif dscr >= 1.25:
        fin_dscr_score = 80.0
        dscr_note = f"Modeled DSCR {dscr}x is adequate."
    elif dscr >= 1.0:
        fin_dscr_score = 50.0
        dscr_note = f"Modeled DSCR {dscr}x leaves little headroom."
    else:
        fin_dscr_score = 20.0
        dscr_note = f"Modeled DSCR {dscr}x is below 1.0; modelled cash does not cover debt service."

    # Payback achieved <= 24m -> 100, <= 36m -> 75, <= 48m -> 50, else 25
    if fin_result.payback_achieved and fin_result.payback_months:
        if fin_result.payback_months <= 24:
            fin_pb_score = 100.0
        elif fin_result.payback_months <= 36:
            fin_pb_score = 75.0
        elif fin_result.payback_months <= 48:
            fin_pb_score = 50.0
        else:
            fin_pb_score = 30.0
    else:
        fin_pb_score = 10.0

    financial_component = round(0.6 * fin_dscr_score + 0.4 * fin_pb_score, 1)

    # 2. Competition Component (0 - 100)
    # Note: 0 mapped OSM competitors does not mean 0 real competitors! Tagged with coverage.
    if mapped_competitors_count == 0:
        competition_component = 70.0  # Moderate score due to mapping uncertainty
        comp_note = "No mapped OSM competitors found (Coverage: LOW/MEDIUM)."
    elif mapped_competitors_count <= 3:
        competition_component = 85.0
        comp_note = "Low competition density detected in catchment."
    elif mapped_competitors_count <= 8:
        competition_component = 60.0
        comp_note = "Moderate competition density in catchment."
    else:
        competition_component = 35.0
        comp_note = "High competition density in local catchment."

    # 3. Demand Proxy Component (0 - 100)
    # Derived from margin of safety & revenue scalability
    mos = fin_result.margin_of_safety_pct
    demand_component = min(100.0, max(20.0, 50.0 + (mos if mos is not None else 0.0)))

    # 4. Risk Component (0 - 100)
    # Inversely tied to DSCR sensitivity & CCC
    if fin_result.cash_conversion_cycle_days > 30:
        risk_component = 40.0
    elif fin_result.cash_conversion_cycle_days > 14:
        risk_component = 65.0
    else:
        risk_component = 85.0

    # Composite YUKTI Score
    total_score = (
        demand_component * weights.demand_weight +
        financial_component * weights.financial_weight +
        competition_component * weights.competition_weight +
        infrastructure_score * weights.infrastructure_weight +
        operations_score * weights.operations_weight +
        risk_component * weights.risk_weight
    )
    final_yukti_score = round(total_score, 1)

    # Main Drivers
    drivers = []
    if dscr is None:
        # "No debt assumed" is only true in one of the cases that produce no DSCR.
        # For a business carrying debt whose coverage could not be expressed as a
        # ratio - negative operating cash, or a year with no service due - the old
        # wording told the reader the debt did not exist, which is the opposite of
        # the risk. The engine's own status is reported instead.
        drivers.append(
            f"? Debt service coverage not available ({fin_result.dscr_status}); "
            f"monthly debt service where applicable is Rs "
            f"{fin_result.monthly_emi:,.0f}"
        )
    elif dscr >= 1.3:
        drivers.append(f"+ Strong Debt Service Coverage (DSCR {dscr}x >= 1.3)")
    else:
        drivers.append(f"- Tight Debt Service Coverage (DSCR {dscr}x < 1.3)")

    if fin_result.economic_viability == "NOT_VIABLE":
        drivers.append("- NOT VIABLE: " + "; ".join(fin_result.viability_reasons))
    elif fin_result.economic_viability == "UNDETERMINED":
        # Silently omitting this made an unjudgeable business read as though the
        # drivers list were complete and nothing outstanding remained.
        drivers.append(
            "? UNDETERMINED - no gate failed, but not everything could be checked: "
            + "; ".join(
                fin_result.assessability_unknowns
                or ["a required input is missing from the model"]
            )
        )

    if not fin_result.financing_reconciled:
        drivers.append(
            f"- Financing gap of Rs {abs(fin_result.financing_gap)} is unfunded"
        )

    if fin_result.payback_achieved and fin_result.payback_months and fin_result.payback_months <= 36:
        drivers.append("+ Rapid Capital Payback (< 36 months)")

    if competition_component >= 70:
        drivers.append("+ Favorable Market Competition Window")
    else:
        drivers.append("- High Local Competition Density")

    if fin_result.net_working_capital > (fin_result.monthly_revenue * 0.3):
        drivers.append("- Heavy Working Capital Requirement")

    # Overall Confidence Calculation
    if competitor_coverage.upper() == "HIGH" and fin_result.tax_status == "MODELED":
        overall_confidence = "HIGH"
        evidence_coverage_pct = 85.0
    elif competitor_coverage.upper() in ["MEDIUM", "LOW"]:
        overall_confidence = "MEDIUM"
        evidence_coverage_pct = 68.0
    else:
        overall_confidence = "LOW"
        evidence_coverage_pct = 45.0

    return {
        "yukti_score": final_yukti_score,
        "evidence_coverage_pct": evidence_coverage_pct,
        "overall_confidence": overall_confidence,
        "breakdown": {
            "demand": demand_component,
            "financial": financial_component,
            "competition": competition_component,
            "infrastructure": infrastructure_score,
            "operations": operations_score,
            "risk": risk_component
        },
        "main_drivers": drivers,
        "competition_note": comp_note,
        "dscr_note": dscr_note
    }


def compute_why_not_analysis(
    applicant_capital: Optional[float],
    recommended_category: str,
    all_categories: List[str],
    cost_models: Optional[dict[str, dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Comparative "Why NOT the alternatives?" matrix.

    The previous version hardcoded six `capital_required` figures with no source
    - dairy at 350,000, agri_machinery at 1,500,000 and so on - gave any
    *unlisted* category a default of 300,000, and then ruled each alternative
    "Pass" or "Fail (Capital Gap)" against an undocumented test
    (`capital >= required * 0.10`) that was never justified anywhere.

    That produced a user-facing verdict. A promoter with 50,000 rupees was told
    their second-choice business was a "Fail (Capital Gap)" against a threshold
    that was invented in this file, for a business they had not described. The
    10% test is also internally incoherent: the cheapest listed business
    (tea_stall, 50,000) only "passes" at 5,000, while agri_machinery needs
    150,000, so the ranking between businesses was arbitrary.

    Capital fit is now computed only where a real cost reference exists, and
    abstains otherwise:

    * `cost_models` may be supplied, mapping category_id to a capital figure.
    * Where no reference exists, `capital_fit` is "Not assessed" and the reason
      says so. It is never a Pass or a Fail.
    * Where the applicant's own capital is unknown, every entry abstains.
    * `why_not_reason` is now a description of what would need checking, not a
      verdict, because a reason for rejection is only legitimate when the
      alternative was actually modelled.
    """
    results: List[Dict[str, Any]] = []
    cost_models = cost_models or {}

    for cat in all_categories:
        if cat == recommended_category:
            continue

        model = cost_models.get(cat) or {}
        required = model.get("capital_required")
        if not isinstance(required, (int, float)) or required <= 0:
            results.append({
                "business_category": cat,
                "capital_fit": "Not assessed",
                "capital_required": None,
                "why_not_reason": (
                    f"No capital requirement is available for '{cat}', so its affordability "
                    f"relative to the applicant's capital was not compared."
                ),
                "evidence_state": "MISSING",
            })
            continue

        if not isinstance(applicant_capital, (int, float)) or applicant_capital <= 0:
            results.append({
                "business_category": cat,
                "capital_fit": "Not assessed",
                "capital_required": float(required),
                "why_not_reason": (
                    f"The applicant's capital was not supplied, so the estimated "
                    f"{float(required):,.0f} requirement for '{cat}' could not be compared."
                ),
                "evidence_state": "MISSING",
            })
            continue

        # Affordability is reported as the share of the requirement that is
        # already funded, which is a real ratio with a stated denominator. No
        # arbitrary pass/fail multiplier is applied.
        funded_share = (applicant_capital / required) * 100.0
        results.append({
            "business_category": cat,
            "capital_fit": (
                f"Applicant capital funds {round(funded_share, 1)}% of the estimated requirement"
            ),
            "capital_required": float(required),
            "applicant_capital_share_pct": round(funded_share, 1),
            "why_not_reason": (
                f"Estimated capital requirement {float(required):,.0f} against declared capital "
                f"{float(applicant_capital):,.0f}. Not modelled in this run, so no feasibility "
                f"verdict is issued for this alternative."
            ),
            "evidence_state": model.get("evidence_state", "ESTIMATED"),
        })

    return results
