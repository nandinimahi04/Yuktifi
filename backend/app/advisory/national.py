from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from app.advisory.templates.registry import get_template
from app.advisory.market import estimate_market
from app.advisory.competitors import analyze_competitors
from app.advisory.finance import calculate, as_dict
from app.advisory.risk import stress_test
from app.advisory.schemes import evaluate
from app.advisory.decision import decide
from app.location.service import resolve_location
from app.phase2.service import upsert_evidence

OFFICIAL_SOURCE_MANIFEST = {
    "census_pca": "https://censusindia.gov.in/census.website/en/data/population-finder",
    "census_pca_catalog": "https://www.censusindia.gov.in/nada/index.php/catalog/42559",
    "livestock": "https://kerala.data.gov.in/resource/maharashtra-20th-livestock-census-2019-village-wise",
    "osm": "https://www.openstreetmap.org/",
    "overpass": "https://dev.overpass-api.de/overpass-doc/en/",
    "agmarknet": "https://www.enam.gov.in/web/dashboard/agmarknet",
    "udyam": "https://udyamregistration.gov.in/",
    "ogd": "https://www.data.gov.in/",
    "nsfdc": "https://nsfdc.nic.in/",
    "mudra": "https://www.mudra.org.in/",
    "pmegp": "https://www.kviconline.gov.in/pmegpeportal/",
}


def _alternative_capital_requirements() -> dict[str, dict[str, Any]]:
    """
    Capital requirements for the alternative categories, from the published cost
    reference models only.

    There is deliberately no hardcoded fallback. The previous implementation
    carried six unsourced thresholds in code plus a 300,000 default for
    anything unlisted, and ruled alternatives "Fail (Capital Gap)" against them.
    A category with no published reference now abstains, which is the only
    honest option: the figure drives a visible verdict about somebody's business.
    """
    from app.services.data_service import data_service

    out: dict[str, dict[str, Any]] = {}
    for model in data_service.get_dataset("cost_models") or []:
        category = model.get("category_id")
        required = model.get("total_setup_cost") or model.get("capital_required")
        if category and isinstance(required, (int, float)) and required > 0:
            out[category] = {
                "capital_required": float(required),
                "evidence_state": "ESTIMATED" if model.get("confidence") != "High" else "VERIFIED",
            }
    return out


def _canonical_location(location: dict[str, Any]) -> dict[str, Any]:
    loc = dict(location or {})
    if loc.get("query") or loc.get("lat") is not None:
        resolved = resolve_location(loc.get("query"), loc.get("lat"), loc.get("lng"))
        if resolved.get("status") == "resolved":
            return {**resolved, **{k: v for k, v in loc.items() if v not in (None, "")}}
        loc["resolution"] = resolved
    # Accept a hierarchy supplied by the UI/import pipeline. No data is fabricated here.
    loc.setdefault("status", "provided")
    return loc


def run_advisory(*, business_id: str, location: dict, promoter_margin: float,
                 monthly_units: float | None = None, price_per_unit: float | None = None,
                 variable_cost_per_unit: float | None = None, fixed_cost_monthly: float | None = None,
                 annual_rate_pct: float = 12.0, tenure_months: int = 60,
                 spatial_population: float | None = None, mapped_competitors: list[dict] | None = None,
                 profile: dict | None = None, demand_rate_per_1000_people: float | None = None,
                 use_demo_assumptions: bool = False, financing_pct: float = 0.90) -> dict:
    t = get_template(business_id)
    location = _canonical_location(location)

    demo_fields = {
        "monthly_units": t.default_monthly_units,
        "price_per_unit": t.default_price_per_unit,
        "variable_cost_per_unit": t.default_variable_cost_per_unit,
        "fixed_cost_monthly": t.fixed_cost_monthly,
        "demand_rate_per_1000_people": t.demand_rate_per_1000_people,
    }
    supplied = {
        "monthly_units": monthly_units, "price_per_unit": price_per_unit,
        "variable_cost_per_unit": variable_cost_per_unit, "fixed_cost_monthly": fixed_cost_monthly,
        "demand_rate_per_1000_people": demand_rate_per_1000_people,
    }
    required_missing = [k for k, v in supplied.items() if v is None and k != "demand_rate_per_1000_people"]
    missing = [k for k, v in supplied.items() if v is None]
    if required_missing and not use_demo_assumptions:
        raise ValueError("Missing business inputs: " + ", ".join(missing) + ". Supply them or set use_demo_assumptions=true.")
    monthly_units = float(monthly_units if monthly_units is not None else demo_fields["monthly_units"])
    price_per_unit = float(price_per_unit if price_per_unit is not None else demo_fields["price_per_unit"])
    variable_cost_per_unit = float(variable_cost_per_unit if variable_cost_per_unit is not None else demo_fields["variable_cost_per_unit"])
    fixed_cost_monthly = float(fixed_cost_monthly if fixed_cost_monthly is not None else demo_fields["fixed_cost_monthly"])
    demand_rate_per_1000_people = float(demand_rate_per_1000_people if demand_rate_per_1000_people is not None else demo_fields["demand_rate_per_1000_people"])

    if promoter_margin <= 0 or monthly_units < 0 or price_per_unit <= 0 or variable_cost_per_unit < 0 or fixed_cost_monthly < 0:
        raise ValueError("Business and financing inputs must be non-negative; price and promoter margin must be positive.")
    if variable_cost_per_unit >= price_per_unit:
        raise ValueError("variable_cost_per_unit must be lower than price_per_unit.")

    census_population = location.get("population")
    households = location.get("households")
    market = estimate_market(
        population=float(census_population) if census_population is not None else None,
        households=float(households) if households is not None else None,
        spatial_population=float(spatial_population) if spatial_population is not None else None,
        catchment_km=t.default_catchment_km,
        monthly_units_per_1000_people=demand_rate_per_1000_people,
        has_competitors=mapped_competitors is not None,
    )
    comp = analyze_competitors(mapped_competitors, t.default_catchment_km, t.direct_competitor_tags, t.substitute_tags)
    base = {"promoter_margin": promoter_margin, "monthly_units": monthly_units, "price_per_unit": price_per_unit,
            "variable_cost_per_unit": variable_cost_per_unit, "fixed_cost_monthly": fixed_cost_monthly,
            "annual_rate_pct": annual_rate_pct, "tenure_months": tenure_months, "financing_pct": financing_pct}
    fin = calculate(**base)
    risk = stress_test(base)
    schemes = evaluate(profile or {}, fin.project_cost)
    from app.engines.feasibility_engine import compute_why_not_analysis
    # Cost references are passed through so alternatives are compared against a
    # real capital requirement where one exists. Absent one, the alternative
    # abstains instead of being ruled on by an invented threshold.
    why_not = compute_why_not_analysis(
        promoter_margin,
        t.id,
        ["dairy", "kirana", "vada_pav", "tailoring", "diagnostic", "agri_machinery",
         "food_processing", "repair_services", "small_hospitality"],
        cost_models=_alternative_capital_requirements(),
    )

    decision = decide({**as_dict(fin), "calculation_integrity": 1},
                      {"population": market.base_population, "households": market.base_households,
                       "estimated_units_monthly": market.estimated_units_monthly},
                      asdict(comp), risk, schemes)
    decision["why_not"] = why_not

    location_label = ", ".join(str(x) for x in [location.get("village"), location.get("subdistrict"), location.get("district"), location.get("state")] if x) or str(location.get("query") or "Unspecified")
    evidence = [
        {"metric": "population", "value": census_population, "unit": "persons", "source": "Census PCA 2011", "source_url": OFFICIAL_SOURCE_MANIFEST["census_pca"], "is_estimate": False, "geography": location_label, "observed_at": "2011"},
        {"metric": "households", "value": households, "unit": "households", "source": "Census PCA 2011", "source_url": OFFICIAL_SOURCE_MANIFEST["census_pca"], "is_estimate": False, "geography": location_label, "observed_at": "2011"},
        {"metric": "estimated_demand", "value": market.estimated_units_monthly, "unit": t.sales_unit + "/month", "source": "YUKTIFI demand model", "source_url": OFFICIAL_SOURCE_MANIFEST["ogd"], "is_estimate": True, "geography": location_label},
        {"metric": "mapped_competitors", "value": comp.mapped_count, "unit": "mapped businesses", "source": "OpenStreetMap", "source_url": OFFICIAL_SOURCE_MANIFEST["osm"], "is_estimate": True, "geography": location_label, "limitations": "OSM coverage is incomplete; mapped count is not a census of businesses."},
    ]
    if use_demo_assumptions:
        evidence.append({"metric": "business_economics_demo_assumptions", "value": json.dumps({k: supplied[k] for k in supplied}), "unit": "mixed", "source": "YUKTIFI demo template", "is_estimate": True, "geography": location_label, "limitations": "Replace with user-entered or sourced business economics before decision use."})

    result = {
        "run_id": str(uuid.uuid4()), "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "phase7-18.2", "business": asdict(t), "location": location,
        "market": {"catchment_km": t.default_catchment_km, "base_population": market.base_population,
                   "base_households": market.base_households, "spatial_population": market.spatial_population,
                   "addressable_population": market.addressable_population, "estimated_units_monthly": market.estimated_units_monthly,
                   "method": market.method, "confidence": market.confidence, "limitations": market.limitations},
        "competition": asdict(comp), "financial": as_dict(fin), "risk": risk, "schemes": schemes, "decision": decision,
        "evidence": evidence, "source_manifest": OFFICIAL_SOURCE_MANIFEST,
        "input_quality": {"used_demo_assumptions": use_demo_assumptions, "missing_inputs_before_defaults": missing, "location_resolution": location.get("method") or location.get("resolution", {}).get("status") or location.get("status")},
        "llm_policy": "LLM may explain this decision only after retrieval; it must not create numeric facts or eligibility decisions.",
        "limitations": [*t.assumptions, "Census 2011 is historical; current demand is modeled.", "No claim of complete competitor coverage is made."],
    }
    return result
