"""
Time Normalization Layer.
Parses reference years, survey rounds, and effective date ranges.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def normalize_time_context(raw_date_or_year: Any, filename: str = "") -> Dict[str, Any]:
    """
    Extracts reference_year, observed_at, effective_from, effective_to from strings or numbers.
    """
    ref_year = None
    observed_at = None
    effective_from = None
    effective_to = None
    survey_period = None

    if isinstance(raw_date_or_year, int):
        ref_year = raw_date_or_year
    elif isinstance(raw_date_or_year, str):
        # Look for 4-digit years
        match_year = re.search(r"\b(19\d\d|20\d\d)\b", raw_date_or_year)
        if match_year:
            ref_year = int(match_year.group(1))

        # Check for fiscal/survey periods like 2022-23 or 2023-24
        match_survey = re.search(r"\b(20\d\d)-(\d\d)\b", raw_date_or_year)
        if match_survey:
            start_yr = int(match_survey.group(1))
            survey_period = f"{start_yr}-{int(match_survey.group(2))}"
            ref_year = start_yr + 1  # Standard reference year is end of survey

    if ref_year is None and filename:
        # Infer from filename if present
        match_fn = re.search(r"\b(20\d\d)\b", filename)
        if match_fn:
            ref_year = int(match_fn.group(1))

    return {
        "reference_year": ref_year,
        "observed_at": observed_at or (f"{ref_year}-01-01" if ref_year else None),
        "effective_from": effective_from,
        "effective_to": effective_to,
        "survey_period": survey_period
    }
