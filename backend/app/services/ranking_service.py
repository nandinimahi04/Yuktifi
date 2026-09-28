"""
Opportunity ranking — evaluates every business category for a location and
declared capital, and returns a ranked list.

This is the "magic moment" screen, which makes it the most dangerous place in the
codebase to be vague: a ranked list reads as a verdict, so any invented input
here becomes a confident recommendation to a real person staking their savings.

What the previous version did, and why each part is now gone:

* `compute_emi(loan_amount, 10.0, 60, 0)` when no scheme matched. It invented a
  10% rate and a 5-year tenure, then reported a DSCR against that fiction. A
  business could be shown as comfortably repaying against a loan that does not
  exist. Financing terms are now either taken from a matched scheme or left
  unknown, and unknown means no DSCR.
* `repayment_capacity = 60 if dscr is None`. An unmeasurable dimension was
  scored 60, i.e. slightly better than neutral, and then dragged into a weighted
  average. It now abstains and is excluded from the average.
* `capital_efficiency = ... else 60`, `gap_score ... or 50`, `roi + 30`,
  `100 - (break_even / 10)`. The same imputation problem, plus affine
  transforms with no stated basis. All scoring now lives in
  `scoring_engine`, which documents each rule.
* `yukti_score: 0, verdict: "NOT_RECOMMENDED"` when cost data was missing.
  Absent evidence presented as a failed business. Missing data now yields no
  score and no verdict, with the reason attached.
* `net_profit` computed pre-interest and pre-tax, then used for DSCR. That
  credits the business with cash it will never have, because the interest on the
  loan is never subtracted. The canonical engine computes the full waterfall.

The score is now the composite from `scoring_engine` over dimensions it can
actually compute, with coverage published alongside it so a thin ranking is
visibly thin rather than quietly authoritative.
"""
from __future__ import annotations

from typing import Any, Optional

from app.data_layer.retrieval import DataRetrieval
from app.services.data_service import data_service
from app.engines.financial_engine import compute_loan_amount
from app.engines.scheme_engine import match_scheme
from app.engines.recommendation_engine import compute_yukti_score
from app.engines.scoring_engine import compute_all_dimensions
from app.engines.market_intelligence import run_full_market_analysis
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)

data_layer = DataRetrieval()

CATEGORY_NAMES = {
    "dairy": "Dairy",
    "retail_kirana": "Retail / Kirana Store",
    "tailoring": "Tailoring",
    "flour_mill": "Flour Mill",
    "poultry": "Poultry",
}


def _category_name(cat_id: str) -> str:
    """
    Display name for a category, read from the dataset.

    The hardcoded map above is retained for the ids it knows, but it is not the
    source of truth: it had drifted from `categories.json`, so `textiles` and
    `services` fell through to rendering as their raw slug ("textiles") in the
    user-facing list. The dataset name is preferred wherever one exists.
    """
    for row in data_service.get_dataset("categories") or []:
        if row.get("id") == cat_id and row.get("name"):
            return row["name"]
    return _category_name(cat_id)

#: Required by the canonical model, which is monthly-scaled. A single product
#: line is expressed as one unit of the reference model, so the line amounts
#: below divide the monthly totals out over the whole month.
UNIT_SCALE = 1.0

#: Applied only when a scheme actually supplies terms. Never a default.
_FALLBACK_NOTE = (
    "No financing terms available: no scheme matched and no loan terms were declared. "
    "Repayment capacity cannot be assessed."
)


def _finite(value: Any) -> Optional[float]:
    """Return a usable positive float, or None. Never coerce junk to 0."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _positive(value: Any) -> Optional[float]:
    f = _finite(value)
    return f if f is not None and f > 0 else None


def _unrankable(
    cat_id: str,
    cat_name: str,
    reason: str,
    evidence_state: str,
    **extra: Any,
) -> dict[str, Any]:
    """
    An entry that cannot be scored.

    `yukti_score` and `verdict` are None. Zero and NOT_RECOMMENDED are
    available values in this schema and both of them are false judgements: a
    business nobody has costed yet is not a business that has been tried and
    failed. Ranking handles the None by sorting these last.
    """
    return {
        "category_id": cat_id,
        "category_name": cat_name,
        "yukti_score": None,
        "ranked": False,
        "verdict": None,
        "confidence": "UNAVAILABLE",
        "evidence_state": evidence_state,
        "dimension_scores": {},
        "unscored_dimensions": [],
        "unscored_labels": [],
        "score_coverage_pct": 0.0,
        "dscr": None,
        "dscr_status": "UNAVAILABLE",
        "roi": None,
        "emi": None,
        "loan_amount": None,
        "financing_terms_status": "UNKNOWN",
        "project_cost": None,
        "project_cost_status": "UNKNOWN",
        "net_profit": None,
        "net_margin": None,
        "break_even_units": None,
        "payback_months": None,
        "payback_status": "UNDETERMINED",
        "npv": None,
        "economic_viability": "UNDETERMINED",
        # The reason a category is unrankable is a missing input, not a failed
        # gate, so it is recorded as an unknown. `viability_reasons` stays empty:
        # listing a data gap there would show a bank officer a failure list for a
        # business that simply has not been costed.
        "viability_reasons": [],
        "assessability_unknowns": [reason],
        "scheme_name": None,
        "scheme_status": "Not evaluated",
        "highlights": [],
        "note": reason,
        **extra,
    }


def _evaluate_category(
    location_id: str, cat_id: str, cat_name: str, own_contribution: float
) -> dict[str, Any]:
    cost_result = data_layer.get_cost_profile(location_id, cat_id)
    cost = cost_result.get("value")

    if not cost:
        return _unrankable(
            cat_id,
            cat_name,
            cost_result.get("note", "No cost profile available for this category."),
            cost_result.get("evidence_state", "MISSING"),
            limitations=cost_result.get("limitations"),
        )

    monthly_units = _positive(cost.get("estimated_monthly_units"))
    selling_price = _positive(cost.get("selling_price_per_unit"))
    variable_cost = _finite(cost.get("variable_cost_per_unit"))
    fixed_cost = _finite(cost.get("fixed_cost_monthly"))
    cat_project_cost = _positive(cost.get("total_setup_cost"))

    # The reference model carries a revenue estimate; the canonical model wants
    # price and volume. Revenue is only used to back out volume when units are
    # genuinely absent, and the row is left unscored when it cannot be derived.
    if monthly_units is None:
        monthly_revenue = _positive(cost.get("estimated_monthly_revenue"))
        if monthly_revenue and selling_price:
            monthly_units = monthly_revenue / selling_price

    missing = [
        label
        for label, val in (
            ("monthly units", monthly_units),
            ("selling price per unit", selling_price),
            ("variable cost per unit", variable_cost),
            ("fixed monthly cost", fixed_cost),
        )
        if val is None
        or (val <= 0 and label not in ("variable cost per unit", "fixed monthly cost"))
    ]
    if missing:
        return _unrankable(
            cat_id,
            cat_name,
            "The published cost reference is incomplete for this category, so it cannot be "
            f"modelled. Missing: {', '.join(missing)}.",
            cost_result.get("evidence_state", "MISSING"),
            limitations=cost_result.get("limitations"),
        )

    # ── Financing, from declared terms only ─────────────────────────────────
    # An unknown capital requirement means no scheme can be matched (schemes are
    # banded on project cost) and no loan can be sized. That is left unknown.
    if cat_project_cost is not None:
        cat_own_contribution = min(own_contribution, cat_project_cost)
        scheme = match_scheme(cat_project_cost, own_contribution=cat_own_contribution)
        loan_amount = compute_loan_amount(
            cat_project_cost,
            scheme.max_loan if scheme.matched else None,
            own_contribution=cat_own_contribution,
        )
    else:
        cat_own_contribution = 0.0
        scheme = match_scheme(0.0)
        loan_amount = 0.0

    rate = _positive(scheme.rate) if (scheme.matched and scheme.rate is not None) else None
    tenure_months = None
    if scheme.matched and scheme.tenure_years:
        tenure_months = int(round(float(scheme.tenure_years) * 12)) or None
    moratorium = int(scheme.moratorium_months or 0) if scheme.matched else 0

    has_financing_terms = loan_amount > 0 and rate is not None and tenure_months

    # ── Canonical model ────────────────────────────────────────────────────
    financial = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type=cat_name,
            products=[
                ProductItem(
                    name=f"{cat_name} (reference unit)",
                    units_per_month=monthly_units * UNIT_SCALE,
                    selling_price=selling_price,
                    variable_cost_per_unit=variable_cost,
                )
            ],
            # The reference model publishes fixed cost as a single line; it is
            # loaded as rent so the canonical opex breakdown stays structured and
            # the figure is not silently dropped.
            opex=OpexBreakdown(rent=max(0.0, fixed_cost)),
            own_capital=cat_own_contribution,
            total_project_cost=cat_project_cost,  # None when uncosted, and left as such
            debt_amount=loan_amount if has_financing_terms else 0.0,
            interest_rate_annual_pct=rate if has_financing_terms else 0.0,
            tenure_months=tenure_months or 60,
            moratorium_months=moratorium if has_financing_terms else 0,
            # asset_cost stays 0 when the project cost is unknown: it is a
            # depreciable base, and there is no base to depreciate. The engine
            # requires a number here, so 0 is the honest "no asset base" value
            # and it suppresses depreciation rather than inventing one.
            asset_cost=cat_project_cost or 0.0,
        )
    )

    # ── Market context (used for scoring, not invented) ─────────────────────
    market = run_full_market_analysis(location_id, cat_id, cat_name)
    competitor_count = _finite(
        (market.get("competitors") or {}).get("value", {}).get("count")
    )
    population = _positive(market.get("population") or (market.get("population_radius") or {}).get("value"))
    threat_count = _positive(
        (market.get("threats") or {}).get("value", {}).get("high_severity_count")
    )
    overall_confidence = market.get("overall_confidence")

    # ── Score via the single shared scoring engine ──────────────────────────
    card = compute_all_dimensions(
        roi=financial.roi_on_total_project_pct,
        dscr=financial.dscr,
        net_margin=financial.net_margin_pct,
        break_even_units=financial.break_even_units_monthly,
        monthly_units=monthly_units,
        competitor_count=int(competitor_count) if competitor_count is not None else None,
        population=int(population) if population is not None else None,
        overall_confidence=overall_confidence,
        threats_count=int(threat_count) if threat_count is not None else None,
        has_debt=bool(has_financing_terms),
    )
    score_result = compute_yukti_score(
        dimension_scores=card,
        confidence_multiplier=market.get("confidence_multiplier", 1.0),
        dscr=financial.dscr,
    )

    highlights: list[str] = []
    if financial.dscr is None:
        highlights.append(_FALLBACK_NOTE if not has_financing_terms else
                          "No debt service obligation, so repayment capacity is not applicable.")
    elif financial.dscr >= 1.5:
        highlights.append(f"Strong repayment capacity (modelled DSCR {financial.dscr}x).")
    elif financial.dscr >= 1.0:
        highlights.append(f"Adequate repayment capacity (modelled DSCR {financial.dscr}x).")
    else:
        highlights.append(f"Weak repayment capacity (modelled DSCR {financial.dscr}x).")
    if financial.roi_on_total_project_pct is not None and financial.roi_on_total_project_pct > 20:
        highlights.append(f"Strong modelled return on capital ({financial.roi_on_total_project_pct}%).")
    if competitor_count is not None and competitor_count <= 3:
        highlights.append(
            f"Few mapped competitors ({int(competitor_count)}), subject to survey coverage."
        )
    if card.unscored:
        highlights.append(
            "Not assessed: "
            + ", ".join(d.key.replace("_", " ") for d in card.dimensions if not d.known)
            + "."
        )

    notes: list[str] = []
    if cost_result.get("requires_confirmation"):
        notes.append(cost_result["note"])
    if cat_project_cost is None:
        notes.append(
            "No capital requirement is published for this category, so return on capital, "
            "payback and net present value are not assessed. Cost economics and market "
            "context below are still modelled."
        )
    if not has_financing_terms and loan_amount > 0:
        notes.append(
            f"Debt of {loan_amount:,.0f} would be required, but no rate and tenure are known, "
            f"so it is excluded from the model and repayment capacity is left unassessed."
        )
    if financial.financing_gap:
        notes.append(
            f"Funding does not cover project cost: unfunded gap of "
            f"{abs(financial.financing_gap):,.0f}."
        )

    return {
        "category_id": cat_id,
        "category_name": cat_name,
        "yukti_score": score_result.final_score,
        "ranked": score_result.final_score is not None,
        "verdict": score_result.verdict,
        # ScoreBreakdown exposes no confidence field of its own, and inventing
        # one here is how "Low" or "Medium" strings ended up attached to results
        # nothing measured. Coverage is the honest signal: it is the share of
        # dimensions actually computed.
        "confidence": (
            "High" if card.coverage >= 100
            else "Medium" if card.coverage >= 60
            else "Low" if card.coverage > 0
            else "UNAVAILABLE"
        ),
        "evidence_state": cost_result.get("evidence_state"),
        "score_coverage_pct": card.coverage,
        "dimension_scores": {
            d.key: d.score for d in card.dimensions
        },
        "unscored_dimensions": [d.key for d in card.dimensions if not d.known],
        "unscored_labels": list(card.unscored),
        "dscr": financial.dscr,
        "dscr_status": financial.dscr_status,
        "roi": financial.roi_on_total_project_pct,
        "emi": financial.monthly_emi if has_financing_terms else None,
        "loan_amount": loan_amount if has_financing_terms else None,
        "financing_terms_status": "DECLARED" if has_financing_terms else "UNKNOWN",
        "project_cost": cat_project_cost,
        "project_cost_status": "DECLARED" if cat_project_cost is not None else "UNKNOWN",
        "net_profit": financial.monthly_pat,
        "net_margin": financial.net_margin_pct,
        "break_even_units": financial.break_even_units_monthly,
        "payback_months": financial.payback_months,
        "payback_status": financial.payback_status,
        "npv": financial.npv,
        "economic_viability": financial.economic_viability,
        "viability_reasons": financial.viability_reasons,
        "assessability_unknowns": financial.assessability_unknowns,
        "scheme_name": scheme.scheme_name if scheme.matched else None,
        "scheme_status": "Potentially eligible" if scheme.matched else "Not matched",
        "highlights": highlights,
        "note": " ".join(notes) if notes else (
            f"Composite score computed from {card.coverage:.0f}% dimension coverage."
        ),
        "limitations": cost_result.get("limitations"),
    }


def rank_opportunities(location_id: str, margin_capital: float) -> list[dict[str, Any]]:
    """
    Evaluate every available business category for the given location and capital.

    Returns a list sorted by YuktiFi score descending, with unscoreable
    categories last. Unscoreable entries are retained rather than filtered out,
    because "we could not assess this" is information the user needs in order to
    know which categories to gather quotes for.
    """
    category_ids = data_layer.get_all_category_ids(location_id)
    if not category_ids:
        return []

    own_contribution = _positive(margin_capital)
    if own_contribution is None:
        return [
            _unrankable(
                cat_id,
                _category_name(cat_id),
                "No usable capital amount was supplied, so affordability cannot be compared.",
                "MISSING",
            )
            for cat_id in category_ids
        ]

    results = [
        _evaluate_category(
            location_id, cat_id, _category_name(cat_id), own_contribution
        )
        for cat_id in category_ids
    ]

    def sort_key(row: dict[str, Any]) -> tuple:
        # Unranked rows sort last, then by coverage so the best-evidenced
        # unranked row appears first among them.
        score = row.get("yukti_score")
        return (
            0 if score is not None else 1,
            -(score if score is not None else 0),
            -(row.get("score_coverage_pct") or 0.0),
        )

    results.sort(key=sort_key)
    for position, row in enumerate(results, start=1):
        row["rank"] = position if row.get("yukti_score") is not None else None
    return results
