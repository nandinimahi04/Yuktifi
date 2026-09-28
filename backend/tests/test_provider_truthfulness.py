"""
Provider and retrieval truthfulness.

Every external figure has to be able to answer "how do you know that?" without
the answer being invented. Three failure modes are tested here, because each of
them is a way of reporting a number the system never measured:

* a transport failure returned as a successful empty result,
* a configured provider silently ignored so a fallback looks like the source,
* a missing API key reported as if the provider had been tried.
"""
from app.api_clients.census_client import CensusClient
from app.api_clients.overpass_client import OverpassClient
from app.core.config import settings


def test_transport_failure_is_not_reported_as_zero_competitors(monkeypatch):
    """A failed Overpass call must not look like a survey that found nothing."""
    client = OverpassClient()

    def explode(*_a, **_kw):
        raise RuntimeError("504 Gateway Timeout")

    monkeypatch.setattr("app.api_clients.overpass_client.httpx.Client", explode)

    survey = client.get_competitor_survey(28.61, 77.21, "dairy")

    assert survey["status"] == "failed"
    assert survey["records"] == []
    assert "504" in survey["error"]


def test_successful_query_with_no_features_is_a_completed_survey(monkeypatch):
    """A real query returning nothing is 'ok', and is distinct from a failure."""
    client = OverpassClient()

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": []}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def post(self, *_a, **_kw):
            return _Response()

    monkeypatch.setattr("app.api_clients.overpass_client.httpx.Client", lambda **_kw: _Client())

    survey = client.get_competitor_survey(28.61, 77.21, "dairy")

    assert survey["status"] == "ok"
    assert survey["records"] == []
    assert survey["error"] is None


def test_client_waits_longer_than_the_server_budget(monkeypatch):
    """
    The query used to declare [timeout:25] while the HTTP call gave up after 5s,
    so the server was told it had 25 seconds to answer a query nobody awaited.
    """
    client = OverpassClient()
    seen: dict = {}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": []}

    class _Client:
        def __init__(self, **kwargs):
            seen["timeout"] = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def post(self, _url, data=None):
            seen["query"] = data["data"]
            return _Response()

    monkeypatch.setattr("app.api_clients.overpass_client.httpx.Client", _Client)
    monkeypatch.setattr(settings, "overpass_timeout_seconds", 12.0)

    client.get_competitor_survey(28.61, 77.21, "dairy")

    assert f"[out:json][timeout:{int(12.0)}]" in seen["query"]
    assert seen["timeout"] > 12.0


def test_node_on_the_equator_is_not_dropped(monkeypatch):
    """`if not el_lat` drops latitude 0.0, because zero is falsy."""
    client = OverpassClient()

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "elements": [
                    {
                        "id": 1,
                        "lat": 0.0,      # Equator
                        "lon": 77.21,
                        "tags": {"name": "Equator Store"},
                    }
                ]
            }

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def post(self, *_a, **_kw):
            return _Response()

    monkeypatch.setattr("app.api_clients.overpass_client.httpx.Client", lambda **_kw: _Client())

    survey = client.get_competitor_survey(0.0, 77.21, "dairy")

    assert survey["status"] == "ok"
    assert len(survey["records"]) == 1
    assert survey["records"][0]["name"] == "Equator Store"


def test_legacy_accessor_keeps_its_list_signature(monkeypatch):
    """get_competitors_in_radius still returns a list for existing callers."""
    client = OverpassClient()
    monkeypatch.setattr(
        OverpassClient,
        "get_competitor_survey",
        lambda *_a, **_kw: {"status": "ok", "records": [{"id": "1"}], "error": None},
    )
    assert client.get_competitors_in_radius(28.61, 77.21, "dairy") == [{"id": "1"}]


def test_census_stub_does_not_claim_a_fallback_it_performs(caplog):
    """
    The stub used to log 'Falling back to next data source', which reads as a
    working client degrading gracefully. It performs no lookup at all.
    """
    import logging

    with caplog.at_level(logging.INFO, logger="app.api_clients.census_client"):
        assert CensusClient(api_key="x").get_demographics(28.61, 77.21) is None
        assert CensusClient().get_demographics(28.61, 77.21) is None

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "Falling back" not in messages
    assert "not implemented" in messages


def test_census_key_is_passed_through_to_the_client():
    """DataRetrieval used to build CensusClient() with no argument at all."""
    import inspect

    from app.data_layer import retrieval

    source = inspect.getsource(retrieval.DataRetrieval.__init__)
    assert "census_api_key" in source


def test_worldpop_reports_areal_estimate_not_absence():
    """
    GRID_ENDPOINT is empty, so valid requests return an INFERRED areal estimate.
    An earlier docstring claimed a missing grid source yields UNAVAILABLE.
    """
    from app.api_clients.worldpop_client import GRID_ENDPOINT, WorldPopClient
    from app.evidence import EvidenceState

    assert GRID_ENDPOINT == ""
    record = WorldPopClient().get_population_record(28.61, 77.21, 5.0)
    assert record.state is EvidenceState.INFERRED
    assert record.usable


def test_worldpop_still_abstains_on_impossible_requests():
    from app.api_clients.worldpop_client import WorldPopClient
    from app.evidence import EvidenceState

    for kwargs in (
        {"lat": None, "lon": 77.21, "radius_km": 5.0},
        {"lat": 999.0, "lon": 77.21, "radius_km": 5.0},
        {"lat": 28.61, "lon": 77.21, "radius_km": 900.0},
    ):
        record = WorldPopClient().get_population_record(**kwargs)
        assert record.state is EvidenceState.UNAVAILABLE
        assert not record.usable
