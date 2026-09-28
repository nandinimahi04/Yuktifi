import logging
from typing import Dict, Any
from app.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# National business templates and categories.
#
# These are the category IDs that carry economics. A model answer is validated
# against this list before being accepted, so a stale list silently rejected
# every correct answer: the model was being told to return IDs such as
# `dairy` and `tailoring`, and those IDs were then discarded as "not one of the
# supported categories". The list mirrors the category IDs present in
# `data/processed/solapur_combined.json` and in the business template registry.
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
#
# The values here must be category IDs that actually carry cost data. This map
# previously pointed at IDs from the *business template* registry (dairy, kirana,
# tailoring, ...) while the only economics dataset ships a different set of IDs
# (retail_shop, manufacturing, agri_business, ...). Every value mapped to a
# category that `get_category_data` could not find, so `total_setup_cost` came
# back null, `financial_data_available` was False, and the financial engine
# returned no project cost, EMI, DSCR or ROI for EVERY user-selected option - the
# analysis returned 200 with `financials: null`.
#
# The ten values are the `category_name` entries in
# `data/processed/solapur_combined.json`, matched one-for-one against the ten
# options the onboarding dropdown offers in `StepBusiness.tsx`. Keys are matched
# case-insensitively by the lookup below, so the labels may be re-worded in the
# UI without silently breaking the mapping.
CATEGORY_MAP = {
    "Retail & Shop": "retail_shop",
    "Manufacturing": "manufacturing",
    "Agri-Business": "agri_business",
    "Services & Tech": "services_tech",
    "Food & Beverage": "food_beverage",
    "Handicrafts & Artisanal": "handicrafts_artisanal",
    "Logistics & Delivery": "logistics_delivery",
    "Education & Training": "education_training",
    "Healthcare & Wellness": "healthcare_wellness",
    "Fashion & Apparel": "fashion_apparel",
}

# Labels still referenced elsewhere in the product - the advisory template
# registry and the RAG seed corpus both name sectors in this vocabulary - mapped
# to the business-template category they describe.
#
# These are kept apart from CATEGORY_MAP on purpose. None of them appears in the
# economics dataset, so a category resolved through this table resolves against
# the business template registry only, whose cost figures are declared assumptions
# rather than observed data. That is a legitimate answer, but it is a different
# and weaker one than a costed dataset category, and merging the two tables would
# hide that distinction. `_CATEGORY_LOOKUP` is the union used for matching.
LEGACY_LABEL_ALIASES = {
    "Dairy Farming & Collection": "dairy",
    "Kirana & General Store": "kirana",
    "Vada Pav & Fast Food": "vada_pav",
    "Tailoring & Garments": "tailoring",
    "Diagnostic Centre": "diagnostic",
    "Agri Machinery": "agri_machinery",
    "Micro Food Processing": "food_processing",
    "Auto & Electronics Repair": "repair_services",
    "Small Hospitality & Dhaba": "small_hospitality",
}

# Merged view consulted by the matcher. CATEGORY_MAP wins on conflict, so a label
# present in both resolves to the costed dataset category.
_CATEGORY_LOOKUP: dict[str, str] = {**LEGACY_LABEL_ALIASES, **CATEGORY_MAP}

async def match_business_category(
    area_of_interest: str,
    suggested_idea: str,
    detailed_idea: str,
    experience: str
) -> Dict[str, Any]:
    """
    Uses Gemini to classify unstructured business ideas into a standard category.
    If the user explicitly selected a known area of interest, it deterministically
    locks in the top-level category and only asks Gemini for subcategory and reasoning.
    """
    gemini = GeminiClient()

    # Deterministic check.
    # Matched case-insensitively and on whitespace-collapsed text, because the
    # dropdown label and the dataset label are maintained separately and a
    # difference in capitalisation or a stray space should not silently drop the
    # user back onto the model-matching path (which abstains without an API key).
    _needle = " ".join((area_of_interest or "").split()).casefold()
    explicit_category = next(
        (cid for label, cid in _CATEGORY_LOOKUP.items()
         if " ".join(label.split()).casefold() == _needle),
        None,
    )
    if not explicit_category and _needle:
        # A near-miss on a known option (e.g. the user typed the label free-hand)
        # is a mapping bug, not an unrecognised business, so it is logged rather
        # than passed to the model as if it were a novel idea.
        logger.info(
            "Category label %r did not match CATEGORY_MAP; treating as free text.",
            area_of_interest,
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
    
    result = await gemini.generate_json_async(prompt, schema=schema)

    if result:
        # Enforce the deterministic category if the user picked one explicitly.
        if explicit_category:
            return {
                **result,
                "matched_category_id": explicit_category,
                "category_source": "USER_SELECTED",
                "confidence": None,
                "reason": (
                    f"Category was set explicitly by the user, so model confidence in the "
                    f"category is not applicable."
                ),
            }

        matched = result.get("matched_category_id")
        if matched in ALLOWED_CATEGORIES:
            return {**result, "category_source": "MODEL_MATCH"}

        # The model named a category that does not exist. Previously this was
        # silently rewritten to ALLOWED_CATEGORIES[0] ("dairy") while KEEPING the
        # model's own confidence - so the published confidence described a
        # category the model had not chosen.
        #
        # The category drives the cost profile, price band, competitor set and
        # every downstream score, so an invented one is worse than none: a
        # dairy cost model applied to a poultry business produces confident,
        # entirely wrong financials. The match is now refused.
        logger.warning(
            "Refusing unmatched category %r; abstaining rather than substituting a default.",
            matched,
        )
        return {
            "matched_category_id": None,
            "matched_subcategory": result.get("matched_subcategory"),
            "confidence": None,
            "category_source": "UNMATCHED",
            "unmatched_category_id": matched,
            "reason": (
                f"The model proposed '{matched}', which is not one of the supported business "
                f"categories, so no category was assigned. Choose a category or supply the "
                f"business inputs directly rather than accepting a substituted template."
            ),
        }

    # No model response.
    #
    # This previously returned "retail_shop" at confidence 0.5. The category
    # selects the cost profile, the price band, the competitor query and every
    # score, so with no API key present EVERY unrecognised business idea was
    # silently modelled as a kirana store and reported with a mid confidence -
    # the most expensive failure mode in the product, since the numbers it
    # produced looked entirely real.
    if explicit_category:
        return {
            "matched_category_id": explicit_category,
            "matched_subcategory": "general",
            "confidence": None,
            "category_source": "USER_SELECTED",
            "reason": "Category supplied by the user; no model matching was performed.",
        }

    return {
        "matched_category_id": None,
        "matched_subcategory": None,
        "confidence": None,
        "category_source": "UNAVAILABLE",
        "reason": (
            "Business categorisation is unavailable: the language model was not reachable and no "
            "category was selected. No default category is assumed, because a substituted "
            "template would produce plausible but entirely wrong financials."
        ),
    }
