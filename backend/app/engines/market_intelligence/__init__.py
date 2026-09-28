"""Market Intelligence orchestrator — fully async with concurrent data fetching."""
import asyncio
import hashlib
import logging
from typing import Optional
try:
    from cachetools import TTLCache
    _market_cache: TTLCache = TTLCache(maxsize=64, ttl=1800)  # 30 min TTL
except ImportError:
    # If cachetools is not installed, create a simple dict fallback (no TTL)
    _market_cache = {}  # type: ignore
from app.data_layer.retrieval import DataRetrieval
from app.engines.market_intelligence.market_reach import estimate_market_reach
from app.engines.market_intelligence.competitor_density import estimate_competitor_density
from app.engines.market_intelligence.pricing import estimate_pricing_band
from app.engines.market_intelligence.opportunity_gaps import analyze_opportunity_gaps_async
from app.engines.market_intelligence.swot import generate_swot_async
from app.engines.market_intelligence.threats import assess_threats_async
from app.services.data_service import data_service
from app.core.config import settings
from app.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)
data_layer = DataRetrieval()
# Single module-level Gemini singleton — avoids creating a new client per request
gemini = GeminiClient()


def wrap_with_provenance(value, dataset_name, confidence_override=None, method=None):
    prov = data_service.get_provenance_for_dataset(dataset_name)
    if confidence_override:
        prov.confidence = confidence_override
    if method:
        prov.methodology = method
    return {
        "value": value,
        "provenance": prov.dict()
    }


async def _get_demographics_async(location_id: str) -> dict:
    """Demographics is now instant (pure algorithmic) — call directly."""
    return data_layer.get_demographics(location_id)


async def _get_competitors_async(location_id: str, category_id: str) -> dict:
    """
    Mapped competitors via Overpass, without blocking the event loop.

    Returns `count` at the TOP level. It previously returned a bare dict while
    the orchestrator read `result["value"]["count"]`, so `.get("value", {})` was
    always `{}` and the competitor count was always 0. Every downstream
    opportunity score, threat assessment and competitive-density figure was
    therefore computed against "no competition exists" - the single most
    consequential bug in this module, because it silently inverted the advice
    toward entering saturated markets.

    A failed query returns `count: None`, which is distinct from a query that
    genuinely found zero. Downstream code can then abstain rather than conclude
    the market is empty.
    """
    from app.api_clients.overpass_client import OverpassClient

    parsed = data_layer._parse_location(location_id)
    if parsed is None:
        return {
            "records": [], "count": None, "query_succeeded": False,
            "confidence": "UNAVAILABLE", "evidence_state": "MISSING",
            "note": "No coordinates for this location, so no competitor survey was run.",
        }
    lat, lon = parsed

    if not settings.network_allowed:
        return {
            "records": [], "count": None, "query_succeeded": False,
            "confidence": "UNAVAILABLE", "evidence_state": "UNAVAILABLE",
            "note": "Network access is disabled (demo mode); no competitor survey was run.",
        }

    radius_meters = 5000

    # One implementation of this query, in OverpassClient. This function used to
    # carry its own copy, and the copy carried the same three defects the client
    # had: `[timeout:25]` in the query against a 7 s HTTP wait, `el.get("lat") or
    # ...` dropping nodes sitting on the Equator, and a flat-degree distance
    # instead of a great-circle one. It was also untested, so nothing would have
    # caught any of them.
    survey = await asyncio.to_thread(
        OverpassClient().get_competitor_survey, lat, lon, category_id, radius_meters
    )

    if survey["status"] != "ok":
        return {
            "records": [], "count": None, "query_succeeded": False,
            "confidence": "UNAVAILABLE", "evidence_state": "UNAVAILABLE",
            "note": (
                f"The competitor survey could not be completed ({survey.get('error')}). "
                f"Competitor count is unknown, not zero."
            ),
        }

    competitors = [
        {
            "id": rec["id"],
            "name": rec["name"],
            "type": rec["type"],
            # `latitude`/`longitude` are the keys the market API and the frontend
            # map both read. The client emits `lat`/`lon`.
            "latitude": rec["lat"],
            "longitude": rec["lon"],
            "distance_km": rec["distance_km"],
        }
        for rec in survey["records"]
    ]

    if not competitors:
        return {
            "records": [], "count": 0, "query_succeeded": True,
            "confidence": "LOW", "evidence_state": "UNAVAILABLE",
            "note": f"No '{category_id}' features are MAPPED within {radius_meters} m. "
                    f"OSM does not record most informal rural businesses, so this is a lower "
                    f"bound of zero, not an empty market.",
        }

    return {
        "records": competitors, "count": len(competitors), "query_succeeded": True,
        "confidence": "MEDIUM", "evidence_state": "INFERRED",
        "note": f"{len(competitors)} mapped competitors within {radius_meters} m. "
                f"Lower bound: unmapped businesses are not included.",
    }


async def _get_cost_profile_async(location_id: str, category_id: str) -> dict:
    """
    Cost profile for a category.

    This previously prompted Gemini to "estimate realistic unit economics" and
    fell back to a hardcoded `fixed 15000 / unit 50 / price 150 / 300 units`
    block. Those five numbers are the entire input to revenue, break-even, DSCR
    and payback, so an LLM guess was deciding whether a business looked viable.
    The estimate is removed: cost data is entered by the applicant or quoted by a
    supplier, and until then this abstains.
    """
    return data_layer.get_cost_profile(location_id, category_id)


async def run_full_market_analysis_async(location_id: str, category_id: str, category_name: str, 
                                       budget: int = None, experience: str = None, idea_details: str = None) -> dict:
    """Fully async orchestrator — fetches all data sources concurrently."""

    # ─── Phase 1: Fetch raw data in parallel ──────────────────────────────────
    demo_result, comp_result, cost_result, pricing_result = await asyncio.gather(
        _get_demographics_async(location_id),
        _get_competitors_async(location_id, category_id),
        _get_cost_profile_async(location_id, category_id),
        data_layer.get_prices_async(location_id, category_id),
    )

    demographics = demo_result.get("value")
    # `count` is read from the top level. Reading it from `["value"]` is what made
    # this permanently 0, which inverted every competition-dependent conclusion.
    comp_count = comp_result.get("count")
    comp_val = {
        "count": comp_count,
        "records": comp_result.get("records", []),
        "is_exhaustive": False,
        "evidence_state": comp_result.get("evidence_state", "UNAVAILABLE"),
    }
    cost_value = cost_result.get("value")

    # The demographics payload keys the field `population`. It was previously read
    # as `population_radius`, which no producer emits, so consumer_base was always
    # 0 and the whole market-reach model ran on an empty catchment.
    consumer_base = demographics.get("population") if demographics else None

    # Confidence is derived from what was actually obtained, not hardcoded.
    overall_confidence = _aggregate_confidence([
        demo_result.get("confidence"), comp_result.get("confidence"),
        pricing_result.get("confidence"),
    ])

    if comp_count is None:
        logger.info("Competitor count unavailable; competition-dependent analysis will abstain.")

    # Context string to inject into AI prompts
    user_context = f"User Budget: {budget}. Experience: {experience}. Details: {idea_details}." if budget else ""

    gemini_client = gemini  # Use the module-level singleton, not a new instance

    # ─── Phase 2: AI inferences in parallel ───────────────────────────────────
    # The AI layer is given what was verified and told plainly what is missing.
    # It narrates; it does not supply the numbers.
    gap_result, swot_result, threats_result = await asyncio.gather(
        analyze_opportunity_gaps_async(consumer_base, comp_count, category_name, gemini_client, confidence=overall_confidence, user_context=user_context),
        generate_swot_async(category_name, comp_count, None, pricing_result, cost_value, demographics, gemini_client, confidence=overall_confidence, user_context=user_context),
        assess_threats_async(comp_count, None, category_name, pricing_result, gemini_client, confidence=overall_confidence, user_context=user_context),
    )

    # ─── Phase 3: Assemble response ───────────────────────────────────────────
    reach_val = estimate_market_reach(demographics)
    market_reach = wrap_with_provenance(
        reach_val,
        "market_metrics",
        demo_result.get("confidence", "low"),
        method="70% addressable filter applied to the catchment population estimate.",
    )

    competitors = wrap_with_provenance(
        comp_val,
        "competitors",
        comp_result.get("confidence", "low"),
        method="Radius search on mapped OSM features. Mapped businesses only - not exhaustive.",
    )

    pricing = wrap_with_provenance(
        pricing_result.get("value"),
        "prices",
        pricing_result.get("confidence", "low"),
        method="AGMARKNET median modal price across reporting mandis. No estimated fallback.",
    )

    opportunity_gaps = wrap_with_provenance(
        gap_result,
        "competitors",
        "medium",
        method="AI-narrated reading of verified demand and competition signals.",
    )

    swot = wrap_with_provenance(
        swot_result,
        "market_metrics",
        overall_confidence,
        method="AI-generated SWOT narration over verified market signals.",
    )

    threats = wrap_with_provenance(
        threats_result,
        "competitors",
        overall_confidence,
        method="AI risk narrative from competition density and verified price spread.",
    )

    return {
        "location_id": location_id,
        "category_id": category_id,
        "category_name": category_name,
        "market_reach": market_reach,
        "competitors": competitors,
        "pricing": pricing,
        "opportunity_gaps": opportunity_gaps,
        "swot": swot,
        "threats": threats,
        "overall_confidence": overall_confidence.lower(),
    }


async def run_full_market_analysis_async_cached(
    location_id: str, category_id: str, category_name: str,
    budget: int = None, experience: str = None, idea_details: str = None
) -> dict:
    """Cache-aware wrapper around run_full_market_analysis_async.
    Results are cached in-memory for 30 minutes per (location_id, category_id).
    User-specific context (budget, experience) is NOT part of the cache key
    to maximize hit rate — the base market data is the same for all users.
    """
    cache_key = f"{location_id}:{category_id}"
    if cache_key in _market_cache:
        logger.info("Market analysis cache HIT for %s", cache_key)
        return _market_cache[cache_key]

    logger.info("Market analysis cache MISS for %s — running full analysis", cache_key)
    result = await run_full_market_analysis_async(
        location_id, category_id, category_name, budget, experience, idea_details
    )
    _market_cache[cache_key] = result
    return result


def run_full_market_analysis(
    location_id: str, category_id: str, category_name: str
) -> dict:
    """
    Sync wrapper for callers outside the event loop.

    The previous version tried to handle the "already inside a loop" case by
    calling `run_until_complete` on the running loop, which always raises
    `RuntimeError: This event loop is already running`. That exception was
    swallowed by a bare `except Exception: pass`, and the function then fell
    through to `asyncio.run(...)`, which raises the same error uncaught. So the
    async branch was dead code that only hid the real failure, and
    `asyncio.get_event_loop()` emitted a DeprecationWarning on Python 3.12+.

    There is no correct way to block on a running loop from synchronous code, so
    that case is now reported clearly and points at the async entry point.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop in this thread: safe to drive one.
        return asyncio.run(
            run_full_market_analysis_async(location_id, category_id, category_name)
        )

    raise RuntimeError(
        "run_full_market_analysis() cannot be called from inside a running event "
        "loop. Await run_full_market_analysis_async() instead, or call this "
        "function from a synchronous worker thread."
    )


def _aggregate_confidence(levels: list) -> str:
    levels = [lvl.lower() for lvl in levels if lvl]
    if "low" in levels:
        return "low"
    if "medium" in levels:
        return "medium"
    return "high"
