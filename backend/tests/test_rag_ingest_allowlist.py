"""
`POST /api/rag/ingest` took any filesystem path and read it.

The original body was four lines: build a Path, check it exists, hand it to the
ingestor. The existence check is what makes this an arbitrary *read* rather than
an arbitrary *write* - it confirms the attacker named a real file, which is
exactly the information an attacker wants from a probe. `backend/.env`, an SSH
key, or a mounted credential file would all pass it, and their contents would be
chunked, embedded and then retrievable through `/api/rag/query`.

These tests pin the allowlist. Note the check order, which is deliberate: the
extension is tested before containment, so a request for `app/main.py` is refused
as "not ingestible" without revealing whether a `.py` file exists there. Testing
containment first would turn the endpoint into an existence oracle for every
in-tree file.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.routes_rag import ALLOWED_INGEST_ROOTS, _resolve_ingest_path
from app.core.paths import DATA_DIR, RAG_DOCUMENTS_DIR, SEED_DIR
from app.main import app

PROBE_NAME = "_rag_allowlist_probe.txt"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def probe_file():
    """A real, ingestible file inside the allowlist."""
    RAG_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    target = RAG_DOCUMENTS_DIR / PROBE_NAME
    target.write_text("probe", encoding="utf-8")
    yield target
    target.unlink(missing_ok=True)


def test_absolute_path_outside_the_allowlist_is_refused():
    outside = DATA_DIR.parent / "app" / "core" / "notes.txt"
    with pytest.raises(Exception) as exc:
        _resolve_ingest_path(str(outside))
    assert "outside the ingest allowlist" in str(exc.value)


def test_traversal_out_of_the_allowlist_is_refused():
    """`..` is collapsed by resolve() before the containment test, so it cannot escape."""
    escape = str(RAG_DOCUMENTS_DIR / ".." / ".." / "app" / "notes.txt")
    with pytest.raises(Exception) as exc:
        _resolve_ingest_path(escape)
    assert "outside the ingest allowlist" in str(exc.value)


def test_a_file_inside_the_allowlist_resolves(probe_file):
    """The allowlist must not simply refuse everything - a corpus file is legitimate."""
    assert _resolve_ingest_path(str(probe_file)) == probe_file.resolve()


def test_relative_paths_are_anchored_to_the_corpus_not_the_cwd(probe_file):
    """
    A relative path anchored to the process working directory would make the
    allowlist mean different things depending on where the server was started,
    and would let `../../..` reach a different tree per deployment.
    """
    assert _resolve_ingest_path(PROBE_NAME).is_relative_to(RAG_DOCUMENTS_DIR.resolve())


def test_disallowed_extensions_are_refused_before_existence_is_considered():
    with pytest.raises(Exception) as exc:
        _resolve_ingest_path(str(SEED_DIR / "payload.sh"))
    assert "not ingestible" in str(exc.value)


def test_a_source_file_is_refused_by_extension_not_by_its_name():
    """
    The refusal must come from the extension allowlist. Anything that keyed off
    the filename (a blocklist of ".env", "id_rsa", "credentials") would be
    bypassed by renaming, and would tell the caller which names are interesting.
    """
    with pytest.raises(Exception) as exc:
        _resolve_ingest_path(str(DATA_DIR.parent / ".env"))
    assert "not ingestible" in str(exc.value)


def test_the_endpoint_answers_403_for_a_path_outside_the_allowlist(client):
    r = client.post("/api/rag/ingest", json={"path": str(DATA_DIR.parent.parent / "notes.txt")})
    assert r.status_code == 403


def test_the_endpoint_answers_403_for_traversal(client):
    r = client.post("/api/rag/ingest", json={"path": "../../../../etc/notes.txt"})
    assert r.status_code == 403


def test_the_endpoint_does_not_confirm_that_a_rejected_file_exists(client):
    """
    The old code answered 404 for a missing file and 200-with-contents for a
    present one, which let a caller enumerate the host. Every path outside the
    allowlist must now answer identically whether or not the target exists.

    Both probes below sit outside the allowlist and one of them does exist on
    disk, so the pair is only indistinguishable if the containment check runs
    before the existence check - which is what stops the endpoint being an
    existence oracle.
    """
    existing = DATA_DIR.parent / "requirements.txt"
    assert existing.is_file(), "probe expects requirements.txt to exist in the repo"

    present_outside = client.post("/api/rag/ingest", json={"path": str(existing)})
    absent_outside = client.post(
        "/api/rag/ingest", json={"path": str(existing.parent / "definitely_absent.txt")}
    )
    assert present_outside.status_code == 403
    assert absent_outside.status_code == 403
    assert present_outside.json() == absent_outside.json()


def test_allowlist_roots_are_inside_the_data_directory():
    """The roots themselves must be inside the tree this app owns."""
    for root in ALLOWED_INGEST_ROOTS:
        assert root.resolve().is_relative_to(DATA_DIR.resolve()), root
