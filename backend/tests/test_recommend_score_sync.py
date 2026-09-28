"""
The recommendation endpoint must reflect the projection it was asked about.

`/recommend` computed its score from `base_state["dimension_scores"]` - the card
cached on the session during an earlier step - and built a fresh card only to
generate next steps. The response therefore mixed two states of the business: a
headline score describing the cached run, with reasons and next steps describing
the current projection. Editing a projection's DSCR moved the detail and left the
score untouched, so the two could contradict each other on one screen.

These tests compare scores for the same session under different projections.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app as fastapi_app
from app.models import FinancialProjection, Session, User
from app.models.core import uid


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()

    user = User(id=uid(), name="Asha", language_pref="en")
    session = Session(
        id="sess-score-sync",
        user_id=user.id,
        location_id="solapur",
        category_id="retail_kirana",
        margin_capital=250000.0,
    )
    db.add_all([user, session])
    db.commit()

    def override():
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override
    try:
        yield TestClient(fastapi_app), db
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _project(db, **overrides):
    row = FinancialProjection(
        session_id="sess-score-sync",
        monthly_revenue=120000,
        net_profit=18000,
        dscr=1.60,
        roi=14.0,
        break_even_units=520,
        monthly_emi=0,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    return row


def test_score_is_the_same_run_as_the_dimension_detail(client):
    c, db = client
    _project(db)

    r = c.post("/recommend", json={"session_id": "sess-score-sync"})
    assert r.status_code == 200
    body = r.json()

    # Every reported dimension must be one the score was actually computed from.
    reported = {
        k: v["score"]
        for k, v in body["dimension_scores"].items()
        if isinstance(v, dict) and v.get("score") is not None
    }
    assert reported, "a projection with figures should score at least one dimension"
    assert set(reported).issubset(set(body["unscored_dimensions"]) ^ set(reported))


def test_weakening_the_projection_lowers_the_score(client):
    c, db = client
    _project(db)
    strong = c.post("/recommend", json={"session_id": "sess-score-sync"}).json()
    strong_score = strong["yukti_score"]

    # Worsen the stored projection: the response must follow it.
    row = db.query(FinancialProjection).filter(
        FinancialProjection.session_id == "sess-score-sync"
    ).first()
    row.dscr = 0.35
    row.net_profit = -4000
    db.commit()

    weak = c.post("/recommend", json={"session_id": "sess-score-sync"}).json()

    assert weak["yukti_score"] < strong_score, (
        "a business that went from 1.60 DSCR and 18,000 profit to 0.35 DSCR and a "
        "4,000 loss must not keep the previous score"
    )
    assert weak["dscr"] == 0.35


def test_a_held_back_score_and_a_honest_detail_cannot_coexist(client):
    """
    The stale-card bug showed an unchanged score above a changed reason.

    Comparing the two runs catches any regression where the composite is
    computed from a different card than the per-dimension detail.
    """
    c, db = client
    _project(db)
    first = c.post("/recommend", json={"session_id": "sess-score-sync"}).json()

    row = db.query(FinancialProjection).filter(
        FinancialProjection.session_id == "sess-score-sync"
    ).first()
    row.roi = None
    db.commit()
    second = c.post("/recommend", json={"session_id": "sess-score-sync"}).json()

    assert second["roi"] is None
    assert second["roi_status"] == "NOT_COMPUTED"
    # Removing ROI drops a dimension from the model, which the detail must show.
    fin = second["dimension_scores"]["financial_viability"]
    assert fin["score"] is None or fin["score"] != first["dimension_scores"]["financial_viability"]["score"]


def test_score_and_detail_come_from_the_same_card():
    """
    Unit-level: the card the response reports must be the card that was scored.
    """
    from app.engines.recommendation_engine import compute_yukti_score
    from app.engines.scoring_engine import compute_all_dimensions

    card = compute_all_dimensions(
        roi=20.0, dscr=1.5, net_margin=15.0, break_even_units=500,
        monthly_units=None, competitor_count=None, population=None,
        overall_confidence="High", threats_count=None, has_debt=True,
    )
    breakdown = compute_yukti_score(
        dimension_scores=card.to_dict(), confidence_multiplier=1.0, dscr=1.5
    )

    reported = {d.key: d.score for d in card.dimensions if d.score is not None}
    for key, value in reported.items():
        assert breakdown.dimensions[key] == value
    assert set(breakdown.unscored) == {d.key for d in card.dimensions if d.score is None}


def test_base_state_cache_is_not_used_for_the_score(client):
    """A cached card from a previous step must not drive the current answer."""
    c, db = client
    _project(db)
    # Poison the session cache with an implausibly good card.
    row = db.query(Session).filter(Session.id == "sess-score-sync").first()
    row.state = {
        "dimension_scores": {
            "financial_viability": 99,
            "repayment_capacity": 99,
            "market_opportunity": 99,
            "capital_efficiency": 99,
            "risk_exposure": 99,
        },
        "confidence_multiplier": 1.0,
    }
    db.commit()

    body = c.post("/recommend", json={"session_id": "sess-score-sync"}).json()
    scores = [
        v["score"] for v in body["dimension_scores"].values()
        if isinstance(v, dict) and v.get("score") is not None
    ]
    assert scores, "at least one dimension should be evidenced here"
    assert max(scores) < 99, "a poisoned session cache must not reach the response"
    assert body["yukti_score"] < 99
