"""
No session, no business, no score.

`get_base_state` previously returned a fully invented company for an unknown
session_id: a ₹9,00,000 loan at 10% over 60 months, ₹1,20,000 monthly revenue,
₹70,000 monthly opex, and dimension scores of 89 / 92 / 88 / 91 / 68. Combined
with a confidence multiplier of 0.85, `/recommend` for any session the database
had never seen returned a score around 90/100 and a confident verdict, for a
business that did not exist, indistinguishable from a real assessment.

These tests pin the corrected behaviour.
"""
import pytest

from app.services.session_service import get_base_state


@pytest.fixture()
def db():
    """A session on the application database, matching the other route tests."""
    from app.core.db import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_j_unknown_session_returns_no_financial_figures(db):
    state = get_base_state(db, "session-that-does-not-exist")

    assert state["state_status"] == "NO_SESSION"
    for key in (
        "principal",
        "rate",
        "tenure_months",
        "monthly_revenue",
        "monthly_opex",
        "break_even_units",
    ):
        assert state[key] is None, f"{key} was invented: {state[key]}"


def test_j_unknown_session_scores_nothing(db):
    state = get_base_state(db, "session-that-does-not-exist")

    card = state["dimension_scores"]
    for dim in card.dimensions:
        assert dim.score is None, f"{dim.key} was scored {dim.score} with no data"
    assert card.unscored, "no dimension should be scorable"
    assert card.composite is None


def test_j_unknown_session_produces_no_verdict(db):
    """The end-to-end consequence: no score, no verdict, request for data."""
    from app.engines.recommendation_engine import compute_yukti_score

    state = get_base_state(db, "session-that-does-not-exist")
    result = compute_yukti_score(
        state["dimension_scores"], state["confidence_multiplier"], dscr=None
    )

    assert result.final_score is None
    assert result.verdict is None
    assert result.unscored


def test_j_unknown_session_recommend_endpoint_refuses_to_invent(db):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post("/recommend", json={"session_id": "no-such-session"})
    assert response.status_code == 200
    body = response.json()

    assert body["yukti_score"] is None
    assert body["verdict"] is None
    assert body["confidence"] == "UNAVAILABLE"
    assert body["dscr"] is None
    assert body["roi"] is None
    # Every dimension is declared, and every one is unknown.
    assert set(body["dimension_scores"]) == {
        "financial_viability",
        "repayment_capacity",
        "market_opportunity",
        "capital_efficiency",
        "risk_exposure",
    }
    for dim in body["dimension_scores"].values():
        assert dim["score"] is None
        assert dim["known"] is False


def test_j_no_scheme_means_no_invented_interest_rate(db):
    """
    LoanProduct stores no rate, so it can only come from a matched scheme.
    The previous `rate = scheme.rate if scheme.matched else 10.0` invented a
    rate and then reported EMI and DSCR against it.
    """
    from app.models import LoanProduct, Session
    from app.models import FinancialProjection

    # The application database persists between runs, so clear these ids first
    # to keep the test re-runnable rather than failing on a duplicate key.
    for model in (FinancialProjection, LoanProduct, Session):
        db.query(model).filter(
            model.id.in_(["p-unmatched", "l-unmatched", "s-unmatched"])
        ).delete(synchronize_session=False)
    db.commit()

    db.add(
        Session(
            id="s-unmatched",
            user_id="u",
            location_id="nashik_maharashtra",
            category_id="dairy",
            margin_capital=50000,
        )
    )
    # A project cost far outside every scheme band, so nothing matches.
    db.add(
        LoanProduct(
            id="l-unmatched",
            session_id="s-unmatched",
            project_cost=90_000_000.0,
            loan_amount=0.0,
            beneficiary_contribution=0.0,
            matched_scheme_id=None,
        )
    )
    db.add(
        FinancialProjection(
            id="p-unmatched",
            session_id="s-unmatched",
            monthly_revenue=10000.0,
            monthly_opex=4000.0,
            net_profit=1000.0,
            break_even_units=50.0,
            dscr=None,
            roi=None,
            monthly_emi=None,
            monthly_interest=None,
        )
    )
    db.commit()

    state = get_base_state(db, "s-unmatched")
    assert state["financing_terms_status"] == "UNKNOWN"
    assert state["rate"] is None
    assert state["tenure_months"] is None
    assert "no interest rate or tenure is known" in state["financing_note"].lower()
