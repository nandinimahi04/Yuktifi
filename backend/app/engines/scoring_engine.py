"""
Composite scoring.

The previous implementation returned an integer for every dimension, substituting
a neutral 50 whenever an input was unknown, then averaged them into a single
"yukti_score" and mapped that to a verdict like "Strong Opportunity". Two
consequences:

* A user with no competitor data, no DSCR and no population figure received a
  score built from three invented 50s and two real numbers, presented with the
  same authority as a fully-evidenced result.
* Because the unknown contributions were free, low evidence produced a
  *middling* score rather than an abstention, and a middling score reads as
  "worth considering".

Now every dimension is either computed from a real input or returns `None`, and
the composite is only produced when enough dimensions are actually known. The
result reports its own coverage, and the verdict is withheld below the coverage
threshold rather than guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

#: Below this many known dimensions, no composite score is published.
MIN_DIMENSIONS_FOR_SCORE = 3

#: Below this composite coverage, the verdict is withheld.
MIN_COVERAGE_FOR_VERDICT = 0.6

#: Consumers per mapped competitor that scores a full 100 on market opportunity.
CONSUMERS_PER_COMPETITOR_TARGET = 2_000.0

#: DSCR at which repayment capacity scores a full 100.
DSCR_TARGET = 2.5

#: ROI and net margin at which financial viability scores a full 100.
ROI_TARGET = 50.0
NET_MARGIN_TARGET = 30.0


@dataclass
class Dimension:
    """One scored dimension, or an explicit absence of one."""

    key: str
    label: str
    score: Optional[int] = None
    known: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "score": self.score,
            "known": self.known,
            "state": "COMPUTED" if self.known else "UNAVAILABLE",
            "reason": self.reason,
        }


def _clamp(v: float) -> int:
    return int(max(0, min(100, v)))


# ── Dimensions ──────────────────────────────────────────────────────────────

def calculate_financial_viability(roi: Optional[float], net_margin: Optional[float]) -> Dimension:
    """
    Weighted blend of ROI and net margin.

    Each component is scored on its own scale first, then weighted, so a missing
    margin reduces the weight the margin can contribute rather than being
    silently replaced by a passing value.
    """
    parts: list[tuple[str, Optional[float], int]] = []
    if roi is not None:
        parts.append(("ROI", min(max(roi, 0.0), ROI_TARGET) / ROI_TARGET * 100, 60))
    if net_margin is not None:
        parts.append(("net margin", min(max(net_margin, 0.0), NET_MARGIN_TARGET) / NET_MARGIN_TARGET * 100, 40))

    if not parts:
        return Dimension("financial_viability", "Financial viability", reason=(
            "Neither ROI nor net margin could be computed, so viability is not scored."
        ))

    total_w = sum(w for _, _, w in parts)
    score = sum(s * w for _, s, w in parts) / total_w
    used = [name for name, _, _ in parts]
    if len(used) == 2:
        reason = "Computed from ROI (60% weight) and net margin (40% weight)."
    else:
        reason = (
            f"Computed from {used[0]} alone. Net margin could not be established, so this "
            f"dimension carries reduced weight and should not be read as a full viability check."
        )
    return Dimension(
        "financial_viability", "Financial viability",
        score=_clamp(score), known=True, reason=reason,
    )


def calculate_repayment_capacity(dscr: Optional[float], has_debt: bool = True) -> Dimension:
    """
    Repayment capacity from DSCR.

    `None` DSCR means there is no debt obligation, not that repayment is
    average. The previous version returned 60 here, which credited a business
    for having borrowed nothing and then averaged that credit into the composite.
    """
    if dscr is None:
        return Dimension("repayment_capacity", "Repayment capacity", reason=(
            "No debt service obligation, so there is nothing to repay and no DSCR to score. "
            "This dimension is not applicable, not average."
            if not has_debt else
            "DSCR could not be computed, so repayment capacity is not scored."
        ))
    if dscr < 1.0:
        return Dimension("repayment_capacity", "Repayment capacity", score=20, known=True,
                         reason=(
                             f"DSCR {dscr:.2f} is below 1.0: projected cash flow does not cover "
                             f"debt service even before any shock."
                         ))
    return Dimension(
        "repayment_capacity", "Repayment capacity",
        score=_clamp(dscr / DSCR_TARGET * 100), known=True,
        reason=f"DSCR {dscr:.2f} against a target of {DSCR_TARGET}.",
    )


def calculate_market_opportunity(
    competitor_count: Optional[int], population: Optional[int]
) -> Dimension:
    """
    Demand headroom from residents per mapped competitor.

    Any of the three states - unknown population, unknown competitor count, or
    too few mapped competitors to be meaningful - yields no score.
    """
    if population is None or population <= 0:
        return Dimension("market_opportunity", "Market opportunity", reason=(
            "No verified population figure for the catchment, so demand headroom is not scored."
        ))
    if competitor_count is None:
        return Dimension("market_opportunity", "Market opportunity", reason=(
            "No competitor survey was completed, so demand headroom is not scored. "
            "An unknown competitor count is not an empty market."
        ))
    if competitor_count < 3:
        return Dimension("market_opportunity", "Market opportunity", reason=(
            f"Only {competitor_count} mapped competitor(s) found. Most informal rural businesses "
            f"are unmapped, so this cannot distinguish an open market from an incomplete map."
        ))

    density = population / competitor_count
    return Dimension(
        "market_opportunity", "Market opportunity",
        score=_clamp(density / CONSUMERS_PER_COMPETITOR_TARGET * 100), known=True,
        reason=(
            f"About {density:,.0f} residents per mapped competitor. Competitor data counts mapped "
            f"businesses only, so this is a lower bound on competitive pressure."
        ),
    )


def calculate_capital_efficiency(
    break_even: Optional[float], projected: Optional[float]
) -> Dimension:
    """
    Capital efficiency from the share of projected sales needed to break even.

    Undefined when contribution per unit is not positive - which is itself the
    answer, and is reported as such rather than as a zero.
    """
    if break_even is None:
        return Dimension("capital_efficiency", "Capital efficiency", reason=(
            "Break-even could not be computed (contribution per unit must exceed zero), so "
            "capital efficiency is not scored. This is a failure of the unit economics, not "
            "an absence of data."
        ))
    if projected is None or projected <= 0:
        return Dimension("capital_efficiency", "Capital efficiency", reason=(
            "No projected revenue, so break-even cannot be expressed as a share of sales."
        ))

    ratio = break_even / projected
    return Dimension(
        "capital_efficiency", "Capital efficiency",
        score=_clamp(100 - ratio * 100), known=True,
        reason=f"Break-even is {ratio * 100:.0f}% of projected revenue.",
    )


def calculate_risk_exposure(confidence: Optional[str], threats_count: Optional[int]) -> Dimension:
    """
    Risk exposure from evidence confidence and the number of identified threats.

    A low evidence confidence is a reason for caution, not a neutral 50.
    """
    if confidence is None:
        return Dimension("risk_exposure", "Risk exposure", reason=(
            "Evidence confidence is undetermined, so risk exposure is not scored."
        ))

    base = {"high": 80, "medium": 55, "low": 30, "unavailable": 0}.get(confidence.lower(), 30)
    if threats_count is None:
        return Dimension("risk_exposure", "Risk exposure", score=_clamp(base), known=True,
                         reason=f"Based on {confidence} evidence confidence; threat count unknown.")

    return Dimension(
        "risk_exposure", "Risk exposure",
        score=_clamp(base - threats_count * 10), known=True,
        reason=f"{confidence} evidence confidence with {threats_count} identified threat(s).",
    )


# ── Composite ───────────────────────────────────────────────────────────────

@dataclass
class ScoreCard:
    """A composite that knows what it does not know."""

    dimensions: list[Dimension] = field(default_factory=list)
    composite: Optional[int] = None
    coverage: float = 0.0
    verdict: Optional[dict[str, Any]] = None
    unscored: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "yukti_score": self.composite,
            "score_coverage_pct": round(self.coverage * 100, 1),
            "verdict": self.verdict,
            "dimensions": {d.key: d.to_dict() for d in self.dimensions},
            "unscored_dimensions": self.unscored,
            "scoring_note": (
                f"Composite is the mean of {len(self.dimensions) - len(self.unscored)} scored "
                f"dimensions. Unscored dimensions are excluded, not imputed, so the score is "
                f"based on a partial evidence base."
            ),
        }


def generate_verdict(overall_score: float) -> dict[str, Any]:
    if overall_score >= 75:
        return {"text": "Strong Opportunity", "color": "emerald-600"}
    if overall_score >= 50:
        return {"text": "Moderate Potential", "color": "amber-600"}
    return {"text": "High Risk", "color": "red-600"}


def compute_all_dimensions(
    roi: Optional[float] = None,
    dscr: Optional[float] = None,
    net_margin: Optional[float] = None,
    break_even_units: Optional[float] = None,
    monthly_units: Optional[float] = None,
    competitor_count: Optional[int] = None,
    population: Optional[int] = None,
    overall_confidence: Optional[str] = None,
    threats_count: Optional[int] = None,
    has_debt: bool = True,
) -> ScoreCard:
    """Compute every dimension, then publish a composite only if it is earned."""
    dims = [
        calculate_financial_viability(roi, net_margin),
        calculate_repayment_capacity(dscr, has_debt=has_debt),
        calculate_market_opportunity(competitor_count, population),
        calculate_capital_efficiency(break_even_units, monthly_units),
        calculate_risk_exposure(overall_confidence, threats_count),
    ]

    known = [d for d in dims if d.known]
    unscored = [d.label for d in dims if not d.known]
    coverage = len(known) / len(dims)

    composite: Optional[int] = None
    verdict: Optional[dict[str, Any]] = None

    if len(known) >= MIN_DIMENSIONS_FOR_SCORE:
        composite = round(sum(d.score for d in known) / len(known))  # type: ignore[misc]
        if coverage >= MIN_COVERAGE_FOR_VERDICT:
            verdict = generate_verdict(composite)

    return ScoreCard(
        dimensions=dims, composite=composite, coverage=coverage,
        verdict=verdict, unscored=unscored,
    )


def generate_next_steps(
    scores: dict[str, Any], financials: dict[str, Any], market: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Next steps, most important first.

    An unscored dimension produces a step to obtain the data, which is the honest
    action: you cannot act on a dimension you could not measure.
    """
    steps: list[dict[str, Any]] = []
    dims = scores.get("dimensions", scores)

    def _score_of(key: str) -> Optional[int]:
        d = dims.get(key)
        if isinstance(d, dict):
            return d.get("score")
        return d if isinstance(d, (int, float)) else None

    repay = _score_of("repayment_capacity")
    if repay is None:
        steps.append({
            "priority": 1, "action": "Confirm the funding structure", "module": "financial",
            "reason": "Repayment capacity could not be scored. Establish whether the project will "
                      "carry debt, and if so on what terms, before relying on this analysis.",
        })
    elif repay < 50:
        steps.append({
            "priority": 1, "action": "Reduce the loan amount or extend tenure", "module": "financial",
            "reason": "DSCR is below 1.5. Projected cash flow does not cover debt service with a "
                      "safe margin, so the repayment schedule needs restructuring.",
        })

    fin = _score_of("financial_viability")
    if fin is not None and fin < 60:
        steps.append({
            "priority": 2, "action": "Re-cost the project before committing", "module": "financial",
            "reason": "Financial viability scores low. Obtain actual supplier quotations and "
                      "confirmed prices rather than sector assumptions.",
        })

    market_dim = _score_of("market_opportunity")
    if market_dim is None:
        steps.append({
            "priority": 1, "action": "Survey competitors on foot", "module": "market",
            "reason": "Local competition was not established. Walk the 5 km catchment and count "
                      "comparable businesses by hand; the map data is known to be incomplete.",
        })
    elif market_dim < 50:
        steps.append({
            "priority": 1, "action": "Survey competitors on foot", "module": "market",
            "reason": "Competitive density appears high relative to the local population. "
                      "Verify with a physical survey before entering.",
        })

    risk = _score_of("risk_exposure")
    if risk is None:
        steps.append({
            "priority": 2, "action": "Gather the missing evidence", "module": "risk",
            "reason": "Risk exposure could not be scored because evidence confidence is undetermined.",
        })
    elif risk < 60:
        steps.append({
            "priority": 2, "action": "Review the identified threats", "module": "risk",
            "reason": "Evidence is thin or several structural risks were flagged.",
        })

    if not steps:
        steps.append({
            "priority": 3, "action": "Move to a detailed business plan", "module": "general",
            "reason": "Every scored dimension is healthy. Begin formalising the launch plan, "
                      "and re-verify the cost and price assumptions with real quotations.",
        })

    steps.sort(key=lambda s: s["priority"])
    return steps
