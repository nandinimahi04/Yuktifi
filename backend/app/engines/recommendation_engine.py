"""
Section 12/13 — hard gates + weighted scoring + verdict banding.

This is the single weighted-score implementation. Two others existed
(`feasibility_engine.compute_yukti_score` and
`scoring_engine.compute_all_dimensions`) with different dimensions, different
weights and different band boundaries, so the same business could receive three
different scores from three endpoints on the same page. Callers that already hold
a `ScoreCard` pass it straight in.

Two corrections to the original arithmetic:

1. Missing dimensions were scored as **0** (`dimension_scores.get(k, 0)`), so a
   dimension nobody measured actively dragged the score down and looked like a
   measured failure. They are now excluded and the remaining weights are
   renormalised, which is the neutral treatment.

2. A dimension present but explicitly `None` - the score card's marker for "not
   computed" - is likewise excluded rather than coerced.

The confidence multiplier is retained: a well-evidenced result should not be
penalised and a poorly-evidenced one should visibly pull the score down.
"""
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

WEIGHTS = {
    "financial_viability": 0.30,
    "repayment_capacity": 0.25,
    "market_opportunity": 0.20,
    "capital_efficiency": 0.15,
    "risk_exposure": 0.10,
}

DSCR_HARD_GATE = 1.0   # below this, verdict cannot be GO regardless of score

#: Below this much evidence, no verdict band is published.
MIN_WEIGHT_FOR_VERDICT = 0.40


@dataclass
class ScoreBreakdown:
    dimensions: dict
    raw_score: Optional[float]
    confidence_multiplier: float
    final_score: Optional[float]
    verdict: Optional[str]
    unscored: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": self.dimensions,
            "raw_score": self.raw_score,
            "confidence_multiplier": self.confidence_multiplier,
            "final_score": self.final_score,
            "verdict": self.verdict,
            "unscored_dimensions": self.unscored,
            "note": self.note,
        }


def band_verdict(score: float, dscr: Optional[float]) -> str:
    """
    Map a score to a verdict band, subject to the DSCR hard gate.

    The gate only applies when there is debt to service. With no debt there is no
    repayment test to fail, so the gate is not applied and the score bands decide
    the verdict on their own.
    """
    if dscr is not None and dscr < DSCR_HARD_GATE:
        return "NOT_RECOMMENDED"
    if score >= 80:
        return "GO"
    if score >= 60:
        return "CAUTION"
    if score >= 40:
        return "ALTERNATIVE"
    return "NOT_RECOMMENDED"


def _as_dimension_map(dimension_scores: Any) -> dict[str, Optional[float]]:
    """
    Normalise the accepted input shapes to {dimension: score-or-None}.

    Accepts a `ScoreCard`, a flat dict of numbers, or the nested
    `{"dimensions": {...}}` payload the API returns.
    """
    if hasattr(dimension_scores, "dimensions") and not isinstance(dimension_scores, Mapping):
        return {d.key: d.score for d in dimension_scores.dimensions}
    if isinstance(dimension_scores, Mapping) and "dimensions" in dimension_scores:
        inner = dimension_scores["dimensions"]
        if isinstance(inner, Mapping):
            return {
                k: (v.get("score") if isinstance(v, Mapping) else v)
                for k, v in inner.items()
            }
        if hasattr(inner, "dimensions"):
            return {d.key: d.score for d in inner.dimensions}
    if isinstance(dimension_scores, Mapping):
        return dict(dimension_scores)
    return {}


def compute_yukti_score(
    dimension_scores: Any,
    confidence_multiplier: float,
    dscr: Optional[float],
) -> ScoreBreakdown:
    """
    Weighted composite over the dimensions that were actually computed.

    `confidence_multiplier` is 0.0-1.0, derived from the aggregate confidence of
    the inputs used. `dscr` is None when the business carries no debt; absent
    DSCR is not a pass and does not satisfy the hard gate.
    """
    dims = _as_dimension_map(dimension_scores)

    scored = {
        k: float(v)
        for k, v in dims.items()
        if k in WEIGHTS and v is not None
    }
    unscored = sorted(set(WEIGHTS) - set(scored))

    if not scored:
        return ScoreBreakdown(
            dimensions=dims, raw_score=None, confidence_multiplier=confidence_multiplier,
            final_score=None, verdict=None, unscored=unscored,
            note=(
                "No dimension could be computed from available evidence, so no composite "
                "score and no verdict are issued. This is a request for data, not a "
                "negative finding."
            ),
        )

    # Renormalise over the scored subset so an unmeasured dimension neither
    # inflates nor deflates the result.
    weight_used = sum(WEIGHTS[k] for k in scored)
    raw = sum(scored[k] * WEIGHTS[k] for k in scored) / weight_used
    final = round(raw * confidence_multiplier, 1)

    if weight_used < MIN_WEIGHT_FOR_VERDICT:
        verdict = None
        note = (
            f"Score computed from {', '.join(sorted(scored))} only "
            f"({weight_used:.0%} of the weighting). Too little of the model is evidenced to "
            f"publish a verdict, so none is issued."
        )
    else:
        verdict = band_verdict(final, dscr)
        note = (
            f"Weighted over {', '.join(sorted(scored))}. "
            f"Not scored (excluded, not imputed as zero): "
            f"{', '.join(unscored) if unscored else 'none'}."
        )

    return ScoreBreakdown(
        dimensions=dims,
        raw_score=round(raw, 1),
        confidence_multiplier=confidence_multiplier,
        final_score=final,
        verdict=verdict,
        unscored=unscored,
        note=note,
    )
