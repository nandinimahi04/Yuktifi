from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class SimulateRequest(BaseModel):
    session_id: str
    # Original API: a volume shock and a variable-cost shock, in percentage
    # points. Kept so existing clients keep working, and translated into
    # `units_multiplier` and `variable_cost_delta_pct` below.
    revenue_delta_pct: float = 0.0
    cost_delta_pct: float = 0.0
    tenure_override_years: Optional[int] = None

    # The canonical WhatIfAdjustments levers, in the units the engine uses.
    # Percentages are percentage points (10.0 means +10%), and
    # `units_multiplier` is a factor (1.10 means 110% of current volume).
    #
    # These existed in the engine and were unreachable over HTTP, so a founder
    # could ask "what if I put in more of my own money", or "what if I borrowed
    # for longer", or "what if my supplier gave me 60 days" and the product had no
    # way to answer. Each is optional; an omitted lever leaves the plan alone.
    # Where both forms set the same lever the explicit one wins.
    units_multiplier: Optional[float] = None
    price_delta_pct: Optional[float] = None
    variable_cost_delta_pct: Optional[float] = None
    fixed_cost_delta_pct: Optional[float] = None
    interest_rate_annual_pct: Optional[float] = None
    tenure_months: Optional[int] = None
    own_capital: Optional[float] = None
    debt_amount: Optional[float] = None
    other_funding: Optional[float] = None
    tax_rate_pct: Optional[float] = None
    operating_days_per_month: Optional[int] = None
    annual_price_growth_pct: Optional[float] = None
    working_capital_days_scale: Optional[float] = None

    def to_adjustments(self) -> dict:
        """Only the levers the caller actually set. An unset lever is absent,
        not zero - a zero here would be read as "set it to nothing"."""
        names = (
            "units_multiplier", "price_delta_pct", "variable_cost_delta_pct",
            "fixed_cost_delta_pct", "interest_rate_annual_pct", "tenure_months",
            "own_capital", "debt_amount", "other_funding", "tax_rate_pct",
            "operating_days_per_month", "annual_price_growth_pct",
            "working_capital_days_scale",
        )
        return {n: getattr(self, n) for n in names if getattr(self, n) is not None}

class SimulateResponse(BaseModel):
    emi: float
    dscr: Optional[float] = None       # None when no debt is modelled
    dscr_status: Optional[str] = None
    break_even_units: Optional[float] = None
    verdict: str
    net_profit: float
    simulated_roi: float          # annualised net_profit / project cost proxy
    # True when the scenario covers its debt service (dscr >= 1.0), False when it
    # does not, and None when there is no debt service to cover.
    #
    # This was typed `bool`, which was the bug: a business with no debt produced
    # dscr=None, and both the engine and Pydantic read that as False - so every
    # debtless plan was reported as failing the stress test. Pydantic would also
    # have silently coerced the null rather than reporting the mismatch. A
    # three-state answer is the only honest one here.
    survives_stress: Optional[bool] = None
    survives_stress_applicable: bool = True  # False when survives_stress is None
    # Which levers moved, and what they were before and after. Needed because
    # the three-field request above cannot express a change of capital, tax or
    # working-capital cycle, so a caller would otherwise have no record of what
    # it actually asked for.
    applied_adjustments: List[Dict[str, Any]] = []
    adjustments: Dict[str, Any] = {}
