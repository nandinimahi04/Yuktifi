from __future__ import annotations
from dataclasses import dataclass
from math import sqrt

@dataclass(frozen=True)
class MarketEstimate:
    catchment_km: float
    base_population: float | None
    base_households: float | None
    spatial_population: float | None
    addressable_population: float | None
    estimated_units_monthly: float | None
    method: str
    confidence: str
    is_estimate: bool
    limitations: list[str]

def _confidence(has_census: bool, has_spatial: bool, has_competitors: bool) -> str:
    score = int(has_census) + int(has_spatial) + int(has_competitors)
    return "High" if score >= 3 else "Medium" if score == 2 else "Low"

def estimate_market(*, population: float | None, households: float | None,
                    spatial_population: float | None, catchment_km: float,
                    monthly_units_per_1000_people: float,
                    has_competitors: bool = False) -> MarketEstimate:
    # Prefer spatial population for a catchment when available; Census remains a local anchor.
    base = spatial_population if spatial_population and spatial_population > 0 else population
    addressable = None if base is None else round(base * 0.35, 2)
    units = None if addressable is None else round(addressable / 1000 * monthly_units_per_1000_people, 2)
    limitations = [
        "Demand is a modeled estimate, not observed sales.",
        "Census 2011 is historical and is not presented as a 2026 population value.",
    ]
    if spatial_population is None:
        limitations.append("No spatial population value was supplied; Census population is used only as the local anchor.")
    if not has_competitors:
        limitations.append("Competition coverage is incomplete or unavailable.")
    return MarketEstimate(catchment_km, population, households, spatial_population, addressable, units,
                          "addressable_population = catchment_population × 35%; units derived from template demand-rate assumption",
                          _confidence(population is not None, spatial_population is not None, has_competitors), True, limitations)
