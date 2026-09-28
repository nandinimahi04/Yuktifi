from __future__ import annotations

from typing import Any


def canonical_location_label(resolved: dict[str, Any]) -> str:
    parts = [resolved.get("village"), resolved.get("block") or resolved.get("subdistrict"), resolved.get("district"), resolved.get("state")]
    parts = [str(x).strip() for x in parts if x not in (None, "")]
    return ", ".join(dict.fromkeys(parts))


def build_location_context(resolved: dict[str, Any]) -> dict[str, Any]:
    if resolved.get("status") != "resolved":
        raise ValueError("Location must be resolved before building canonical business context")
    label = canonical_location_label(resolved)
    return {
        "status": "resolved",
        "canonical_label": label,
        "state": resolved.get("state"),
        "district": resolved.get("district"),
        "subdistrict": resolved.get("subdistrict"),
        "block": resolved.get("block"),
        "village": resolved.get("village"),
        "codes": resolved.get("codes", {}),
        "coordinates": {"lat": resolved.get("lat"), "lng": resolved.get("lng")},
        "resolution_method": resolved.get("method"),
        "match_score": resolved.get("match_score"),
        "distance_km": resolved.get("distance_km"),
    }
