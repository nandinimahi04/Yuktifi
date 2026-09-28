"""Section 10 — the trust layer. Central place that decides confidence levels."""

def calculate_composite_confidence(
    source_conf: str, 
    freshness_conf: str, 
    geo_conf: str, 
    completeness_conf: str
) -> str:
    """
    Calculates the composite confidence as the minimum of the 4 sub-scores.
    Levels: High (3), Medium (2), Low (1), Unavailable (0).
    """
    levels = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "Unavailable": 0
    }
    
    scores = [
        levels.get(source_conf.capitalize(), 0),
        levels.get(freshness_conf.capitalize(), 0),
        levels.get(geo_conf.capitalize(), 0),
        levels.get(completeness_conf.capitalize(), 0)
    ]
    
    min_score = min(scores)
    
    for k, v in levels.items():
        if v == min_score:
            return k
            
    return "Unavailable"

def tag_confidence(data_origin: str, sample_size: int | None = None) -> str:
    """Legacy tag_confidence, kept for backward compatibility."""
    if data_origin == "public_source" and (sample_size is None or sample_size >= 5):
        return "High"
    if data_origin == "public_source":
        return "Medium"
    if data_origin == "prototype_curated":
        return "Medium" if sample_size and sample_size >= 3 else "Low"
    return "Low"
