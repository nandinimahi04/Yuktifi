"""
Advisory Finance module — redirects to Canonical Financial Engine.
Ensures identical mathematical results across all application interfaces.
"""
from dataclasses import dataclass, asdict
from typing import Optional
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    ProductItem,
    OpexBreakdown,
    compute_canonical_financials
)

@dataclass(frozen=True)
class FinancialModel:
    project_cost: float
    promoter_margin: float
    loan_amount: float
    financing_gap: float
    financing_reconciled: bool
    monthly_revenue: float
    variable_cost: float
    fixed_cost: float
    operating_profit: float
    monthly_emi: float
    dscr: Optional[float]
    dscr_status: str
    break_even_units: Optional[float]
    economic_viability: str
    viability_reasons: list[dict]
    assessability_unknowns: list[str]
    assumptions: list[dict]

def calculate(*, promoter_margin: float, monthly_units: float, price_per_unit: float,
              variable_cost_per_unit: float, fixed_cost_monthly: float,
              annual_rate_pct: float, tenure_months: int, financing_pct: float = 0.90,
              scheme_max_loan: float | None = None,
              total_project_cost: float | None = None) -> FinancialModel:

    # SCHEME QUOTE, not an engine default. The canonical engine never infers
    # project cost from margin. This wrapper does, but only because the caller
    # has declared `financing_pct`: the promoter margin is being treated as
    # the scheme's required contribution share of (1 - financing_pct).
    # Pass total_project_cost to use a real quoted project cost instead.
    if total_project_cost is not None:
        project_cost = float(total_project_cost)
    elif 0 < financing_pct < 1:
        project_cost = float(promoter_margin) / (1.0 - financing_pct)
    else:
        project_cost = float(promoter_margin)

    own_contribution = min(promoter_margin, project_cost)
    debt = max(0.0, project_cost - own_contribution)
    if scheme_max_loan is not None:
        debt = min(debt, scheme_max_loan)

    inp = CanonicalFinancialInput(
        business_type="advisory",
        products=[ProductItem(name="Default Item", units_per_month=monthly_units, selling_price=price_per_unit, variable_cost_per_unit=variable_cost_per_unit)],
        opex=OpexBreakdown(other=fixed_cost_monthly),
        own_capital=own_contribution,
        total_project_cost=project_cost,
        debt_amount=debt,
        scheme_financing_rate=financing_pct,
        scheme_ceiling=scheme_max_loan,
        interest_rate_annual_pct=annual_rate_pct,
        tenure_months=tenure_months
    )

    res = compute_canonical_financials(inp)

    return FinancialModel(
        project_cost=res.total_project_cost,
        promoter_margin=res.own_capital,
        loan_amount=res.debt_amount,
        financing_gap=res.financing_gap,
        financing_reconciled=res.financing_reconciled,
        monthly_revenue=res.monthly_revenue,
        variable_cost=res.monthly_variable_costs,
        fixed_cost=res.monthly_opex,
        operating_profit=res.monthly_pat,
        monthly_emi=res.monthly_emi,
        dscr=res.dscr,
        dscr_status=res.dscr_status,
        break_even_units=res.break_even_units_monthly,
        economic_viability=res.economic_viability,
        viability_reasons=res.viability_reasons,
        assessability_unknowns=res.assessability_unknowns,
        assumptions=res.assumptions_provenance
    )

def as_dict(x: FinancialModel):
    return asdict(x)
