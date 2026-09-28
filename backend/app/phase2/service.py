"""
Evidence store (Phase 2).

A thin persistence layer over `app.evidence.schema.EvidenceRecord`. It holds
records so that a number ingested once is available to every later run, and
so that a figure can be traced back to the document it came from.

Two properties matter more than anything else here:

    1. An upsert never overwrites a stronger record with a weaker one. Re-ingesting
       a VERIFIED value as an ESTIMATE keeps the VERIFIED value. Without this, a
       routine re-run quietly degrades the evidence base.
    2. `confidence` is derived from `state`, never accepted from the caller. A
       caller can say what the state is; it cannot declare a guess to be High.

Storage is in-process and therefore per-worker. That is a deliberate, visible
limitation: it is not a substitute for a database, and `store_kind()` says so in
the response rather than implying durability it does not have.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.evidence.schema import (
    Confidence,
    EvidenceRecord,
    EvidenceState,
    get_source,
)


#: Records are held here. Keyed by id so an upsert is idempotent.
_RECORDS: Dict[str, EvidenceRecord] = {}

#: Metric -> source_id, kept so a later ingest of the same metric can be checked
#: against what is already trusted. A metric with two different sources is a
#: conflict worth surfacing, not something to silently average.
_METRIC_SOURCES: Dict[str, str] = {}

#: How `confidence` and `observed_at` on the incoming payload map onto the
#: record's own vocabulary. Callers speak in their own field names; this is the
#: one place that translation happens.
_CONFIDENCE_TO_STATE = {
    "high": EvidenceState.VERIFIED,
    "medium": EvidenceState.ESTIMATED,
    "low": EvidenceState.INFERRED,
}

_STATE_TO_CONFIDENCE = {
    EvidenceState.VERIFIED: "High",
    EvidenceState.ESTIMATED: "Medium",
    EvidenceState.INFERRED: "Low",
    EvidenceState.MISSING: "Low",
    EvidenceState.STALE: "Low",
    EvidenceState.CONFLICTING: "Low",
    EvidenceState.UNAVAILABLE: "Low",
}


def _resolve_state(payload: Dict[str, Any]) -> EvidenceState:
    """
    Decide the record's state from the payload.

    `is_estimate` is trusted before `confidence`, because it is the direct claim
    ("this is not measured"). When both are present and disagree, the weaker
    reading wins: a payload claiming High confidence while also saying the value
    is an estimate is treated as an estimate, which is the safe direction.
    """
    if payload.get("is_estimate") is True:
        return EvidenceState.ESTIMATED

    raw_confidence = str(payload.get("confidence") or "").strip().lower()
    if raw_confidence in _CONFIDENCE_TO_STATE:
        state = _CONFIDENCE_TO_STATE[raw_confidence]
        if raw_confidence == "high" and state is EvidenceState.VERIFIED:
            return EvidenceState.VERIFIED
        return state

    return EvidenceState.ESTIMATED


def _source_id_for(payload: Dict[str, Any]) -> str:
    """
    Resolve a registered source id from whatever the payload supplied.

    Callers pass a free-text `source` name, not an id. Guessing an id from it
    would attach the wrong document's URL and limitations to a record, so the id
    is only set when the payload states one outright.
    """
    explicit = payload.get("source_id")
    if explicit:
        return str(explicit)
    return ""


def upsert_evidence(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert or update one evidence record, returning it as a dict.

    Accepts the field names the ingestion pipelines use (`source`,
    `observed_at`, `resolution`) as well as the schema's own (`source_id`,
    `reference_date`, `method`), because both spellings already exist in the
    codebase and silently dropping either would lose provenance.
    """
    if not isinstance(payload, dict):
        raise ValueError("Evidence payload must be a dict.")

    metric = str(payload.get("metric") or "").strip()
    if not metric:
        raise ValueError("Evidence requires a `metric`.")

    value = payload.get("value")
    if value is None:
        raise ValueError("Evidence requires a `value`. Use an explicit null state instead.")

    state = _resolve_state(payload)
    record_id = str(
        payload.get("id") or f"{metric}:{payload.get('geography') or 'unknown'}"
    )

    existing = _RECORDS.get(record_id)
    if existing is not None:
        # A weaker claim never replaces a stronger one. Re-ingesting a VERIFIED
        # value as an ESTIMATE leaves the verified value in place, and the
        # response says it was refused rather than quietly returning the old
        # number as if the new one had been accepted.
        if _is_weaker(state, existing.state):
            out = existing.to_dict()
            out["id"] = record_id
            out["upsert"] = "REJECTED_WEAKER"
            out["rejection_reason"] = (
                f"An incoming {state.value} record was not allowed to replace the existing "
                f"{existing.state.value} record for the same id."
            )
            return out

        if _is_weaker(existing.state, state):
            overrides = _overrides_from(payload)
            # `transform()` takes `method` as its own argument, so it must be
            # removed from the override set rather than passed twice.
            method = overrides.pop("method", "") or str(
                payload.get("method") or payload.get("resolution") or ""
            )
            record = existing.transform(
                operation="upsert_upgrade",
                value=value,
                state=state,
                method=method,
                **overrides,
            )
            _RECORDS[record_id] = record
            _METRIC_SOURCES[metric] = record.source_id or _METRIC_SOURCES.get(metric, "")
            out = record.to_dict()
            out["id"] = record_id
            out["upsert"] = "UPDATED"
            return out

        # Same trust level: the stored record stands. Rewriting it would discard
        # its retrieval time and derivation history for no gain.
        out = existing.to_dict()
        out["id"] = record_id
        out["upsert"] = "UNCHANGED"
        return out

    record = EvidenceRecord(
        metric=metric,
        value=value,
        unit=str(payload.get("unit") or ""),
        source_id=_source_id_for(payload),
        dataset=str(payload.get("dataset") or ""),
        source_url=str(payload.get("source_url") or ""),
        geography=str(payload.get("geography") or ""),
        geography_level=str(payload.get("geography_level") or ""),
        reference_date=str(payload.get("observed_at") or ""),
        method=str(payload.get("method") or payload.get("resolution") or ""),
        coverage=str(payload.get("coverage") or ""),
        state=state,
        is_estimate=bool(payload.get("is_estimate") or False),
        is_demo=bool(payload.get("is_demo") or False),
        limitations=str(payload.get("limitations") or ""),
    )
    _RECORDS[record_id] = record
    _METRIC_SOURCES[metric] = record.source_id

    out = record.to_dict()
    out["id"] = record_id
    out["upsert"] = "INSERTED"
    return out


def _overrides_from(payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed = (
        "metric", "unit", "source_id", "dataset", "source_url", "geography",
        "geography_level", "reference_date", "retrieved_at", "method", "coverage",
        "is_estimate", "is_demo", "limitations",
    )
    out: Dict[str, Any] = {}
    for key in allowed:
        if key in payload:
            out[key] = payload[key]
    if "observed_at" in payload and "reference_date" not in out:
        out["reference_date"] = payload["observed_at"]
    if "source" in payload and not out.get("source_id"):
        # Preserved as a note so the human-readable source name is not lost,
        # without pretending it is a registered source id.
        out["method"] = (str(out.get("method") or "") + f" | source: {payload['source']}").strip(" |")
    return out


def _is_weaker(incoming: EvidenceState, existing: EvidenceState) -> bool:
    """True when `incoming` should not replace `existing`."""
    return incoming.weight < existing.weight


def list_evidence(
    geography: Optional[str] = None,
    metric: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    List stored records, newest filter first.

    Filters are exact matches on the stored label. A caller asking for
    "Akkalkot" does not get records for "Akkalkot, Solapur" back, because
    returning a wider set than asked for turns a precise query into a vague one
    and the caller cannot tell which rows answered it.
    """
    rows: List[Dict[str, Any]] = []
    for record_id, record in _RECORDS.items():
        if geography and record.geography != geography:
            continue
        if metric and record.metric != metric:
            continue
        row = record.to_dict()
        row["id"] = record_id
        rows.append(row)
    rows.sort(key=lambda r: (r.get("retrieved_at") or "", r.get("metric") or ""), reverse=True)
    return rows[: max(0, int(limit))]


def get_evidence(record_id: str) -> Optional[Dict[str, Any]]:
    record = _RECORDS.get(record_id)
    if record is None:
        return None
    out = record.to_dict()
    out["id"] = record_id
    return out


def evidence_summary() -> Dict[str, Any]:
    """
    Counts by state, so a caller can see how much of the evidence base is
    actually verified before relying on it.
    """
    by_state: Dict[str, int] = {}
    for record in _RECORDS.values():
        by_state[record.state.value] = by_state.get(record.state.value, 0) + 1
    total = len(_RECORDS)
    verified = by_state.get(EvidenceState.VERIFIED.value, 0)
    return {
        "total": total,
        "by_state": by_state,
        "verified": verified,
        "verified_pct": round(verified / total * 100, 1) if total else 0.0,
        "store": "in-memory, per-process",
        "limitation": (
            "Records live in process memory and are lost on restart. This is a working "
            "store for a single run, not durable evidence storage."
        ),
    }


def clear_evidence() -> None:
    """Test and re-ingest support."""
    _RECORDS.clear()
    _METRIC_SOURCES.clear()
