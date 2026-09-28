from pydantic import BaseModel
from typing import Any, Optional


class SchemeMatchRequest(BaseModel):
    session_id: str
    project_cost: Optional[float] = None
    # Optional: when omitted the session's declared capital is used, because a
    # funded amount is the gap between project cost and the applicant's own
    # money. Passing a session_id and then never reading it meant this endpoint
    # could only ever report max_loan=None.
    own_contribution: Optional[float] = None


class SchemeMatchResponse(BaseModel):
    matched: bool
    scheme_name: Optional[str] = None
    max_loan: Optional[float] = None
    rate: Optional[float] = None
    tenure_years: Optional[int] = None
    moratorium_months: Optional[int] = None
    rejected_alternative: Optional[str] = None
    explanation: str
    source_url: Optional[str] = None

    potentially_eligible: bool = False
    eligibility_statement: str = ""
    rule_id: Optional[str] = None
    rule_version: Optional[str] = None
    rule_effective_from: Optional[str] = None
    rule_verification: Optional[dict[str, Any]] = None
    criteria_met: list[str] = []
    criteria_unmet: list[str] = []
    requires_confirmation: list[str] = []
    not_evaluated_schemes: list[str] = []
    disclaimer: str = ""
