import os
import json
import sys
from pathlib import Path

# Add backend to path so we can import from app
base_dir = Path(__file__).resolve().parent.parent
backend_dir = base_dir / "backend"
sys.path.append(str(backend_dir))

from app.data_layer.normalizer import merge_dicts
from app.data_layer.validation import clean_competitor_list
from app.data_layer.geospatial import filter_within_radius
from app.data_layer.feature_engineering import calculate_eppi, calculate_demand_index, calculate_business_density
from app.data_layer.confidence_tagging import calculate_composite_confidence

def run_pipeline():
    source_dir = backend_dir / "data" / "source"
    processed_dir = backend_dir / "data" / "processed"
    
    # Ensure processed dir exists
    os.makedirs(processed_dir, exist_ok=True)
    
    detailed_path = source_dir / "solapur_business_dataset_detailed.json"
    strict_path = source_dir / "solapur_business_dataset_strict.json"
    combined_path = processed_dir / "solapur_combined.json"

    print("1. Loading source datasets...")
    with open(detailed_path, 'r', encoding='utf-8') as f:
        detailed_data = json.load(f)
        
    with open(strict_path, 'r', encoding='utf-8') as f:
        strict_data = json.load(f)

    print("2. Normalizing and merging schemas...")
    combined_data = merge_dicts(detailed_data, strict_data)
    
    print("3. Validating and enriching categories...")
    # Solapur center for Haversine filtering
    SOLAPUR_LAT = 17.6599
    SOLAPUR_LON = 75.9064
    RADIUS_KM = 5.0
    
    categories = combined_data.get("categories", {})
    for cat_id, cat_data in categories.items():
        market_data = cat_data.get("competitor_market_data", {})
        
        # A. Validation & Cleaning
        competitors = market_data.get("competitor_list", [])
        cleaned_competitors = clean_competitor_list(competitors)
        
        # B. Geospatial Processing
        filtered_competitors = filter_within_radius(
            SOLAPUR_LAT, SOLAPUR_LON, cleaned_competitors, RADIUS_KM
        )
        market_data["competitor_list"] = filtered_competitors
        market_data["competitor_count"] = len(filtered_competitors)
        
        # C. Feature Engineering
        # Calculate EPPI based on location data (Solapur is typically Medium/High tier for purchasing power compared to rural)
        eppi = calculate_eppi("medium", local_price_adjustments=1.1)
        
        # Calculate demand index
        category_baseline = 60.0 # Heuristic placeholder
        pop_proxy = 50000.0 # Solapur local catchment proxy
        seasonality = 1.0 
        demand_idx = calculate_demand_index(category_baseline, pop_proxy, eppi, seasonality)
        
        # Calculate business density
        households = pop_proxy / 4.5 # ~4.5 people per household
        area = 3.14159 * (RADIUS_KM ** 2)
        density = calculate_business_density(len(filtered_competitors), households, area)
        
        market_data["derived_metrics"] = {
            "eppi": eppi,
            "demand_index": demand_idx,
            "density": density
        }
        
        # D. Confidence Tagging
        # Based on Part 17 rules
        composite_conf = calculate_composite_confidence(
            source_conf="Medium", # OSM data
            freshness_conf="High", 
            geo_conf="High", # We geolocated them specifically within radius
            completeness_conf="Medium" if len(filtered_competitors) > 0 else "Low"
        )
        market_data["confidence"] = composite_conf
        
        cat_data["competitor_market_data"] = market_data

    print(f"4. Writing curated dataset to {combined_path}...")
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    run_pipeline()
