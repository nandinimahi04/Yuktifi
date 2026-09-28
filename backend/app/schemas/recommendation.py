from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class RecommendRequest(BaseModel):
    session_id: str


class DimensionScore(BaseModel):
    """A single dimension, which may be explicitly unscored."""

    score: Optional[float] = None
    known: bool = False
    label: str = ""
    reason: str = ""


class DimensionScores(BaseModel):
    financial_viability: DimensionScore
    repayment_capacity: DimensionScore
    market_opportunity: DimensionScore
    capital_efficiency: DimensionScore
    risk_exposure: DimensionScore


class RecommendResponse(BaseModel):
    session_id: str
    # Optional throughout: a recommendation that cannot be evidenced reports
    # None rather than a placeholder. `dscr = 1.0` and `roi = 15.0` were
    # previously returned when no projection existed - a DSCR of exactly 1.0 is
    # the borderline "just covers debt service" figure, so a business with no
    # financial data at all was presented as having precisely borderline
    # repayment capacity.
    yukti_score: Optional[float] = None
    raw_score: Optional[float] = None
    confidence_multiplier: float
    verdict: Optional[str] = None
    dimension_scores: DimensionScores
    dscr: Optional[float] = None
    dscr_status: str = "UNAVAILABLE"
    roi: Optional[float] = None
    roi_status: str = "UNAVAILABLE"
    next_steps: List[Dict[str, Any]] = []
    confidence: str
    unscored_dimensions: List[str] = []
    note: str = ""
