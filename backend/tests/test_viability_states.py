"""
Economic viability has three states, and conflating two of them misinforms a
lender.

* VIABLE       - every gate evaluated and cleared.
* NOT_VIABLE   - at least one gate evaluated and failed.
* UNDETERMINED - nothing failed, but a gate could not be evaluated for want of
  evidence.

An uncosted business previously returned NOT_VIABLE. Its own comment said
otherwise - "Calling that VIABLE would be a judgement about a business nobody has
costed" - and then went on to call it NOT_VIABLE, which is the same error pointed
the other way. Both are conclusions; the only evidence held was the absence of a
project cost. A bank officer reading NOT_VIABLE is told to reject a business for
the crime of not having been costed yet.
"""
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)

GOOD_PRODUCT = ProductItem(name="u", units_per_month=500, selling_price=50,
                           variable_cost_per_unit=20)
LOSS_PRODUCT = ProductItem(name="u", units_per_month=500, selling_price=50,
                           variable_cost_per_unit=80)


def test_unknown_capital_is_undetermined_not_not_viable():
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="uncosted",
            products=[GOOD_PRODUCT],
            opex=OpexBreakdown(rent=5000),
            own_capital=0,
            total_project_cost=0.0,
            debt_amount=0,
        )
    )
    assert res.economic_viability == "UNDETERMINED"
    assert res.viability_reasons == [], "no gate failed, so there is nothing to report"
    assert any("capital requirement is unknown" in u for u in res.assessability_unknowns)


def test_a_real_failure_outranks_an_unknown():
    """A failed gate must never be masked by the softer UNDETERMINED state."""
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="loss_making_and_uncosted",
            products=[LOSS_PRODUCT],
            opex=OpexBreakdown(rent=5000),
            own_capital=0,
            total_project_cost=0.0,
            debt_amount=0,
        )
    )
    assert res.economic_viability == "NOT_VIABLE"
    assert res.viability_reasons
    assert res.assessability_unknowns, "the gap is still worth recording alongside the failure"


def test_a_costed_profitable_business_is_viable():
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="healthy",
            products=[GOOD_PRODUCT],
            opex=OpexBreakdown(rent=5000),
            own_capital=100_000,
            total_project_cost=300_000,
            debt_amount=200_000,
            interest_rate_annual_pct=10.0,
            tenure_months=60,
        )
    )
    assert res.economic_viability == "VIABLE"
    assert res.viability_reasons == []
    assert res.assessability_unknowns == []


def test_undetermined_is_not_described_as_a_failure_in_the_dossier_shape():
    """The two lists are separate, so a renderer cannot mix them up."""
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="uncosted",
            products=[GOOD_PRODUCT],
            opex=OpexBreakdown(rent=5000),
            own_capital=0,
            total_project_cost=0.0,
            debt_amount=0,
        )
    )
    payload = res.to_dict()
    assert "assessability_unknowns" in payload
    assert payload["viability_reasons"] == []
    assert payload["assessability_unknowns"]


def test_capital_dependent_figures_are_withheld_when_the_cost_is_unknown():
    """
    The self-contradiction this removes: one response stated "the capital
    requirement is unknown, so return on capital, payback and net present value
    cannot be assessed" and, three fields away, published an NPV of 475,137.

    That NPV came from discounting the inflows against a project cost of zero, so
    it was the discounted value of the cash flows with no investment subtracted at
    all - a large positive number that looks like a strong result.
    """
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="uncosted",
            products=[GOOD_PRODUCT],
            opex=OpexBreakdown(rent=5000),
            own_capital=0,
            total_project_cost=0.0,
            debt_amount=0,
        )
    )
    assert res.npv is None
    assert res.irr_pct is None
    assert res.roi_on_total_project_pct is None
    assert res.payback_months is None
    assert res.payback_achieved is False
    assert res.payback_status == "NOT_COMPUTABLE_NO_PROJECT_COST"


def test_a_costed_business_still_gets_every_figure():
    """The withholding must not leak into costed models."""
    res = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="healthy",
            products=[GOOD_PRODUCT],
            opex=OpexBreakdown(rent=5000),
            own_capital=100_000,
            total_project_cost=300_000,
            debt_amount=200_000,
            interest_rate_annual_pct=10.0,
            tenure_months=60,
        )
    )
    assert res.npv is not None
    assert res.roi_on_total_project_pct is not None
    assert res.payback_status in ("ACHIEVED", "NOT_ACHIEVED_IN_HORIZON")
