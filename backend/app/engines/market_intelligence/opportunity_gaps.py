"""
Demand vs supply gap analysis.

The `gap_score` is computed here, deterministically, from the two signals that
actually exist. It is never asked for from a language model.

Two earlier behaviours made this number untrustworthy:

* The Gemini prompt requested `gap_score` and `demand_supply_ratio` directly, so
  a model was producing the headline market score on a 0-100 scale with no
  arithmetic behind it. A score is a calculation, not an opinion.
* When Gemini was unavailable the fallback returned a hardcoded
  `gap_score: 70` with the note "Fallback estimate used" - a specific,
  confident-looking number attached to no evidence at all.

Now: the ratio and score are derived in code, the LLM may only rephrase the
finding in plain language, and if either input is missing the module abstains
rather than producing a number.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: Consumers per mapped competitor at which the market reads as saturated.
SATURATION_CONSUMERS_PER_COMPETITOR = 2_000.0

#: Below this many mapped competitors the coverage is too thin to score.
MIN_COMPETITORS_FOR_SCORING = 3


def _abstain(reason: str, confidence: str = "UNAVAILABLE") -> dict[str, Any]:
    return {
        "gap_score": None,
        "demand_supply_ratio": None,
        "assessment": reason,
        "confidence": "UNAVAILABLE",
        "note": reason,
        "basis": "insufficient_evidence",
    }


def compute_gap_score(consumer_base: Optional[int], competitor_count: Optional[int]) -> dict[str, Any]:
    """
    Deterministic demand/supply reading. Pure function of its inputs.

    Returns `gap_score: None` when the inputs cannot support one. `competitor_count`
    is a count of MAPPED businesses, so the score is explicitly a lower-bound
    reading of demand pressure: more unmapped competitors would mean a more
    saturated market than the score suggests.
    """
    if not consumer_base or consumer_base <= 0:
        return _abstain(
            "No verified population figure for the catchment, so demand pressure cannot be "
            "estimated."
        )
    if competitor_count is None:
        return _abstain(
            "No competitor survey was completed, so supply cannot be compared with demand. "
            "This is not evidence of an underserved market."
        )
    if competitor_count < MIN_COMPETITORS_FOR_SCORING:
        return _abstain(
            f"Only {competitor_count} mapped competitor(s) found. That is too thin to distinguish "
            f"an underserved market from an unmapped one, since most informal rural businesses are "
            f"absent from OpenStreetMap."
        )

    ratio = consumer_base / competitor_count
    gap_score = max(0, min(100, int(ratio / SATURATION_CONSUMERS_PER_COMPETITOR * 100)))

    if gap_score > 70:
        reading = (
            f"High apparent demand pressure: about {ratio:,.0f} residents per mapped competitor."
        )
    elif gap_score > 40:
        reading = f"Balanced market: about {ratio:,.0f} residents per mapped competitor."
    else:
        reading = (
            f"Apparent saturation: only about {ratio:,.0f} residents per mapped competitor."
        )

    return {
        "gap_score": gap_score,
        "demand_supply_ratio": round(ratio, 2),
        "assessment": reading,
        "confidence": "MEDIUM",
        "note": (
            f"Computed as residents-per-mapped-competitor against a saturation reference of "
            f"{SATURATION_CONSUMERS_PER_COMPETITOR:,.0f}. Because competitor data counts MAPPED "
            f"businesses only, this is a lower bound on competitive pressure: if unmapped "
            f"competitors exist, the market is more saturated than this score indicates."
        ),
        "basis": "computed",
    }


async def analyze_opportunity_gaps_async(
    consumer_base: Optional[int],
    competitor_count: Optional[int],
    category_name: str,
    gemini=None,
    confidence: str = "LOW",
    user_context: str = "",
) -> dict[str, Any]:
    """
    Computes the score in code, then optionally asks the model to restate it.

    The model is given the computed figures and instructed not to introduce new
    ones. If it returns numbers, they are ignored: only the prose is kept.
    """
    computed = compute_gap_score(consumer_base, competitor_count)

    if computed["basis"] == "insufficient_evidence":
        return computed

    if gemini is not None:
        try:
            narrative = await gemini.generate_json_async(
                f"""
                A market analysis computed these figures for a '{category_name}' business:
                - Residents in the {consumer_base:,} catchment: {consumer_base:,}
                - Mapped competitors found: {competitor_count}
                - Residents per mapped competitor: {computed['demand_supply_ratio']:,.0f}
                - Demand-pressure score (0-100, 100 = most headroom): {computed['gap_score']}

                {user_context}

                Write a two-sentence plain-language reading for a first-time rural entrepreneur.
                Do NOT introduce any new numbers. Do NOT restate or reinterpret the score.
                Explain only what the existing figures mean for someone considering this business.
                Output ONLY a JSON object: {{"commentary": string}}
                """
            )
            if isinstance(narrative, dict) and narrative.get("commentary"):
                computed["commentary"] = str(narrative["commentary"])
                computed["commentary_source"] = "AI narrative over computed figures (no new numbers)"
        except Exception as exc:  # noqa: BLE001 - narrative is optional
            logger.info("Gap commentary unavailable: %s", exc)

    return computed


def analyze_opportunity_gaps(
    consumer_base: Optional[int],
    competitor_count: Optional[int],
    category_name: str,
    confidence: str = "LOW",
) -> dict[str, Any]:
    """Deterministic, no model. Used by tests and offline callers."""
    return compute_gap_score(consumer_base, competitor_count)
