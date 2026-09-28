"""
Financial engine compatibility layer.

All arithmetic here DELEGATES to app.financial.canonical_engine, which is the
single source of truth. This module exists only to preserve the historical
call signatures used by the API routes, ranking service and tests.

If you are adding a new financial calculation, add it to canonical_engine.py
and call it from here. Do not reimplement financial math in this file.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    ProductItem,
    OpexBreakdown,
    WorkingCapitalConfig,
    build_loan_schedule,
    compute_canonical_financials,
    compute_emi as _canonical_compute_emi,
    normalise_seasonality,
)
from app.engines.scheme_engine import match_scheme

logger = logging.getLogger(__name__)

CONTRIBUTION_PCT = 0.10
FINANCING_PCT = 0.90

# Seasonal demand multipliers by industry (index 0 = January).
# These scale SALES VOLUME only. Fixed costs do not scale with season, and
# variable costs scale with volume, so applying this index to revenue and
# opex together would cancel out and make the index meaningless.
#
# The raw tables below were hand-written with means of 0.958 (dairy) and 0.983
# (poultry). A seasonality profile is supposed to REDISTRIBUTE demand across the
# year, not delete it: a profile averaging 0.958 silently cut a dairy unit's
# modelled annual revenue by 4.2%, and because EBITDA is a small residual of
# revenue minus costs, the same 4.2% produced a far larger proportional error in
# profit. The shape is preserved and the level is corrected by
# `normalise_seasonality` - the canonical engine's own function, not a second
# copy of it, so the tables here and the forecast there cannot disagree about
# what normalisation means.
SEASONAL_INDEX_RAW: dict[str, list[float]] = {
    "dairy":        [1.05, 1.00, 0.95, 0.90, 0.85, 0.80, 0.85, 0.90, 0.95, 1.00, 1.10, 1.15],
    "retail_kirana": [1.10, 0.95, 0.90, 0.95, 0.90, 0.85, 0.90, 0.90, 0.95, 1.10, 1.20, 1.30],
    "tailoring":    [1.15, 0.85, 0.90, 1.05, 0.80, 0.85, 0.90, 0.90, 0.95, 1.20, 1.10, 1.35],
    "flour_mill":   [1.00, 1.00, 0.95, 0.95, 1.05, 1.10, 1.10, 1.05, 1.00, 1.00, 0.95, 0.85],
    "poultry":      [1.10, 1.00, 0.90, 0.85, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.15, 1.25],
}
SEASONAL_DEFAULT = [1.0] * 12


def _revenue_neutral(index: list[float]) -> list[float]:
    """
    Rescale a 12-month seasonal profile so its mean is exactly 1.0.

    Kept as a named alias for the historical import path, but the arithmetic is
    `normalise_seasonality`'s. Two copies of this function would eventually
    disagree, and a seasonality table that means one thing here and another in
    the forecast is invisible until a user compares a revenue line with a
    monthly chart and cannot reconcile them.
    """
    return normalise_seasonality(index)


SEASONAL_INDEX: dict[str, list[float]] = {
    category: _revenue_neutral(profile)
    for category, profile in SEASONAL_INDEX_RAW.items()
}

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]


def compute_project_cost(margin_capital: float) -> float:
    """
    Scheme-quote helper: the project cost implied when the entrepreneur's
    margin is exactly the scheme's minimum contribution (10%).

    This is a SCHEME RULE applied at the point of quoting, not a default
    project cost for the financial engine. The engine itself never infers
    project cost from margin capital. Use only for scheme band routing.
    """
    if margin_capital <= 0:
        raise ValueError("margin_capital must be > 0")
    return margin_capital / CONTRIBUTION_PCT


def compute_loan_amount(project_cost: float, scheme_max_loan: float | None = None,
                        own_contribution: float = 0.0,
                        other_funding: float = 0.0) -> float:
    """
    Debt = project cost - own contribution - other funding, capped at the
    scheme ceiling. Never returns more than the project actually needs, so a
    financing structure always reconciles.
    """
    loan = max(0.0, project_cost - own_contribution - other_funding)
    if scheme_max_loan is not None:
        loan = min(loan, scheme_max_loan)
    return round(loan, 2)


def compute_emi(principal: float, annual_rate_pct: float, tenure_months: int,
                moratorium_months: int = 0) -> float:
    return _canonical_compute_emi(principal, annual_rate_pct, tenure_months, moratorium_months)


def compute_dscr(cash_available_for_debt_service: float, emi: float) -> Optional[float]:
    """
    Returns None when there is no debt service. A business with no loan has
    no DSCR, and reporting a large sentinel number would read as a perfect
    repayment record that was never computed.
    """
    if emi is None or emi <= 0:
        return None
    return round(cash_available_for_debt_service / emi, 2)


def compute_break_even_units(fixed_costs_monthly: float, price_per_unit: float,
                             variable_cost_per_unit: float) -> Optional[float]:
    """
    Units needed to cover fixed costs. Returns None when contribution per
    unit is not positive, because no volume can break even in that case.
    """
    contribution = price_per_unit - variable_cost_per_unit
    if contribution <= 0:
        return None
    return round(fixed_costs_monthly / contribution, 1)


def compute_net_profit(monthly_revenue: float, monthly_fixed_cost: float,
                       monthly_variable_cost: float = 0.0) -> float:
    """
    Operating profit = revenue - variable cost - fixed cost.

    Variable cost must be passed explicitly. It is never inferred as a
    percentage of revenue.
    """
    return round(monthly_revenue - monthly_variable_cost - monthly_fixed_cost, 2)


def compute_roi(net_annual_profit: float, total_investment: float) -> float:
    if total_investment == 0:
        return 0.0
    return round((net_annual_profit / total_investment) * 100, 2)


def compute_cashflow_projection(
    monthly_revenue: float,
    monthly_fixed_cost: float,
    monthly_variable_cost: float,
    emi: float,
    category_id: str,
    moratorium_months: int = 0,
    num_months: int = 12,
) -> List[Dict[str, Any]]:
    """
    Month-by-month cash flow. Seasonality scales sales volume, so revenue and
    variable cost move together while fixed cost does not.
    """
    seasonals = SEASONAL_INDEX.get(category_id, SEASONAL_DEFAULT)
    cumulative = 0.0
    projection = []
    for i in range(num_months):
        month_idx = i % 12
        idx = seasonals[month_idx]
        rev = round(monthly_revenue * idx, 2)
        var = round(monthly_variable_cost * idx, 2)
        fixed = round(monthly_fixed_cost, 2)
        emi_payment = round(emi, 2) if i >= moratorium_months else 0.0
        net = round(rev - var - fixed - emi_payment, 2)
        cumulative = round(cumulative + net, 2)
        projection.append({
            "month": MONTH_NAMES[month_idx],
            "month_num": i + 1,
            "seasonal_index": idx,
            "revenue": rev,
            "variable_cost": var,
            "fixed_cost": fixed,
            "total_expenses": round(var + fixed, 2),
            "emi_payment": emi_payment,
            "net_cash": net,
            "cumulative": cumulative,
        })
    return projection


def compute_pnl_statement(
    monthly_revenue: float,
    monthly_variable_cost: float,
    monthly_fixed_cost: float = 0.0,
    monthly_depreciation: float = 0.0,
    monthly_interest: float = 0.0,
    tax_rate_pct: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Monthly Profit & Loss. Every cost line is passed in explicitly. There is
    no default COGS ratio and no default tax rate, because inventing either
    would silently change the owner's decision.
    """
    revenue = round(monthly_revenue, 2)
    variable = round(monthly_variable_cost, 2)
    fixed = round(monthly_fixed_cost, 2)
    depreciation = round(monthly_depreciation, 2)
    interest = round(monthly_interest, 2)

    gross_profit = round(revenue - variable, 2)
    gross_margin_pct = round((gross_profit / revenue) * 100, 1) if revenue else 0.0
    ebitda = round(gross_profit - fixed, 2)
    ebit = round(ebitda - depreciation, 2)
    pbt = round(ebit - interest, 2)

    if tax_rate_pct is None:
        tax = 0.0
        tax_status = "NOT_MODELED"
    else:
        tax = round(max(0.0, pbt * (tax_rate_pct / 100.0)), 2)
        tax_status = "MODELED"

    net_profit = round(pbt - tax, 2)
    net_margin_pct = round((net_profit / revenue) * 100, 1) if revenue else 0.0

    return {
        "revenue": revenue,
        "cogs": variable,
        "variable_cost": variable,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin_pct,
        "operating_expenses": fixed,
        "ebitda": ebitda,
        "depreciation": depreciation,
        "ebit": ebit,
        "interest": interest,
        "pbt": pbt,
        "tax": tax,
        "tax_status": tax_status,
        "net_profit": net_profit,
        "net_margin_pct": net_margin_pct,
    }


def compute_working_capital(
    monthly_revenue: float,
    monthly_variable_cost: float,
    monthly_fixed_cost: float = 0.0,
    receivable_days: int = 7,
    payable_days: int = 14,
    inventory_days: int = 10,
) -> Dict[str, Any]:
    """
    Net working capital = inventory + receivables - payables, each derived
    from the actual declared revenue and variable cost.
    """
    annual_revenue = monthly_revenue * 12.0
    annual_variable = monthly_variable_cost * 12.0

    inventory_req = round((annual_variable / 365.0) * inventory_days, 2)
    receivables = round((annual_revenue / 365.0) * receivable_days, 2)
    payables = round((annual_variable / 365.0) * payable_days, 2)
    net_wc = round(inventory_req + receivables - payables, 2)

    daily_fixed = round(monthly_fixed_cost / 30.0, 2)
    daily_cash_needed = round(daily_fixed + (monthly_variable_cost / 30.0), 2)

    return {
        "daily_cash_needed": daily_cash_needed,
        "weekly_cash_needed": round(daily_cash_needed * 7, 2),
        "monthly_working_capital": net_wc,
        "net_working_capital": net_wc,
        "inventory_requirement": inventory_req,
        "receivables": receivables,
        "payables": payables,
        "recommended_buffer": round(net_wc * 0.20, 2),
        "receivable_days": receivable_days,
        "payable_days": payable_days,
        "inventory_days": inventory_days,
    }


def compute_revenue_scenarios(
    monthly_revenue: float,
    monthly_variable_cost: float,
    monthly_fixed_cost: float,
    emi: float,
    total_investment: float,
    monthly_interest: float = 0.0,
    monthly_depreciation: float = 0.0,
    effective_tax_rate_pct: float = 0.0,
    variable_cost_elasticity: float = 1.0,
) -> Dict[str, Any]:
    """
    Three revenue scenarios. Variable cost scales with volume by
    `variable_cost_elasticity` (1.0 = fully variable). Fixed cost does not
    scale, which is the whole point of a fixed cost.

    Two different measures are reported, because they are not the same thing
    and conflating them is what made this table disagree with the headline:

      * profit  = EBITDA - depreciation - interest - tax. Principal repayment
        is a financing cash flow, not an expense, so it is excluded. This is
        the basis of the headline PAT and ROI.
      * cash    = EBITDA - EMI - tax, i.e. profit after also servicing
        principal. This is the only figure a payback period may use.

    The `realistic` row reconciles to the headline PAT by construction.
    """
    scenarios = {}
    for label, factor in [("pessimistic", 0.60), ("realistic", 1.00), ("optimistic", 1.30)]:
        rev = round(monthly_revenue * factor, 2)
        var = round(monthly_variable_cost * factor * variable_cost_elasticity, 2)
        fixed = round(monthly_fixed_cost, 2)
        ebitda = round(rev - var - fixed, 2)
        ebit = round(ebitda - monthly_depreciation, 2)
        pbt = round(ebit - monthly_interest, 2)
        tax = round(max(0.0, pbt * (effective_tax_rate_pct / 100.0)), 2)
        profit = round(pbt - tax, 2)
        cash = round(ebitda - emi - tax, 2)
        roi = round((profit * 12 / total_investment) * 100, 1) if total_investment else 0.0
        payback = round(total_investment / cash, 1) if cash > 0 else None
        scenarios[label] = {
            "monthly_revenue": rev,
            "monthly_variable_cost": var,
            "monthly_fixed_cost": fixed,
            "monthly_ebitda": ebitda,
            "monthly_net_profit": profit,
            "monthly_cash_after_debt_service": cash,
            "annual_net_profit": round(profit * 12, 2),
            "roi_pct": roi,
            "payback_months": payback,
        }
    return scenarios


def compute_payback_period(
    monthly_revenue: float,
    monthly_variable_cost: float,
    monthly_fixed_cost: float,
    emi: float,
    total_investment: float,
    category_id: str,
    moratorium_months: int = 0,
    max_months: int = 60,
    interest_rate_annual_pct: float = 0.0,
    outstanding_balance: Optional[float] = None,
    working_capital: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Month in which cumulative net cash recovers the owner's outlay.

    `total_investment` is the owner's outlay EXCLUDING working capital. Working
    capital is added here, exactly once. It used to be added here and again at
    the call site, so the business had to recover its working capital twice
    before payback was recorded - which understated payback on precisely the
    working-capital-intensive businesses where it matters most.

    During a moratorium the loan is interest-only, not interest-free. The
    previous model set the payment to zero for the whole moratorium, so cash
    flow in those months was overstated by the entire interest obligation and
    payback could land inside a period when no principal was actually being
    repaid. Interest is now charged every month the balance is non-zero, and
    principal reduces the balance from the end of the moratorium.
    """
    if working_capital is None:
        working_capital = compute_working_capital(monthly_revenue, monthly_variable_cost)[
            "net_working_capital"
        ]
    total_outlay = total_investment + working_capital

    seasonals = SEASONAL_INDEX.get(category_id, SEASONAL_DEFAULT)
    monthly_rate = (interest_rate_annual_pct / 100.0) / 12.0
    balance = float(outstanding_balance) if outstanding_balance else None

    cumulative = -total_outlay
    payback_month = None
    for i in range(max_months):
        idx = seasonals[i % 12]
        rev = monthly_revenue * idx
        var = monthly_variable_cost * idx

        if i < moratorium_months:
            # Interest-only: interest is payable, principal is not repaid.
            # Without an outstanding balance there is no way to know the
            # interest-only amount, so it is reported as zero and the caller is
            # told the moratorium was not costed rather than being handed a
            # figure that pretends interest does not accrue.
            payment = round(balance * monthly_rate, 2) if balance is not None else 0.0
        else:
            payment = emi
            if balance is not None and emi > 0:
                interest = round(balance * monthly_rate, 2)
                balance = max(0.0, round(balance - max(0.0, emi - interest), 2))

        net = rev - var - monthly_fixed_cost - payment
        cumulative += net
        if cumulative >= 0 and payback_month is None:
            payback_month = i + 1
            break

    return {
        "payback_months": payback_month,
        "payback_achieved": payback_month is not None,
        "payback_status": "ACHIEVED" if payback_month else "NOT_ACHIEVED_IN_HORIZON",
        "total_investment": round(total_investment, 2),
        "net_working_capital": round(working_capital, 2),
        "total_outlay": round(total_outlay, 2),
        "working_capital_counted_once": True,
        "moratorium_interest_costed": balance is not None,
        "note": (
            f"Business recovers its full outlay of Rs {round(total_outlay):,} "
            f"(investment + working capital, counted once) in ~{payback_month} months"
            if payback_month
            else f"Outlay of Rs {round(total_outlay):,} not recovered within "
                 f"{max_months} months at the modelled rate. Payback is undetermined "
                 f"in this horizon, not zero."
        ),
    }


def compute_seasonal_revenue(
    monthly_revenue: float,
    category_id: str,
) -> List[Dict[str, Any]]:
    """
    Twelve months of revenue under this category's seasonal profile.

    This applies the same normalisation the canonical forecast applies, and the
    same single multiplication - revenue is base revenue times the month's
    factor. The two are held together by
    `tests/test_financial_consistency.py::test_seasonal_revenue_matches_the_canonical_forecast_month_for_month`,
    which asserts this table equals the engine's own forecast month for month.
    That test is the right place for the guarantee: asserting it here by running
    a whole extra model pass on every call would make this shim the most
    expensive thing in the request path in order to check arithmetic that is one
    multiplication long.
    """
    profile = normalise_seasonality(SEASONAL_INDEX.get(category_id, SEASONAL_DEFAULT))
    return [
        {
            "month": MONTH_NAMES[i],
            "revenue": round(monthly_revenue * profile[i], 2),
            "index": profile[i],
        }
        for i in range(12)
    ]


@dataclass
class FinancialSnapshot:
    project_cost: float
    loan_amount: float
    contribution: float
    emi: float
    dscr: Optional[float]
    break_even_units: Optional[float]
    net_profit: float
    roi: float


def _normalize_financial_data(setup_costs: Dict, pricing_margins: Dict,
                              monthly_costs: Dict, unit_economics: Dict) -> Dict:
    """
    Map dataset field names into the canonical engine's input shape.
    Every field is read from the dataset. Nothing is defaulted into
    existence, and a missing field returns financial_data_available=False
    rather than a substituted number.
    """
    total_setup = setup_costs.get("total_setup_cost")
    if total_setup is None:
        logger.warning("[FINANCIAL] total_setup_cost missing from dataset")
        return {"financial_data_available": False, "reason": "total_setup_cost missing from dataset"}

    total_fixed = monthly_costs.get("total_fixed_costs")
    if total_fixed is None:
        logger.warning("[FINANCIAL] total_fixed_costs missing from dataset")
        return {"financial_data_available": False, "reason": "total_fixed_costs missing from dataset"}

    margin_pct_raw = pricing_margins.get("average_margin_percentage")
    if margin_pct_raw is None:
        logger.warning("[FINANCIAL] average_margin_percentage missing from dataset")
        return {"financial_data_available": False, "reason": "average_margin_percentage missing from dataset"}
    margin_pct = float(margin_pct_raw) / 100.0

    expected_revenue = unit_economics.get("expected_monthly_revenue")
    variable_costs = unit_economics.get("variable_costs")
    net_operating_income = unit_economics.get("net_operating_income")

    if expected_revenue is None or variable_costs is None or net_operating_income is None:
        logger.warning("[FINANCIAL] unit_economics fields missing from dataset")
        return {"financial_data_available": False, "reason": "unit_economics incomplete in dataset"}

    return {
        "financial_data_available": True,
        "startup_cost": float(total_setup),
        "monthly_fixed_cost": float(total_fixed),
        "gross_margin_pct": margin_pct,
        "expected_monthly_revenue": float(expected_revenue),
        "monthly_variable_cost": float(variable_costs),
        "net_operating_income": float(net_operating_income),
    }


def _units_from_margin(monthly_revenue: float, gross_margin_pct: float) -> Optional[float]:
    """
    Derive a unit-equivalent count from the dataset's own revenue and margin
    so that per-unit economics stay consistent. Returns None when the margin
    is unusable, so callers abstain instead of dividing by zero.
    """
    if gross_margin_pct <= 0 or gross_margin_pct >= 1:
        return None
    return round(monthly_revenue / (1.0 - gross_margin_pct), 1)


def run_financial_engine(
    user_capital: float,
    setup_costs: Dict[str, Any],
    pricing_margins: Dict[str, Any],
    monthly_costs: Dict[str, Any],
    category_id: str,
    unit_economics: Optional[Dict[str, Any]] = None,
    working_capital_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Dataset-driven entry point. Builds a canonical input from the dataset and
    returns the canonical result.

    The project cost is the dataset's declared setup cost. The entrepreneur's
    margin is their own contribution. Debt is whatever the matched scheme
    actually offers against the remaining gap, capped by the scheme ceiling.
    Any residue is reported as an explicit financing gap rather than being
    quietly absorbed.
    """
    if unit_economics is None:
        unit_economics = {}

    normalized = _normalize_financial_data(setup_costs, pricing_margins, monthly_costs, unit_economics)
    if not normalized.get("financial_data_available"):
        return {
            "financial_data_available": False,
            "reason": normalized.get("reason", "Dataset fields missing"),
        }

    project_cost = normalized["startup_cost"]
    expected_revenue = normalized["expected_monthly_revenue"]
    monthly_variable = normalized["monthly_variable_cost"]
    monthly_fixed = normalized["monthly_fixed_cost"]
    dataset_noi = normalized["net_operating_income"]

    own_contribution = min(user_capital, project_cost)
    scheme = match_scheme(project_cost, own_contribution=own_contribution)
    scheme_max_loan = scheme.max_loan if scheme.matched else None

    debt = compute_loan_amount(project_cost, scheme_max_loan, own_contribution=own_contribution)

    rate = scheme.rate if (scheme.matched and scheme.rate is not None) else 10.0
    tenure = (scheme.tenure_years * 12) if (scheme.matched and scheme.tenure_years) else 60
    moratorium = scheme.moratorium_months if scheme.matched else 0

    # Per-unit economics are NOT manufactured.
    #
    # The previous code derived a unit count from the dataset's own revenue
    # (`units = revenue / (1 - margin)`) and then split revenue and cost across
    # that invented count to obtain a "price per unit" and a "cost per unit".
    # The derivation is circular - the units exist only because revenue and
    # margin were known, and adding rounding of the count to 1 decimal made
    # each rupee of per-unit cost wrong by a different amount from each rupee of
    # per-unit price, which is precisely how a rounding artefact becomes a
    # margin error.
    #
    # The dataset states amounts, not volumes, so a single aggregate line is
    # declared. The waterfall arithmetic is exact; the per-unit metrics that
    # depend on a real volume are reported as not applicable instead of being
    # derived from a volume nobody observed.
    products = [ProductItem(
        name=category_id,
        units_per_month=1.0,
        selling_price=expected_revenue,
        variable_cost_per_unit=monthly_variable,
    )]
    unit_metrics_available = False

    # Working capital is cash tied up in the business cycle, not a fixed asset.
    # Including it in `asset_cost` depreciated it across the asset life, which
    # understated depreciation and overstated taxable profit. Only the capital
    # asset base is depreciable, so working capital is computed first and
    # deducted.
    projected_working_capital = compute_working_capital(
        expected_revenue, monthly_variable
    )["net_working_capital"]
    depreciable_asset_base = max(0.0, project_cost - projected_working_capital)

    # One working-capital cycle, declared once and used for both the canonical
    # model and the published working-capital block. Deriving the days twice
    # from two sources is how a summary card ends up quoting a different float
    # from the model that produced it.
    wc_cfg = working_capital_cfg or {}
    inv_days = int(wc_cfg.get("inventory_days", 10))
    out_days = int(wc_cfg.get("payable_days", 14))
    inp_days = int(wc_cfg.get("receivable_days", 7))
    declared_wc = WorkingCapitalConfig(
        inventory_days=inv_days,
        receivable_days=inp_days,
        payable_days=out_days,
    )

    canon_input = CanonicalFinancialInput(
        business_type=category_id,
        products=products,
        opex=OpexBreakdown(other=monthly_fixed),
        own_capital=own_contribution,
        total_project_cost=project_cost,
        debt_amount=debt,
        eligible_subsidy=0.0,
        asset_cost=depreciable_asset_base,
        useful_life_years=10.0,
        interest_rate_annual_pct=rate,
        tenure_months=tenure,
        moratorium_months=moratorium,
        scheme_ceiling=scheme_max_loan,
        scheme_name=scheme.scheme_name,
        derive_debt_from_scheme=False,
        working_capital_cfg=declared_wc,
    )
    res = compute_canonical_financials(canon_input)

    # The dataset states its own net operating income. If the canonical
    # waterfall disagrees with it, that is a data integrity problem and is
    # surfaced rather than hidden.
    noi_variance = round(res.monthly_pat - dataset_noi, 2)

    cashflow_projection = compute_cashflow_projection(
        monthly_revenue=res.monthly_revenue,
        monthly_fixed_cost=res.monthly_opex,
        monthly_variable_cost=res.monthly_cogs,
        emi=res.monthly_emi,
        moratorium_months=moratorium,
        category_id=category_id,
        num_months=12,
    )
    seasonal_revenue = compute_seasonal_revenue(res.monthly_revenue, category_id)
    revenue_scenarios = compute_revenue_scenarios(
        monthly_revenue=res.monthly_revenue,
        monthly_variable_cost=res.monthly_cogs,
        monthly_fixed_cost=res.monthly_opex,
        emi=res.monthly_emi,
        total_investment=project_cost,
        monthly_interest=res.monthly_interest,
        monthly_depreciation=res.monthly_depreciation,
        effective_tax_rate_pct=canon_input.tax_rate_pct or 0.0,
    )
    payback_period = compute_payback_period(
        monthly_revenue=res.monthly_revenue,
        monthly_variable_cost=res.monthly_cogs,
        monthly_fixed_cost=res.monthly_opex,
        emi=res.monthly_emi,
        # Own contribution only. The function adds working capital itself, and
        # passing `res.net_working_capital` here as well made the business
        # recover it twice before payback was recorded.
        total_investment=own_contribution,
        moratorium_months=moratorium,
        category_id=category_id,
        # Reuse the canonical engine's working capital figure so the two
        # engines cannot disagree, and supply the loan terms so moratorium
        # interest is charged instead of waived.
        working_capital=res.net_working_capital,
        interest_rate_annual_pct=rate,
        outstanding_balance=res.debt_amount,
        max_months=max(60, tenure),
    )

    logger.info(
        "[FINANCIAL] project_cost=%.0f debt=%.0f gap=%.0f emi=%.0f DSCR=%s ROI=%.1f%% scheme=%s",
        res.total_project_cost, res.debt_amount, res.financing_gap, res.monthly_emi,
        res.dscr, res.roi_on_total_project_pct, scheme.scheme_name
    )

    return {
        "financial_data_available": True,
        "project_cost": round(res.total_project_cost),
        "user_capital": round(user_capital),
        "own_contribution": round(own_contribution),
        "loan_amount": round(res.debt_amount),
        "financing_gap": res.financing_gap,
        "financing_reconciled": res.financing_reconciled,
        "scheme": scheme.scheme_name,
        "scheme_source_url": scheme.source_url,
        "scheme_explanation": scheme.explanation,
        "interest_rate_pct": rate,
        "tenure_months": tenure,
        "moratorium_months": moratorium,
        "emi": round(res.monthly_emi),
        "monthly_revenue": round(res.monthly_revenue),
        "monthly_opex": round(res.monthly_opex),
        "monthly_cogs": round(res.monthly_cogs),
        "monthly_fixed_cost": round(monthly_fixed),
        "monthly_variable_cost": round(res.monthly_cogs),
        "net_profit": round(res.monthly_pat),
        "gross_margin_pct": round(res.gross_margin_pct, 1),
        # Net margin, not gross. The scoring layer previously received
        # gross_margin_pct as its net-margin input, which overstated viability
        # by the entire operating-expense ratio.
    # Net margin, not gross. The scoring layer previously received
    # gross_margin_pct as its net-margin input, which overstated viability by the
    # entire operating-expense ratio. The value itself is the engine's, passed
    # through below rather than recomputed here.
    "gross_margin_pct": round(res.gross_margin_pct, 1),
        "dscr": res.dscr,
        "dscr_status": res.dscr_status,
        "roi_pct": round(res.roi_on_total_project_pct, 1),
        # Break-even in UNITS requires a real volume. The canonical engine
        # computes it against the single aggregate line, which yields figures
        # like "0.8 units" - arithmetically correct and completely meaningless.
        # It is withheld rather than published; break-even in rupees is the
        # figure that is actually usable here.
        "break_even_units": None if not unit_metrics_available else res.break_even_units_monthly,
        "break_even_monthly_revenue": res.break_even_revenue_monthly,
        "break_even_basis": res.break_even_basis,
        # The engine's margin of safety: how far actual revenue sits above
        # break-even. A client asking for "percent capacity utilisation" and
        # getting break-even divided by revenue-per-100-units is a ratio between
        # two unrelated quantities, which is why the screen no longer shows one.
        "margin_of_safety_pct": res.margin_of_safety_pct,
        "total_repayment": res.total_repayment,
        "total_interest_paid": res.total_interest_paid,
        # The dataset supplies amounts, not volumes, so per-unit figures are
        # reported as not applicable rather than derived from an invented count.
        "unit_metrics_available": unit_metrics_available,
        "unit_metrics_note": (
            "The source dataset states monthly amounts, not a sales volume. Price per unit, "
            "cost per unit and break-even in units are therefore not available. Enter a monthly "
            "volume to obtain them."
        ),
        "depreciable_asset_base": round(depreciable_asset_base, 2),
        "working_capital_excluded_from_depreciation": True,
        "economic_viability": res.economic_viability,
        "viability_reasons": res.viability_reasons,
        "assessability_unknowns": res.assessability_unknowns,
        "net_working_capital": res.net_working_capital,
        "npv": res.npv,
        "npv_horizon_years_used": res.npv_horizon_years_used,
        "irr_pct": res.irr_pct,
        "payback_months": res.payback_months,
        "payback_status": res.payback_status,
        "annual_debt_service": res.annual_debt_service,
        "total_interest_paid": res.total_interest_paid,
        "dataset_net_operating_income": round(dataset_noi, 2),
        "dataset_noi_variance": noi_variance,
        "capital_sufficient": user_capital >= (project_cost * CONTRIBUTION_PCT),
        "cashflow_projection": cashflow_projection,
        "seasonal_revenue": seasonal_revenue,
        "revenue_scenarios": revenue_scenarios,
        "payback_period": payback_period,
        "assumptions_provenance": res.assumptions_provenance,
        # The canonical engine's own verdicts and forward-looking blocks, passed
        # through rather than re-summarised. This entry point used to return the
        # arithmetic and drop the engine's reasoning, so callers had no way to
        # show a gate, a stress case or a cash profile without importing the
        # canonical module and re-running it - which is how two engines end up
        # answering the same question.
        "monthly_ebitda": round(res.monthly_ebitda, 2),
        "monthly_gross_profit": round(res.monthly_gross_profit, 2),
        "monthly_depreciation": round(res.monthly_depreciation, 2),
        "monthly_interest": round(res.monthly_interest, 2),
        "monthly_tax": round(res.monthly_tax, 2),
        # EBIT, PBT and PAT as distinct lines. The P&L screen used to label net
        # profit plus an EMI as "EBIT (earnings before tax)" and print a tax
        # figure that had never been calculated, so the three steps of the
        # waterfall that sit between EBITDA and net profit were missing and a
        # tax of zero was indistinguishable from an unmodelled tax.
        "monthly_ebit": round(res.monthly_ebit, 2),
        "monthly_pbt": round(res.monthly_pbt, 2),
        "monthly_pat": round(res.monthly_pat, 2),
        "tax_status": res.tax_status,
        # The engine's own net margin, not a re-derivation from PAT and revenue
        # at the call site. A client that recomputes it from rounded figures will
        # disagree with the engine in the second decimal, and the two numbers end
        # up on the same screen.
        "net_margin_pct": round(res.net_margin_pct, 1),
        "operating_days_per_month": res.operating_days_per_month,
        # The working-capital block is assembled from the canonical result, not
        # from a second private calculation. `compute_working_capital` is still
        # used above for the depreciable asset base, but the published block
        # reports what the model actually used, so a screen cannot disagree with
        # the payback and cash figures built from it.
        #
        # Daily and weekly cash are the operating cash *flow* per day and per
        # week. They are not net_working_capital divided by a month: net working
        # capital is a stock of cash tied up in the cycle, while the daily figure
        # is the day's cash out and back. Conflating them was one of the
        # substitutions the client used to make. The day count is the declared
        # one, not a literal 30.
        "working_capital": {
            "monthly_working_capital": res.net_working_capital,
            "net_working_capital": res.net_working_capital,
            "inventory_requirement": res.inventory_requirement,
            "receivables": res.receivables_requirement,
            "payables": res.payables_requirement,
            "cash_conversion_cycle_days": res.cash_conversion_cycle_days,
            "receivable_days": inp_days,
            "payable_days": out_days,
            "inventory_days": inv_days,
            "daily_cash_needed": round(
                res.monthly_operating_cash_flow / res.operating_days_per_month, 2
            ),
            # A week is seven days of trading, not a seventh of the month.
            "weekly_cash_needed": round(
                res.monthly_operating_cash_flow / res.operating_days_per_month * 7.0, 2
            ),
            "recommended_buffer": round(res.net_working_capital * 0.20, 2),
        },
        "contribution_per_unit": res.contribution_per_unit if unit_metrics_available else None,
        "minimum_cash_balance": res.minimum_cash_balance,
        "ending_cash_balance": res.ending_cash_balance,
        "months_negative_cash": res.months_negative_cash,
        "working_capital_funding_gap": res.working_capital_funding_gap,
        "monthly_forecast": res.monthly_forecast,
        "stress_scenarios": res.stress_scenarios,
        "decision_gates": res.decision_gates,
        "gate_benchmarks": res.gate_benchmarks,
        "financial_status": res.financial_status,
        "financial_confidence": res.financial_confidence,
        "explainability": res.explainability,
        "input_provenance": res.input_provenance,
        "validation_issues": res.validation_issues,
        "loan_schedule": res.loan_schedule,
    }
