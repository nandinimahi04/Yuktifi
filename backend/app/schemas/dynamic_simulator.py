from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class SimulatorRequest(BaseModel):
    business_id: str
    month: int
    cash_balance: float
    active_events: List[str]
    decision: str
    scenario_parameters: Dict[str, Any]
    # The business's own declared financial baseline. The simulator computes
    # from these; it does not assume a revenue, a cost, an investment or an EMI.
    #
    # Used only when `session_id` is absent or unknown. With a session the
    # simulator re-runs that session's own canonical model instead, so its
    # figures are the same ones the analysis screen shows.
    baseline: Optional[Dict[str, Any]] = None
    # Optional. When supplied, the session's canonical input is used and every
    # figure on the response comes from re-running the full model.
    session_id: Optional[str] = None

class EventInfo(BaseModel):
    id: str
    title: str

class DecisionInfo(BaseModel):
    selected: str

class FinancialImpact(BaseModel):
    revenue: Optional[float]
    operating_cost: Optional[float]
    net_cash_flow: Optional[float]
    roi: Optional[float]
    dscr: Optional[float]
    dscr_status: str
    roi_status: str
    ending_cash_balance: Optional[float]
    starting_cash_balance: Optional[float]
    monthly_emi: Optional[float]
    available: bool
    reason: Optional[str]
    assumptions: List[Dict[str, Any]]
    # "canonical" when the full model was re-run, "scalar_baseline" when the
    # lighter model over a declared baseline dict was used. A reader comparing
    # this screen against the analysis screen should know whether the two are
    # the same model.
    model: Optional[str] = None
    # Present only on the canonical path, where a verdict exists to report.
    decision: Optional[str] = None
    viability_reasons: Optional[List[str]] = None
    break_even_units: Optional[float] = None


class SimulatorResponse(BaseModel):
    month: int
    event: EventInfo
    decision: DecisionInfo
    financial_impact: FinancialImpact
    risk_level: str
    # Not computed for the dynamic simulator. See `score_note`. Previously a
    # hardcoded 74 was returned for every scenario.
    yukti_score: Optional[int]
    score_available: bool
    score_note: str
    ai_explanation: Optional[str]
    next_month_available: bool
