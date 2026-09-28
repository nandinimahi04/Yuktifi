from pydantic import BaseModel
from typing import Optional, List


class FinanceRequest(BaseModel):
    session_id: str


class PnlStatement(BaseModel):
    revenue: float
    cogs: float
    gross_profit: float
    gross_margin_pct: float
    operating_expenses: float
    ebit: float
    tax: float
    net_profit: float
    net_margin_pct: float


class WorkingCapital(BaseModel):
    daily_cash_needed: float
    weekly_cash_needed: float
    monthly_working_capital: float
    inventory_requirement: float
    receivables: float
    payables: float
    recommended_buffer: float
    receivable_days: int
    payable_days: int
    inventory_days: int


class PaybackPeriod(BaseModel):
    payback_months: Optional[int]
    payback_achieved: bool
    total_investment: float
    note: str


class LoanScheduleMonth(BaseModel):
    month: int
    opening_balance: float
    interest: float
    principal_repaid: float
    payment: float
    closing_balance: float


class FinanceResponse(BaseModel):
    # Core
    project_cost: float
    loan_amount: float
    beneficiary_contribution: float
    scheme: dict
    emi: float
    rate: float
    tenure_months: int
    moratorium_months: int
    monthly_revenue: float
    monthly_opex: float
    net_profit: float
    dscr: Optional[float] = None
    break_even_units: Optional[float] = None
    roi: float
    # Both ROI bases are published: the headline is on total project cost, and
    # the promoter-equity return is larger only because equity is thinner.
    roi_on_total_project_pct: float = 0.0
    roi_on_owner_equity_pct: float = 0.0
    capital_turnover_ratio: Optional[float] = None
    revenue_source: Optional[str] = None
    cost_confidence: str

    # Financing reconciliation: project cost must equal the sum of its sources.
    other_funding: float = 0.0
    financing_gap: float = 0.0
    financing_reconciled: bool = True
    viability: Optional[str] = None
    viability_reasons: List[str] = []

    # Extended
    cashflow_projection: List[dict] = []
    loan_schedule: List[LoanScheduleMonth] = []
    pnl_statement: Optional[PnlStatement] = None
    working_capital: Optional[WorkingCapital] = None
    revenue_scenarios: dict = {}
    seasonal_revenue: List[dict] = []
    payback_period: Optional[PaybackPeriod] = None
