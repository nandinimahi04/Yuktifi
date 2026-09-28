def calculate_eppi(mospi_mpce_band: str, local_price_adjustments: float = 1.0) -> int:
    """
    Calculates the Estimated Purchasing Power Index (EPPI) (0-100).
    mospi_mpce_band is a string like "low", "medium", "high".
    local_price_adjustments is a multiplier based on user input or regional differences.
    """
    base_scores = {
        "low": 30,
        "medium": 60,
        "high": 90
    }
    
    base = base_scores.get(mospi_mpce_band.lower(), 50)
    eppi = int(base * local_price_adjustments)
    return max(0, min(100, eppi))

def calculate_demand_index(
    category_baseline: float, 
    population_proxy: float, 
    eppi: int, 
    seasonality_factor: float
) -> int:
    """
    Calculates a hybrid demand index (0-100) based on multiple factors.
    """
    # Normalize population proxy (assume 100000 is a highly dense area score of 1.0)
    pop_score = min(1.0, population_proxy / 100000.0)
    
    # Normalize EPPI
    eppi_score = eppi / 100.0
    
    # Simple weighted heuristic
    raw_demand = (
        (category_baseline * 0.4) + 
        (pop_score * 0.3) + 
        (eppi_score * 0.3)
    ) * seasonality_factor
    
    return max(0, min(100, int(raw_demand * 100)))

def calculate_business_density(competitor_count: int, households: int, area_km2: float) -> dict:
    """
    Calculates competitor density per household and per square kilometer.
    """
    households = max(households, 1)
    area_km2 = max(area_km2, 0.1)
    
    return {
        "per_1000_households": round((competitor_count / households) * 1000, 2),
        "per_sq_km": round(competitor_count / area_km2, 2)
    }
