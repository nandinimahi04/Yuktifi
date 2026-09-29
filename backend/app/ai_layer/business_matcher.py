import logging
from typing import Dict, Any
from app.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# National business templates and categories.
ALLOWED_CATEGORIES = [
    "retail_shop",
    "manufacturing",
    "agri_business",
    "services_tech",
    "food_beverage",
    "handicrafts_artisanal",
    "logistics_delivery",
    "education_training",
    "healthcare_wellness",
    "fashion_apparel",
    "dairy",
    "kirana",
    "vada_pav",
    "tailoring",
    "diagnostic",
    "agri_machinery",
    "food_processing",
    "repair_services",
    "small_hospitality",
]

# Deterministic mapping for explicit frontend options.
CATEGORY_MAP = {
    "Retail & Shop": "retail_shop",
    "Retail & Grocery": "retail_shop",
    "Manufacturing": "manufacturing",
    "Manufacturing & Processing": "manufacturing",
    "Agri-Business": "agri_business",
    "Agri-Business & Farming": "agri_business",
    "Services & Tech": "services_tech",
    "Food & Beverage": "food_beverage",
    "Handicrafts & Artisanal": "handicrafts_artisanal",
    "Logistics & Delivery": "logistics_delivery",
    "Logistics & Transport": "logistics_delivery",
    "Education & Training": "education_training",
    "Healthcare & Wellness": "healthcare_wellness",
    "Fashion & Apparel": "fashion_apparel",
    "Other": "retail_shop",
}

LEGACY_LABEL_ALIASES = {
    "Dairy Farming & Collection": "dairy",
    "Dairy Farming": "dairy",
    "Dairy Farming & Milk Chilling": "dairy",
    "Kirana & General Store": "kirana",
    "Kirana / Grocery Store": "kirana",
    "Grocery Store": "kirana",
    "General Store": "kirana",
    "Supermarket & Mart": "retail_shop",
    "Pooja Samagri Store": "kirana",
    "Stationery & Xerox": "retail_shop",
    "Vada Pav & Fast Food": "vada_pav",
    "Tea & Snacks Shop": "food_beverage",
    "Tea & Snacks Stall": "food_beverage",
    "Vada Pav Center": "vada_pav",
    "Bakery & Confectionery": "food_beverage",
    "Juice & Milkshake Bar": "food_beverage",
    "Fast Food & Chaat Stall": "food_beverage",
    "Tailoring & Garments": "tailoring",
    "Diagnostic Centre": "diagnostic",
    "Diagnostic & Pathology Lab": "diagnostic",
    "Pathology & Clinical Lab": "diagnostic",
    "Agri Machinery": "agri_machinery",
    "Micro Food Processing": "food_processing",
    "Atta Chakki / Flour Mill": "manufacturing",
    "Flour Mill": "manufacturing",
    "Mobile Repair Shop": "services_tech",
    "Mobile & Electronics Repair": "services_tech",
    "Two-Wheeler Service Garage": "services_tech",
    "Auto & Electronics Repair": "services_tech",
    "Beauty & Hair Salon": "services_tech",
    "Solar Installation & Service": "services_tech",
    "E-Rickshaw Transport": "logistics_delivery",
    "E-Rickshaw Commercial Transport": "logistics_delivery",
    "E-Rickshaw Passenger Fleet": "logistics_delivery",
    "Local Parcel Delivery Service": "logistics_delivery",
    "Mini Cargo Van Transport": "logistics_delivery",
    "Poultry Farm": "agri_business",
    "Goat Farming": "agri_business",
    "Organic Fertilizer & Vermicompost": "agri_business",
    "Small Hospitality & Dhaba": "small_hospitality",
}

_CATEGORY_LOOKUP: dict[str, str] = {**LEGACY_LABEL_ALIASES, **CATEGORY_MAP}


async def match_business_category(
    area_of_interest: str,
    suggested_idea: str,
    detailed_idea: str,
    experience: str
) -> Dict[str, Any]:
    """
    Uses Gemini to classify unstructured business ideas into a standard category.
    If the user explicitly selected a known area of interest or typed a recognizable idea,
    it deterministically matches the category.
    """
    gemini = GeminiClient()

    _needle = " ".join((area_of_interest or "").split()).casefold()
    explicit_category = next(
        (cid for label, cid in _CATEGORY_LOOKUP.items()
         if " ".join(label.split()).casefold() == _needle),
        None,
    )
    
    if explicit_category:
        prompt = f"""
        You are a business categorization expert for YUKTI (a business intelligence platform).
        The user has provided the following inputs for their new business idea:
        - Area of Interest: {area_of_interest} (Deterministic Category: {explicit_category})
        - Suggested Idea Template: {suggested_idea}
        - Detailed Idea Description: {detailed_idea}
        - Prior Experience: {experience}

        The top-level category is ALREADY DETERMINED as '{explicit_category}'.
        Do NOT change it.
        
        Determine a 'subcategory' based on the user's detailed description (e.g., 'grocery', 'tailoring', 'dairy').
        Provide a 1-sentence explanation of how this idea fits the category.
        Return a strict JSON object with this schema, and nothing else.
        """
    else:
        prompt = f"""
        You are a business categorization expert for YUKTI (a business intelligence platform).
        The user has provided the following inputs for their new business idea:
        - Area of Interest: {area_of_interest}
        - Suggested Idea Template: {suggested_idea}
        - Detailed Idea Description: {detailed_idea}
        - Prior Experience: {experience}

        You must map this idea to ONE of the following EXACT allowed category IDs:
        {', '.join(ALLOWED_CATEGORIES)}

        Also determine a 'subcategory' based on the user's detailed description.
        Return a strict JSON object with this schema, and nothing else.
        """
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "matched_category_id": {
                "type": "STRING",
                "description": "The exact category ID from the allowed list."
            },
            "matched_subcategory": {
                "type": "STRING",
                "description": "A short subcategory name (e.g. 'grocery', 'electronics')."
            },
            "confidence": {
                "type": "NUMBER",
                "description": "A float between 0.0 and 1.0 indicating confidence."
            },
            "reason": {
                "type": "STRING",
                "description": "A 1-sentence explanation of why this category was chosen."
            }
        },
        "required": ["matched_category_id", "matched_subcategory", "confidence", "reason"]
    }
    
    result = None
    try:
        result = await gemini.generate_json_async(prompt, schema=schema)
    except Exception as e:
        logger.warning("[MATCHER] Gemini call failed: %s", str(e))

    if explicit_category:
        return {
            **(result or {}),
            "matched_category_id": explicit_category,
            "matched_subcategory": (result or {}).get("matched_subcategory") or area_of_interest,
            "confidence": None,
            "category_source": "USER_SELECTED",
            "reason": f"Category was mapped from user selection: {area_of_interest}.",
        }

    if result:
        matched = result.get("matched_category_id")
        if matched in ALLOWED_CATEGORIES:
            return {**result, "category_source": "MODEL_MATCH"}
        else:
            return {
                "matched_category_id": None,
                "matched_subcategory": result.get("matched_subcategory"),
                "confidence": None,
                "category_source": "UNMATCHED",
                "unmatched_category_id": matched,
                "reason": f"Model suggested unmatched category: {matched}."
            }

    return {
        "matched_category_id": None,
        "matched_subcategory": None,
        "confidence": None,
        "category_source": "UNAVAILABLE",
        "reason": "No model was reachable to classify the idea, and no explicit area of interest was selected."
    }
