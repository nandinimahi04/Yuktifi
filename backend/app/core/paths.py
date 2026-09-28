"""
Single source of truth for filesystem locations inside the backend.

Every data directory used by the application is resolved here. Previously
`seed.py` and `data_service.py` each computed `backend/app/data`, which does not
exist in the repository, so seeding silently inserted nothing and every dataset
lookup returned an empty list. One resolver removes that class of bug and makes the
layout portable: all data lives under `backend/data/`, discoverable relative to this
file, so the project can be cloned to any path on any OS.

Layout:
    backend/data/seed/        JSON seed fixtures (categories, schemes, prices, ...)
    backend/data/source/      original source datasets as received
    backend/data/processed/   derived, merged datasets consumed at runtime
    backend/data/reference/   reference masters (location master, manifests)
    backend/data/raw/         raw downloads
    backend/data/manifests/   ingestion manifests
    backend/data/rag_documents/ bundled RAG corpus
"""
from pathlib import Path

# .../backend/app/core/paths.py -> parents[2] == .../backend
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]
REPO_ROOT: Path = BACKEND_DIR.parent

DATA_DIR: Path = BACKEND_DIR / "data"
SEED_DIR: Path = DATA_DIR / "seed"
PROCESSED_DIR: Path = DATA_DIR / "processed"
REFERENCE_DIR: Path = DATA_DIR / "reference"
RAW_DIR: Path = DATA_DIR / "raw"
MANIFEST_DIR: Path = DATA_DIR / "manifests"
RAG_DOCUMENTS_DIR: Path = DATA_DIR / "rag_documents"

DEFAULT_DB_PATH: Path = BACKEND_DIR / "yukti.db"


def ensure_dir(path: Path) -> Path:
    """Create a directory if absent and return it. Safe to call repeatedly."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_to_backend(path: Path | str) -> str:
    """Render a path relative to the repo root for logs and provenance records."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return str(path)
