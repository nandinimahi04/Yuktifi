"""
Tests for YUKTI score banding and the DSCR hard gate.

The gate must only bite when there is debt to service, and an absent DSCR must
never be treated as a pass by accident.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engines.recommendation_engine import (
    DSCR_HARD_GATE, WEIGHTS, band_verdict, compute_yukti_score,
)

PERFECT = {k: 100.0 for k in WEIGHTS}
WEAK = {k: 40.0 for k in WEIGHTS}


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_high_score_with_healthy_dscr_is_go():
    b = compute_yukti_score(PERFECT, 1.0, dscr=2.0)
    assert b.final_score == 100.0
    assert b.verdict == "GO"


def test_dscr_below_gate_blocks_go_even_with_a_perfect_score():
    """A top-scoring business that cannot service its debt is not a GO."""
    b = compute_yukti_score(PERFECT, 1.0, dscr=DSCR_HARD_GATE - 0.01)
    assert b.raw_score == 100.0
    assert b.verdict == "NOT_RECOMMENDED"


def test_dscr_exactly_at_the_gate_does_not_block():
    assert band_verdict(95.0, dscr=DSCR_HARD_GATE) == "GO"
    assert band_verdict(95.0, dscr=DSCR_HARD_GATE - 0.01) == "NOT_RECOMMENDED"


def test_no_debt_does_not_trip_the_gate():
    """None means no repayment test exists, which is not the same as failing it."""
    assert band_verdict(100.0, dscr=None) == "GO"
    b = compute_yukti_score(PERFECT, 1.0, dscr=None)
    assert b.verdict == "GO"


def test_no_debt_still_cannot_rescue_a_weak_score():
    assert band_verdict(30.0, dscr=None) == "NOT_RECOMMENDED"
    assert band_verdict(50.0, dscr=None) == "ALTERNATIVE"


def test_bands_are_contiguous_and_descending():
    assert band_verdict(80.0, None) == "GO"
    assert band_verdict(79.9, None) == "CAUTION"
    assert band_verdict(60.0, None) == "CAUTION"
    assert band_verdict(59.9, None) == "ALTERNATIVE"
    assert band_verdict(40.0, None) == "ALTERNATIVE"
    assert band_verdict(39.9, None) == "NOT_RECOMMENDED"
    assert band_verdict(0.0, None) == "NOT_RECOMMENDED"


def test_confidence_multiplier_visibly_reduces_the_score():
    high = compute_yukti_score(PERFECT, 1.0, dscr=2.0)
    low = compute_yukti_score(PERFECT, 0.5, dscr=2.0)
    assert low.raw_score == high.raw_score
    assert low.final_score == pytest.approx(high.final_score * 0.5)


def test_low_confidence_can_change_the_verdict():
    """A perfect business assessed on half-confidence evidence is not a GO."""
    b = compute_yukti_score(PERFECT, 0.5, dscr=2.0)
    assert b.final_score == 50.0
    assert b.verdict == "ALTERNATIVE"


def test_heavier_weights_carry_more_influence():
    base = {k: 50.0 for k in WEIGHTS}
    financial = dict(base, financial_viability=100.0)
    market = dict(base, market_opportunity=100.0)

    assert compute_yukti_score(financial, 1.0, None).raw_score > \
        compute_yukti_score(market, 1.0, None).raw_score


def test_no_dimensions_abstains_instead_of_scoring_zero():
    """
    With nothing measurable, the engine issues no score and no verdict.

    This previously returned `raw_score == 0.0` and `verdict == "NOT_RECOMMENDED"`.
    A score of zero is not a neutral result: it is the most negative result the
    scale allows, and `NOT_RECOMMENDED` is a decision. Both were being asserted
    from zero inputs, so a user who had supplied no evidence at all was told the
    business was not recommended. Absence of data is a request for data.
    """
    b = compute_yukti_score({}, 1.0, dscr=2.0)
    assert b.raw_score is None
    assert b.final_score is None
    assert b.verdict is None
    assert sorted(b.unscored) == sorted(WEIGHTS)


def test_partially_missing_dimensions_are_excluded_and_renormalised():
    """
    An unmeasured dimension must not drag the score toward zero.

    Scoring missing dimensions as 0 conflated "unmeasured" with "measured and
    terrible". The scored subset is now reweighted so a partial evidence base
    still produces a meaningful figure, while naming what it could not measure.
    """
    half = {"financial_viability": 80.0, "repayment_capacity": 80.0}
    b = compute_yukti_score(half, 1.0, dscr=2.0)

    # Both known dimensions are 80, so the composite is 80 - not 80 * 0.55.
    assert b.raw_score == pytest.approx(80.0)
    assert b.final_score == pytest.approx(80.0)
    assert b.verdict == "GO"
    assert set(b.unscored) == {"market_opportunity", "capital_efficiency", "risk_exposure"}
    assert "excluded, not imputed as zero" in b.note


def test_explicit_none_dimension_is_treated_as_unmeasured():
    """`None` is the score card's marker for 'not computed', and is excluded."""
    dims = {k: None for k in WEIGHTS}
    dims["financial_viability"] = 90.0
    b = compute_yukti_score(dims, 1.0, dscr=2.0)
    assert b.raw_score == pytest.approx(90.0)
    assert "market_opportunity" in b.unscored


def test_verdict_is_withheld_when_too_little_of_the_model_is_evidenced():
    """A single dimension cannot carry a verdict for the whole business."""
    b = compute_yukti_score({"financial_viability": 100.0}, 1.0, dscr=3.0)
    assert b.raw_score == pytest.approx(100.0)
    assert b.final_score == pytest.approx(100.0)
    assert b.verdict is None
    assert "Too little of the model is evidenced" in b.note


def test_accepts_a_score_card_directly():
    """A ScoreCard can be passed without unwrapping it first."""
    from app.engines.scoring_engine import compute_all_dimensions

    card = compute_all_dimensions(roi=50.0, dscr=2.0, competitor_count=None, population=None)
    b = compute_yukti_score(card, 1.0, dscr=2.0)
    assert b.raw_score is not None
    assert "market_opportunity" in b.unscored


def test_verdict_is_always_one_of_the_four_bands():
    for score in (0, 39.9, 40, 59.9, 60, 79.9, 80, 100):
        for dscr in (None, 0.2, 1.0, 3.0):
            assert band_verdict(score, dscr) in {
                "GO", "CAUTION", "ALTERNATIVE", "NOT_RECOMMENDED",
            }
