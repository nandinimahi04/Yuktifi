"""
Data retrieval and the boundary where fabrication used to start.

Every accessor here returns a dict shaped for the existing consumers, but the dict
now always carries `evidence_state`, `confidence`, `data_origin` and
`limitations`, and a value is only present when something actually produced it.

Three rules this module enforces:

1. A missing input yields an absent value plus a reason, never a placeholder.
   The old `get_category_data` fallback invented a ₹200,000 setup cost, a
   competitor count of 2 and a 5,000-person customer base from a template's
   percentage fields. Those numbers were arithmetically meaningless
   (`typical_cogs_pct * 10` units at a hardcoded ₹100/unit) yet flowed into a
   report as though measured.

2. A zero is only reported as a zero when the source can support it. OSM returning
   no features means nothing is mapped, not that nothing exists.

3. Attribution names the method, not an organisation. An areal density estimate
   is described as an areal estimate; it is never labelled "WorldPop".
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.api_clients import (
    AgmarknetClient,
    CensusClient,
    OverpassClient,
    WorldPopClient,
)
from app.core.config import settings
from app.core.paths import PROCESSED_DIR
from app.evidence import EvidenceState, compute_coverage
from app.services.data_service import data_service

logger = logging.getLogger(__name__)

#: Radius used for the local trade catchment, in metres.
CATCHMENT_RADIUS_M = 5_000


def _unavailable(metric: str, reason: str) -> dict[str, Any]:
    """The canonical 'we do not know' payload. One shape, used everywhere."""
    return {
        "value": None,
        "metric": metric,
        "confidence": "UNAVAILABLE",
        "evidence_state": EvidenceState.UNAVAILABLE.value,
        "data_origin": "Not available",
        "note": reason,
        "limitations": reason,
    }


class DataRetrieval:
    def __init__(self) -> None:
        # The key is read here. It used to be constructed with no argument, so
        # `self.api_key` was always None and the client always reported "no key
        # provided" even when CENSUS_API_KEY was set. The client is a stub
        # either way - see its docstring - so this does not change any figure,
        # but the log it writes is now about the real cause.
        self.census = CensusClient(settings.census_api_key)
        self.worldpop = WorldPopClient()
        self.overpass = OverpassClient()
        self.agmarknet = AgmarknetClient()

        # Curated district dataset, if the processed file is present.
        self.local_data: dict[str, Any] = {"categories": {}}
        processed_path = PROCESSED_DIR / "solapur_combined.json"
        if processed_path.exists():
            try:
                with open(processed_path, "r", encoding="utf-8") as f:
                    self.local_data = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("Could not read %s: %s", processed_path, exc)
        else:
            logger.info("No processed district dataset at %s; using seed fixtures only.", processed_path)

    # ── Category economics ──────────────────────────────────────────────────

    def get_category_data(self, location_id: str, category_id: str) -> dict[str, Any]:
        """
        Economics for a category, from the curated district dataset if available.

        When no dataset covers the location, the business template's declared
        assumptions are returned as assumptions - with `evidence_state:
        INFERRED` and the template named as the origin - rather than as an
        invented measurement. Every block the callers read is present; blocks
        that cannot be supported are present with a null value and a reason.
        """
        local_cat = self.local_data.get("categories", {}).get(category_id)
        if local_cat:
            return local_cat

        from app.templates.business_templates import get_business_template

        tmpl = get_business_template(category_id)
        if tmpl is None:
            return _unavailable(
                "cost_profile",
                f"No business template and no curated dataset for category '{category_id}'. "
                f"No cost assumptions can be stated.",
            )

        # The template's own declared assumptions, used as-is and labelled.
        # No unit count, price or customer base is invented here: the template
        # describes ratios, and ratios are not amounts.
        return {
            "initial_setup_costs": {
                "total_setup_cost": None,
                "evidence_state": EvidenceState.MISSING.value,
                "limitations": (
                    "Setup capital for this category has not been costed for this location. "
                    "It must be entered by the user or quoted from a supplier; it is not inferred "
                    "from a sector percentage."
                ),
            },
            "pricing_margins": {
                "average_margin_percentage": round(100.0 - tmpl.typical_cogs_pct, 1),
                "evidence_state": EvidenceState.INFERRED.value,
                "data_origin": "YUKTIFI business template",
                "limitations": (
                    f"Derived from the template's declared cost-of-goods ratio "
                    f"({tmpl.typical_cogs_pct}%). This is a gross-margin norm for the sector, "
                    f"not a measured margin for this business or location."
                ),
            },
            "monthly_running_costs": {
                "total_fixed_costs": None,
                "evidence_state": EvidenceState.MISSING.value,
                "limitations": (
                    "Fixed monthly cost has not been costed for this location. Rent, power and "
                    "labour must be entered; a sector percentage cannot be multiplied into an "
                    "amount without knowing the base."
                ),
            },
            "unit_economics": {
                "expected_monthly_revenue": None,
                "variable_costs": None,
                "net_operating_income": None,
                "evidence_state": EvidenceState.MISSING.value,
                "limitations": (
                    "Revenue, variable cost and operating income require a price and a volume. "
                    "Neither is observed, so none is stated."
                ),
            },
            "competitor_market_data": {
                "competitor_count": None,
                "confidence": "UNAVAILABLE",
                "evidence_state": EvidenceState.MISSING.value,
                "data_origin": "Not collected",
                "limitations": (
                    "No competitor survey has been run for this category and location. "
                    "This is not zero competitors."
                ),
            },
            "qualitative_insights": {
                "threats": [
                    "Unverified local competition (not surveyed for this location)",
                    "Unpriced input cost exposure (no current commodity price)",
                ]
            },
            "risk_rating": {"level": "Unknown", "reason": "No supporting data available."},
            "data_scope": "template_assumptions_only",
        }

    def get_market_data(self, location_id: str, category_id: str) -> dict[str, Any]:
        cat_data = self.get_category_data(location_id, category_id)
        if cat_data and "competitor_market_data" in cat_data:
            return cat_data["competitor_market_data"]
        return _unavailable("competitor_evidence", "No market dataset covers this category and location.")

    def get_financial_data(self, location_id: str, category_id: str) -> dict[str, Any]:
        cat_data = self.get_category_data(location_id, category_id)
        if not cat_data:
            return {}
        return {
            "pricing_margins": cat_data.get("pricing_margins", {}),
            "initial_setup_costs": cat_data.get("initial_setup_costs", {}),
            "monthly_running_costs": cat_data.get("monthly_running_costs", {}),
            "unit_economics": cat_data.get("unit_economics", {}),
        }

    def get_all_categories(self) -> list[str]:
        return list(self.local_data.get("categories", {}).keys())

    # ── Locations and demographics ──────────────────────────────────────────

    def _parse_location(self, location_id: str) -> Optional[tuple[float, float]]:
        """
        Extract coordinates from a "lat,lon" string.

        Returns None when the id is not a coordinate pair. It deliberately does
        not fall back to a default city: a confidently formatted population for
        the wrong district is worse than stating that the location is unknown.
        """
        try:
            if location_id and "," in location_id:
                lat, lon = location_id.split(",", 1)
                return float(lat), float(lon)
        except (ValueError, TypeError):
            return None
        return None

    def get_demographics(self, location_id: str) -> dict[str, Any]:
        coords = self._parse_location(location_id)
        if coords is None:
            return _unavailable(
                "local_population",
                "No coordinates available for this location, so no demographic figure is asserted.",
            )
        return self.get_demographics_at(*coords)

    def get_demographics_at(self, lat: float, lon: float) -> dict[str, Any]:
        """Census first, then the areal estimate, then an explicit abstention."""
        demo = self.census.get_demographics(lat, lon)
        if demo:
            return {
                "value": demo,
                "metric": "local_population",
                "confidence": demo.get("confidence", "MEDIUM"),
                "evidence_state": EvidenceState.VERIFIED.value,
                "data_origin": "Census of India",
                "note": "Official census figure.",
                "limitations": demo.get("limitations", "Census reference year 2011; not a current count."),
            }

        record = self.worldpop.get_population_record(lat, lon, radius_km=CATCHMENT_RADIUS_M / 1000)
        if not record.usable:
            return {
                "value": None,
                "metric": "local_population",
                "confidence": "UNAVAILABLE",
                "evidence_state": record.state.value,
                "data_origin": "Not available",
                "note": record.method,
                "limitations": record.limitations,
            }

        pop = int(record.value)
        return {
            "value": {
                "population": pop,
                "households": int(pop / 4.8),
                "avg_monthly_income": None,
            },
            "metric": "local_population",
            "confidence": record.confidence.value,
            "evidence_state": record.state.value,
            "data_origin": record.method,
            "note": record.method,
            "limitations": record.limitations,
        }

    # ── Competitors ─────────────────────────────────────────────────────────

    def get_competitors(self, location_id: str, category_id: str) -> dict[str, Any]:
        """
        Mapped competitors within the catchment.

        OSM completeness is the whole story here. A rural Indian trade area is
        mostly unmapped, so a zero result is a statement about OSM, not about the
        market. It is returned with `is_exhaustive: False` and an explicit note,
        and callers must not convert it into "no competition".
        """
        coords = self._parse_location(location_id)
        if coords is None:
            return {
                "records": [],
                "count": None,
                "is_exhaustive": False,
                "confidence": "UNAVAILABLE",
                "evidence_state": EvidenceState.MISSING.value,
                "data_origin": "Not collected",
                "note": "No coordinates, so no competitor survey could be run.",
                "limitations": "Competitor count is unknown, not zero.",
            }

        lat, lon = coords
        survey = self.overpass.get_competitor_survey(
            lat, lon, category_id, radius_meters=CATCHMENT_RADIUS_M
        )

        # A survey that did not run is not a survey that found nothing. These
        # were the same `[]` until the client started reporting them apart, and
        # a timeout was being reported to the founder as "no competitors are
        # mapped near you" - a measured fact about the market, when nothing had
        # been measured at all.
        if survey["status"] != "ok":
            logger.warning(
                "[COMPETITORS] Survey did not complete for %s at %s,%s: %s",
                category_id, lat, lon, survey.get("error"),
            )
            return {
                "records": [],
                "count": None,
                "is_exhaustive": False,
                "confidence": "UNAVAILABLE",
                "evidence_state": EvidenceState.MISSING.value,
                "data_origin": "Not collected",
                "note": (
                    f"The competitor survey for '{category_id}' could not be run, so the number of "
                    f"competitors is unknown. This is not a finding of low competition."
                ),
                "limitations": (
                    "The OpenStreetMap Overpass query did not complete. No count is reported, "
                    "because reporting a zero here would state that no competitors exist, which "
                    "was never established. Retry when the service is reachable."
                ),
            }

        records = survey["records"]
        found = len(records)

        if found == 0:
            return {
                "records": [],
                "count": 0,
                "is_exhaustive": False,
                "confidence": "LOW",
                "evidence_state": EvidenceState.UNAVAILABLE.value,
                "data_origin": "OpenStreetMap Overpass (mapped features only)",
                "note": (
                    f"No '{category_id}' features are MAPPED within {CATCHMENT_RADIUS_M} m. "
                    f"This is not evidence that the market is empty."
                ),
                "limitations": (
                    "OpenStreetMap records only businesses that volunteers have mapped. Coverage of "
                    "unregistered and informal micro businesses in rural India is very low. A zero "
                    "here means zero mapped features. The true number of competitors is unknown and "
                    "is almost certainly higher. Treat this as a lower bound only."
                ),
            }

        return {
            "records": records,
            "count": found,
            "is_exhaustive": False,
            "confidence": "MEDIUM",
            "evidence_state": EvidenceState.INFERRED.value,
            "data_origin": "OpenStreetMap Overpass (mapped features only)",
            "note": f"{found} mapped competitors within {CATCHMENT_RADIUS_M} m.",
            "limitations": (
                f"Count of MAPPED businesses only. Unmapped competitors are not included, so "
                f"{found} is a lower bound on actual competition, not an estimate of it."
            ),
        }

    # ── Prices ──────────────────────────────────────────────────────────────

    async def get_prices_async(self, location_id: str, category_id: str) -> dict[str, Any]:
        """
        Current commodity price for the location's state.

        The state is resolved from the location record rather than hardcoded to
        Maharashtra, which previously made every request outside Maharashtra
        silently return Maharashtra prices.
        """
        state = self._resolve_state(location_id)
        if not state:
            return _unavailable(
                "commodity_price",
                "The state for this location is unknown, so no mandi price can be attributed "
                "to it. Prices are state-specific and are not interchangeable.",
            )

        prices = await self.agmarknet.get_prices_async(state, category_id)
        if not prices:
            return _unavailable(
                "commodity_price",
                f"No current AGMARKNET price was returned for this commodity in {state}.",
            )

        return {
            "value": prices,
            "metric": "commodity_price",
            "state": state,
            "confidence": "MEDIUM",
            "evidence_state": EvidenceState.VERIFIED.value,
            "data_origin": "AGMARKNET (Ministry of Agriculture)",
            "note": f"Wholesale mandi price reported for {state}.",
            "limitations": (
                "Wholesale modal price from reporting mandis, not the retail price a small "
                "business will charge. Covering mandis are unevenly distributed. A retail price "
                "requires a documented margin on top of this figure."
            ),
        }

    def _resolve_state(self, location_id: str) -> str | None:
        """Best-effort state for a location id, or None rather than a guess."""
        if not location_id:
            return None
        for loc in data_service.get_dataset("locations") or []:
            if str(loc.get("id")) == str(location_id):
                return loc.get("state") or None
        return None

    # ── Cost profile ────────────────────────────────────────────────────────

    def get_cost_profile(self, location_id: str, category_id: str) -> dict[str, Any]:
        """
        Indicative cost reference for a category, or an honest abstention.

        This was previously a Gemini call that invented a cost breakdown, which
        made the decisive input to every financial output hallucinated. That
        route is gone permanently.

        What remains is a curated reference model shipped in
        `backend/data/seed/cost_models.json`. It is published research, not a
        supplier quotation, so it is returned as `ESTIMATED` at low-to-medium
        confidence and carries the assumptions it was built on. That is a
        materially weaker claim than a quotation, and the note says so, because
        the entire capital requirement and payback period scale off these four
        numbers.

        Categories with no published reference return MISSING. A missing profile
        is reported, never defaulted: a fabricated ₹0 cost would make every
        business look free to start.
        """
        models = [
            m
            for m in data_service.get_dataset("cost_models")
            if m.get("category_id") == category_id
        ]
        if not models:
            return {
                "value": None,
                "metric": "cost_profile",
                "confidence": "UNAVAILABLE",
                "evidence_state": EvidenceState.MISSING.value,
                "data_origin": "None",
                "note": (
                    f"No published cost reference for '{category_id}'. Costs must be entered "
                    f"from the applicant's own quotes and bills."
                ),
                "limitations": (
                    "A cost profile must come from the applicant or a supplier quotation. It is "
                    "not inferred from a sector average, because the capital requirement and "
                    "payback period depend entirely on it."
                ),
            }

        model = models[0]
        source = None
        if model.get("source_id"):
            source = next(
                (
                    s
                    for s in data_service.get_dataset("data_sources")
                    if s.get("id") == model["source_id"]
                ),
                None,
            )

        published_confidence = model.get("confidence") or "Medium"
        confidence = "Low" if published_confidence.lower() != "high" else "Medium"

        return {
            "value": {
                "fixed_cost_monthly": model.get("fixed_cost_monthly"),
                "variable_cost_per_unit": model.get("variable_cost_per_unit"),
                "selling_price_per_unit": model.get("selling_price_per_unit"),
                "estimated_monthly_revenue": model.get("estimated_monthly_revenue"),
                "estimated_monthly_units": model.get("estimated_monthly_units"),
            },
            "metric": "cost_profile",
            "confidence": confidence,
            "evidence_state": EvidenceState.ESTIMATED.value,
            "data_origin": (
                f"Published reference model ({model.get('id')})"
                + (f" via {source.get('name')}" if source else "")
            ),
            "source": source,
            "assumption_note": model.get("assumption_note"),
            "note": (
                "An indicative published reference, NOT a quotation. Replace these figures with "
                "the applicant's own quotes before relying on the outcome."
            ),
            "limitations": (
                f"Reference model '{model.get('id')}' assumes: {model.get('assumption_note')}. "
                f"It is a representative unit and is not adjusted for this location, this "
                f"business's scale, or current supplier prices. The capital requirement and "
                f"payback period are highly sensitive to these inputs."
            ),
            "requires_confirmation": True,
        }

    def get_all_category_ids(self, location_id: str) -> list[str]:
        """
        Every business category the system knows about, not only those that
        happen to have a cost reference.

        This previously derived the list from `cost_models`, so the ranking
        screen showed one category out of five. The categories nobody has costed
        are precisely the ones the user needs to see: their absence from the
        list read as "not worth considering" rather than "we need a quotation
        for this one".
        """
        categories = data_service.get_dataset("categories")
        if categories:
            return sorted({c.get("id") for c in categories if c.get("id")})
        return sorted({c.get("category_id") for c in data_service.get_dataset("cost_models") if c.get("category_id")})

    def get_schemes(self) -> list[dict]:
        return data_service.get_dataset("schemes")
