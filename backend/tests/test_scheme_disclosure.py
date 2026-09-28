"""
Scheme results must state what they are: a routing suggestion with an unverified
rule behind it.

The problems these lock down:

* `match_scheme` had no rule id, version, effective date or verification state,
  while the response carried `rate: 6.5` - an undated number presented as a
  current offer. Nothing in the repository re-verifies it against a circular.
* `PMEGP` sat in the scheme table with no routing rule, so no code path could ever
  select it, and a `PMEGP_FINANCING_PCT = 0.25` "margin money subsidy" constant
  advertised a 25% subsidy that no calculation applied. It has been removed and
  the scheme is now reported as not evaluated.
* `match_scheme(0.0)` - which `ranking_service` calls for an unpriced category -
  routed the business into the micro-finance band. An unknown project cost is
  not a zero project cost.
* `/match-scheme` required a `session_id` and then never read it, so it could not
  pass the applicant's own contribution and always answered max_loan=None.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.engines.scheme_engine import (
    MICRO_FINANCE_CEILING,
    NOT_EVALUATED,
    SCHEMES,
    match_scheme,
)
from app.main import app as fastapi_app
from app.models import Session as SessionModel, User
from app.models.core import uid


def test_no_rule_is_quoted_without_its_identity():
    m = match_scheme(1_000_000.0, own_contribution=200_000.0)
    assert m.rule_id
    assert m.rule_version
    assert m.rule_verification["status"] == "UNVERIFIED"
    # An absent effective date must be stated, not left to look like "no change
    # since inception".
    assert any("effective date" in r for r in m.requires_confirmation)


def test_eligibility_is_only_ever_potential():
    m = match_scheme(100_000.0, own_contribution=40_000.0)
    assert m.potentially_eligible is True
    assert "Potentially eligible" in m.eligibility_statement
    assert "not an eligibility decision" in m.disclaimer.lower() or \
           "not an eligibility decision" in m.eligibility_statement


def test_matched_criteria_and_gaps_are_both_listed():
    m = match_scheme(1_000_000.0, own_contribution=200_000.0)
    assert m.criteria_met
    assert m.criteria_unmet, "an untested requirement must appear as unmet"
    assert m.requires_confirmation


def test_unknown_contribution_yields_no_loan_and_says_why():
    m = match_scheme(1_000_000.0)
    assert m.max_loan is None
    assert any("contribution" in u.lower() for u in m.criteria_unmet)


def test_pmegp_is_reported_as_not_evaluated():
    assert "PMEGP" in NOT_EVALUATED
    assert NOT_EVALUATED["PMEGP"]
    assert SCHEMES["PMEGP"]["implemented"] is False
    m = match_scheme(1_000_000.0, own_contribution=200_000.0)
    assert "PMEGP" in m.not_evaluated_schemes


def test_the_unused_subsidy_constant_is_gone():
    """It advertised a 25% margin-money subsidy that no code applied."""
    import app.engines.scheme_engine as se

    assert not hasattr(se, "PMEGP_FINANCING_PCT")


def test_zero_project_cost_does_not_route_into_the_smallest_band():
    m = match_scheme(0.0)
    assert m.matched is False
    assert m.scheme_name is None


def test_unknown_project_cost_does_not_route_into_the_smallest_band():
    m = match_scheme(None)
    assert m.matched is False
    assert m.scheme_name is None
    assert "project cost" in m.explanation.lower()
    assert "Cannot be assessed" in m.eligibility_statement


def test_above_ceiling_states_the_limit_is_ours_not_the_agencys():
    m = match_scheme(9_000_000.0, own_contribution=1_000_000.0)
    assert m.matched is False
    assert "not a refusal by any agency" in m.eligibility_statement
    assert m.criteria_unmet


def test_no_scheme_suggests_a_subsidy_percentage():
    m = match_scheme(1_000_000.0, own_contribution=200_000.0)
    body = m.to_dict()
    assert "25%" not in str(body.get("explanation", ""))
    assert "subsidy" not in str(body.get("criteria_met", [])).lower()


# ── endpoint ───────────────────────────────────────────────────────────────


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    user = User(id=uid(), name="Asha", language_pref="en")
    session = SessionModel(id="sess-scheme", user_id=user.id, location_id="solapur",
                           category_id="retail_kirana", margin_capital=200_000.0)
    db.add_all([user, session])
    db.commit()

    def override():
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override
    try:
        yield TestClient(fastapi_app)
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_endpoint_uses_the_sessions_own_contribution(client):
    """The session_id was required and then ignored, so max_loan was always None."""
    r = client.post("/match-scheme", json={"session_id": "sess-scheme",
                                           "project_cost": 1_000_000})
    assert r.status_code == 200
    body = r.json()
    assert body["max_loan"] == 800_000.0
    assert body["rule_id"] == "NSFDC-TL"
    assert body["rule_verification"]["status"] == "UNVERIFIED"


def test_endpoint_rejects_an_unknown_session(client):
    r = client.post("/match-scheme", json={"session_id": "nope", "project_cost": 100_000})
    assert r.status_code == 404


def test_endpoint_without_a_project_cost_abstains_rather_than_defaulting(client):
    r = client.post("/match-scheme", json={"session_id": "sess-scheme"})
    assert r.status_code == 200
    body = r.json()
    assert body["matched"] is False
    assert body["max_loan"] is None


def test_schemes_listing_labels_verification(client):
    r = client.get("/schemes")
    assert r.status_code == 200
    body = r.json()
    assert body["verification"]["status"] == "UNVERIFIED"
    by_name = {s["rule_id"]: s for s in body["schemes"]}
    assert by_name["PMEGP"]["evaluation_status"] == "NOT_EVALUATED"
    assert by_name["PMEGP"]["not_evaluated_reason"]
    assert body["disclaimer"]


def test_schemes_listing_carries_every_field_a_scheme_card_has_to_render(client):
    """
    The market-intelligence scheme tab renders one card per rule from this
    response. It was written against a response that had none of these fields,
    which is how it ended up hardcoding amounts instead: the card needed a
    display name, a verification block and an effective-date state, and the
    endpoint supplied none of them, so the markup asserted MUDRA and PMEGP terms
    from constants.
    """
    r = client.get("/schemes")
    body = r.json()
    required = {
        "scheme_name", "rule_id", "rule_version", "effective_from",
        "effective_date_state", "source_url", "implemented",
        "evaluation_status", "not_evaluated_reason", "max_loan", "rate",
        "rule_verification",
    }
    for scheme in body["schemes"]:
        assert required <= set(scheme), f"{scheme.get('rule_id')} is missing fields"
        assert scheme["scheme_name"], "a card has no heading without a display name"
        assert scheme["rule_verification"]["status"] == "UNVERIFIED"
        assert scheme["rule_verification"]["note"]
        # An undated rule must say so. The point of the field is that a reader
        # cannot mistake a prototype constant for a term currently in force.
        if scheme["effective_from"] is None:
            assert scheme["effective_date_state"] == "UNDATED_IN_THIS_REPOSITORY"


def test_a_scheme_the_build_does_not_evaluate_carries_no_quotable_terms(client):
    """
    PMEGP holds a max_loan in the rule table while this build deliberately does
    not evaluate it. A client that gates on `max_loan !== null` rather than on
    the evaluation status will print a loan ceiling for a scheme the engine has
    declined to assess - the exact figure the abstention exists to withhold.
    """
    r = client.get("/schemes")
    body = r.json()
    pmegp = next(s for s in body["schemes"] if s["rule_id"] == "PMEGP")
    assert pmegp["implemented"] is False
    assert pmegp["evaluation_status"] == "NOT_EVALUATED"
    assert pmegp["not_evaluated_reason"]
    # The reason must be present, so a client has something to show in place of
    # the withheld amounts.
    assert "not evaluated" in pmegp["not_evaluated_reason"].lower()
