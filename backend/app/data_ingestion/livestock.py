from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any

from app.phase2.service import upsert_evidence

SUPPORTED_SOURCE_URL = "https://kerala.data.gov.in/resource/maharashtra-20th-livestock-census-2019-village-wise"
SOURCE_DATASET = "Maharashtra 20th Livestock Census 2019 Village wise"

REQUIRED = {"district", "block", "village", "livestock_name", "gender", "value"}
ALIASES = {
    "district_as_per_source": "district",
    "district_as_per_lgd": "district",
    "town_or_block_name": "block",
    "village_or_ward_name": "village",
    "livestock": "livestock_name",
    "animal": "livestock_name",
    "sex": "gender",
    "count": "value",
}


def _norm_key(value: Any) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip()).strip("_")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        k = _norm_key(key)
        k = ALIASES.get(k, k)
        normalized[k] = value
    return normalized


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [_normalize_row(r) for r in csv.DictReader(f)]


def _read_xlsx(path: Path) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("XLSX ingestion requires openpyxl") from exc
    wb = load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    for ws in wb.worksheets:
        iterator = ws.iter_rows(values_only=True)
        try:
            headers = [str(x).strip() if x is not None else "" for x in next(iterator)]
        except StopIteration:
            continue
        for values in iterator:
            if not any(v is not None for v in values):
                continue
            rows.append(_normalize_row(dict(zip(headers, values))))
    return rows


def _read_file(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path)
    if suffix == ".xlsx":
        return _read_xlsx(path)
    raise ValueError(f"Unsupported livestock file format: {path.suffix}. Use CSV or XLSX after extracting the official resource.")


def read_source(path: str | Path) -> list[dict[str, Any]]:
    """Read the official resource or an extracted CSV/XLSX copy.

    ZIP files are accepted and the first CSV/XLSX member is parsed. The source
    file itself is never modified.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf:
            members = [n for n in zf.namelist() if Path(n).suffix.lower() in {".csv", ".xlsx"} and not n.endswith("/")]
            if not members:
                raise ValueError("ZIP contains no CSV/XLSX livestock resource")
            member = sorted(members)[0]
            extracted = Path("/tmp") / f"yukti_livestock_{Path(member).name}"
            extracted.write_bytes(zf.read(member))
            return _read_file(extracted)
    return _read_file(source)


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Livestock source contains no rows")
    missing = REQUIRED - set(rows[0].keys())
    if missing:
        raise ValueError(f"Livestock source missing required columns: {sorted(missing)}")
    valid = 0
    for row in rows:
        try:
            float(row["value"])
            valid += 1
        except (TypeError, ValueError):
            continue
    if valid == 0:
        raise ValueError("Livestock source has no numeric value rows")
    return {"rows": len(rows), "numeric_rows": valid, "columns": sorted(rows[0].keys())}


def _matches(value: str, target: str) -> bool:
    return _norm_key(value) == _norm_key(target)


def summarize_location(rows: list[dict[str, Any]], district: str, block: str, village: str | None = None) -> dict[str, Any]:
    """Aggregate livestock records for one Maharashtra block/village.

    This is a supply-context metric. It is not converted into milk demand or
    revenue and therefore does not create financial facts.
    """
    selected = [
        r for r in rows
        if _matches(str(r.get("district", "")), district)
        and _matches(str(r.get("block", "")), block)
        and (village is None or _matches(str(r.get("village", "")), village))
    ]
    totals: dict[str, float] = {}
    for row in selected:
        species = str(row.get("livestock_name", "")).strip()
        try:
            value = float(row.get("value", 0) or 0)
        except (TypeError, ValueError):
            continue
        totals[species] = totals.get(species, 0) + value
    return {
        "source_year": 2019,
        "district": district,
        "block": block,
        "village": village,
        "matched_rows": len(selected),
        "livestock_totals": {k: int(v) if v.is_integer() else v for k, v in sorted(totals.items())},
    }


def ingest_to_evidence(path: str | Path, district: str, block: str, village: str | None = None) -> dict[str, Any]:
    rows = read_source(path)
    validation = validate_rows(rows)
    summary = summarize_location(rows, district, block, village)
    geography = ", ".join(x for x in [village, block, district, "Maharashtra"] if x)
    evidence = upsert_evidence({
        "id": "livestock_2019_maharashtra_" + "_".join(_norm_key(x) for x in [district, block, village or "block"]),
        "metric": "livestock_population_by_species",
        "value": json.dumps(summary["livestock_totals"], sort_keys=True),
        "unit": "animals",
        "source": "Maharashtra Animal Husbandry, Dairy Development and Fisheries Department",
        "dataset": SOURCE_DATASET,
        "source_url": SUPPORTED_SOURCE_URL,
        "geography": geography,
        "geography_level": "village" if village else "block",
        "observed_at": "2019",
        "resolution": "village/block",
        "method": "direct aggregation of source livestock rows; no demand or financial conversion",
        "confidence": "High",
        "is_estimate": False,
        "limitations": "20th Livestock Census is a 2019 census; it is supply-context evidence and not a current 2026 animal count.",
    })
    return {"validation": validation, "summary": summary, "evidence": evidence}
