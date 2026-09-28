"""
Gridded population estimation for a radius around a coordinate.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not query WorldPop. The previous implementation computed a number from a
hand-written urban/rural density switch keyed on four metro bounding boxes,
returned it, and let the caller label it `data_origin: "WorldPop Spatial API"`.
That is a fabricated figure carrying a real organisation's name on it, which is
the single most damaging failure mode this product can have: the number looks
authoritative and nobody can check it.

A genuine WorldPop answer requires reading the 100 m population GeoTIFF and
summing grid cells inside the radius. That needs the raster, a GDAL install and
tens of megabytes per tile, so it is not something a request-time path should do.
So this module abstains unless a real gridded source is configured, and otherwise
falls back to a **documented areal estimate** that says exactly what it is.

The fallback is the one the project's data strategy explicitly allows: a
national-average density multiplied by circle area, reported as
`INFERRED / "coarse areal estimate, not grid-based"`. It is never attributed to
WorldPop or the Census as a count for this location.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

from app.evidence import EvidenceRecord, EvidenceState, finite, validated
from app.evidence.schema import require

logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088

# Census of India 2011 national figures, used only as the area-averaged basis of
# the areal fallback. These are national aggregates and carry no information
# about any particular village; that is exactly why the result is INFERRED.
# Ref: Census of India, Primary Census Abstract, Total Population and Area.
CENSUS_2011_TOTAL_POPULATION = 1_210_854_977
INDIA_LAND_AREA_KM2 = 3_287_263
RURAL_SHARE = 0.682
NATIONAL_MEAN_DENSITY_PER_KM2 = CENSUS_2011_TOTAL_POPULATION / INDIA_LAND_AREA_KM2
RURAL_MEAN_DENSITY_PER_KM2 = NATIONAL_MEAN_DENSITY_PER_KM2 * RURAL_SHARE

#: A gridded provider is optional. If a deployment wires one in (e.g. a locally
#: cached GeoTIFF served by its own endpoint) it is set here and used instead of
#: the areal fallback. Deliberately empty by default.
GRID_ENDPOINT: str = ""
GRID_SOURCE_ID = "worldpop_grid"

#: Radius bounds for the search circle, in km. Outside these the caller is doing
#: something other than a local market catchment.
MIN_RADIUS_KM = 0.5
MAX_RADIUS_KM = 25.0

#: People per household, Census 2011 national average. Used only to express
#: population in households, and always reported as derived, never as a count.
PEOPLE_PER_HOUSEHOLD = 4.8


def circle_area_km2(radius_km: float) -> float:
    return math.pi * radius_km**2


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class WorldPopClient:
    """
    Population within a radius around a point, with an honest evidence state.

    The returned record is one of:
      * VERIFIED  - a configured gridded source returned cells for this circle
      * INFERRED  - areal estimate from a national mean density, clearly labelled
      * UNAVAILABLE - no estimate is possible, e.g. bad coordinates or an
        out-of-range radius

    Note that the absence of a gridded source is NOT an `UNAVAILABLE` outcome.
    `GRID_ENDPOINT` is empty in this build, so every valid request takes the
    areal path and returns an INFERRED figure. An earlier docstring here said the
    opposite, which described an abstention the code does not perform.

    `unavailable` is a legitimate, expected outcome and must not be replaced
    with a guess. Callers are expected to propagate the abstention.
    """

    BASE_URL = "https://www.worldpop.org/rest/data/pop"

    def __init__(self, grid_endpoint: str = GRID_ENDPOINT):
        self.grid_endpoint = grid_endpoint

    # ── Public API ──────────────────────────────────────────────────────────

    def get_population_record(
        self, lat: float, lon: float, radius_km: float = 5.0
    ) -> EvidenceRecord:
        """
        Population evidence record for the circle. Never raises for bad input;
        returns a record whose state explains what happened.
        """
        lat_f, lon_f, radius_f = finite(lat), finite(lon), finite(radius_km)

        if lat_f is None or lon_f is None:
            return EvidenceRecord(
                metric="local_population", value=None, source_id="", state=EvidenceState.UNAVAILABLE,
                method="coordinate validation",
                limitations="No usable coordinates were supplied, so no population estimate is possible.",
            )
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            return EvidenceRecord(
                metric="local_population", value=None, source_id="", state=EvidenceState.UNAVAILABLE,
                method="coordinate range check",
                limitations=f"Coordinates ({lat_f}, {lon_f}) are outside the valid range.",
            )
        if radius_f is None or not (MIN_RADIUS_KM <= radius_f <= MAX_RADIUS_KM):
            return EvidenceRecord(
                metric="local_population", value=None, source_id="", state=EvidenceState.UNAVAILABLE,
                method="radius validation",
                limitations=(
                    f"Catchment radius must be between {MIN_RADIUS_KM} and {MAX_RADIUS_KM} km. "
                    f"A local trade catchment beyond {MAX_RADIUS_KM} km is not meaningful for a "
                    f"micro enterprise."
                ),
            )

        if self.grid_endpoint:
            verified = self._query_grid(lat_f, lon_f, radius_f)
            if verified is not None:
                return verified

        return self._areal_estimate(lat_f, lon_f, radius_f)

    def get_population_estimate(
        self, lat: float, lon: float, radius_km: float = 5.0
    ) -> Optional[dict[str, Any]]:
        """
        Legacy dict-shaped accessor.

        Returns None when the value is not usable. The previous signature promised
        `Optional[Dict]` but always returned a dict, which is why callers had no
        way to express "I do not know" and defaulted to zero downstream.
        """
        record = self.get_population_record(lat, lon, radius_km)
        if not record.usable:
            return None
        pop = int(record.value)
        return {
            "population": pop,
            "households": int(pop / PEOPLE_PER_HOUSEHOLD),
            "data_origin": record.method,
            "evidence_state": record.state.value,
            "confidence": record.confidence.value,
            "radius_km": radius_km,
            "source_url": record.source_url,
            "limitations": record.limitations,
        }

    # ── Providers ───────────────────────────────────────────────────────────

    def _query_grid(self, lat: float, lon: float, radius_km: float) -> Optional[EvidenceRecord]:
        """Query a configured gridded source. Not wired up by default."""
        logger.info("Gridded population source configured: %s", self.grid_endpoint)
        return None

    def _areal_estimate(self, lat: float, lon: float, radius_km: float) -> EvidenceRecord:
        """
        Area-averaged fallback: circle area x national mean density.

        This uses no information about the actual place. A dense village and a
        sparse one get the same figure, which is precisely why the result is
        INFERRED and capped at MEDIUM confidence, and why the user-facing copy
        must describe it as a coarse areal estimate.
        """
        area = circle_area_km2(radius_km)
        population = int(area * RURAL_MEAN_DENSITY_PER_KM2)

        record = validated(
            "local_population",
            population,
            "census_pca_2011",
            unit="persons",
            minimum=0,
            integer=True,
            state=EvidenceState.INFERRED,
            geography=f"{lat:.4f},{lon:.4f} +/- {radius_km} km",
            geography_level="catchment circle",
            method=(
                f"Coarse areal estimate: circle area {area:,.0f} km2 x national mean density "
                f"{RURAL_MEAN_DENSITY_PER_KM2:.0f} persons/km2. Not a grid-based count."
            ),
            limitations=(
                "COARSE AREAL ESTIMATE, NOT A GRID-BASED COUNT. The density factor is a national "
                f"average and carries no information about this location: a densely settled village "
                f"and a sparse one receive the same figure. The underlying national total is the "
                f"2011 Census, which is now {(2026 - 2011)} years old and is not a current count. "
                f"Actual population within {radius_km} km could be several times higher or lower. "
                f"Use this only as a floor for preliminary screening."
            ),
            derivation=[f"areal_estimate(r={radius_km}km)"],
        )
        return record

    @staticmethod
    def density_basis() -> dict[str, Any]:
        """The constants behind the areal estimate, for the assumptions panel."""
        return {
            "method": "national mean density x circle area",
            "national_mean_density_per_km2": round(NATIONAL_MEAN_DENSITY_PER_KM2, 1),
            "rural_mean_density_per_km2": round(RURAL_MEAN_DENSITY_PER_KM2, 1),
            "basis": "Census of India 2011 national totals over land area",
            "reference_year": 2011,
            "people_per_household": PEOPLE_PER_HOUSEHOLD,
            "grid_source_configured": bool(GRID_ENDPOINT),
            "note": "Areal estimate only. A gridded source is not configured in this build.",
        }
