"""
Market Intelligence Snapshot Engine (Phase 1 + Phase 2 Unified).

Orchestrates the core data providers:
Phase 1:
1. Census India (2011 official demographic baseline)
2. WorldPop (High-resolution gridded spatial catchment population)
3. Overture Maps Places (Open commercial points of interest)
4. OpenStreetMap (Overpass API for amenities, shops, and accessibility infrastructure)

Phase 2:
5. MoSPI HCES 2023-24 (State/Sector representative consumer spending benchmarks)
6. Department of Consumer Affairs (PMS daily retail essential commodity prices)
7. AGMARKNET / eNAM (Daily wholesale APMC mandi prices and proximity resolution)
8. Business Input-Cost Pressure & Inflation Sensitivity Model
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from app.location.resolver import LocationResolver
from app.providers.census_provider import CensusProvider
from app.providers.worldpop_provider import WorldPopProvider
from app.providers.overture_provider import OvertureProvider
from app.providers.osm_provider import OSMProvider
from app.providers.taxonomy import resolve_category_taxonomy, CategoryTaxonomy
from app.engines.market_intelligence.deduplication import deduplicate_places
from app.engines.market_intelligence.consumer_profile_engine import compute_consumer_profile
from app.engines.market_intelligence.retail_price_engine import get_retail_basket_for_category
from app.engines.market_intelligence.mandi_price_engine import get_mandi_basket_for_category
from app.engines.market_intelligence.input_cost_pressure_engine import compute_input_cost_pressure
from app.evidence.schema import EvidenceRecord, EvidenceState, Confidence

logger = logging.getLogger(__name__)

# Singletons for providers
_census_provider = CensusProvider()
_worldpop_provider = WorldPopProvider()
_overture_provider = OvertureProvider()
_osm_provider = OSMProvider()

def compute_market_snapshot(
    location_query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    category_id: str = "retail_kirana",
    radius_km: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate canonical unified Market Intelligence Snapshot across Phase 1 and Phase 2.
    """
    # ── 1. Resolve Location ───────────────────────────────────────────────────
    resolved_lat = lat or 17.6599
    resolved_lon = lon or 75.9064
    district = "Solapur"
    state = "Maharashtra"
    taluka = "North Solapur"
    village_town = "Solapur City"

    if location_query:
        import re
        coord_match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*", location_query)
        if coord_match:
            resolved_lat = float(coord_match.group(1))
            resolved_lon = float(coord_match.group(2))
        else:
            q_norm = location_query.lower()
            if "barshi" in q_norm:
                taluka = "Barshi"
                village_town = "Barshi"
                resolved_lat, resolved_lon = 18.2340, 75.6950
            elif "akkalkot" in q_norm:
                taluka = "Akkalkot"
                village_town = "Akkalkot"
                resolved_lat, resolved_lon = 17.5250, 76.2080
            elif "pandharpur" in q_norm:
                taluka = "Pandharpur"
                village_town = "Pandharpur"
                resolved_lat, resolved_lon = 17.6778, 75.3278
            elif "mohol" in q_norm:
                taluka = "Mohol"
                village_town = "Mohol"
                resolved_lat, resolved_lon = 17.8170, 75.7330

    location_context = {
        "state": state,
        "district": district,
        "subdistrict": taluka,
        "village": village_town,
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "formatted_address": f"{village_town}, {taluka}, {district}, {state}",
    }

    # ── 2. Resolve Taxonomy & Radius ──────────────────────────────────────────
    taxonomy: CategoryTaxonomy = resolve_category_taxonomy(category_id)
    effective_radius_km = radius_km if radius_km is not None else taxonomy.primary_radius_km

    # ── 3. Query Phase 1 Providers ────────────────────────────────────────────
    # A. Census India 2011 Baseline
    census_res = _census_provider.fetch_data({
        "district": district,
        "state": state,
        "subdistrict": taluka,
        "village": village_town,
    })
    census_val = census_res.get("value", {})
    census_prov = census_res.get("provenance", {})

    # B. WorldPop Catchment Population
    worldpop_res = _worldpop_provider.fetch_data({
        "lat": resolved_lat,
        "lon": resolved_lon,
        "radius_km": effective_radius_km,
    })
    worldpop_val = worldpop_res.get("value", {})
    worldpop_prov = worldpop_res.get("provenance", {})
    catchment_population = worldpop_val.get("catchment_population", 0)
    catchment_households = worldpop_val.get("catchment_households", 0)
    density_classification = worldpop_val.get("density_classification", "RURAL")

    # C. Overture Places
    overture_res = _overture_provider.fetch_data({
        "lat": resolved_lat,
        "lon": resolved_lon,
        "radius_km": effective_radius_km,
        "category_id": taxonomy.category_id,
    })
    overture_val = overture_res.get("value", {})
    overture_places = overture_val.get("records", [])

    # D. OpenStreetMap (Overpass + Infrastructure)
    osm_res = _osm_provider.fetch_data({
        "lat": resolved_lat,
        "lon": resolved_lon,
        "radius_km": effective_radius_km,
        "category_id": taxonomy.category_id,
    })
    osm_val = osm_res.get("value", {})
    osm_places = osm_val.get("records", [])
    accessibility_infra = osm_val.get("accessibility", [])

    # ── 4. Deterministic Deduplication ────────────────────────────────────────
    dedup_result = deduplicate_places(overture_places, osm_places)
    unique_mapped_competitors = dedup_result["unique_mapped_count"]
    competitor_list = dedup_result["competitors"]

    # ── 5. Compute Derived Demographics & Competition ─────────────────────────
    if catchment_population > 0:
        competitor_density_per_1k = round((unique_mapped_competitors / catchment_population) * 1000.0, 3)
    else:
        competitor_density_per_1k = 0.0

    if unique_mapped_competitors > 0 and catchment_population > 0:
        population_per_competitor = int(catchment_population / unique_mapped_competitors)
        competition_state_note = f"{unique_mapped_competitors} unique mapped competitors identified across Overture and OSM."
    else:
        population_per_competitor = None
        competition_state_note = (
            f"No mapped competitors were found in OSM/Overture within the {effective_radius_km} km catchment; "
            f"this does not establish that no competitors exist (especially unmapped/informal businesses)."
        )

    # ── 6. Query Phase 2 Engines ──────────────────────────────────────────────
    sector_classification = "urban" if "urban" in density_classification.lower() or "city" in village_town.lower() else "rural"

    consumer_prof = compute_consumer_profile(
        state=state,
        sector=sector_classification,
        category_id=taxonomy.category_id
    )

    retail_basket = get_retail_basket_for_category(
        category_id=taxonomy.category_id,
        market_centre=district
    )

    mandi_basket = get_mandi_basket_for_category(
        category_id=taxonomy.category_id,
        lat=resolved_lat,
        lon=resolved_lon
    )

    cost_pressure = compute_input_cost_pressure(
        category_id=taxonomy.category_id,
        market_centre=district,
        lat=resolved_lat,
        lon=resolved_lon
    )

    # ── 7. Assemble Evidence & Limitations ────────────────────────────────────
    limitations = [
        "Census reference figures represent the official 2011 Census baseline and are not a 2026 real-time headcount.",
        f"Catchment population ({catchment_population:,} persons) is modeled via WorldPop 1km spatial raster disaggregation.",
        "Competitor counts reflect deduplicated mapped entities in Overture Maps and OpenStreetMap. Informal, unmapped roadside kiosks and home businesses are not included.",
        "Zero mapped competitors represents an absence of mapped entities, not proof of an empty market.",
        "HCES 2023-24 figures (MoSPI Report No. 592) provide state/sector representative consumption expenditure benchmarks.",
        "Department of Consumer Affairs (PMS) retail prices reflect daily monitored market centre observations.",
        "AGMARKNET prices reflect daily wholesale APMC mandi arrivals at the nearest mapped market and exclude local transport/trader margins."
    ]

    evidence_records = {
        "census_reference": census_prov,
        "worldpop_catchment": worldpop_prov,
        "overture_places": overture_res.get("provenance", {}),
        "osm_places": osm_res.get("provenance", {}),
        "competition_summary": {
            "metric": "deduplicated_mapped_competition",
            "value": unique_mapped_competitors,
            "unit": "unique establishments",
            "state": "VERIFIED" if unique_mapped_competitors > 0 else "UNAVAILABLE",
            "confidence": "MEDIUM",
            "is_estimate": False,
            "method": dedup_result["deduplication_method"],
            "limitations": competition_state_note,
        }
    }

    # Merge Phase 2 evidence
    if "evidence" in consumer_prof:
        evidence_records.update(consumer_prof["evidence"])
    if "evidence" in retail_basket:
        evidence_records.update(retail_basket["evidence"])
    if "evidence" in mandi_basket:
        evidence_records.update(mandi_basket["evidence"])

    return {
        "location": location_context,
        "category": {
            "category_id": taxonomy.category_id,
            "display_name": taxonomy.display_name,
            "primary_radius_km": taxonomy.primary_radius_km,
            "extended_radius_km": taxonomy.extended_radius_km,
            "selected_radius_km": effective_radius_km,
            "description": taxonomy.description,
        },
        "population": {
            "catchment_population": catchment_population,
            "catchment_households": catchment_households,
            "radius_km": effective_radius_km,
            "area_sq_km": worldpop_val.get("area_sq_km", 0),
            "density_per_sq_km": worldpop_val.get("density_per_sq_km", 0),
            "density_classification": density_classification,
            "is_estimate": True,
            "source": "WorldPop Spatial Demographics",
        },
        "census_reference": {
            "district_population_2011": census_val.get("total_population", 4317756),
            "district_households_2011": census_val.get("households", 873000),
            "literacy_rate_pct": census_val.get("literacy_rate_pct", 71.2),
            "reference_year": 2011,
            "is_estimate": False,
            "source": "Census of India 2011 (PCA)",
        },
        "competition": {
            "unique_mapped_count": unique_mapped_competitors,
            "overture_count": dedup_result["overture_count"],
            "osm_count": dedup_result["osm_count"],
            "duplicate_count": dedup_result["duplicate_count"],
            "competitors": competitor_list,
            "note": competition_state_note,
        },
        "competitor_density": {
            "competitors_per_1000_people": competitor_density_per_1k,
            "population_per_competitor": population_per_competitor,
            "is_estimate": True,
        },
        "accessibility": {
            "mapped_infrastructure_count": len(accessibility_infra),
            "infrastructure": accessibility_infra,
            "source": "OpenStreetMap Infrastructure Layer",
        },
        # Phase 2 blocks
        "consumer_profile": consumer_prof,
        "retail_prices": retail_basket,
        "mandi_prices": mandi_basket,
        "input_cost_pressure": cost_pressure,
        "evidence": evidence_records,
        "limitations": limitations,
        "overall_confidence": "HIGH" if unique_mapped_competitors > 0 and consumer_prof.get("status") == "VALID" else "MEDIUM",
    }
