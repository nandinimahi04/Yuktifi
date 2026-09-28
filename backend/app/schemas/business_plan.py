from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class DataSource(BaseModel):
    """
    Provenance for a field in the plan.

    `source` is populated by the SERVER from the evidence layer, never by the
    model. A language model that writes its own citation will happily attach
    "Census 2011 / High confidence" to a figure it invented, which converts a
    hallucination into a forged reference. The model is told to omit this
    section; whatever it returns is discarded.
    """
    field: str
    value: Any = None
    source: Optional[str] = None
    confidence: Optional[str] = None
    source_kind: str = "UNATTRIBUTED"
    note: Optional[str] = None

class ProposalMetadata(BaseModel):
    """
    Server-generated. The model previously authored every field here, including
    `proposal_id` and `data_confidence` - so the document identified itself with
    an invented number and rated its own evidence quality. A plan that rates its
    own confidence is not a source of confidence.
    """
    proposal_id: Optional[str] = None
    generated_at: Optional[str] = None
    location: Optional[str] = None
    business_category: Optional[str] = None
    data_confidence: Optional[str] = None
    computed_by: str = "server"

class ExecutiveSummary(BaseModel):
    business_overview: str
    opportunity: str
    recommendation: str
    key_metrics: Dict[str, Any]

class ProjectCost(BaseModel):
    """
    Computed by the canonical engine. Optional because the engine returns None
    when the capital requirement is unknown, and an unknown capital requirement
    is not a zero one.
    """
    total_project_cost: Optional[float] = None
    own_contribution: Optional[float] = None
    financing_required: Optional[float] = None
    financing_gap: Optional[float] = None
    computed_by: str = "canonical_financial_engine"

class ProfitabilityAnalysis(BaseModel):
    """
    Computed by the canonical engine.

    `dscr` is Optional and legitimately None for a debtless business, which is
    the single most common case. The previous schema required a float, so the
    model had to invent one - a DSCR for a business with no loan.
    """
    roi: Optional[float] = None
    dscr: Optional[float] = None
    dscr_status: Optional[str] = None
    break_even: Optional[float] = None
    net_margin_pct: Optional[float] = None
    payback_months: Optional[float] = None
    payback_status: Optional[str] = None
    npv: Optional[float] = None
    economic_viability: Optional[str] = None
    computed_by: str = "canonical_financial_engine"

class BusinessPlan(BaseModel):
    proposal_metadata: ProposalMetadata
    executive_summary: ExecutiveSummary
    entrepreneur_profile: Dict[str, Any] = Field(default_factory=dict)
    proposed_business: Dict[str, Any] = Field(default_factory=dict)
    local_market_analysis: Dict[str, Any] = Field(default_factory=dict)
    competition_analysis: Dict[str, Any] = Field(default_factory=dict)
    products_and_services: List[Dict[str, Any]] = Field(default_factory=list)
    infrastructure_and_equipment: Dict[str, Any] = Field(default_factory=dict)
    project_cost: ProjectCost
    financial_structure: Dict[str, Any] = Field(default_factory=dict)
    revenue_projection: Dict[str, Any] = Field(default_factory=dict)
    operating_expenses: Dict[str, Any] = Field(default_factory=dict)
    cash_flow_projection: Dict[str, Any] = Field(default_factory=dict)
    profitability_analysis: ProfitabilityAnalysis
    risk_analysis: Dict[str, Any] = Field(default_factory=dict)
    swot_analysis: Dict[str, Any] = Field(default_factory=dict)
    marketing_strategy: Dict[str, Any] = Field(default_factory=dict)
    implementation_plan: Dict[str, Any] = Field(default_factory=dict)
    ninety_day_action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    financing_readiness: Dict[str, Any] = Field(default_factory=dict)
    required_documents: List[str] = Field(default_factory=list)
    scheme_information: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    data_sources: List[DataSource] = Field(default_factory=list)
    conclusion: Dict[str, Any] = Field(default_factory=dict)
