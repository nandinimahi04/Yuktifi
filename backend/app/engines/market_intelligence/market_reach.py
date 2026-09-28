"""Section 11 — Consumer base estimation from demographic data."""


def estimate_market_reach(demographics: dict, radius_km: float = 10.0) -> dict:
    """
    Estimate the consumer base within the market radius.
    demographics: the 'value' dict from DataRetrieval.get_demographics()
    """
    if demographics is None:
        return {
            "consumer_base": None,
            "households": None,
            "radius_km": radius_km,
            "confidence": "Low",
            "note": "No demographic data available — cannot estimate market reach.",
        }

    population = demographics.get("population")
    households = demographics.get("households")

    if population is None:
        return {
            "consumer_base": None,
            "households": None,
            "radius_km": radius_km,
            "confidence": "Low",
            "note": "Population data missing for this location.",
        }

    # Simple estimate: ~70% of local population within radius are potential consumers
    consumer_base = int(population * 0.70)
    confidence = demographics.get("confidence", "Medium")

    return {
        "consumer_base": consumer_base,
        "households": households,
        "radius_km": radius_km,
        "avg_monthly_income": demographics.get("avg_monthly_income"),
        "confidence": confidence,
        "note": f"Estimated {consumer_base:,} potential consumers within {radius_km}km radius.",
    }
