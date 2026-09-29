"""
Geography Normalization Layer.
Normalizes administrative locations, resolves LGD codes, census codes, and historic aliases.
"""
from typing import Any, Dict, List, Optional

# Official Historical and Current Administrative Aliases
ALIASES_MAP = {
    "ahmadnagar": "Ahilyanagar",
    "ahmednagar": "Ahilyanagar",
    "ahilyanagar": "Ahilyanagar",
    "osmanabad": "Dharashiv",
    "dharashiv": "Dharashiv",
    "aurangabad": "Chhatrapati Sambhajinagar",
    "chhatrapati sambhajinagar": "Chhatrapati Sambhajinagar",
    "poona": "Pune",
    "pune": "Pune",
    "sholapur": "Solapur",
    "solapur": "Solapur",
    "bombay": "Mumbai",
    "mumbai": "Mumbai"
}

# LGD & Census Codes for Solapur Talukas / Subdistricts
SOLAPUR_TALUKAS = {
    "akkalkot": {"lgd_code": "04256", "census_code": "04256", "name": "Akkalkot", "district": "Solapur", "state": "Maharashtra"},
    "barshi": {"lgd_code": "04250", "census_code": "04250", "name": "Barshi", "district": "Solapur", "state": "Maharashtra"},
    "karmala": {"lgd_code": "04247", "census_code": "04247", "name": "Karmala", "district": "Solapur", "state": "Maharashtra"},
    "madha": {"lgd_code": "04249", "census_code": "04249", "name": "Madha", "district": "Solapur", "state": "Maharashtra"},
    "malshiras": {"lgd_code": "04251", "census_code": "04251", "name": "Malshiras", "district": "Solapur", "state": "Maharashtra"},
    "mangalvedhe": {"lgd_code": "04254", "census_code": "04254", "name": "Mangalvedhe", "district": "Solapur", "state": "Maharashtra"},
    "mohol": {"lgd_code": "04252", "census_code": "04252", "name": "Mohol", "district": "Solapur", "state": "Maharashtra"},
    "pandharpur": {"lgd_code": "04253", "census_code": "04253", "name": "Pandharpur", "district": "Solapur", "state": "Maharashtra"},
    "sangole": {"lgd_code": "04255", "census_code": "04255", "name": "Sangole", "district": "Solapur", "state": "Maharashtra"},
    "solapur north": {"lgd_code": "04248", "census_code": "04248", "name": "Solapur North", "district": "Solapur", "state": "Maharashtra"},
    "solapur south": {"lgd_code": "04257", "census_code": "04257", "name": "Solapur South", "district": "Solapur", "state": "Maharashtra"},
    "solapur": {"lgd_code": "488", "census_code": "526", "name": "Solapur", "district": "Solapur", "state": "Maharashtra"}
}

def normalize_geography(
    raw_name: str,
    raw_state: Optional[str] = None,
    raw_district: Optional[str] = None,
    raw_subdistrict: Optional[str] = None
) -> Dict[str, Any]:
    """
    Normalizes a geographical name, preserving historical name and matching current standard.
    """
    clean = (raw_name or "").strip()
    clean_lower = clean.lower()
    
    # Check alias
    normalized_name = ALIASES_MAP.get(clean_lower, clean)
    
    # Check subdistrict lookup
    taluka_info = SOLAPUR_TALUKAS.get(clean_lower)
    if not taluka_info and raw_subdistrict:
        taluka_info = SOLAPUR_TALUKAS.get(raw_subdistrict.lower())

    state = raw_state or "Maharashtra"
    district = raw_district or (taluka_info["district"] if taluka_info else "Solapur")
    subdistrict = raw_subdistrict or (taluka_info["name"] if taluka_info and taluka_info["name"] != "Solapur" else None)
    lgd_code = taluka_info["lgd_code"] if taluka_info else None
    census_code = taluka_info["census_code"] if taluka_info else None

    level = "VILLAGE" if clean_lower not in SOLAPUR_TALUKAS and clean_lower not in ["solapur", "maharashtra", "india"] else ("SUBDISTRICT" if subdistrict else ("DISTRICT" if district else "STATE"))

    return {
        "original_name": raw_name,
        "normalized_name": normalized_name,
        "level": level,
        "state": state,
        "district": district,
        "subdistrict": subdistrict,
        "lgd_code": lgd_code,
        "census_2011_code": census_code,
        "country": "India"
    }
