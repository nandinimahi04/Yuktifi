from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class RankRequest(BaseModel):
    session_id: str
    location_id: str
    margin_capital: float


class RankedCategory(BaseModel):
    """
    One category in the ranked list.

    `yukti_score` and `verdict` are Optional and are None for categories that
    could not be evaluated. They were previously required floats, so an
    unevaluable category raised a validation error and the whole ranking
    request failed with a 500 instead of showing the category as needing data.
    """
    category_id: str
    category_name: str
    yukti_score: Optional[float] = None
    verdict: Optional[str] = None
    confidence: str = "UNAVAILABLE"
    rank: Optional[int] = None
    ranked: bool = False
    evidence_state: Optional[str] = None
    score_coverage_pct: float = 0.0
    dimension_scores: Dict[str, Optional[int]] = {}
    unscored_dimensions: List[str] = []
    unscored_labels: List[str] = []
    dscr: Optional[float] = None
    dscr_status: Optional[str] = None
    roi: Optional[float] = None
    emi: Optional[float] = None
    loan_amount: Optional[float] = None
    financing_terms_status: str = "UNKNOWN"
    project_cost: Optional[float] = None
    project_cost_status: str = "UNKNOWN"
    net_profit: Optional[float] = None
    net_margin: Optional[float] = None
    break_even_units: Optional[float] = None
    payback_months: Optional[int] = None
    payback_status: Optional[str] = None
    npv: Optional[float] = None
    economic_viability: Optional[str] = None
    viability_reasons: List[str] = []
    assessability_unknowns: List[str] = []
    scheme_name: Optional[str] = None
    # "Potentially eligible" only. A bare "eligible" reads as approval.
    scheme_status: str = "Not evaluated"
    highlights: List[str] = []
    note: str = ""
    limitations: Optional[str] = None

    # Extra detail is preserved rather than dropped, so a UI can surface
    # provenance without a second endpoint.
    model_config = {"extra": "allow"}


class RankResponse(BaseModel):
    session_id: str
    rankings: List[RankedCategory]
    ranked_count: int = 0
    unranked_count: int = 0
    # Schemes can only be evaluated against a declared project cost, not
    # against the entrepreneur's margin, so this is usually None.
    scheme_matched: bool = False
    scheme_name: Optional[str] = None
    scheme_status: str = "Not evaluated"
    scheme_note: Optional[str] = None
