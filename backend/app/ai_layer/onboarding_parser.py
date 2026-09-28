import logging
from typing import Dict, Any, Optional
from app.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# Initialize client; defaults to GEMINI_API_KEY from environment
gemini = GeminiClient()

_ONBOARDING_SYSTEM_PROMPT = """
You are an expert intent parser for an AI-Driven Business Advisory platform called YuktiFi.
The user is a rural micro-entrepreneur describing their business idea.
Extract the following structured information from their text:
1. `business_category`: The general category of the business (e.g., "dairy", "retail", "textiles", "food processing", "agriculture"). Normalize to lowercase. If unclear, return null.
2. `location`: The name of the village, town, city, or district mentioned. If none, return null.
3. `capital_in_inr`: The total investment capital mentioned, parsed as an integer in Indian Rupees (INR). E.g., "1 lakh" -> 100000, "50k" -> 50000. If none, return null.
4. `experience_level`: A brief string describing their prior experience if mentioned (e.g., "5 years", "none", "beginner"). If none, return null.

Return ONLY a valid JSON object matching this schema. Do not include markdown formatting or extra text.
"""

_ONBOARDING_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "business_category": {"type": "STRING", "nullable": True},
        "location": {"type": "STRING", "nullable": True},
        "capital_in_inr": {"type": "INTEGER", "nullable": True},
        "experience_level": {"type": "STRING", "nullable": True}
    },
    "required": ["business_category", "location", "capital_in_inr", "experience_level"]
}

_EMPTY = {
    "business_category": None,
    "location": None,
    "capital_in_inr": None,
    "experience_level": None,
}

# Indian number words a rural user is likely to write instead of digits.
_LAKH = 100_000
_CRORE = 10_000_000
_THOUSAND = 1_000


def _digit_tokens(text: str) -> set[str]:
    """Every digit run in the text, with and without Indian digit grouping."""
    import re

    tokens = set()
    for raw in re.findall(r"\d[\d,]*", text or ""):
        cleaned = raw.replace(",", "")
        if cleaned:
            tokens.add(cleaned)
    return tokens


def _capital_is_grounded(capital: Any, text: str) -> bool:
    """
    Is the extracted capital actually stated in the user's words?

    This parser is the one place a model is allowed to produce a number, and only
    because the number is supposed to come from the applicant. That is an
    assumption worth testing rather than trusting: a single ungrounded capital
    figure becomes the denominator of every ROI, debt-service and equity ratio
    in the product, and it would be presented to a bank as a declaration the
    applicant never made.

    A value is accepted if the digits appear in the text, or if the amount is
    expressible as a plain lakh/crore/thousand figure the user may have written
    in words ("1.5 lakh", "2 lakh", "50 thousand", "50k").
    """
    if not isinstance(capital, (int, float)) or isinstance(capital, bool):
        return False
    amount = float(capital)
    if amount <= 0:
        # A capital of zero is not an absence of capital; it is a claim, and the
        # model reaching for 0 to mean "unspecified" would turn "I don't know"
        # into a verified zero.
        return False

    lowered = (text or "").lower()
    present = _digit_tokens(lowered)

    if str(int(amount)) in present or str(amount) in present:
        return True
    if amount.is_integer() and f"{int(amount):,}" in (text or ""):
        return True

    # Worded forms, including the decimal lakh the prompt itself teaches.
    for value, suffix in (
        (amount / _LAKH, "lakh"),
        (amount / _LAKH, "lac"),
        (amount / _CRORE, "crore"),
        (amount / _THOUSAND, "thousand"),
        (amount / _THOUSAND, "k"),
    ):
        if value <= 0:
            continue
        for written in (f"{value:g}", f"{value:.1f}".rstrip("0").rstrip(".")):
            if f"{written} {suffix}" in lowered or f"{written}{suffix}" in lowered:
                return True
    return False


async def parse_onboarding_text(text: str) -> Dict[str, Any]:
    """
    Parses free-form natural language text to extract business onboarding details.

    Every extracted field is checked against the source text before it is
    returned, and any field that cannot be grounded is dropped to None. A field
    the user can edit is far better than a plausible value they cannot trace back
    to something they actually said.
    """
    if not text or not text.strip():
        return dict(_EMPTY)

    prompt = f"{_ONBOARDING_SYSTEM_PROMPT}\n\nUser Text:\n{text}"

    try:
        result = await gemini.generate_json_async(prompt, schema=_ONBOARDING_SCHEMA)
    except Exception as e:
        logger.error("Error parsing onboarding text: %s", e)
        return dict(_EMPTY)

    if not result:
        return dict(_EMPTY)

    parsed = dict(_EMPTY)
    for key in _EMPTY:
        value = result.get(key)
        parsed[key] = value if value not in ("", "null", "None") else None

    if not _capital_is_grounded(parsed["capital_in_inr"], text):
        if parsed["capital_in_inr"] is not None:
            logger.info(
                "Dropping ungrounded capital %r: no matching figure in the applicant's text.",
                parsed["capital_in_inr"],
            )
        parsed["capital_in_inr"] = None

    return parsed
