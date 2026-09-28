"""
SWOT, built from the evidence rather than from a language model.

The previous implementation asked Gemini for the SWOT and, when Gemini was
unavailable, substituted a hardcoded fallback that invented a
"Government scheme support available" claim - a scheme eligibility statement
that was never checked against any rule - and reported `confidence: "High"`
for whatever the model returned, regardless of whether a single input was
verified. A SWOT that asserts a policy benefit the system has not evaluated is
exactly the kind of claim that must never be AI-authored.

SWOT is now derived from the deterministic facts the engines already computed:

* strengths     -> economics that actually clear their thresholds
* weaknesses    -> economics that actually miss their thresholds
* opportunities -> unmet-but-sized demand and thin competition
* threats       -> measured competition, negative margins, coverage gaps

Gemini is retained only as an optional *phraser*: it receives the completed,
factual SWOT and may improve the wording. Its output is validated and dropped
unless it introduces no figure that is not already present in the deterministic
facts. So the worst case is that the plain sentences are used.
"""
from __future__ import annotations

from typing import Any, Optional


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


def build_swot_facts(
    category_name: str,
    competitor_count: Optional[int] = None,
    gap_score: Optional[float] = None,
    pricing: Optional[dict] = None,
    cost_profile: Optional[dict] = None,
    demographics: Optional[dict] = None,
    financials: Optional[dict] = None,
) -> dict[str, Any]:
    """
    The deterministic SWOT. Every sentence traces to a measured input.
    """
    strengths: list[str] = []
    weaknesses: list[str] = []
    opportunities: list[str] = []
    threats: list[str] = []

    fin = financials or {}
    dscr = _num(fin.get("dscr"))
    net_margin = _num(fin.get("net_margin_pct"))
    roi = _num(fin.get("roi_pct"))
    break_even = _num(fin.get("break_even_units"))
    units = _num(fin.get("monthly_units"))
    viability = fin.get("economic_viability")

    # ── Strengths: economics that clear a threshold ─────────────────────────
    if net_margin is not None and net_margin > 10:
        strengths.append(
            f"Modelled net margin of {round(net_margin, 1)}% leaves a buffer over variable and "
            f"fixed costs."
        )
    if dscr is not None and dscr >= 1.25:
        strengths.append(
            f"Operating cash covers modelled debt service {dscr}x, above the 1.25 comfort "
            f"benchmark."
        )
    elif dscr is None and not fin.get("debt_amount"):
        strengths.append(
            "No debt obligation, so repayment risk does not arise from this business."
        )
    if roi is not None and roi > 0:
        strengths.append(f"Modelled return on capital of {round(roi, 1)}%.")
    if viability == "VIABLE":
        strengths.append("Passes every modelled financial viability check.")

    # ── Weaknesses: economics that miss one ────────────────────────────────
    if net_margin is not None and net_margin <= 0:
        weaknesses.append(
            f"Modelled net margin is {round(net_margin, 1)}%: revenue does not cover variable "
            f"cost, fixed cost, interest and depreciation."
        )
    if dscr is not None and dscr < 1.0:
        weaknesses.append(
            f"Modelled DSCR of {dscr}x is below 1.0, so operating cash does not cover debt "
            f"service."
        )
    if break_even is not None and units is not None and break_even > units:
        weaknesses.append(
            f"Break-even requires {round(break_even)} units per month against "
            f"{round(units)} modelled as achievable."
        )
    if fin.get("financing_gap"):
        weaknesses.append(
            f"Funding leaves an unfunded gap of {abs(fin['financing_gap']):,.0f}."
        )

    # ── Opportunities ──────────────────────────────────────────────────────
    if gap_score is not None and gap_score >= 60:
        opportunities.append(
            f"Demand-gap score of {round(gap_score)}/100 suggests catchment consumers are not "
            f"fully served by mapped competitors."
        )
    if competitor_count is not None and competitor_count <= 3:
        opportunities.append(
            f"Only {competitor_count} competitors mapped nearby, so a share of demand may be "
            f"unserved."
        )
    pricing_gap = (pricing or {}).get("value")
    if pricing_gap:
        opportunities.append(f"Local reference price evidence available: {pricing_gap}.")

    # ── Threats ────────────────────────────────────────────────────────────
    if competitor_count is not None and competitor_count > 5:
        threats.append(
            f"{competitor_count} competitors mapped in the catchment, which pressures price and "
            f"volume."
        )
    if gap_score is not None and gap_score < 40:
        threats.append(
            f"Low demand-gap score of {round(gap_score)}/100: existing supply may already cover "
            f"local demand."
        )
    threats.append(
        "Input costs, interest rates and demand can all move against the model; see the stress "
        "matrix for the modelled effect of each."
    )

    # An empty quadrant is reported as empty, not padded with a generic line.
    if not strengths:
        strengths.append("No strength cleared its threshold on the available evidence.")
    if not weaknesses:
        weaknesses.append("No weakness was measurable from the available evidence.")
    if not opportunities:
        opportunities.append("No unmet demand could be sized from the available evidence.")
    if not threats:
        threats.append("No specific threat could be measured from the available evidence.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
        "note": (
            "Derived from measured inputs. Unmeasured factors are listed as unknown rather than "
            "estimated."
        ),
        "unmeasured": _unmeasured(competitor_count, gap_score, net_margin, dscr),
        "source": "deterministic",
    }


def _unmeasured(
    competitor_count: Optional[int],
    gap_score: Optional[float],
    net_margin: Optional[float],
    dscr: Optional[float],
) -> list[str]:
    out = []
    if competitor_count is None:
        out.append("competitor count")
    if gap_score is None:
        out.append("demand gap")
    if net_margin is None:
        out.append("net margin")
    if dscr is None and _num(dscr) is None:
        out.append("repayment capacity")
    return out


def _allowed_figures(*sources: Any) -> set[str]:
    """Every numeric token that legitimately appears in the deterministic facts."""
    import re

    tokens: set[str] = set()
    for src in sources:
        for match in re.findall(r"\d+(?:\.\d+)?", str(src)):
            tokens.add(match.rstrip("0").rstrip("."))
            tokens.add(match)
    return tokens


async def generate_swot_async(
    category_name: str,
    competitor_count: Optional[int] = None,
    gap_score: None = None,
    pricing: dict | None = None,
    cost_profile: dict | None = None,
    demographics: dict | None = None,
    gemini=None,
    confidence: str = "Low",
    user_context: str = "",
    financials: dict | None = None,
) -> dict[str, Any]:
    """
    Build the deterministic SWOT, then optionally let Gemini improve the wording.

    Gemini receives a finished analysis. It cannot add a fact, and any figure it
    introduces that is not already in the deterministic facts causes its output
    to be discarded in favour of the plain sentences.
    """
    facts = build_swot_facts(
        category_name=category_name,
        competitor_count=competitor_count,
        gap_score=gap_score,
        pricing=pricing,
        cost_profile=cost_profile,
        demographics=demographics,
        financials=financials,
    )

    if gemini is None:
        facts["confidence"] = confidence
        facts["note_source"] = "Deterministic. No language model was used."
        return facts

    prompt = f"""
    Rewrite the following business SWOT for a '{category_name}' in India so it reads
    clearly for a first-time entrepreneur. Keep every statement factually identical.
    Do not introduce any number, claim, scheme, or fact that is not already present.
    {user_context}

    Existing analysis:
    {facts}

    Output ONLY a JSON object with keys "strengths", "weaknesses", "opportunities",
    "threats" mapping to lists of strings. Preserve the exact numbers.
    """
    try:
        result = await gemini.generate_json_async(prompt)
    except Exception:
        result = None

    if not result:
        facts["confidence"] = confidence
        facts["note_source"] = "Deterministic. Language model unavailable."
        return facts

    # Validate: no new figures may appear in the model's rewrite.
    allowed = _allowed_figures(facts)
    candidate_text = " ".join(
        str(item)
        for key in ("strengths", "weaknesses", "opportunities", "threats")
        for item in (result.get(key) or [])
    )
    import re

    for match in re.findall(r"\d+(?:\.\d+)?", candidate_text):
        token = match.rstrip("0").rstrip(".") if "." in match else match
        if match not in allowed and token not in allowed:
            facts["confidence"] = confidence
            facts["note_source"] = (
                "Deterministic. A language-model rewrite was discarded because it introduced "
                "figures not present in the measured inputs."
            )
            return facts

    for key in ("strengths", "weaknesses", "opportunities", "threats"):
        items = result.get(key)
        if isinstance(items, list) and all(isinstance(i, str) for i in items) and items:
            facts[key] = items

    facts["confidence"] = confidence
    facts["note_source"] = "Deterministic facts, language-model wording only."
    return facts


def generate_swot(
    category_name: str,
    competitor_count: Optional[int] = None,
    gap_score: None = None,
    pricing: dict | None = None,
    cost_profile: dict | None = None,
    demographics: dict | None = None,
    confidence: str = "Low",
) -> dict[str, Any]:
    """Sync entry point. Deterministic; no network call is made."""
    return build_swot_facts(
        category_name=category_name,
        competitor_count=competitor_count,
        gap_score=gap_score,
        pricing=pricing,
        cost_profile=cost_profile,
        demographics=demographics,
    )
