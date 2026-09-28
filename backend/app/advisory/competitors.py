from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CompetitorAnalysis:
    mapped_count: int
    direct_count: int
    substitute_count: int
    density_per_sq_km: float
    coverage: str
    interpretation: str
    limitations: list[str]

def analyze_competitors(mapped: list[dict] | None, catchment_km: float, direct_tags: tuple[str, ...], substitute_tags: tuple[str, ...]) -> CompetitorAnalysis:
    rows = mapped or []
    direct = sum(1 for r in rows if str(r.get("tag", "")).lower() in {x.lower() for x in direct_tags})
    substitute = sum(1 for r in rows if str(r.get("tag", "")).lower() in {x.lower() for x in substitute_tags})
    area = 3.1415926535 * max(catchment_km, 0.1) ** 2
    density = round(len(rows) / area, 2)
    coverage = "Low" if not rows else "Medium"
    interpretation = "No mapped competitors found; this does not establish absence." if not rows else f"{len(rows)} mapped businesses found in the selected catchment."
    return CompetitorAnalysis(len(rows), direct, substitute, density, coverage, interpretation,
                              ["OSM/business mapping is incomplete and may omit informal or unmapped businesses."])
