import pytest
from app.engines.financial_engine import compute_project_cost, compute_loan_amount
from app.engines.scheme_engine import match_scheme, MICRO_FINANCE_CEILING, TERM_LOAN_CEILING

# Encodes the exact table from Section 17.1
@pytest.mark.parametrize("margin,expected_scheme", [
    (14_000, "Micro Credit Finance"),      # exactly at boundary — inclusive
    (14_001, "Term Loan"),                 # just above — exclusive
    (100_000, "Term Loan"),
    (500_000, "Term Loan"),                # PC = 50L exactly, at ceiling
    (600_000, None),                       # PC = 60L, exceeds both schemes
])
def test_boundary_routing(margin, expected_scheme):
    pc = compute_project_cost(margin)
    result = match_scheme(pc)
    if expected_scheme is None:
        assert result.matched is False
    else:
        assert result.scheme_name == expected_scheme

def test_project_cost_formula():
    """10% minimum promoter contribution is a SCHEME quote rule only."""
    assert compute_project_cost(100_000) == 1_000_000
    assert compute_project_cost(14_000) == 140_000


def test_engine_never_infers_project_cost_from_margin_capital():
    """
    Regression guard: a dataset that omits setup cost must abstain, not assume
    a 10x multiple and manufacture Rs 9L of debt from Rs 1L of margin.
    """
    from app.engines.financial_engine import run_financial_engine

    result = run_financial_engine(
        user_capital=100_000.0,
        setup_costs={}, pricing_margins={},
        monthly_costs={}, unit_economics={},
    )
    assert result["financial_data_available"] is False
    assert "loan_amount" not in result


def test_loan_capped_at_term_loan_ceiling():
    pc = compute_project_cost(500_000)  # PC = 50,00,000
    result = match_scheme(pc, own_contribution=500_000)
    # Gap of 45L, which lands exactly on the Rs 45L ceiling.
    assert result.max_loan == 4_500_000


def test_scheme_loan_never_exceeds_the_funding_gap():
    pc = compute_project_cost(100_000)  # PC = 10,00,000
    result = match_scheme(pc, own_contribution=100_000)
    assert result.max_loan == pc - 100_000

def test_zero_margin_raises():
    with pytest.raises(ValueError):
        compute_project_cost(0)
