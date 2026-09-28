"""
Tests for scheme routing.

The engine is a rule table over NSFDC-verified bands. It must never quote a
funded amount that exceeds the promoter's actual funding gap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engines.scheme_engine import (
    MICRO_FINANCE_CEILING, TERM_LOAN_CEILING, match_scheme,
)


def test_micro_band_routes_to_micro_credit():
    m = match_scheme(100_000.0, own_contribution=40_000.0)
    assert m.matched is True
    assert m.scheme_name == "Micro Credit Finance"
    assert m.rate == 6.5
    assert m.moratorium_months == 3
    assert m.source_url


def test_term_loan_band_routes_to_term_loan():
    m = match_scheme(1_000_000.0, own_contribution=200_000.0)
    assert m.matched is True
    assert m.scheme_name == "Term Loan"
    assert "Micro Credit Finance" in m.rejected_alternative


def test_above_ceiling_is_not_matched_and_stays_helpful():
    m = match_scheme(9_000_000.0, own_contribution=1_000_000.0)
    assert m.matched is False
    assert m.scheme_name is None
    assert m.max_loan is None
    assert m.source_url is None
    # Must not tell the user the business is unfinanceable.
    assert "unfinanceable" in m.explanation
    assert "not modelled" in m.explanation


def test_funded_amount_is_the_funding_gap_not_a_percentage_of_cost():
    """A 90%-of-project-cost rule invents debt the promoter cannot service."""
    m = match_scheme(1_000_000.0, own_contribution=800_000.0)
    assert m.max_loan == 200_000.0
    assert m.max_loan < 1_000_000.0 * 0.90


def test_funded_amount_is_the_gap_when_gap_is_under_the_ceiling():
    m = match_scheme(1_000_000.0, own_contribution=10_000.0)
    assert m.max_loan == 990_000.0


def test_funded_amount_is_capped_by_the_scheme_ceiling():
    m = match_scheme(5_000_000.0, own_contribution=0.0)
    assert m.max_loan == 4_500_000.0


def test_no_funded_amount_is_quoted_without_a_known_contribution():
    """An unknown contribution means an unknown gap, not a guessed loan."""
    m = match_scheme(1_000_000.0)
    assert m.matched is True
    assert m.max_loan is None
    assert "unknown" in m.explanation.lower()


def test_funded_amount_never_goes_negative():
    m = match_scheme(500_000.0, own_contribution=900_000.0)
    assert m.max_loan == 0.0


def test_explanation_states_the_gap_it_used():
    m = match_scheme(1_000_000.0, own_contribution=250_000.0)
    assert "750,000" in m.explanation
    assert "1,000,000" in m.explanation
    assert "250,000" in m.explanation


def test_band_boundaries_are_inclusive_at_the_ceiling():
    at_micro = match_scheme(MICRO_FINANCE_CEILING, own_contribution=0.0)
    above_micro = match_scheme(MICRO_FINANCE_CEILING + 1, own_contribution=0.0)
    at_term = match_scheme(TERM_LOAN_CEILING, own_contribution=0.0)
    above_term = match_scheme(TERM_LOAN_CEILING + 1, own_contribution=0.0)

    assert at_micro.scheme_name == "Micro Credit Finance"
    assert above_micro.scheme_name == "Term Loan"
    assert at_term.scheme_name == "Term Loan"
    assert above_term.matched is False


def test_matched_scheme_terms_are_complete_when_usable():
    for cost in (100_000.0, 1_000_000.0):
        m = match_scheme(cost, own_contribution=0.0)
        assert m.tenure_years and m.tenure_years > 0
        assert m.moratorium_months is not None
        assert 0 <= m.moratorium_months < m.tenure_years * 12
        assert m.source_url.startswith("https://")
