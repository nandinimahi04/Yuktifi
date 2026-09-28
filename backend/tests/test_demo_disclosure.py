"""
`/api/v2/dairy-demo` silently supplied the caller's finances.

The route built a complete-looking plan for a business from parameters it chose
itself:

    margin_capital=float(payload.get('margin_capital', 100000)),
    annual_interest_rate_pct=float(payload.get('annual_interest_rate_pct', 12.0)),
    tenure_months=int(payload.get('tenure_months', 60)),

A caller that posted nothing - or posted only a location - received EMI, DSCR,
payback and loan-sizing figures derived from an assumed ₹1 lakh margin, with
nothing in the response recording that the margin had been invented. The only
disclosure was a `limitations` string array, which a client has to know to parse
in order to surface at all.

These tests pin the disclosure so it travels as data: which inputs were supplied,
which were assumed, and that the payload is flagged as demo output.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.phase1.dairy_demo import build_dairy_demo


@pytest.fixture
def client():
    return TestClient(app)


def test_dairy_demo_is_flagged_as_demo_data():
    """The status has to be machine-readable, not only a prose caveat."""
    out = build_dairy_demo()
    assert out["is_demo"] is True
    assert out["data_status"] == "DEMO DATA / NOT LIVE"


def test_assumed_capital_is_published_as_an_assumption():
    """
    `total_project_cost` and `margin_capital` are not measured. Every figure
    derived from them inherits that status, so the assumed values are returned
    under a key that says so.
    """
    out = build_dairy_demo()
    assumed = out["assumed_inputs"]
    assert assumed["margin_capital"] == 100000
    assert assumed["total_project_cost"] == 1000000.0
    assert "assumption" in assumed["note"].lower()


def test_the_scenario_block_marks_the_margin_as_assumed():
    out = build_dairy_demo()
    assert out["scenario"]["margin_capital_is_assumed"] is True


def test_the_route_reports_that_no_capital_was_supplied(client):
    """An empty POST must not look like a user with ₹1 lakh of margin."""
    r = client.post("/api/v2/dairy-demo", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["inputs_supplied"]["margin_capital"] is False
    assert body["is_demo"] is True


def test_the_route_reports_capital_when_it_was_supplied(client):
    r = client.post("/api/v2/dairy-demo", json={"margin_capital": 250000})
    assert r.status_code == 200
    body = r.json()
    assert body["inputs_supplied"]["margin_capital"] is True
    assert body["scenario"]["margin_capital"] == 250000
    assert body["assumed_inputs"]["margin_capital"] == 250000


def test_the_demo_disclosure_survives_the_location_aware_route(client):
    """
    The location-aware variant resolves the district canonically, which made it
    look authoritative. It still assumed the margin, so it must carry the same
    disclosure.
    """
    r = client.post(
        "/api/v2/dairy-demo/location-aware",
        json={"location": "Akkalkot", "lat": 17.51, "lng": 75.79},
    )
    # Whether the location resolves depends on the bundled master; either way the
    # response must not be a bare plan with no status.
    assert r.status_code in (200, 422)
    body = r.json()
    if r.status_code == 200 and "financial" in body:
        assert body["is_demo"] is True
        assert body["inputs_supplied"]["margin_capital"] is False
