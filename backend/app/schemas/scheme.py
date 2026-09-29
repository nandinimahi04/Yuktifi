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


class EvaluatedSchemeModel(BaseModel):
    scheme_id: str
    scheme_name: str
    ministry: str
    match_status: str
    is_eligible: bool
    eligibility_score: int
    subsidy_pct: float
    subsidy_amount: float
    subsidy_label: str
    max_loan: float
    loan_amount: float
    required_equity: float
    equity_pct: float
    interest_rate: str
    tenure_months: int
    moratorium_months: int
    highlights: list[str] = []
    criteria_met: list[str] = []
    criteria_unmet: list[str] = []
    special_benefit: Optional[str] = None
    portal_url: str
    rag_citation: Optional[dict[str, Any]] = None


class SchemeEvaluationRequest(BaseModel):
    session_id: Optional[str] = None
    social_category: Optional[str] = "General"
    gender: Optional[str] = "Male"
    location_type: Optional[str] = "Rural"
    state: Optional[str] = "Maharashtra"
    district: Optional[str] = "Solapur"
    category_id: Optional[str] = "retail_kirana"
    project_cost: Optional[float] = 200000.0
    own_contribution: Optional[float] = None


class SchemeEvaluationResponse(BaseModel):
    applicant_profile: dict[str, Any]
    project_cost: float
    own_contribution: Optional[float] = None
    eligible_schemes: list[EvaluatedSchemeModel] = []
    total_eligible_count: int
    top_recommended_scheme: Optional[EvaluatedSchemeModel] = None
    disclaimer: str

