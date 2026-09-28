"""
Monthly projection, stress scenarios and what-if adjustments.

Part of the canonical engine (app.financial.*).

The central invariant of this module: the 12-month forecast is a DECOMPOSITION
of the engine's own monthly base, not a parallel estimate of it. Revenue,
variable cost and fixed cost per month are the base figures the engine already
computed, scaled by the declared seasonality profile and growth rates. With no
seasonality and no growth the twelve months therefore sum back to the annual
figures exactly, which is asserted in the test suite. A forecast that could
drift from the headline is a second engine, and there is only one engine here.

Stress scenarios and what-if adjustments are both implemented as a
transformation of the INPUT followed by a full re-run of the model. Nothing is
approximated from a summary, so a stressed figure is produced by identical
arithmetic to the base case and is directly comparable to it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.financial.canonical_engine import (
        CanonicalFinancialInput,
        CanonicalFinancialResult,
        ProductItem,
    )

MONTH_NAMES = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

#: Days in a month used for daily conversions. 30 is the convention; the
#: entrepreneur's own declared operating days are used wherever they are given.
DAYS_PER_MONTH = 30.0
DAYS_PER_YEAR = 365.0


# ── Seasonality ──────────────────────────────────────────────────────────────

def normalise_seasonality(index: Optional[List[float]]) -> List[float]:
    """
    Rescale a 12-month profile so its mean is exactly 1.0.

    A seasonality profile REDISTRIBUTES demand across the year; it does not
    forecast the level of it. A profile averaging 0.958 silently removes 4.2%
    of a year's revenue, and because EBITDA is a small residual of revenue minus
    costs, that same 4.2% produces a much larger proportional error in profit.
    Dividing by the mean preserves the shape - which months are strong, which
    are weak - while guaranteeing that twelve months reproduce the annual
    figure the engine was given.

    A flat profile is returned only for `None`, which means "no seasonality was
    declared". A profile that WAS declared but is unusable - the wrong length, a
    non-number, a month at or below zero - raises instead. Falling back to flat
    would be a silent correction: the caller would see twelve even months and
    have no way to know their profile had been discarded. Validation reports the
    problem as an error; the engine then declines to model seasonality rather
    than quietly modelling something the caller did not ask for.
    """
    if index is None:
        return [1.0] * 12
    if not isinstance(index, (list, tuple)) or len(index) != 12:
        raise ValueError(
            f"A seasonality profile needs exactly 12 monthly factors, got "
            f"{len(index) if hasattr(index, '__len__') else type(index).__name__}."
        )
    try:
        values = [float(v) for v in index]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Seasonality factors must all be numbers: {exc}") from exc
    bad = [(m, v) for m, v in enumerate(values, start=1) if v <= 0]
    if bad:
        # A month with zero or negative demand cannot be modelled, and clipping it
        # to a small positive number would invent demand for that month.
        month, value = bad[0]
        raise ValueError(
            f"Month {month} seasonality factor is {value}. A month with zero or negative "
            "demand cannot be modelled."
        )
    mean = sum(values) / len(values)
    if mean <= 0:
        raise ValueError("A seasonality profile cannot have a non-positive mean.")
    factors = [round(v / mean, 6) for v in values]
    # Rounding each factor to 6 decimal places leaves the twelve months summing
    # to 12.000001 or 11.999999 rather than 12, which means the forecast stops
    # reconciling to the annual headline by a fraction of a rupee. The residual
    # is folded into the largest month so the invariant holds exactly. It is put
    # on the largest month because that is where a rounding correction is least
    # visible, not on the smallest, where it could turn a positive factor into a
    # negative one.
    residual = round(12.0 - sum(factors), 6)
    if residual:
        peak = max(range(len(factors)), key=lambda i: factors[i])
        factors[peak] = round(factors[peak] + residual, 6)
    return factors


def seasonality_or_flat(inp: "CanonicalFinancialInput") -> List[float]:
    """
    Seasonality for the forecast, or a flat profile when the declared one is
    unusable.

    The refusal to use a bad profile is not silent: `validate_financial_input`
    has already recorded a `seasonality_index` error, and that error travels in
    `validation_errors` on the result. This is the difference between declining
    to model something and quietly substituting something else.
    """
    try:
        return normalise_seasonality(getattr(inp, "seasonality_index", None))
    except ValueError:
        return [1.0] * 12


def growth_factor(annual_pct: float, month_index: int) -> float:
    """
    Compounded factor for month `month_index` (1-based) at an annual rate.

    Growth compounds continuously within the year, so month 1 is the base
    figure exactly and month 13 would be the full annual rate. Twelve months
    therefore average about half the annual rate, which is what a rate of "x%
    a year" means in the first year of a business.
    """
    if not annual_pct:
        return 1.0
    return (1.0 + annual_pct / 100.0) ** ((month_index - 1) / 12.0)


# ── Monthly forecast ─────────────────────────────────────────────────────────

def build_monthly_forecast(
    inp: "CanonicalFinancialInput",
    base: "CanonicalFinancialResult",
    *,
    months: int = 12,
) -> List[Dict[str, Any]]:
    """
    Month-by-month projection of the SAME model that produced `base`.

    Every column is derived from the engine's own monthly figures:
        revenue        = base monthly revenue x seasonality x price growth
        variable cost  = base monthly variable cost x seasonality x volume growth
        fixed cost     = base monthly opex x fixed-cost growth
        interest/principal = the real amortisation schedule row for that month
        free cash flow = PAT + depreciation - principal repaid - change in WC

    Depreciation is added back because it is not cash. Principal is deducted
    because it is cash. Interest is NOT deducted again here: it is already
    inside PAT, and deducting the full debt service on top would charge the
    borrower for the same interest twice.
    """
    seasonality = seasonality_or_flat(inp)
    price_growth = float(getattr(inp, "annual_price_growth_pct", 0.0) or 0.0)
    volume_growth = float(getattr(inp, "annual_volume_growth_pct", 0.0) or 0.0)
    cost_growth = float(getattr(inp, "annual_variable_cost_growth_pct", 0.0) or 0.0)
    fixed_growth = float(getattr(inp, "annual_fixed_cost_growth_pct", 0.0) or 0.0)
    tax_rate = inp.tax_rate_pct
    depreciation_m = base.monthly_depreciation
    base_units = sum(p.units_per_month for p in inp.products)
    opening_cash = float(getattr(inp, "opening_cash_balance", 0.0) or 0.0)

    schedule = {row["month"]: row for row in base.loan_schedule}
    rows: List[Dict[str, Any]] = []
    cash = opening_cash
    cumulative = 0.0
    previous_nwc: Optional[float] = None

    for m in range(1, months + 1):
        month_name = MONTH_NAMES[(m - 1) % 12]
        seasonal = seasonality[(m - 1) % 12]
        g_price = growth_factor(price_growth, m)
        g_volume = growth_factor(volume_growth, m)
        g_cost = growth_factor(cost_growth, m)
        g_fixed = growth_factor(fixed_growth, m)

        units = base_units * seasonal * g_volume
        revenue = base.monthly_revenue * seasonal * g_price
        # Variable cost tracks volume and its own input-price path, not revenue:
        # a price rise must not quietly raise the cost side.
        variable_cost = base.monthly_variable_costs * seasonal * g_cost
        contribution = revenue - variable_cost
        gross_profit = contribution
        opex = base.monthly_opex * g_fixed
        ebitda = gross_profit - opex
        ebit = ebitda - depreciation_m

        loan = schedule.get(m)
        interest = float(loan["interest"]) if loan else 0.0
        principal = float(loan["principal_repaid"]) if loan else 0.0
        debt_service = float(loan["payment"]) if loan else 0.0

        pbt = ebit - interest
        if tax_rate is not None:
            tax = max(0.0, pbt * (tax_rate / 100.0))
        else:
            tax = 0.0
        pat = pbt - tax

        # Working capital on this month's actuals, not on the annual base.
        wc = inp.working_capital_cfg
        annualised_revenue = revenue * 12.0
        annualised_variable = variable_cost * 12.0
        nwc = (
            (annualised_variable / DAYS_PER_YEAR) * wc.inventory_days
            + (annualised_revenue / DAYS_PER_YEAR) * wc.receivable_days
            - (annualised_variable / DAYS_PER_YEAR) * wc.payable_days
        )
        # Month 1 funds the whole requirement: it is a cash requirement at
        # commencement, not a monthly expense. Afterwards only the movement is
        # charged, so a seasonal dip in sales releases cash rather than
        # consuming a second full cycle.
        wc_change = nwc if previous_nwc is None else (nwc - previous_nwc)
        previous_nwc = nwc

        operating_cash_flow = pat + depreciation_m - wc_change
        free_cash_flow = operating_cash_flow - principal
        cash = round(cash + free_cash_flow, 2)
        cumulative = round(cumulative + free_cash_flow, 2)

        rows.append({
            "month": m,
            "month_name": month_name,
            "seasonal_index": seasonal,
            "price_growth_factor": round(g_price, 6),
            "volume_growth_factor": round(g_volume, 6),
            "units": round(units, 1),
            "revenue": round(revenue, 2),
            "variable_cost": round(variable_cost, 2),
            "contribution": round(contribution, 2),
            "cogs": round(variable_cost, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_pct": round((gross_profit / revenue * 100) if revenue else 0.0, 2),
            "fixed_costs": round(opex, 2),
            "ebitda": round(ebitda, 2),
            "depreciation": round(depreciation_m, 2),
            "ebit": round(ebit, 2),
            "interest": round(interest, 2),
            "principal_repaid": round(principal, 2),
            "debt_service": round(debt_service, 2),
            "pbt": round(pbt, 2),
            "tax": round(tax, 2),
            "tax_status": base.tax_status,
            "pat": round(pat, 2),
            "working_capital": round(nwc, 2),
            "change_in_working_capital": round(wc_change, 2),
            "operating_cash_flow": round(operating_cash_flow, 2),
            "free_cash_flow": round(free_cash_flow, 2),
            "ending_cash_balance": cash,
            "cumulative_cash_flow": cumulative,
            "outstanding_loan_balance": round(float(loan["closing_balance"]), 2) if loan else 0.0,
        })

    return rows


def cash_profile(rows: List[Dict[str, Any]], opening_cash: float = 0.0) -> Dict[str, Any]:
    """Ending and minimum cash across a forecast, plus the working-capital gap."""
    if not rows:
        return {
            "opening_cash_balance": round(opening_cash, 2),
            "ending_cash_balance": round(opening_cash, 2),
            "minimum_cash_balance": round(opening_cash, 2),
            "months_negative_cash": 0,
            "lowest_cash_month": None,
        }
    balances = [r["ending_cash_balance"] for r in rows]
    lowest = min(balances)
    lowest_month = rows[balances.index(lowest)]["month"]
    return {
        "opening_cash_balance": round(opening_cash, 2),
        "ending_cash_balance": round(rows[-1]["ending_cash_balance"], 2),
        "minimum_cash_balance": round(lowest, 2),
        "lowest_cash_month": lowest_month,
        "months_negative_cash": sum(1 for b in balances if b < 0),
    }


# ── Stress scenarios ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StressScenario:
    key: str
    name: str
    description: str
    severity: str
    demand_pct: float = 0.0
    price_pct: float = 0.0
    cost_pct: float = 0.0
    rate_points: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "applied_shocks": {
                "demand_delta_pct": round(self.demand_pct * 100, 1),
                "price_delta_pct": round(self.price_pct * 100, 1),
                "variable_cost_delta_pct": round(self.cost_pct * 100, 1),
                "interest_delta_points": round(self.rate_points, 1),
            },
        }


#: The stress matrix required by the product specification. Every entry is a
#: transform of the input, re-run through the full model.
STRESS_SCENARIOS: tuple[StressScenario, ...] = (
    StressScenario(
        "demand_minus_10", "Demand Shock (-10%)",
        "Sales volume falls 10%. Revenue moves with volume while fixed costs and per-unit costs "
        "stay put, so the whole loss falls to EBITDA.",
        "moderate", demand_pct=-0.10,
    ),
    StressScenario(
        "demand_minus_20", "Demand Shock (-20%)",
        "Sales volume falls 20%. A plausible local outcome from a new competitor or a poor season.",
        "severe", demand_pct=-0.20,
    ),
    StressScenario(
        "price_minus_10", "Price Shock (-10%)",
        "Selling price falls 10% on every product. Unit volume is held, so the entire reduction "
        "lands on revenue while variable cost per unit is unchanged. This is a competitor undercutting "
        "on price, not a fall in demand.",
        "moderate", price_pct=-0.10,
    ),
    StressScenario(
        "cost_plus_10", "Input Cost Inflation (+10%)",
        "Variable input cost per unit rises 10%. Fixed operating costs are unaffected, because a "
        "supplier price rise does not raise the rent.",
        "moderate", cost_pct=0.10,
    ),
    StressScenario(
        "cost_plus_15", "Input Cost Inflation (+15%)",
        "Variable input cost per unit rises 15%.",
        "severe", cost_pct=0.15,
    ),
    StressScenario(
        "interest_plus_2", "Interest Rate Hike (+2 points)",
        "The declared interest rate rises by 2 percentage points and the full amortisation "
        "schedule, including total interest, is rebuilt.",
        "severe", rate_points=2.0,
    ),
    StressScenario(
        "combined_severe", "Combined Severe Shock (demand -20%, price -10%, cost +15%, rate +2)",
        "Every shock at once. The effects compound on the same contribution line, so this is "
        "materially worse than any single shock in isolation.",
        "combined", demand_pct=-0.20, price_pct=-0.10, cost_pct=0.15, rate_points=2.0,
    ),
)


def apply_shock(
    inp: "CanonicalFinancialInput",
    *,
    demand_pct: float = 0.0,
    price_pct: float = 0.0,
    cost_pct: float = 0.0,
    rate_points: float = 0.0,
) -> "CanonicalFinancialInput":
    """
    Return a new input with the shock applied. The base input is not mutated.

    Demand scales units. Price scales the selling price. Cost scales variable
    cost per unit. Interest adds to the declared rate. They are separate
    parameters because they are separate economic events: a demand fall and a
    price fall are not the same shock, and conflating them is what makes a
    stress table flatter than reality.
    """
    from app.financial.canonical_engine import ProductItem  # local import: avoids a cycle

    products = [
        ProductItem(
            name=p.name,
            units_per_month=p.units_per_month * (1.0 + demand_pct),
            selling_price=p.selling_price * (1.0 + price_pct),
            variable_cost_per_unit=p.variable_cost_per_unit * (1.0 + cost_pct),
        )
        for p in inp.products
    ]
    return replace(
        inp,
        products=products,
        interest_rate_annual_pct=inp.interest_rate_annual_pct + rate_points,
    )


def run_stress_scenarios(
    base_input: "CanonicalFinancialInput",
    base_result: "CanonicalFinancialResult",
    *,
    scenarios: Optional[List[StressScenario]] = None,
) -> Dict[str, Any]:
    """
    Re-run the full model under every stress scenario.

    The base result is passed in rather than recomputed, so the caller cannot
    accidentally compare a stressed run against a differently-parameterised
    baseline.
    """
    from app.financial.canonical_engine import compute_canonical_financials

    chosen = scenarios if scenarios is not None else list(STRESS_SCENARIOS)
    out: Dict[str, Any] = {}
    for spec in chosen:
        shocked = apply_shock(
            base_input,
            demand_pct=spec.demand_pct,
            price_pct=spec.price_pct,
            cost_pct=spec.cost_pct,
            rate_points=spec.rate_points,
        )
        # Scenarios are one level deep. Without this the stressed input
        # inherits `include_scenarios=True` and each of the seven scenarios
        # recursively runs its own seven, and so on.
        stressed = compute_canonical_financials(replace(shocked, include_scenarios=False))
        out[spec.key] = {
            **spec.to_dict(),
            "monthly_ebitda": stressed.monthly_ebitda,
            "monthly_pat": stressed.monthly_pat,
            "monthly_revenue": stressed.monthly_revenue,
            # Carried so a reader can see WHY EBITDA moved, rather than only how
            # far. A demand fall and a cost rise reach the same EBITDA by
            # different routes, and those routes call for different responses.
            "monthly_variable_costs": stressed.monthly_variable_costs,
            "monthly_opex": stressed.monthly_opex,
            "contribution_per_unit": stressed.contribution_per_unit,
            "monthly_emi": stressed.monthly_emi,
            "break_even_units_monthly": stressed.break_even_units_monthly,
            "dscr": stressed.dscr,
            "dscr_status": stressed.dscr_status,
            "roi_on_total_project_pct": stressed.roi_on_total_project_pct,
            "payback_months": stressed.payback_months,
            "economic_viability": stressed.economic_viability,
            "financial_status": stressed.financial_status,
            "ebitda_change": round(stressed.monthly_ebitda - base_result.monthly_ebitda, 2),
            "roi_change_points": (
                round(stressed.roi_on_total_project_pct - base_result.roi_on_total_project_pct, 2)
                if stressed.roi_on_total_project_pct is not None
                and base_result.roi_on_total_project_pct is not None
                else None
            ),
            "dscr_change": (
                round(stressed.dscr - base_result.dscr, 2)
                if stressed.dscr is not None and base_result.dscr is not None
                else None
            ),
            "decision_changed": stressed.financial_status["value"] != base_result.financial_status["value"],
        }
    # The unshocked case is published alongside the shocked ones. Without it a
    # reader has to reconstruct the baseline from a different part of the
    # response, and "EBITDA drops 4,200 under a 10% demand fall" is only
    # checkable if the 42,000 it drops from is right there.
    out["BASE"] = {
        "key": "BASE",
        "name": "Base case (as declared)",
        "description": (
            "The plan exactly as the caller stated it: no shock applied. Every other entry in "
            "this block is measured against these figures."
        ),
        "severity": "none",
        "applied_shocks": {"demand_pct": 0.0, "price_pct": 0.0, "cost_pct": 0.0, "rate_points": 0.0},
        "monthly_ebitda": base_result.monthly_ebitda,
        "monthly_pat": base_result.monthly_pat,
        "monthly_revenue": base_result.monthly_revenue,
        "monthly_variable_costs": base_result.monthly_variable_costs,
        "monthly_opex": base_result.monthly_opex,
        "contribution_per_unit": base_result.contribution_per_unit,
        "monthly_emi": base_result.monthly_emi,
        "break_even_units_monthly": base_result.break_even_units_monthly,
        "dscr": base_result.dscr,
        "dscr_status": base_result.dscr_status,
        "roi_on_total_project_pct": base_result.roi_on_total_project_pct,
        "payback_months": base_result.payback_months,
        "economic_viability": base_result.economic_viability,
        "financial_status": base_result.financial_status,
        "ebitda_change": 0.0,
        "roi_change_points": 0.0,
        "dscr_change": 0.0,
        "decision_changed": False,
    }
    return out


# ── What-if ──────────────────────────────────────────────────────────────────

@dataclass
class WhatIfAdjustments:
    """
    The levers a user may pull in a what-if. Anything not supplied is left at
    the base value; nothing is defaulted into a change.
    """
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

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @property
    def is_empty(self) -> bool:
        return not self.to_dict()


def apply_what_if(
    inp: "CanonicalFinancialInput",
    adj: WhatIfAdjustments,
) -> tuple["CanonicalFinancialInput", List[Dict[str, Any]]]:
    """
    Apply user adjustments to the input and report what was actually applied.

    Each applied entry records the lever, the previous value, the new value and
    the direction, so the UI can show the user exactly what they changed
    instead of silently returning different numbers.
    """
    from app.financial.canonical_engine import OpexBreakdown, ProductItem, WorkingCapitalConfig

    applied: List[Dict[str, Any]] = []
    changes: Dict[str, Any] = {}
    products = inp.products
    opex = inp.opex

    def note(lever: str, before: Any, after: Any) -> None:
        applied.append({
            "lever": lever,
            "previous": before,
            "applied": after,
            "change": round(after - before, 2) if isinstance(before, (int, float))
            and isinstance(after, (int, float)) else None,
        })

    if adj.units_multiplier is not None:
        before = sum(p.units_per_month for p in inp.products)
        products = [
            ProductItem(p.name, p.units_per_month * adj.units_multiplier,
                        p.selling_price, p.variable_cost_per_unit)
            for p in inp.products
        ]
        after = sum(p.units_per_month for p in products)
        note("monthly_units", before, after)
        changes["products"] = products

    if adj.price_delta_pct is not None:
        before = sum(p.selling_price for p in inp.products)
        products = [
            ProductItem(p.name, p.units_per_month,
                        p.selling_price * (1 + adj.price_delta_pct / 100.0),
                        p.variable_cost_per_unit)
            for p in products
        ]
        after = sum(p.selling_price for p in products)
        note("selling_price_total", before, after)
        changes["products"] = products

    if adj.variable_cost_delta_pct is not None:
        before = sum(p.variable_cost_per_unit for p in inp.products)
        products = [
            ProductItem(p.name, p.units_per_month, p.selling_price,
                        p.variable_cost_per_unit * (1 + adj.variable_cost_delta_pct / 100.0))
            for p in products
        ]
        after = sum(p.variable_cost_per_unit for p in products)
        note("variable_cost_per_unit_total", before, after)
        changes["products"] = products

    if adj.fixed_cost_delta_pct is not None:
        factor = 1 + adj.fixed_cost_delta_pct / 100.0
        before = inp.opex.total_monthly_opex
        opex = OpexBreakdown(**{
            k: (getattr(inp.opex, k) * factor if k != "total_monthly_opex" else 0.0)
            for k in (
                "rent", "salaries", "electricity", "transport", "maintenance",
                "marketing", "insurance", "admin", "other",
            )
        })
        note("monthly_fixed_costs", before, opex.total_monthly_opex)
        changes["opex"] = opex

    for lever, attr, value in (
        ("interest_rate_annual_pct", "interest_rate_annual_pct", adj.interest_rate_annual_pct),
        ("tenure_months", "tenure_months", adj.tenure_months),
        ("own_capital", "own_capital", adj.own_capital),
        ("debt_amount", "debt_amount", adj.debt_amount),
        ("other_funding", "other_funding", adj.other_funding),
        ("tax_rate_pct", "tax_rate_pct", adj.tax_rate_pct),
        ("operating_days_per_month", "operating_days_per_month", adj.operating_days_per_month),
        ("annual_price_growth_pct", "annual_price_growth_pct", adj.annual_price_growth_pct),
    ):
        if value is not None:
            before = getattr(inp, attr)
            changes[attr] = value
            note(lever, before, value)

    if adj.working_capital_days_scale is not None:
        factor = adj.working_capital_days_scale
        wc = inp.working_capital_cfg
        before = wc.inventory_days + wc.receivable_days - wc.payable_days
        after_wc = WorkingCapitalConfig(
            inventory_days=wc.inventory_days * factor,
            receivable_days=wc.receivable_days * factor,
            payable_days=wc.payable_days * factor,
            assumptions_source=wc.assumptions_source,
        )
        after = after_wc.inventory_days + after_wc.receivable_days - after_wc.payable_days
        note("cash_conversion_cycle_days", before, after)
        changes["working_capital_cfg"] = after_wc

    return replace(inp, **changes), applied
