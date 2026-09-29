"""
Universal Evidence Retrieval Service.
Provides unified query, filtering, confidence calculation, and hybrid RAG document retrieval
across the Universal Yukti Data Layer.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.rag.store import search as rag_search
from app.data_layer.universal.business_mapping import resolve_business_category

def _find_universal_dir() -> Path:
    # Check directory ancestry
    curr = Path(__file__).resolve()
    for _ in range(6):
        cand = curr / "data" / "universal"
        if (cand / "evidence" / "evidence_store.json").exists():
            return cand
        curr = curr.parent
    if Path("data/universal/evidence/evidence_store.json").exists():
        return Path("data/universal").resolve()
    return Path(__file__).resolve().parents[4] / "data" / "universal"

UNIVERSAL_DIR = _find_universal_dir()

_EVIDENCE_CACHE: Optional[List[Dict[str, Any]]] = None
_CATALOG_CACHE: Optional[List[Dict[str, Any]]] = None
_VALIDATION_CACHE: Optional[Dict[str, Any]] = None

def _load_evidence_cache() -> List[Dict[str, Any]]:
    global _EVIDENCE_CACHE
    if _EVIDENCE_CACHE is None:
        evi_file = _find_universal_dir() / "evidence" / "evidence_store.json"
        if evi_file.exists():
            try:
                with open(evi_file, "r", encoding="utf-8") as f:
                    _EVIDENCE_CACHE = json.load(f)
            except Exception:
                _EVIDENCE_CACHE = []
        else:
            _EVIDENCE_CACHE = []
    return _EVIDENCE_CACHE

def _load_catalog_cache() -> List[Dict[str, Any]]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        cat_file = _find_universal_dir() / "catalog" / "dataset_catalog.json"
        if cat_file.exists():
            try:
                with open(cat_file, "r", encoding="utf-8") as f:
                    _CATALOG_CACHE = json.load(f)
            except Exception:
                _CATALOG_CACHE = []
        else:
            _CATALOG_CACHE = []
    return _CATALOG_CACHE

def _load_validation_cache() -> Dict[str, Any]:
    global _VALIDATION_CACHE
    if _VALIDATION_CACHE is None:
        val_file = _find_universal_dir() / "validation" / "validation_report.json"
        if val_file.exists():
            try:
                with open(val_file, "r", encoding="utf-8") as f:
                    _VALIDATION_CACHE = json.load(f)
            except Exception:
                _VALIDATION_CACHE = {}
        else:
            _VALIDATION_CACHE = {}
    return _VALIDATION_CACHE

def retrieve_evidence(
    business_category: Optional[str] = None,
    location: Optional[str] = None,
    metrics: Optional[List[str]] = None,
    date_range: Optional[tuple[int, int]] = None,
    radius: Optional[float] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Retrieves normalized evidence records matching business category, geography, and metric requirements.
    """
    evidence_records = _load_evidence_cache()
    matched = []
    sources = set()

    loc_term = (location or "").strip().lower()
    cat_term = (business_category or "").strip().lower()

    for rec in evidence_records:
        # Business category filter
        if cat_term:
            rec_cats = [c.lower() for c in rec.get("business_context", {}).get("business_categories", [])]
            if rec_cats and not any(cat_term in c or c in cat_term for c in rec_cats):
                continue

        # Location filter
        if loc_term:
            entity = rec.get("entity", {})
            e_name = (entity.get("name") or "").lower()
            e_dist = (entity.get("district") or "").lower()
            e_sub = (entity.get("subdistrict") or "").lower()
            if loc_term not in e_name and loc_term not in e_dist and loc_term not in e_sub:
                continue

        # Metric filter
        if metrics:
            obs_metric = (rec.get("observation", {}).get("metric") or "").lower()
            if not any(m.lower() in obs_metric for m in metrics):
                continue

        matched.append(rec)
        sources.add(rec.get("provenance", {}).get("source", "Official Indian Dataset"))
        if len(matched) >= limit:
            break

    # If no exact match, return benchmark/macro records
    if not matched and evidence_records:
        matched = evidence_records[:10]
        for r in matched:
            sources.add(r.get("provenance", {}).get("source", "Official Indian Dataset"))

    confidence = "HIGH" if len(matched) >= 5 else ("MEDIUM" if len(matched) > 0 else "INSUFFICIENT_DATA")
    coverage = "FULL" if len(matched) >= 10 else ("PARTIAL" if len(matched) > 0 else "NONE")

    return {
        "results": matched,
        "total_results": len(matched),
        "sources": list(sources),
        "confidence": confidence,
        "coverage": coverage,
        "limitations": [
            "Values derived directly from Census 2011, MoSPI HCES 2023, and Local Government Directory (LGD) official records.",
            "Spatial competitor observations represent mapped POIs and should not be treated as absolute real-world census."
        ]
    }

def retrieve_documents(
    query: str,
    business_category: Optional[str] = None,
    location: Optional[str] = None,
    source_filters: Optional[List[str]] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Hybrid semantic and lexical retrieval over official monographs and policy guidelines.
    """
    enriched_query = query
    if business_category:
        enriched_query = f"{enriched_query} {business_category}"
    if location:
        enriched_query = f"{enriched_query} {location}"

    raw_results = rag_search(enriched_query, top_k=top_k * 2)
    filtered = []
    sources = set()

    for r in raw_results:
        src = r.get("source", "")
        if source_filters and not any(sf.lower() in src.lower() for sf in source_filters):
            continue
        filtered.append(r)
        if src:
            sources.add(src)
        if len(filtered) >= top_k:
            break

    return {
        "results": filtered,
        "total_results": len(filtered),
        "sources": list(sources),
        "confidence": "HIGH" if len(filtered) >= 3 else "MEDIUM",
        "coverage": "OFFICIAL_MONOGRAPHS",
        "limitations": ["Document chunks extracted verbatim from official District Census Handbooks and MoSPI HCES reports."]
    }

def get_dataset_catalog(source_type: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
    catalog = _load_catalog_cache()
    filtered = []
    for entry in catalog:
        if source_type and entry.get("source_type") != source_type:
            continue
        if query:
            q = query.lower()
            name = entry.get("dataset_name", "").lower()
            org = entry.get("organization", "").lower()
            if q not in name and q not in org:
                continue
        filtered.append(entry)
    return filtered

def get_evidence_by_id(evidence_id: str) -> Optional[Dict[str, Any]]:
    records = _load_evidence_cache()
    for r in records:
        if r.get("evidence_id") == evidence_id:
            return r
    return None

def get_data_quality_report() -> Dict[str, Any]:
    return _load_validation_cache()
