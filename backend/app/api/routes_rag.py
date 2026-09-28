"""
RAG query and ingestion endpoints.

`POST /ingest` previously accepted any filesystem path and read it:

    p = Path(req.path)
    if not p.exists() or not p.is_file(): raise HTTPException(404)

With no root restriction that is an arbitrary file read exposed on the API - an
attacker (or a careless script) could name `backend/.env`, a private key, or any
file on the host and have its contents chunked, embedded and returned in the
retrieval results. The 404 check confirms the file exists, which is the opposite
of what a guard should do here.

Ingestion is now confined to the directories this application owns, resolved
through `paths.py` so it stays portable. The check is done on the *resolved* path
and then verified to be inside the allowed root, so neither `..` traversal nor a
symlink pointing outside the tree can escape it. A relative path is interpreted
against the allowed roots rather than the process working directory, which would
otherwise make the allowlist depend on where the server happened to be started.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.paths import DATA_DIR, RAG_DOCUMENTS_DIR, RAW_DIR, SEED_DIR
from app.rag.service import answer
from app.rag.ingest import ingest_file

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# The only directories a request may read from. Ingestion exists to load
# reference and source material; it is not a general file-upload API.
ALLOWED_INGEST_ROOTS: tuple[Path, ...] = (
    RAG_DOCUMENTS_DIR,
    SEED_DIR,
    RAW_DIR,
    DATA_DIR,
)

ALLOWED_SUFFIXES = {".txt", ".md", ".csv", ".json", ".pdf"}


class RagQuery(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=20)
    use_llm: bool = True


class RagIngest(BaseModel):
    path: str = Field(min_length=1)
    source: str = "local"
    source_url: str = ""
    effective_date: str = ""


def _resolve_ingest_path(raw: str) -> Path:
    """Resolve `raw` inside the allowlist, or raise HTTPException."""
    candidate = Path(raw)

    # A relative path is taken against the RAG documents directory. Anchoring it
    # to the process CWD would let the allowlist mean different things depending
    # on the launch directory.
    if not candidate.is_absolute():
        candidate = RAG_DOCUMENTS_DIR / candidate

    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:  # unreadable, or a symlink loop
        raise HTTPException(status_code=400, detail=f"Path could not be resolved: {exc}")

    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Suffix '{resolved.suffix}' is not ingestible. "
                f"Allowed: {', '.join(sorted(ALLOWED_SUFFIXES))}."
            ),
        )

    # is_relative_to on the resolved path is what defeats `..` and symlinks: both
    # are collapsed by resolve() before the containment test.
    if not any(
        resolved == root.resolve() or resolved.is_relative_to(root.resolve())
        for root in ALLOWED_INGEST_ROOTS
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Path is outside the ingest allowlist. Ingestion is limited to "
                + ", ".join(str(r.relative_to(DATA_DIR.parent)) for r in ALLOWED_INGEST_ROOTS)
                + "."
            ),
        )

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return resolved


@router.post("/query")
def rag_query(req: RagQuery):
    return answer(req.query, req.top_k, req.use_llm)


@router.post("/ingest")
def rag_ingest(req: RagIngest):
    resolved = _resolve_ingest_path(req.path)
    try:
        return ingest_file(str(resolved), req.source, req.source_url, req.effective_date)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
