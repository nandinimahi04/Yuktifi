"""Section 11 — reads curated/OSM data, always returns a confidence tag."""


def estimate_competitor_density(location_id: str, category_id: str, data_layer) -> dict:
    """
    Estimate competitor density from structured data.
    data_layer: a DataRetrieval instance.
    """
    result = data_layer.get_competitors(location_id, category_id)
    records = result.get("records", [])
    if not records:
        return {
            "count_estimate": None,
            "confidence": "Low",
            "note": "No competitor data available for this location/category.",
        }
    return {
        "count_estimate": len(records),
        "confidence": result.get("confidence", "Medium"),
        "records": records,
        "note": result.get("note", ""),
    }
