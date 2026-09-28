"""
YuktiFi Canonical Financial Engine.

THE SINGLE SOURCE OF TRUTH for all financial arithmetic in YuktiFi.
Every other module (API, dashboard, what-if, report, AI context) must
derive its numbers from this module so that identical inputs always
produce identical outputs down to the last rupee.

DETERMINISTIC MATH ONLY. NEVER IMPORT AN LLM OR AI CLIENT HERE.

Design rules enforced here:
  1. The engine never manufactures debt. Debt is either stated by the
     caller or derived from an explicitly opted-in scheme.
  2. Project cost is never inflated from margin capital.
  3. Financing always reconciles: the gap is surfaced, never hidden.
  4. Absent quantities are None (N/A), never sentinel numbers like 999.
  5. Missing evidence never becomes fabricated certainty.

The engine is the `app.financial` package. This module holds the input and
result types and the P&L / cash waterfall; its siblings hold the parts of the
same engine that do not compute the waterfall:

    inputs.py       input typing, provenance, validation
    projection.py   monthly forecast, stress scenarios, what-if
    gates.py        decision gates, status, confidence, explainability

There is exactly one implementation of each formula in the package.
`app.engines.financial_engine`, `app.engines.stress_engine` and
`app.engines.simulation_engine` are adapters onto this package for their
historical call signatures; they reimplement nothing.
"""
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import math

from app.financial.gates import (
    DEFAULT_GATE_BENCHMARK,
    GateBenchmark,
    assess_confidence,
    build_explanations,
    derive_financial_status,
    evaluate_gates,
)
from app.financial.inputs import (
    FinancialValidationError,
    InputSource,
    ProvenanceEntry,
    ValidationIssue,
    provenance_summary,
    raise_on_errors,
    split_issues,
    validate_financial_input,
)
from app.financial.projection import (
    STRESS_SCENARIOS,
    WhatIfAdjustments,
    apply_shock,
    apply_what_if,
    build_monthly_forecast,
    cash_profile,
    growth_factor,
    normalise_seasonality,
    run_stress_scenarios,
    seasonality_or_flat,
)

__all__ = [
    "RUPEE",
    "FINANCING_RECONCILED_TOLERANCE",
    "ProductItem",
    "OpexBreakdown",
    "WorkingCapitalConfig",
    "CanonicalFinancialInput",
    "CanonicalFinancialResult",
    "InputSource",
    "ProvenanceEntry",
    "ValidationIssue",
    "FinancialValidationError",
    "GateBenchmark",
    "DEFAULT_GATE_BENCHMARK",
    "WhatIfAdjustments",
    "STRESS_SCENARIOS",
    "compute_emi",
    "build_loan_schedule",
    "resolve_financing",
    "compute_canonical_financials",
    "validate_financial_input",
    "run_what_if",
    "normalise_seasonality",
    "seasonality_or_flat",
    "apply_shock",
    "run_stress_scenarios",
    "assert_financing_reconciles",
]


RUPEE = "₹"

FINANCING_RECONCILED_TOLERANCE = 1.0


@dataclass
class ProductItem:
    name: str
    units_per_month: float
    selling_price: float
    variable_cost_per_unit: float = 0.0


@dataclass
class OpexBreakdown:
    rent: float = 0.0
    salaries: float = 0.0
    electricity: float = 0.0
    transport: float = 0.0
    maintenance: float = 0.0
    marketing: float = 0.0
    insurance: float = 0.0
    admin: float = 0.0
    other: float = 0.0

    @property
    def total_monthly_opex(self) -> float:
        return round(
            self.rent + self.salaries + self.electricity + self.transport +
            self.maintenance + self.marketing + self.insurance + self.admin + self.other,
            2
        )


@dataclass
class WorkingCapitalConfig:
    inventory_days: int = 10
    receivable_days: int = 7
    payable_days: int = 14
    assumptions_source: str = "Business Template Default"


@dataclass
class CanonicalFinancialInput:
    """
    business_type: identifier for the business template.
    products:      one or more product/service lines. All revenue and
                   variable cost must be declared here, never assumed
                   as a percentage of revenue.
    opex:          monthly fixed operating expenses.
    own_capital:   margin money the entrepreneur actually has.

    Financing is declared, never inferred:
      total_project_cost  explicit project cost. If omitted, falls back to
                          asset_cost, then to own_capital.
      debt_amount         explicit debt. If omitted the engine raises, and
                          will NOT invent a loan.
      other_funding       grants/family support counted as funding.
      derive_debt_from_scheme
                          opt-in. When True and debt_amount is omitted,
                          debt is derived from scheme_financing_rate
                          against the funding gap. Off by default.
    """
    business_type: str
    products: List[ProductItem]
    opex: OpexBreakdown
    own_capital: float

    total_project_cost: Optional[float] = None
    debt_amount: Optional[float] = None
    other_funding: float = 0.0
    derive_debt_from_scheme: bool = False

    scheme_contribution_rate: float = 0.10
    scheme_financing_rate: float = 0.90
    scheme_ceiling: Optional[float] = None
    scheme_name: Optional[str] = None
    eligible_subsidy: float = 0.0
    asset_cost: float = 0.0
    salvage_value: float = 0.0
    useful_life_years: float = 10.0
    interest_rate_annual_pct: float = 9.0
    tenure_months: int = 60
    moratorium_months: int = 0
    working_capital_cfg: WorkingCapitalConfig = field(default_factory=WorkingCapitalConfig)
    tax_rate_pct: Optional[float] = None
    discount_rate_pct: float = 10.0
    npv_horizon_years: int = 5

    # ── 6.1 Seasonality, growth and operating calendar ──────────────────────
    # All of the fields below default to the behaviour the engine had before
    # they existed: no seasonality, no growth, 12 even months. That is
    # deliberate. A default that quietly changed annual revenue would silently
    # invalidate every figure already published.
    operating_days_per_month: int = 30
    #: Twelve monthly demand factors, e.g. [1.1, 0.9, ...]. Rescaled to mean
    #: 1.0 by `normalise_seasonality`, so it redistributes demand across the
    #: year without changing the annual total.
    seasonality_index: Optional[List[float]] = None
    annual_price_growth_pct: float = 0.0
    annual_volume_growth_pct: float = 0.0
    annual_variable_cost_growth_pct: float = 0.0
    annual_fixed_cost_growth_pct: float = 0.0

    #: Cash on hand when the business starts trading. Working capital committed
    #: at commencement is not inside the declared project cost, so this is what
    #: absorbs it; 0 means the funding stack has been fully committed to assets.
    opening_cash_balance: float = 0.0

    #: How many months the 12-month projection should cover. Kept at 12 because
    #: the projection is a first-year cash plan, not a life-of-business model.
    projection_months: int = 12

    # ── Input typing and provenance ─────────────────────────────────────────
    #: field name -> provenance. Accepts a bare InputSource value or a dict with
    #: `source`, `as_of`, `note` and `freshness_days`. See app.financial.inputs.
    field_provenance: Dict[str, Any] = field(default_factory=dict)
    #: Fields whose values contradict each other, e.g. a declared project cost
    #: below the declared own capital. Reported in confidence; never resolved
    #: by the engine, because choosing which figure is right is the caller's
    #: decision and not an arithmetic one.
    conflicting_fields: List[str] = field(default_factory=list)

    #: Thresholds the decision gates are measured against. Left None, the
    #: engine uses DEFAULT_GATE_BENCHMARK, whose values are stated in the
    #: output as model assumptions rather than as any lender's rule.
    gate_benchmark: Optional[Any] = None

    #: When True, an input that cannot be interpreted (negative price, 40-day
    #: month) raises FinancialValidationError instead of being computed around.
    #: Off by default so that historical callers, which pass placeholder zeros
    #: for unmodelled fields, keep working; those zeros surface as warnings and
    #: reduce confidence instead of crashing a live endpoint.
    strict_validation: bool = False

    #: When False, the stress matrix and the monthly projection are skipped.
    #: Exists for the rare bulk path that only needs the headline figures; the
    #: default keeps every output populated.
    include_scenarios: bool = True


@dataclass
class CanonicalFinancialResult:
    # 6.1 Revenue & 6.2 Variable Costs
    monthly_revenue: float
    annual_revenue: float
    monthly_variable_costs: float
    annual_variable_costs: float

    # 6.3 COGS & 6.4 Gross Profit
    monthly_cogs: float
    annual_cogs: float
    monthly_gross_profit: float
    annual_gross_profit: float
    gross_margin_pct: float

    # 6.5 Operating Expenses & 6.6 EBITDA
    monthly_opex: float
    annual_opex: float
    monthly_ebitda: float
    annual_ebitda: float

    # 6.7 Depreciation & 6.8 EBIT
    monthly_depreciation: float
    annual_depreciation: float
    monthly_ebit: float
    annual_ebit: float

    # 6.9 Interest & 6.10 Tax & 6.11 PAT
    monthly_interest: float
    annual_interest: float
    monthly_pbt: float
    annual_pbt: float
    tax_status: str
    monthly_tax: float
    annual_tax: float
    monthly_pat: float
    annual_pat: float
    # Net margin, i.e. PAT as a share of revenue. This is AFTER interest, tax and
    # depreciation, unlike gross_margin_pct. Callers previously re-derived this
    # from pat/revenue in three separate places, which is how net_margin = roi/12
    # and a gross-margin figure both ended up labelled "net margin".
    net_margin_pct: float

    # 6.13 Working Capital & 6.14 Cash Conversion Cycle
    inventory_requirement: float
    receivables_requirement: float
    payables_requirement: float
    net_working_capital: float
    cash_conversion_cycle_days: int

    # 6.12 Operating Cash Flow
    monthly_operating_cash_flow: float
    annual_operating_cash_flow: float
    cfads_monthly: float
    cfads_annual: float

    # 6.15 Project Cost & 6.16 Loan Amount
    total_project_cost: float
    own_capital: float
    other_funding: float
    eligible_subsidy: float
    debt_amount: float
    funding_gap_before_debt: float
    financing_gap: float
    financing_reconciled: bool
    modeled_loan_requirement: float
    approved_loan_amount: float
    debt_service_status: str

    # 6.17 EMI & 6.18 Debt Service & 6.19 DSCR
    monthly_emi: float
    annual_debt_service: float
    cash_available_for_debt_service_monthly: float
    dscr: Optional[float]
    dscr_status: str
    total_interest_paid: float
    total_repayment: float
    loan_schedule: List[Dict[str, Any]]

    # 6.20 - 6.23 Unit Economics, Break-even & MOS
    avg_price_per_unit: float
    avg_variable_cost_per_unit: float
    contribution_per_unit: float
    contribution_margin_pct: float
    break_even_units_monthly: Optional[float]
    break_even_revenue_monthly: Optional[float]
    break_even_basis: str
    margin_of_safety_pct: Optional[float]

    # 6.24 Economic viability gate
    #   VIABLE       - every gate evaluated and cleared.
    #   NOT_VIABLE   - at least one gate evaluated and failed. `viability_reasons`
    #                  lists the failures and is never empty in this state.
    #   UNDETERMINED - nothing failed, but at least one gate could not be
    #                  evaluated for want of evidence. `assessability_unknowns`
    #                  says what is missing. This is not a soft NO.
    economic_viability: str
    viability_reasons: List[str]

    # 6.25 ROI. Optional: None when the capital base is unknown, because ROI is a
    # ratio and an unknown denominator cannot yield 0%.
    roi_on_total_project_pct: Optional[float]
    roi_on_owner_equity_pct: Optional[float]

    # 6.26 Payback
    payback_months: Optional[float]
    payback_achieved: bool
    payback_status: str
    payback_undetermined_reason: str

    # 6.27 NPV & 6.28 IRR
    npv: Optional[float]
    npv_horizon_years_used: int
    irr_pct: Optional[float]

    # Cashflow Schedule
    cashflow_projection_12m: List[Dict[str, Any]]
    assumptions_provenance: List[Dict[str, Any]]

    #: What could NOT be assessed, as distinct from `viability_reasons` which
    #: lists what was assessed and failed. An absence of evidence is not evidence
    #: of failure: these entries alone yield UNDETERMINED, never NOT_VIABLE.
    assessability_unknowns: List[str] = field(default_factory=list)

    # ── 6.24 Decision gates ─────────────────────────────────────────────────
    #: Every gate the plan was tested against, with its own status, value,
    #: threshold and reason. Configurable via input.gate_benchmark.
    decision_gates: List[Dict[str, Any]] = field(default_factory=list)
    #: The thresholds used, carried in the output so a reader can disagree with
    #: them. Explicitly model benchmarks, not legal or lender requirements.
    gate_benchmarks: Dict[str, Any] = field(default_factory=dict)

    #: GO | CONDITIONAL | NO_GO | INSUFFICIENT_EVIDENCE, with the reasons,
    #: the conditions that would change it, and what remains unknown.
    financial_status: Dict[str, Any] = field(default_factory=dict)

    #: Confidence in the NUMBERS (band, score, basis). Kept separate from
    #: financial_status on purpose: a well-evidenced loss is high confidence and
    #: a profitable projection on template defaults is low confidence.
    financial_confidence: Dict[str, Any] = field(default_factory=dict)

    # ── 6.12 Forecast ───────────────────────────────────────────────────────
    #: Twelve monthly rows: revenue through to ending cash balance. A
    #: decomposition of the figures above, not an independent estimate.
    monthly_forecast: List[Dict[str, Any]] = field(default_factory=list)
    ending_cash_balance: Optional[float] = None
    minimum_cash_balance: Optional[float] = None
    lowest_cash_month: Optional[int] = None
    months_negative_cash: int = 0
    #: Peak working capital need that the declared funding stack does not cover.
    working_capital_funding_gap: float = 0.0

    # ── Stress ──────────────────────────────────────────────────────────────
    #: Every stress scenario re-run through this same model, keyed by scenario.
    stress_scenarios: Dict[str, Any] = field(default_factory=dict)

    # ── Explainability and provenance ───────────────────────────────────────
    #: Per-metric: value, the formula that produced it, why it matters, and the
    #: module that produced it.
    explainability: Dict[str, Any] = field(default_factory=dict)
    #: Every input with its declared source, so a reader can see which figures
    #: are observed and which are assumed.
    input_provenance: List[Dict[str, Any]] = field(default_factory=list)

    # ── Validation ──────────────────────────────────────────────────────────
    #: ERROR entries mean a value was not interpretable. WARNING entries mean the
    #: engine proceeded on a gap, which is carried into confidence and status.
    validation_issues: List[Dict[str, Any]] = field(default_factory=list)
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)
    validation_warnings: List[Dict[str, Any]] = field(default_factory=list)

    #: Seasons actually applied, after rescaling to mean 1.0, so a reader can
    #: confirm the profile redistributed demand rather than changing its level.
    seasonality_applied: List[float] = field(default_factory=list)
    operating_days_per_month: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def confidence(self) -> Dict[str, Any]:
        """
        Alias for `financial_confidence`.

        The attribute is named `financial_confidence` on the result because a
        field called `confidence` sitting next to a numeric `dscr` invites a
        client to read it as a ratio. Responses that are specced or consumed
        against a flatter shape still look for `confidence`, so it is exposed
        under both names rather than made to be spelled the long way everywhere.
        """
        return self.financial_confidence


def compute_emi(principal: float, annual_rate_pct: float, tenure_months: int,
                moratorium_months: int = 0) -> float:
    """
    Standard reducing-balance EMI. Repayment begins after the moratorium.
    Returns 0.0 when there is no debt or no repayment period. It never raises
    and never invents a loan.
    """
    if principal <= 0:
        return 0.0
    repayment_months = tenure_months - moratorium_months
    if repayment_months <= 0:
        return 0.0
    r = (annual_rate_pct / 100.0) / 12.0
    if r == 0:
        return round(principal / repayment_months, 2)
    factor = (1 + r) ** repayment_months
    return round(principal * r * factor / (factor - 1), 2)


def build_loan_schedule(principal: float, annual_rate_pct: float, tenure_months: int,
                        moratorium_months: int = 0) -> List[Dict[str, Any]]:
    """
    Month-by-month reducing-balance amortisation table.

    During the moratorium interest accrues and is serviced interest-only,
    which is the conservative reading. Every row records the interest and
    principal actually repaid for that month, so total interest over the
    loan life is the sum of the column and total repayment is the sum of EMI.
    """
    if principal <= 0 or tenure_months <= 0:
        return []

    r = (annual_rate_pct / 100.0) / 12.0
    repayment_months = tenure_months - moratorium_months
    emi = compute_emi(principal, annual_rate_pct, tenure_months, moratorium_months)

    schedule: List[Dict[str, Any]] = []
    balance = float(principal)

    for month in range(1, tenure_months + 1):
        interest = round(balance * r, 2)
        in_moratorium = month <= moratorium_months

        if in_moratorium:
            principal_repaid = 0.0
            payment = interest
        elif month == tenure_months or (balance * r) >= emi - 0.01:
            # Final repayment: retire the whole outstanding balance so the
            # loan closes at exactly zero instead of leaving a rounding sliver.
            principal_repaid = round(balance, 2)
            payment = round(interest + principal_repaid, 2)
        else:
            principal_repaid = round(min(balance, max(0.0, emi - interest)), 2)
            payment = round(interest + principal_repaid, 2)

        opening = round(balance, 2)
        balance = round(balance - principal_repaid, 2)
        if abs(balance) < 0.01:
            balance = 0.0

        schedule.append({
            "month": month,
            "in_moratorium": in_moratorium,
            "opening_balance": opening,
            "interest": interest,
            "principal_repaid": principal_repaid,
            "emi": round(emi, 2) if not in_moratorium else 0.0,
            "payment": payment,
            "closing_balance": balance,
        })

    return schedule


def resolve_financing(inp: "CanonicalFinancialInput") -> Dict[str, Any]:
    """
    Resolve project cost and debt WITHOUT manufacturing either.

    project_cost:  explicit total_project_cost, else asset_cost, else own_capital.
    debt:          explicit debt_amount, else scheme-derived ONLY when
                   derive_debt_from_scheme is explicitly enabled.
    financing_gap: project_cost - own_capital - other_funding - subsidy - debt.
    """
    if inp.total_project_cost is not None:
        project_cost = float(inp.total_project_cost)
    elif inp.asset_cost > 0:
        project_cost = float(inp.asset_cost)
    else:
        project_cost = float(inp.own_capital)

    project_cost = max(0.0, project_cost)
    funding_available = inp.own_capital + inp.other_funding + inp.eligible_subsidy
    funding_gap_before_debt = round(max(0.0, project_cost - funding_available), 2)

    if inp.debt_amount is not None:
        debt = float(inp.debt_amount)
    elif inp.derive_debt_from_scheme:
        # The scheme funds the actual shortfall, capped at its ceiling. It does
        # not lend a fixed percentage of whatever project cost was declared:
        # that manufactures debt the promoter has no claim on and cannot
        # necessarily service.
        debt = funding_gap_before_debt
    else:
        debt = 0.0

    debt = max(0.0, debt)
    if inp.scheme_ceiling is not None:
        debt = min(debt, float(inp.scheme_ceiling))

    financing_gap = round(
        project_cost - inp.own_capital - inp.other_funding
        - inp.eligible_subsidy - debt, 2
    )
    financing_gap = round(financing_gap, 2)

    return {
        "total_project_cost": round(project_cost, 2),
        "debt_amount": round(debt, 2),
        "funding_gap_before_debt": funding_gap_before_debt,
        "financing_gap": financing_gap,
        "financing_reconciled": abs(financing_gap) <= FINANCING_RECONCILED_TOLERANCE,
    }


def _solve_irr(cashflows: List[float]) -> Optional[float]:
    """
    Bisection IRR over the cashflow vector. Returns None when the flows
    never change sign, because an IRR is undefined in that case and must
    not be faked.
    """
    if not cashflows or not any(cf > 0 for cf in cashflows) or not any(cf < 0 for cf in cashflows):
        return None

    def npv_at(rate: float) -> float:
        return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cashflows))

    low, high = -0.9999, 10.0
    npv_low, npv_high = npv_at(low), npv_at(high)
    if npv_low * npv_high > 0:
        return None

    for _ in range(200):
        mid = (low + high) / 2
        npv_mid = npv_at(mid)
        if abs(npv_mid) < 1e-6:
            return round(mid * 100, 2)
        if npv_low * npv_mid < 0:
            high, npv_high = mid, npv_mid
        else:
            low, npv_low = mid, npv_mid

    return round(((low + high) / 2) * 100, 2)


def compute_canonical_financials(inp: CanonicalFinancialInput) -> CanonicalFinancialResult:
    # ── Input validation ───────────────────────────────────────────────────
    # Runs before any arithmetic. Nothing here is corrected: an input that
    # cannot be interpreted is either raised (strict mode) or carried as an
    # issue that reduces confidence and feeds the financial status.
    issues: List[ValidationIssue] = validate_financial_input(inp)
    if inp.strict_validation:
        raise_on_errors(issues)
    split = split_issues(issues)
    provenance = provenance_summary(inp.field_provenance)

    # 6.1 Revenue & 6.2 Variable Costs
    tot_revenue_m = sum(p.units_per_month * p.selling_price for p in inp.products)
    tot_var_cost_m = sum(p.units_per_month * p.variable_cost_per_unit for p in inp.products)
    tot_units_m = sum(p.units_per_month for p in inp.products)

    tot_revenue_a = tot_revenue_m * 12.0
    tot_var_cost_a = tot_var_cost_m * 12.0

    # 6.3 COGS & 6.4 Gross Profit
    cogs_m = tot_var_cost_m
    cogs_a = tot_var_cost_a

    gross_profit_m = tot_revenue_m - cogs_m
    gross_profit_a = tot_revenue_a - cogs_a
    gross_margin_pct = (gross_profit_m / tot_revenue_m * 100.0) if tot_revenue_m > 0 else 0.0

    # 6.5 Operating Expenses & 6.6 EBITDA
    opex_m = inp.opex.total_monthly_opex
    opex_a = opex_m * 12.0

    ebitda_m = gross_profit_m - opex_m
    ebitda_a = gross_profit_a - opex_a

    # 6.7 Depreciation & 6.8 EBIT
    if inp.useful_life_years > 0 and inp.asset_cost > 0:
        depreciation_a = max(0.0, inp.asset_cost - inp.salvage_value) / inp.useful_life_years
    else:
        depreciation_a = 0.0
    depreciation_m = depreciation_a / 12.0

    ebit_m = ebitda_m - depreciation_m
    ebit_a = ebitda_a - depreciation_a

    # 6.15 Project Cost & 6.16 Loan Amount
    fin = resolve_financing(inp)
    total_project_cost = fin["total_project_cost"]
    debt = fin["debt_amount"]

    # 6.17 EMI & 6.18 Debt Service
    monthly_emi = compute_emi(debt, inp.interest_rate_annual_pct, inp.tenure_months,
                              inp.moratorium_months)
    loan_schedule = build_loan_schedule(debt, inp.interest_rate_annual_pct,
                                        inp.tenure_months, inp.moratorium_months)
    total_interest_paid = round(sum(r["interest"] for r in loan_schedule), 2)
    total_repayment = round(sum(r["payment"] for r in loan_schedule), 2)

    # Annual debt service is the sum of ACTUAL payments in year one, not
    # `emi * 12`. During a moratorium the monthly payment is interest-only, so
    # multiplying the EMI by twelve overstated the first-year outflow - and, more
    # seriously, overstated it in the same direction as the interest-only period
    # for a business that is not yet generating cash.
    year1_payments = loan_schedule[:12]
    annual_debt_service = round(sum(r["payment"] for r in year1_payments), 2)
    first_year_principal = round(sum(r["principal_repaid"] for r in year1_payments), 2)

    # 6.9 Interest from the actual amortisation schedule, not a flat
    # approximation on the original principal.
    year1_interest = round(sum(r["interest"] for r in year1_payments), 2)
    if loan_schedule:
        monthly_interest = round(year1_interest / 12.0, 2)
    else:
        monthly_interest = 0.0
    annual_interest = year1_interest

    pbt_m = ebit_m - monthly_interest
    pbt_a = ebit_a - annual_interest

    # 6.10 Tax & 6.11 PAT
    if inp.tax_rate_pct is not None:
        tax_status = "MODELED"
        tax_m = round(max(0.0, pbt_m * (inp.tax_rate_pct / 100.0)), 2)
        tax_a = round(max(0.0, pbt_a * (inp.tax_rate_pct / 100.0)), 2)
    else:
        tax_status = "NOT_MODELED"
        tax_m = 0.0
        tax_a = 0.0

    pat_m = pbt_m - tax_m
    pat_a = pbt_a - tax_a

    # 6.13 Working Capital & 6.14 Cash Conversion Cycle
    wc_cfg = inp.working_capital_cfg
    inv_req = (cogs_a / 365.0) * wc_cfg.inventory_days
    rec_req = (tot_revenue_a / 365.0) * wc_cfg.receivable_days
    pay_req = (cogs_a / 365.0) * wc_cfg.payable_days
    net_working_capital = round(inv_req + rec_req - pay_req, 2)
    ccc = wc_cfg.inventory_days + wc_cfg.receivable_days - wc_cfg.payable_days

    # 6.12 Operating Cash Flow
    # Working capital is a real cash requirement, funded at commencement.
    # It is deducted from the cash flow rather than computed and ignored.
    monthly_wc_outlay = net_working_capital
    monthly_ocf = round(pat_m + depreciation_m, 2)
    annual_ocf = round(pat_a + depreciation_a, 2)
    cfads_m = round(ebitda_m - tax_m, 2)
    cfads_a = round(ebitda_a - tax_a, 2)

    # 6.19 DSCR
    cash_available_for_debt_service_monthly = cfads_m
    if debt > 0 and year1_payments:
        # DSCR is measured against the debt service ACTUALLY due in the first
        # year. Using the EMI during a moratorium would compare a full
        # principal-and-interest obligation against a period in which only
        # interest is payable, understating coverage precisely when the business
        # is under most strain.
        if annual_debt_service > 0:
            if cfads_a > 0:
                dscr = round(cfads_a / annual_debt_service, 2)
                dscr_status = "COMPUTED"
            else:
                # DSCR is a RATIO. When the numerator is negative it has no
                # financial meaning, and it moves backwards: a higher EMI
                # (e.g. from a rate rise) pushes a negative ratio CLOSER to
                # zero, so a rate hike would appear to IMPROVE coverage on a
                # business that is losing money. Reporting a negative DSCR
                # therefore creates a figure that is both unreadable and
                # directionally wrong. Cash coverage is reported instead.
                dscr = None
                dscr_status = "NEGATIVE_CFADS"
        else:
            dscr = None
            dscr_status = "NOT_COMPUTABLE"
        debt_service_status = "ACTIVE"
    else:
        dscr = None
        dscr_status = "NOT_APPLICABLE_NO_DEBT"
        debt_service_status = "NO_DEBT"

    # 6.20 Contribution & 6.21 Break-even
    avg_price = (tot_revenue_m / tot_units_m) if tot_units_m > 0 else 0.0
    avg_var_cost = (tot_var_cost_m / tot_units_m) if tot_units_m > 0 else 0.0
    contrib_unit = round(avg_price - avg_var_cost, 2)
    contrib_margin_pct = (contrib_unit / avg_price * 100.0) if avg_price > 0 else 0.0

    # Break-even is a CASH question, so it is measured against cash fixed costs.
    # Depreciation is a non-cash accounting charge: including it inflated
    # break-even by the whole depreciation line and understated margin of safety
    # for every asset-heavy business. It is reported separately for the reader
    # who wants the accounting view.
    total_cash_fixed_m = opex_m
    total_fixed_incl_dep_m = opex_m + depreciation_m

    viability_reasons: List[str] = []
    #: Things that could NOT be assessed, kept separate from `viability_reasons`.
    #: An absence of evidence is not evidence of failure, so these never produce
    #: a NOT_VIABLE; they produce UNDETERMINED on their own.
    assessability_unknowns: List[str] = []
    # (declared on the dataclass below, after the non-default fields)

    if contrib_unit <= 0:
        be_units_m = None
        be_rev_m = None
        mos_pct = None
        viability_reasons.append(
            f"Contribution per unit is {RUPEE}{contrib_unit}: selling price "
            f"{RUPEE}{round(avg_price, 2)} does not cover variable cost "
            f"{RUPEE}{round(avg_var_cost, 2)}. No sales volume can ever cover fixed costs."
        )
    else:
        be_units_m = round(total_cash_fixed_m / contrib_unit, 1)
        be_rev_m = round(total_cash_fixed_m / (contrib_margin_pct / 100.0), 2) if contrib_margin_pct > 0 else None
        mos_pct = round(((tot_revenue_m - be_rev_m) / tot_revenue_m) * 100.0, 2) \
            if (tot_revenue_m > 0 and be_rev_m is not None) else None

    if tot_revenue_m <= 0:
        viability_reasons.append("Monthly revenue is zero; there is no modelled demand.")
    elif ebitda_m <= 0:
        viability_reasons.append(
            f"EBITDA is {RUPEE}{round(ebitda_m, 2)} per month. Revenue does not cover "
            f"variable cost plus fixed operating expenses."
        )
    if be_units_m is not None and tot_units_m > 0 and be_units_m > tot_units_m:
        viability_reasons.append(
            f"Break-even requires {be_units_m} units/month but only {round(tot_units_m, 1)} "
            f"are modelled as achievable."
        )
    if debt > 0 and dscr is not None and dscr < 1.0:
        viability_reasons.append(
            f"Modeled DSCR {dscr}x is below 1.0; modelled operating cash does not cover "
            f"modelled debt service."
        )
    if debt > 0 and dscr_status == "NEGATIVE_CFADS":
        # Reported instead of a negative DSCR, which would be directionally wrong.
        annual_deficit = abs(cfads_a)
        coverage_share = (cfads_a / annual_debt_service * 100.0) if annual_debt_service > 0 else 0.0
        viability_reasons.append(
            f"Operating cash is negative by {RUPEE}{round(annual_deficit, 2)} a year while "
            f"{RUPEE}{round(annual_debt_service, 2)} of debt service falls due, so the business "
            f"must fund {round(abs(coverage_share), 1)}% of its own repayments from other sources."
        )
    if not fin["financing_reconciled"]:
        viability_reasons.append(
            f"Financing does not reconcile: unfunded gap of {RUPEE}"
            f"{abs(fin['financing_gap'])}."
        )

    if total_project_cost is None or total_project_cost <= 0:
        # Cost economics can pass while the plan is still unjudgeable: without a
        # capital requirement there is no ROI, no payback, no NPV, and no way to
        # know whether the entrepreneur's capital is sufficient. Neither VIABLE
        # nor NOT_VIABLE is honest here. Both are conclusions about a business
        # nobody has costed: "we could not check" and "we checked and it fails"
        # are different statements, and the only evidence we hold is the first.
        # This previously appended to viability_reasons and returned NOT_VIABLE,
        # so an uncosted business was reported as a proven failure - which tells a
        # bank officer to reject a business for the crime of not having been
        # costed yet.
        assessability_unknowns.append(
            "The capital requirement is unknown, so return on capital, payback and net present "
            "value cannot be assessed. Unit economics can be positive while the business is "
            "still unaffordable to start."
        )

    if dscr is None and debt > 0 and dscr_status not in ("NEGATIVE_CFADS",):
        assessability_unknowns.append(
            f"Repayment capacity could not be expressed as a ratio (status: {dscr_status})."
        )

    economic_viability = (
        "NOT_VIABLE" if viability_reasons
        else ("UNDETERMINED" if assessability_unknowns else "VIABLE")
    )

    # 6.25 ROI
    # ROI is Optional. When the capital requirement is unknown, ROI is unknown.
    # Returning 0.0 made "we do not know what this business costs to start" render
    # as "this business earns nothing", which is a different and much harsher
    # statement than the truth.
    roi_project = (
        round(pat_a / total_project_cost * 100.0, 2) if total_project_cost > 0 else None
    )
    roi_equity = (
        round(pat_a / inp.own_capital * 100.0, 2) if inp.own_capital > 0 else None
    )

    # NPV, IRR and payback are all measured against money that was spent up front.
    # When the capital requirement is unknown they cannot be computed at all, and
    # the engine must say so rather than substitute a project cost of zero: NPV
    # computed against a zero outlay is simply the discounted sum of the inflows,
    # so an uncosted business published a five-figure "NPV" in the same response
    # that stated the capital requirement was unknown. The three figures are
    # withheld together, and the reason is already in assessability_unknowns.
    capital_known = total_project_cost is not None and total_project_cost > 0

    # 6.26 Payback on owner's outlay, using the real amortisation schedule
    # and including the working capital actually committed at commencement.
    owner_outlay = inp.own_capital + inp.other_funding + net_working_capital
    cumulative = -owner_outlay
    payback_month = None
    cashflow_proj: List[Dict[str, Any]] = []
    schedule_by_month = {r["month"]: r for r in loan_schedule}

    # The projection must run at least as long as the debt. A hardcoded 60-month
    # loop silently ignored months 61-84 of a 7-year PMEGP loan, so the tail of
    # the repayment never reduced cumulative cash and payback looked shorter
    # than it is.
    projection_months = max(60, inp.tenure_months, 1)
    undetermined_reason = (
        f"Cumulative owner cash did not turn positive within {projection_months} months. "
        f"Payback is undetermined within the modelled horizon, not zero."
    )

    for m in range(1, projection_months + 1):
        row = schedule_by_month.get(m)
        # Only PRINCIPAL is deducted here. `pat_m` has already had interest
        # deducted when it was derived from PBT, so subtracting the full payment
        # charged the borrower interest twice in every month of the loan - which
        # understated cash flow and overstated payback.
        principal_due = row["principal_repaid"] if row else 0.0
        net_cash = round(pat_m + depreciation_m - principal_due, 2)
        cumulative = round(cumulative + net_cash, 2)

        if m <= 12:
            cashflow_proj.append({
                "month": m,
                "revenue": round(tot_revenue_m, 2),
                "cogs": round(cogs_m, 2),
                "opex": round(opex_m, 2),
                "ebitda": round(ebitda_m, 2),
                "interest": row["interest"] if row else 0.0,
                "principal_repaid": principal_due,
                "debt_service": row["payment"] if row else 0.0,
                "net_cash_flow": net_cash,
                "cumulative_cash_flow": cumulative
            })

        if cumulative >= 0 and payback_month is None:
            payback_month = float(m)

    payback_achieved = payback_month is not None
    if not capital_known and payback_month is not None:
        # Without a declared outlay there is no investment to recover, so a
        # "payback" here would be measuring against the applicant's own savings
        # rather than against what the business costs. Withheld with the others.
        payback_month = None
        payback_achieved = False
        payback_status = "NOT_COMPUTABLE_NO_PROJECT_COST"
    else:
        payback_status = "ACHIEVED" if payback_achieved else "NOT_ACHIEVED_IN_HORIZON"

    # 6.27 NPV & 6.28 IRR
    #
    discount_r = inp.discount_rate_pct / 100.0
    # The horizon must cover the full loan life. A 5-year default against a
    # 7-year PMEGP or 84-month NSFDC term truncated the schedule, so the final
    # two years of repayments vanished and both NPV and IRR were overstated -
    # the NPV most, because the omitted outflows are the ones still outstanding.
    debt_years = math.ceil(inp.tenure_months / 12) if inp.tenure_months > 0 else 0
    horizon = max(1, inp.npv_horizon_years, debt_years)
    horizon_extended = horizon > inp.npv_horizon_years

    yearly_cf = []
    for year in range(horizon):
        months = [schedule_by_month.get(year * 12 + m) for m in range(1, 13)]
        service = sum(r["payment"] for r in months if r) if months else 0.0
        # `annual_ocf` is PAT + depreciation, and PAT is already net of interest.
        # Subtracting the full payment - principal *and* interest - from that
        # post-interest figure charged the borrower for the same interest twice,
        # once inside PAT and once again in the service line, so every year of the
        # projection was understated by the annual interest and the NPV came out
        # pessimistic by roughly the present value of the loan's interest.
        # The NPV is a project valuation, so it is run unlevered: interest is added
        # back into the operating cash flow and then removed exactly once as part of
        # the debt service. This mirrors the payback loop above, which deducts
        # principal only for the same reason.
        yearly_cf.append(round(annual_ocf + annual_interest - service, 2))

    if capital_known:
        npv = -total_project_cost + sum(
            cf / ((1 + discount_r) ** (t + 1)) for t, cf in enumerate(yearly_cf)
        )
        npv_val = round(npv, 2)
        irr_val = _solve_irr([-total_project_cost] + yearly_cf)
    else:
        # Withheld rather than computed against a zero outlay. See the note where
        # `capital_known` is set.
        npv_val = None
        irr_val = None

    assumptions = [
        {"name": "total_project_cost", "value": round(total_project_cost, 2), "source": "Declared project cost"},
        {"name": "debt_amount", "value": round(debt, 2), "source": "Declared debt" if inp.debt_amount is not None else "No debt declared"},
        {"name": "financing_gap", "value": fin["financing_gap"], "source": "Reconciliation"},
        {"name": "working_capital_inventory_days", "value": wc_cfg.inventory_days, "source": wc_cfg.assumptions_source},
        {"name": "working_capital_receivable_days", "value": wc_cfg.receivable_days, "source": wc_cfg.assumptions_source},
        {"name": "working_capital_payable_days", "value": wc_cfg.payable_days, "source": wc_cfg.assumptions_source},
        {"name": "tax_status", "value": tax_status, "source": "Tax Rule Engine"},
        {"name": "interest_rate_annual_pct", "value": inp.interest_rate_annual_pct, "source": "Loan Terms"},
        {"name": "tenure_months", "value": inp.tenure_months, "source": "Loan Terms"},
        {"name": "moratorium_months", "value": inp.moratorium_months, "source": "Loan Terms"},
        {"name": "npv_horizon_years", "value": horizon, "source": (
            f"Extended from the requested {inp.npv_horizon_years} years to cover the "
            f"{inp.tenure_months}-month loan term. A shorter horizon would drop outstanding "
            f"repayments and overstate NPV."
        ) if horizon_extended else "Requested analysis horizon"},
        {"name": "break_even_basis", "value": "cash_fixed_costs_only", "source": (
            "Break-even is a cash measure, so non-cash depreciation is excluded."
        )},
        {"name": "payback_basis", "value": "owner_outlay_plus_working_capital", "source": (
            "Cumulative owner cash recovers the declared own capital, other funding and the "
            "working capital committed at commencement."
        )},
    ]
    result = CanonicalFinancialResult(

        monthly_revenue=round(tot_revenue_m, 2),
        annual_revenue=round(tot_revenue_a, 2),
        monthly_variable_costs=round(tot_var_cost_m, 2),
        annual_variable_costs=round(tot_var_cost_a, 2),
        monthly_cogs=round(cogs_m, 2),
        annual_cogs=round(cogs_a, 2),
        monthly_gross_profit=round(gross_profit_m, 2),
        annual_gross_profit=round(gross_profit_a, 2),
        gross_margin_pct=round(gross_margin_pct, 2),
        monthly_opex=round(opex_m, 2),
        annual_opex=round(opex_a, 2),
        monthly_ebitda=round(ebitda_m, 2),
        annual_ebitda=round(ebitda_a, 2),
        monthly_depreciation=round(depreciation_m, 2),
        annual_depreciation=round(depreciation_a, 2),
        monthly_ebit=round(ebit_m, 2),
        annual_ebit=round(ebit_a, 2),
        monthly_interest=round(monthly_interest, 2),
        annual_interest=round(annual_interest, 2),
        monthly_pbt=round(pbt_m, 2),
        annual_pbt=round(pbt_a, 2),
        tax_status=tax_status,
        monthly_tax=round(tax_m, 2),
        annual_tax=round(tax_a, 2),
        monthly_pat=round(pat_m, 2),
        annual_pat=round(pat_a, 2),
        net_margin_pct=(
            round(pat_a / tot_revenue_a * 100.0, 2) if tot_revenue_a > 0 else 0.0
        ),
        inventory_requirement=round(inv_req, 2),
        receivables_requirement=round(rec_req, 2),
        payables_requirement=round(pay_req, 2),
        net_working_capital=net_working_capital,
        cash_conversion_cycle_days=ccc,
        monthly_operating_cash_flow=monthly_ocf,
        annual_operating_cash_flow=annual_ocf,
        cfads_monthly=cfads_m,
        cfads_annual=cfads_a,
        total_project_cost=round(total_project_cost, 2),
        own_capital=round(inp.own_capital, 2),
        other_funding=round(inp.other_funding, 2),
        eligible_subsidy=round(inp.eligible_subsidy, 2),
        debt_amount=round(debt, 2),
        funding_gap_before_debt=fin["funding_gap_before_debt"],
        financing_gap=fin["financing_gap"],
        financing_reconciled=fin["financing_reconciled"],
        modeled_loan_requirement=fin["funding_gap_before_debt"],
        approved_loan_amount=round(debt, 2),
        debt_service_status=debt_service_status,
        monthly_emi=monthly_emi,
        annual_debt_service=annual_debt_service,
        cash_available_for_debt_service_monthly=cash_available_for_debt_service_monthly,
        dscr=dscr,
        dscr_status=dscr_status,
        total_interest_paid=total_interest_paid,
        total_repayment=total_repayment,
        loan_schedule=loan_schedule,
        avg_price_per_unit=round(avg_price, 2),
        avg_variable_cost_per_unit=round(avg_var_cost, 2),
        contribution_per_unit=contrib_unit,
        contribution_margin_pct=round(contrib_margin_pct, 2),
        break_even_units_monthly=be_units_m,
        break_even_revenue_monthly=be_rev_m,
        break_even_basis=(
            "Cash break-even: fixed operating expenses only. Depreciation is a non-cash "
            "charge and is excluded, which is why this figure is lower than an accounting "
            "break-even computed on opex plus depreciation."
        ),
        margin_of_safety_pct=mos_pct,
        economic_viability=economic_viability,
        viability_reasons=viability_reasons,
        assessability_unknowns=assessability_unknowns,
        roi_on_total_project_pct=roi_project,
        roi_on_owner_equity_pct=roi_equity,
        payback_months=payback_month,
        payback_achieved=payback_achieved,
        payback_status=payback_status,
        payback_undetermined_reason="" if payback_achieved else undetermined_reason,
        npv=npv_val,
        npv_horizon_years_used=horizon,
        irr_pct=irr_val,
        cashflow_projection_12m=cashflow_proj,
        assumptions_provenance=assumptions
    )

    # ── 6.12 Monthly forecast, ending and minimum cash ─────────────────────
    # A decomposition of the figures above, not a second estimate of them.
    forecast = build_monthly_forecast(inp, result, months=inp.projection_months)
    cash_summary = cash_profile(forecast, opening_cash=inp.opening_cash_balance)
    result.monthly_forecast = forecast
    result.ending_cash_balance = cash_summary["ending_cash_balance"]
    result.minimum_cash_balance = cash_summary["minimum_cash_balance"]
    result.lowest_cash_month = cash_summary["lowest_cash_month"]
    result.months_negative_cash = cash_summary["months_negative_cash"]
    result.working_capital_funding_gap = round(max(0.0, -cash_summary["minimum_cash_balance"]), 2)
    result.seasonality_applied = seasonality_or_flat(inp)
    result.operating_days_per_month = inp.operating_days_per_month

    # ── 6.24 Decision gates and status ─────────────────────────────────────
    benchmark = inp.gate_benchmark or DEFAULT_GATE_BENCHMARK
    ebitda_margin_pct = round(ebitda_m / tot_revenue_m * 100.0, 2) if tot_revenue_m > 0 else None
    gates = evaluate_gates(
        benchmark=benchmark,
        financing_reconciled=fin["financing_reconciled"],
        financing_gap=fin["financing_gap"],
        contribution_margin_pct=contrib_margin_pct if tot_revenue_m > 0 else None,
        ebitda_margin_pct=ebitda_margin_pct,
        break_even_units_monthly=be_units_m,
        modelled_units_monthly=tot_units_m or None,
        monthly_ebitda=ebitda_m,
        monthly_revenue=tot_revenue_m,
        dscr=dscr,
        dscr_status=dscr_status,
        debt_amount=debt,
        roi_on_total_project_pct=roi_project,
        payback_months=payback_month,
        payback_status=payback_status,
        minimum_cash_balance=cash_summary["minimum_cash_balance"],
        project_cost_known=capital_known,
    )
    result.decision_gates = [g.to_dict() for g in gates]
    result.gate_benchmarks = benchmark.to_dict()
    result.financial_status = derive_financial_status(
        gates,
        validation_issues=issues,
        roi_on_total_project_pct=roi_project,
        payback_months=payback_month,
        payback_status=payback_status,
    )

    # ── Confidence in the numbers ──────────────────────────────────────────
    # Separate from the status above: this asks how much weight the figures
    # deserve, not whether the business is worth starting.
    result.financial_confidence = assess_confidence(
        provenance=provenance,
        validation_issues=issues,
        conflicts=inp.conflicting_fields,
    )

    # ── Provenance, validation, explainability ──────────────────────────────
    result.input_provenance = [e.to_dict() for e in provenance.values()]
    result.validation_issues = [i.to_dict() for i in issues]
    result.validation_errors = [i.to_dict() for i in split["errors"]]
    result.validation_warnings = [i.to_dict() for i in split["warnings"]]
    result.explainability = build_explanations(
        monthly_revenue=tot_revenue_m,
        monthly_variable_costs=tot_var_cost_m,
        monthly_opex=opex_m,
        monthly_ebitda=ebitda_m,
        contribution_per_unit=contrib_unit,
        avg_price_per_unit=avg_price,
        break_even_units_monthly=be_units_m,
        operating_days_per_month=inp.operating_days_per_month,
        dscr=dscr,
        dscr_status=dscr_status,
        annual_debt_service=annual_debt_service,
        cfads_annual=cfads_a,
        debt_amount=debt,
        break_even_basis=(
            "Cash break-even excludes depreciation, which is a non-cash charge."
        ),
        roi_on_total_project_pct=roi_project,
        total_project_cost=total_project_cost,
        annual_pat=pat_a,
        payback_months=payback_month,
        payback_status=payback_status,
        net_working_capital=net_working_capital,
        min_cash_balance=cash_summary["minimum_cash_balance"],
    )

    # ── Stress matrix ──────────────────────────────────────────────────────
    # Every scenario is a full re-run of this model with a shocked input, so a
    # stressed figure is produced by identical arithmetic to the base case.
    if inp.include_scenarios:
        result.stress_scenarios = run_stress_scenarios(inp, result)

    return result


def run_what_if(
    inp: CanonicalFinancialInput,
    adj: WhatIfAdjustments,
) -> Dict[str, Any]:
    """
    Re-run the canonical model with user adjustments applied.

    This is a thin, explicit front door onto the same engine - not a separate
    calculator. It returns the base result, the adjusted result, and exactly
    which levers moved, so the interface can show the user what changed instead
    of silently returning different numbers.

    An adjustment that is absent is left at the base value. Nothing is
    defaulted into a change.
    """
    if adj is None or adj.is_empty:
        base = compute_canonical_financials(inp)
        return {
            "applied_adjustments": [],
            "base": base.to_dict(),
            "result": base.to_dict(),
            "delta": {},
            "decision_changed": False,
            "base_decision": base.financial_status["value"],
            "result_decision": base.financial_status["value"],
            "note": "No adjustment was supplied, so the base case is returned unchanged.",
        }

    shocked_input, applied = apply_what_if(inp, adj)
    base = compute_canonical_financials(inp)
    adjusted = compute_canonical_financials(shocked_input)

    def delta(field_name: str) -> Optional[float]:
        b = getattr(base, field_name, None)
        a = getattr(adjusted, field_name, None)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            return round(a - b, 2)
        return None

    return {
        "applied_adjustments": applied,
        "base": base.to_dict(),
        "result": adjusted.to_dict(),
        "delta": {
            "monthly_revenue": delta("monthly_revenue"),
            "monthly_ebitda": delta("monthly_ebitda"),
            "monthly_pat": delta("monthly_pat"),
            "monthly_emi": delta("monthly_emi"),
            "dscr": delta("dscr"),
            "roi_on_total_project_pct": delta("roi_on_total_project_pct"),
            "break_even_units_monthly": delta("break_even_units_monthly"),
            "payback_months": delta("payback_months"),
            "minimum_cash_balance": delta("minimum_cash_balance"),
            "ending_cash_balance": delta("ending_cash_balance"),
        },
        "decision_changed": base.financial_status["value"] != adjusted.financial_status["value"],
        "base_decision": base.financial_status["value"],
        "result_decision": adjusted.financial_status["value"],
        "note": (
            "Recalculated by the canonical engine from the same base input. The dashboard, the "
            "business plan, the report and the AI narration all read this result, so they cannot "
            "disagree with it."
        ),
    }


def assert_financing_reconciles(result: CanonicalFinancialResult) -> None:
    """
    Hard invariant. Raises if the funding stack does not sum to project cost.
    Any module that assembles a financing plan must pass it through here.
    """
    expected = (result.total_project_cost - result.own_capital - result.other_funding
                - result.eligible_subsidy - result.debt_amount)
    if abs(round(expected, 2)) > FINANCING_RECONCILED_TOLERANCE:
        raise ValueError(
            f"Financing does not reconcile: project cost {result.total_project_cost} "
            f"!= own {result.own_capital} + other {result.other_funding} "
            f"+ subsidy {result.eligible_subsidy} + debt {result.debt_amount} "
            f"(gap {result.financing_gap})"
        )
