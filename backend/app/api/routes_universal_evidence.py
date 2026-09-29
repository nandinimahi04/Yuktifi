"""
API Router for Universal Yukti Data & Evidence Layer (UYEC-1.0).
Provides standard REST endpoints for querying evidence, provenance, catalogs, quality audits, and RAG.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.data_layer.universal.retrieval_service import (
    retrieve_evidence,
    retrieve_documents,
    get_dataset_catalog,
    get_evidence_by_id,
    get_data_quality_report
)

router = APIRouter(prefix="/api", tags=["Universal Evidence & Data Layer"])

class RAGQueryRequest(BaseModel):
    query: str
    business_category: Optional[str] = None
    location: Optional[str] = None
    source_filters: Optional[List[str]] = None
    top_k: int = 5

@router.get("/evidence/datasets")
def list_evidence_datasets(
    source_type: Optional[str] = Query(None, description="Filter by source type (e.g. OFFICIAL_STATISTICAL)"),
    search: Optional[str] = Query(None, description="Search term in name or organization")
):
    """Lists official datasets in the Universal Dataset Catalog."""
    catalog = get_dataset_catalog(source_type=source_type, query=search)
    return {
        "datasets": catalog,
        "total_datasets": len(catalog),
        "schema_version": "UYDF-1.0"
    }

@router.get("/evidence/search")
def search_evidence(
    business_category: Optional[str] = Query(None, description="e.g. kirana, dairy, agriculture"),
    location: Optional[str] = Query(None, description="e.g. Solapur, Akkalkot"),
    metric: Optional[str] = Query(None, description="e.g. population, consumption, price"),
    limit: int = Query(50, ge=1, le=200)
):
    """Searches normalized evidence records with provenance, confidence, and quality envelope."""
    metrics_list = [metric] if metric else None
    return retrieve_evidence(
        business_category=business_category,
        location=location,
        metrics=metrics_list,
        limit=limit
    )

@router.get("/evidence/{evidence_id}")
def get_single_evidence(evidence_id: str):
    """Retrieves a single evidence record by ID."""
    record = get_evidence_by_id(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")
    return record

@router.get("/evidence/provenance/{evidence_id}")
def get_single_evidence_provenance(evidence_id: str):
    """Retrieves the full origin lineage, file provenance, and transformation audit for an evidence record."""
    record = get_evidence_by_id(evidence_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Evidence record '{evidence_id}' not found.")
    return {
        "evidence_id": record["evidence_id"],
        "dataset_id": record["dataset_id"],
        "provenance": record.get("provenance", {}),
        "quality": record.get("quality", {}),
        "limitations": record.get("limitations", [])
    }

@router.get("/data/catalog")
def get_catalog_summary():
    """Returns the full Universal Dataset Catalog."""
    catalog = get_dataset_catalog()
    return {
        "catalog": catalog,
        "total": len(catalog),
        "version": "UYDF-1.0"
    }

@router.get("/data/quality")
def get_quality_report():
    """Returns the validation, quarantine, and duplicate detection audit report."""
    return get_data_quality_report()

@router.get("/rag/search")
def search_rag_documents(
    query: str = Query(..., description="Query string"),
    business_category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    top_k: int = Query(5, ge=1, le=20)
):
    """Performs hybrid semantic and lexical retrieval across official document monographs."""
    return retrieve_documents(
        query=query,
        business_category=business_category,
        location=location,
        top_k=top_k
    )

@router.get("/rag/sources")
def list_rag_sources():
    """Lists all official monographs currently indexed in the RAG store."""
    from app.rag.store import ensure_schema
    from app.core.db import engine
    from sqlalchemy import text
    ensure_schema()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, title, source, source_url, effective_date FROM yukti_rag_documents")).mappings().all()
    return {
        "documents": [dict(r) for r in rows],
        "total_documents": len(rows)
    }

@router.post("/rag/query")
def query_rag_endpoint(payload: RAGQueryRequest):
    """Structured RAG retrieval endpoint for copilot and explanation services."""
    return retrieve_documents(
        query=payload.query,
        business_category=payload.business_category,
        location=payload.location,
        source_filters=payload.source_filters,
        top_k=payload.top_k
    )
