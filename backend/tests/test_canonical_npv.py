"""
The canonical NPV must count interest exactly once.

`annual_ocf` is PAT + depreciation, and PAT is already net of interest. The NPV
loop then subtracted the full debt service - principal *and* interest - from that
post-interest figure, so every year of the projection was credited with interest
that had been paid out and then credited again. NPV and IRR were overstated by
roughly the present value of the loan's total interest, which is the difference
between a project that clears a bank hurdle and one that does not.

The tests recompute the NPV independently from the engine's own published
schedule, so they fail if the treatment of interest changes again in either
direction.
"""
import math

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)


def _model(**overrides):
    params = dict(
        business_type="retail_kirana",
        products=[ProductItem("Kirana", units_per_month=900, selling_price=120,
                              variable_cost_per_unit=84)],
        opex=OpexBreakdown(other=25000),
        own_capital=300000,
        total_project_cost=800000,
        debt_amount=500000,
        interest_rate_annual_pct=12.0,
        tenure_months=84,
        discount_rate_pct=10.0,
        npv_horizon_years=5,
    )
    params.update(overrides)
    return compute_canonical_financials(CanonicalFinancialInput(**params))


def _independent_npv(res, years):
    """Rebuild the yearly cash flow from the engine's own outputs."""
    schedule = {r["month"]: r for r in res.loan_schedule}
    annual_interest = res.annual_interest
    annual_ocf_post_interest = res.annual_operating_cash_flow
    unlevered = annual_ocf_post_interest + annual_interest

    flows = []
    for year in range(years):
        service = sum(
            schedule[m]["payment"]
            for m in range(year * 12 + 1, year * 12 + 13)
            if m in schedule
        )
        flows.append(unlevered - service)

    r = 10.0 / 100.0
    return -res.total_project_cost + sum(
        cf / ((1 + r) ** (t + 1)) for t, cf in enumerate(flows)
    )


def test_npv_matches_an_independent_recomputation():
    res = _model()
    years = res.npv_horizon_years_used
    assert math.isclose(res.npv, round(_independent_npv(res, years), 2), abs_tol=1.0)


def test_interest_is_not_counted_twice():
    """
    The published NPV must exceed the figure produced by double counting.

    Recomputing with the old `annual_ocf - service` (no interest add-back) is the
    exact number this test asserts we have moved away from. Because the double
    count subtracted interest that PAT had already removed, it made the project
    look *worse* than it is - a bank could refuse a viable business on a figure
    that was wrong by the present value of the whole loan's interest.
    """
    res = _model()
    years = res.npv_horizon_years_used
    schedule = {r["month"]: r for r in res.loan_schedule}
    r = 10.0 / 100.0

    doubled = -res.total_project_cost + sum(
        (
            res.annual_operating_cash_flow
            - sum(
                schedule[m]["payment"]
                for m in range(y * 12 + 1, y * 12 + 13)
                if m in schedule
            )
        )
        / ((1 + r) ** (t + 1))
        for t, y in enumerate(range(years))
    )

    assert res.npv > round(doubled, 2)
    # The gap is the present value of the interest that was being deducted twice.
    assert round(res.npv - doubled, 2) > 0


def test_npv_does_not_improve_when_the_borrower_pays_more_interest():
    """
    Holding operations constant, a higher rate must not raise the project's NPV.

    Before the fix, paying more interest reduced the post-interest OCF by the
    full amount and then removed only the principal's share from the service line
    in the payback loop - so the two disagreed about the same rupee.
    """
    base = _model()
    dearer = _model(interest_rate_annual_pct=18.0)
    assert dearer.npv < base.npv


def test_debtless_model_is_unaffected_by_the_add_back():
    res = _model(debt_amount=0.0)
    assert res.annual_interest == 0.0
    years = res.npv_horizon_years_used
    r = 10.0 / 100.0
    expected = -res.total_project_cost + sum(
        res.annual_operating_cash_flow / ((1 + r) ** (t + 1)) for t in range(years)
    )
    assert math.isclose(res.npv, round(expected, 2), abs_tol=1.0)
