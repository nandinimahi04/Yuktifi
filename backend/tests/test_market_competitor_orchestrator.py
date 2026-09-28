"""
The async market orchestrator's competitor path.

`_get_competitors_async` used to carry its own copy of the Overpass query. That
copy had the same three defects the client had, and no test covered it, so
nothing would have caught them. These tests exist so a second implementation
cannot quietly reappear.
"""
import asyncio

import pytest

from app.engines import market_intelligence as mi


def _survey(status: str, records=None, error=None) -> dict:
    return {"status": status, "records": records or [], "error": error}


def _stub_location(monkeypatch, parsed):
    monkeypatch.setattr(
        mi, "data_layer",
        type("_DL", (), {"_parse_location": staticmethod(lambda _l: parsed)})(),
    )


def _stub_survey(monkeypatch, survey):
    import app.api_clients.overpass_client as oc

    monkeypatch.setattr(oc.OverpassClient, "get_competitor_survey", lambda *a, **kw: survey)


def _run(monkeypatch, survey):
    _stub_location(monkeypatch, (28.61, 77.21))
    _stub_survey(monkeypatch, survey)
    return asyncio.run(mi._get_competitors_async("loc-1", "dairy"))


def test_failed_survey_reports_unknown_count_not_zero(monkeypatch):
    out = _run(monkeypatch, _survey("failed", error="504 Gateway Timeout"))

    assert out["count"] is None
    assert out["query_succeeded"] is False
    assert out["evidence_state"] == "UNAVAILABLE"
    assert "unknown, not zero" in out["note"]


def test_completed_empty_survey_reports_zero(monkeypatch):
    out = _run(monkeypatch, _survey("ok", records=[]))

    assert out["count"] == 0
    assert out["query_succeeded"] is True
    assert "MAPPED" in out["note"]


def test_records_are_keyed_the_way_the_frontend_map_reads(monkeypatch):
    """The map reads comp.lat/comp.lon; the API emits lat/lon."""
    record = {
        "id": "1",
        "name": "Village Dairy",
        "type": "dairy",
        "lat": 28.62,
        "lon": 77.22,
        "distance_km": 1.47,
    }
    out = _run(monkeypatch, _survey("ok", records=[record]))

    assert out["count"] == 1
    got = out["records"][0]
    assert got["latitude"] == 28.62
    assert got["longitude"] == 77.22
    assert got["distance_km"] == 1.47


def test_module_does_not_build_its_own_overpass_query():
    """A duplicated query is how the timeout/Equator/distance bugs came back."""
    import inspect
    import re

    source = inspect.getsource(mi._get_competitors_async)
    assert "out:json" not in source
    assert "around:" not in source
    assert "AsyncClient" not in source
    assert "get_competitor_survey" in source


def test_equator_node_survives_the_orchestrator(monkeypatch):
    """`el.get("lat") or center` dropped 0.0; the shared client does not."""
    record = {
        "id": "9", "name": "Equator Store", "type": "shop",
        "lat": 0.0, "lon": 77.21, "distance_km": 0.0,
    }
    out = _run(monkeypatch, _survey("ok", records=[record]))
    assert out["count"] == 1
    assert out["records"][0]["latitude"] == 0.0


def test_missing_coordinates_yield_unknown_not_zero(monkeypatch):
    _stub_location(monkeypatch, None)
    _stub_survey(monkeypatch, _survey("ok", records=[]))

    out = asyncio.run(mi._get_competitors_async("loc-1", "dairy"))
    assert out["count"] is None
    assert "no competitor survey was run" in out["note"]


def test_demo_mode_yields_unknown_not_zero(monkeypatch):
    """demo_mode is a real field; network_allowed is a derived property."""
    _stub_location(monkeypatch, (28.61, 77.21))
    _stub_survey(monkeypatch, _survey("ok", records=[]))
    monkeypatch.setattr(mi.settings, "demo_mode", True)
    monkeypatch.setattr(mi.settings, "demo_allow_network", False)

    out = asyncio.run(mi._get_competitors_async("loc-1", "dairy"))
    assert out["count"] is None
    assert "Network access is disabled" in out["note"]
