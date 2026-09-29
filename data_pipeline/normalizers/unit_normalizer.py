"""
Unit Normalization Layer.
Normalizes monetary values, units of measure, time periods, and percentages
while strictly preserving original values and conversion derivations.
"""
from typing import Any, Dict, Optional, Tuple

def normalize_currency_and_period(raw_value: Any, raw_unit: str) -> Dict[str, Any]:
    """
    Normalizes monetary values to standard INR per Month / per Year / Total.
    Example: ₹75,000/month -> value=75000, currency=INR, period=MONTH
    """
    if raw_value is None:
        return {
            "original_value": None,
            "original_unit": raw_unit,
            "normalized_value": None,
            "normalized_unit": raw_unit,
            "conversion_method": "IDENTITY_NULL"
        }

    import re
    multiplier = 1.0
    method = "DIRECT"

    clean_val = raw_value
    if isinstance(raw_value, str):
        val_str = raw_value.lower()
        if "lakh" in val_str or "lac" in val_str:
            multiplier = 100000.0
            method = "MULTIPLY_100K"
            raw_value = re.sub(r"(?i)lakhs?|lacs?", "", raw_value)
        elif "crore" in val_str or "cr" in val_str:
            multiplier = 10000000.0
            method = "MULTIPLY_10M"
            raw_value = re.sub(r"(?i)crores?|cr", "", raw_value)
        elif "thousand" in val_str or " k" in val_str or val_str.endswith("k"):
            multiplier = 1000.0
            method = "MULTIPLY_1K"
            raw_value = re.sub(r"(?i)thousands?|k", "", raw_value)

        cleaned = raw_value.replace("₹", "").replace("Rs.", "").replace("INR", "").replace(",", "").replace("%", "").strip()
        try:
            clean_val = float(cleaned)
        except ValueError:
            return {
                "original_value": raw_value,
                "original_unit": raw_unit,
                "normalized_value": None,
                "normalized_unit": raw_unit,
                "conversion_method": "NON_NUMERIC_STRING"
            }

    u_lower = (raw_unit or "").lower()
    
    # Handle Lakhs and Crores in unit if not already multiplied
    if multiplier == 1.0:
        if "lakh" in u_lower or "lac" in u_lower:
            multiplier = 100000.0
            method = "MULTIPLY_100K"
        elif "crore" in u_lower or "cr" in u_lower:
            multiplier = 10000000.0
            method = "MULTIPLY_10M"
        elif "thousand" in u_lower or "k" in u_lower:
            multiplier = 1000.0
            method = "MULTIPLY_1K"

    norm_val = float(clean_val) * multiplier
    norm_unit = "INR"

    if "per month" in u_lower or "/month" in u_lower or "monthly" in u_lower or "/mo" in u_lower:
        norm_unit = "INR / month"
    elif "per year" in u_lower or "/year" in u_lower or "annual" in u_lower or "/yr" in u_lower:
        norm_unit = "INR / year"
    elif "per day" in u_lower or "/day" in u_lower or "daily" in u_lower:
        norm_unit = "INR / day"
    elif "per quintal" in u_lower or "/quintal" in u_lower or "/qtl" in u_lower:
        norm_unit = "INR / quintal"
    elif "per kg" in u_lower or "/kg" in u_lower:
        norm_unit = "INR / kg"
    elif "per litre" in u_lower or "/litre" in u_lower or "/l" in u_lower:
        norm_unit = "INR / litre"
    elif "%" in u_lower or "percent" in u_lower or "pct" in u_lower:
        norm_unit = "%"

    return {
        "original_value": raw_value,
        "original_unit": raw_unit,
        "normalized_value": norm_val,
        "normalized_unit": norm_unit,
        "conversion_method": method
    }
