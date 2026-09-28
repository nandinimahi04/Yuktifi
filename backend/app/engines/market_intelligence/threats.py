"""
Threat assessment, computed from measured inputs.

`risk_score` from this module is consumed by the ranking service and becomes the
`risk_exposure` scored dimension, so a value produced here is not commentary: it
changes a number a real entrepreneur sees and acts on.

That is why it is no longer produced by a language model. The previous version
asked Gemini for `risk_score` (defaulting to 50 if the model omitted it) and
self-reported `confidence: "High"` for whatever came back. So the risk dimension
of the ranking screen was, in the absence of a key, a hardcoded 50 minus 50 =
a neutral-looking 50, presented as a High-confidence model output. The offline
fallback had the same shape: 50, plus 20 if `competitor_count >= 7`.

The deterministic rules below are conservative on purpose. A threat that cannot
be measured is reported as unmeasured rather than folded into a score, and the
number of identified threats is what the scoring engine consumes.
"""
from __future__ import annotations

from typing import Any, Optional

#: Mapped competitors at or above this count are treated as dense competition.
COMPETITION_DENSITY_THRESHOLD = 7

#: A demand-gap score at or below this indicates supply may already cover demand.
SATURATION_GAP_THRESHOLD = 40

#: Risk points contributed by each identified threat.
_BASE_RISK = 50
_DENSE_COMPETITION_RISK = 20
_SATURATED_MARKET_RISK = 15
_UNMEASURED_COMPETITION_RISK = 10


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def build_threat_assessment(
    category_name: str,
    competitor_count: Optional[int] = None,
    gap_score: Optional[float] = None,
    pricing: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Deterministic threat list and risk score.

    Each risk factor records the evidence it came from, so the user can see what
    is driving the score rather than being handed a number.
    """
    factors: list[dict[str, Any]] = []
    risk = _BASE_RISK
    unmeasured: list[str] = []

    comp = _num(competitor_count)
    gap = _num(gap_score)

    if comp is None:
        unmeasured.append("competitor count")
        risk += _UNMEASURED_COMPETITION_RISK
        factors.append({
            "factor": "Competition not measured",
            "severity": "Medium",
            "detail": (
                "No competitor survey is available for this location, so competitive pressure is "
                "unquantified. Absence of a count is not evidence of low competition."
            ),
            "evidence_state": "UNAVAILABLE",
        })
    elif comp >= COMPETITION_DENSITY_THRESHOLD:
        risk += _DENSE_COMPETITION_RISK
        factors.append({
            "factor": "High competition density",
            "severity": "High",
            "detail": (
                f"{int(comp)} competitors mapped in the catchment, which pressures both price and "
                f"available volume. Mapped counts cover OSM-visible businesses only."
            ),
            "evidence_state": "ESTIMATED",
        })

    if gap is None:
        unmeasured.append("demand gap")
    elif gap <= SATURATION_GAP_THRESHOLD:
        risk += _SATURATED_MARKET_RISK
        factors.append({
            "factor": "Demand may already be served",
            "severity": "Medium",
            "detail": (
                f"Demand-gap score is {round(gap)}/100, indicating existing supply may cover much "
                f"of local demand."
            ),
            "evidence_state": "ESTIMATED",
        })

    # Structural risks that are true of the model rather than of the measurement.
    factors.append({
        "factor": "Input cost volatility",
        "severity": "Medium",
        "detail": (
            "Input prices and interest rates can rise against the model. The stress matrix "
            "quantifies the effect of +10%/+15% costs and a +2 point rate rise."
        ),
        "evidence_state": "STRUCTURAL",
    })
    factors.append({
        "factor": "First-hand cost evidence",
        "severity": "Medium",
        "detail": (
            "Cost figures are published reference models, not the applicant's own quotations, so "
            "the modelled margin may not survive contact with real supplier prices."
        ),
        "evidence_state": "STRUCTURAL",
    })

    severity_counts = {
        s: sum(1 for f in factors if f["severity"] == s) for s in ("High", "Medium", "Low")
    }

    return {
        "risk_score": max(0, min(100, int(round(risk)))),
        "risk_factors": factors,
        "count": len(factors),
        "severity_counts": severity_counts,
        "high_severity_count": severity_counts["High"],
        "competitor_count": int(comp) if comp is not None else None,
        "gap_score": gap,
        "unmeasured": unmeasured,
        "confidence": "Medium" if not unmeasured else "Low",
        "note": (
            "Risk score is computed from measured inputs by fixed rules. "
            + (
                f"Not measured: {', '.join(unmeasured)}."
                if unmeasured
                else "All risk inputs were available."
            )
        ),
        "source": "deterministic",
    }


async def assess_threats_async(
    competitor_count: Optional[int] = None,
    gap_score: Any = None,
    category_name: str = "",
    pricing: Optional[dict] = None,
    gemini: Any = None,
    confidence: str = "Low",
    user_context: str = "",
) -> dict[str, Any]:
    """
    Deterministic assessment. `gemini` is accepted for call-site compatibility
    and is deliberately unused: this output is scored, so it cannot be authored.
    """
    return build_threat_assessment(
        category_name=category_name,
        competitor_count=competitor_count,
        gap_score=gap_score,
        pricing=pricing,
    )


def assess_threats(
    competitor_count: Optional[int] = None,
    gap_score: Any = None,
    category_name: str = "",
    pricing: Optional[dict] = None,
    confidence: str = "Low",
) -> dict[str, Any]:
    """Sync entry point. No network call is made."""
    return build_threat_assessment(
        category_name=category_name,
        competitor_count=competitor_count,
        gap_score=gap_score,
        pricing=pricing,
    )
