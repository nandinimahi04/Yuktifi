from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any


class ValidationWarning(BaseModel):
    field: str
    message: str
    code: str


class FinancialAssumptionsInput(BaseModel):
    project_cost: Optional[float] = Field(None, ge=0, description="Total capital required for setup (INR)")
    own_capital: Optional[float] = Field(None, ge=0, description="Promoter's equity contribution (INR)")
    loan_amount: Optional[float] = Field(None, ge=0, description="Borrowing required (INR)")
    
    # Revenue Mode & Parameters
    is_direct_revenue_mode: Optional[bool] = Field(None, description="Whether to use direct monthly revenue override")
    monthly_revenue: Optional[float] = Field(None, ge=0, description="Direct monthly revenue if override enabled")
    selling_price: Optional[float] = Field(None, ge=0, description="Selling price per unit/customer (INR)")
    units_per_day: Optional[float] = Field(None, ge=0, description="Expected volume per operating day")
    operating_days: Optional[int] = Field(None, ge=1, le=31, description="Working days in a month")
    
    # Cost Parameters
    variable_cost_per_unit: Optional[float] = Field(None, ge=0, description="Direct cost of raw material/packaging per unit")
    monthly_expenses: Optional[float] = Field(None, ge=0, description="Fixed monthly operational expenses (rent, salary, utility)")
    
    # Financing Parameters
    interest_rate_annual_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Annual borrowing interest rate (%)")
    loan_tenure_months: Optional[int] = Field(None, ge=0, le=360, description="Loan term in months")
    moratorium_months: Optional[int] = Field(None, ge=0, le=60, description="Moratorium / grace period in months")
    tax_rate_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Effective corporate/business tax rate (%)")
    
    # Concurrency version
    version: Optional[int] = Field(None, description="Expected version for optimistic concurrency control")

    @model_validator(mode="after")
    def validate_cross_fields(self):
        if self.own_capital is not None and self.project_cost is not None:
            if self.own_capital > self.project_cost:
                raise ValueError(f"Own contribution (₹{self.own_capital:,.0f}) cannot exceed total project cost (₹{self.project_cost:,.0f})")
            if self.loan_amount is None:
                self.loan_amount = max(0.0, self.project_cost - self.own_capital)
            
        return self


class FinancialAssumptionsDTO(BaseModel):
    session_id: str
    version: int
    project_cost: float
    own_capital: float
    loan_amount: float
    is_direct_revenue_mode: bool
    monthly_revenue: float
    selling_price: float
    units_per_day: float
    operating_days: int
    variable_cost_per_unit: float
    monthly_expenses: float
    interest_rate_annual_pct: float
    loan_tenure_months: int
    moratorium_months: int
    tax_rate_pct: Optional[float] = None
    created_at: str
    updated_at: str
    last_updated_ist: str
    validation_warnings: List[ValidationWarning] = []


class FinancialRecalculateRequest(BaseModel):
    session_id: str
    assumptions: FinancialAssumptionsInput
    category_id: Optional[str] = None
    changed_by: Optional[str] = "user"


class FinancialRecalculateResponse(BaseModel):
    status: str
    assumptions_version: int
    last_updated_ist: str
    validation_warnings: List[ValidationWarning]
    assumptions: FinancialAssumptionsDTO
    financials: Dict[str, Any]
    scores: Optional[Dict[str, Any]] = None

