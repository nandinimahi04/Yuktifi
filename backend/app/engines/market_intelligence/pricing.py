"""Section 11 — pricing band estimation from curated data."""


def estimate_pricing_band(location_id: str, category_id: str, data_layer) -> dict:
    """
    Return pricing band from structured data.
    data_layer: a DataRetrieval instance.
    """
    result = data_layer.get_pricing(location_id, category_id)
    if result.get("value") is None:
        return {"low": None, "high": None, "confidence": "Low",
                "note": "No pricing data available."}
    return {
        "low": result["value"]["low"],
        "high": result["value"]["high"],
        "unit": result["value"].get("unit", ""),
        "confidence": result.get("confidence", "Medium"),
        "note": result.get("note", ""),
    }
