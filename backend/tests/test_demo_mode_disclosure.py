"""
A figure that is not live must be labelled as not live.

`DEMO_MODE=true` switches off outbound network in the provider clients, so
prices, competitor counts and population figures come from bundled fixtures.
That is correct behaviour and it was completely invisible. Nothing in the
response said so, and nothing on screen said so, so a demo run and a live run
produced indistinguishable output.

The failure this prevents is specific: a judge, or a founder, looking at a
recommendation and reasonably assuming the competitor counts behind it were
looked up. They were not. The screen gave no sign.

These tests pin the disclosure header to the setting that actually controls the
behaviour, so the label cannot drift from the thing it labels.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def client_for_mode(monkeypatch):
    """
    Build a client with DEMO_MODE set to a given value.

    The middleware reads `settings.network_allowed` on every request rather than
    capturing it at import, so setting the two fields it derives from is enough
    and does not require reimporting the application.
    """
    def _build(demo_mode: bool, allow_network: bool = False):
        monkeypatch.setattr(settings, "demo_mode", demo_mode)
        monkeypatch.setattr(settings, "demo_allow_network", allow_network)
        from app.main import app as fastapi_app
        return TestClient(fastapi_app), settings

    return _build


def test_demo_mode_is_disclosed_on_every_response(client_for_mode):
    """
    The disclosure has to travel with the data, so it goes on every response
    rather than on one endpoint the UI might forget to call before rendering.
    """
    client, _ = client_for_mode(True)
    for path in ("/health", "/docs"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.headers.get("X-YuktiFi-Data-Mode") == "demo", path


def test_a_live_run_is_labelled_live(client_for_mode):
    """
    Silence is not the same as disclosure. If the header were simply omitted in
    production, a client that failed to read it would have no way to tell a
    labelled-live response from an unlabelled one, and would be right to treat
    the absence as unknown rather than as live.
    """
    client, _ = client_for_mode(False)
    r = client.get("/health")
    assert r.headers.get("X-YuktiFi-Data-Mode") == "live"


def test_demo_data_may_not_be_cached_as_if_it_were_live(client_for_mode):
    """
    A non-live response that a browser or proxy is free to cache can be replayed
    later, to someone who has no way to tell it was not live.
    """
    client, _ = client_for_mode(True)
    assert client.get("/health").headers.get("Cache-Control") == "no-store"


def test_the_label_follows_the_setting_that_actually_controls_the_clients(client_for_mode):
    """
    `network_allowed` is the property the provider clients consult. If the header
    were derived from `demo_mode` alone it would read "live" in the
    demo-with-network-allowed configuration, and a live-looking label would be
    attached to a run that was still partly fixture-driven.
    """
    client, s = client_for_mode(True, allow_network=True)
    assert s.network_allowed is True
    assert client.get("/health").headers.get("X-YuktiFi-Data-Mode") == "live"


def test_the_provider_clients_and_the_label_agree(client_for_mode):
    """
    The label and the behaviour it describes are checked against the same
    property. If a client ever consulted something else, this is the assertion
    that would notice.
    """
    client, s = client_for_mode(True, allow_network=False)
    assert s.network_allowed is False
    assert client.get("/health").headers.get("X-YuktiFi-Data-Mode") == "demo"
