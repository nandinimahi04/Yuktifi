from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import Any

from app.phase2.service import upsert_evidence

SOURCE_URL = "https://censusindia.gov.in/nada/index.php/catalog/42554"
SOURCE_DATASET = "Basic Population Figures of India/State/District/Sub-District/Village - 2011"
SOURCE_YEAR = "2011"

ALIASES = {
    "state_name": "state",
    "district_name": "district",
    "sub_district": "subdistrict",
    "sub_district_name": "subdistrict",
    "subdistrict_name": "subdistrict",
    "taluka": "subdistrict",
    "tehsil": "subdistrict",
    "village_name": "village",
    "village_town_name": "village",
    "town_name": "village",
    "location_name": "village",
    "state_code": "state_code",
    "district_code": "district_code",
    "subdistrict_code": "subdistrict_code",
    "sub_district_code": "subdistrict_code",
    "village_code": "village_code",
    "town_code": "village_code",
    "location_code": "location_code",
    "number_of_households": "households",
    "no_of_households": "households",
    "households": "households",
    "total_population": "population",
    "total_population_persons": "population",
    "population_total": "population",
    "population_persons": "population",
    "population_males": "male_population",
    "total_population_males": "male_population",
    "population_females": "female_population",
    "total_population_females": "female_population",
    "population_0_6_years_persons": "age_0_6",
    "population_in_age_group_0_6_years_persons": "age_0_6",
    "scheduled_caste_population_persons": "sc_population",
    "scheduled_tribe_population_persons": "st_population",
    "literates_persons": "literates",
    "population_literate": "literates",
    "non_workers_persons": "non_workers",
}

REQUIRED = {"state", "district", "village", "population"}


def _key(value: Any) -> str:
    s = "" if value is None else str(value).strip().casefold()
    out = "".join(ch if ch.isalnum() else "_" for ch in s)
    out = "_".join(x for x in out.split("_") if x)
    return ALIASES.get(out, out)


def _norm(value: Any) -> str:
    s = "" if value is None else str(value).casefold().strip()
    return "".join(ch for ch in s if ch.isalnum())


def _row(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        out[_key(k)] = v
    return out


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [_row(r) for r in csv.DictReader(f)]


def _read_xlsx(path: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    for ws in wb.worksheets:
        it = ws.iter_rows(values_only=True)
        try:
            headers = next(it)
        except StopIteration:
            continue
        normalized = [_key(h) for h in headers]
        if not any(normalized):
            continue
        for values in it:
            if any(v is not None for v in values):
                rows.append(_row(dict(zip(normalized, values))))
    return rows


def read_source(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            members = [n for n in zf.namelist() if Path(n).suffix.lower() in {".csv", ".xlsx"} and not n.endswith("/")]
            if not members:
                raise ValueError("Census ZIP contains no CSV/XLSX resource")
            # Prefer PCA/village resources over unrelated files.
            members.sort(key=lambda n: (0 if any(x in n.casefold() for x in ("pca", "village", "population")) else 1, n))
            extracted = Path("/tmp") / f"yukti_census_{Path(members[0]).name}"
            extracted.write_bytes(zf.read(members[0]))
            return read_source(extracted)
    if path.suffix.lower() == ".csv":
        return _read_csv(path)
    if path.suffix.lower() == ".xlsx":
        return _read_xlsx(path)
    raise ValueError("Unsupported Census source format; use CSV, XLSX or ZIP")


def validate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Census source contains no rows")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError(f"Census source missing required columns: {sorted(missing)}")
    numeric = 0
    for r in rows:
        try:
            if float(r["population"]) >= 0:
                numeric += 1
        except (TypeError, ValueError):
            pass
    if numeric == 0:
        raise ValueError("Census source contains no valid population values")
    return {"rows": len(rows), "numeric_population_rows": numeric, "columns": sorted(rows[0])}


def _match(row: dict[str, Any], context: dict[str, Any]) -> bool:
    # Prefer official codes whenever both datasets expose them.
    code_pairs = [
        ("state_code", "state_code"),
        ("district_code", "district_code"),
        ("subdistrict_code", "subdistrict_code"),
        ("village_code", "village_code"),
    ]
    used_code = False
    for field, context_field in code_pairs:
        rv, cv = row.get(field), context.get("codes", {}).get(context_field)
        if rv not in (None, "") and cv not in (None, ""):
            used_code = True
            if _norm(rv) != _norm(cv):
                return False
    if used_code:
        return True

    # Fall back to the canonical hierarchy. Never substitute district-only data.
    for field in ("state", "district", "subdistrict", "village"):
        target = context.get(field)
        if target not in (None, "") and _norm(row.get(field)) != _norm(target):
            return False
    return bool(context.get("village"))


def summarize_location(rows: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    selected = [r for r in rows if _match(r, context)]
    if not selected:
        return {
            "status": "unavailable",
            "reason": "no_exact_village_match",
            "matched_rows": 0,
            "source_year": SOURCE_YEAR,
        }

    # PCA should normally have one Total row. If multiple residence rows exist,
    # prefer Total, then Rural, and never sum Total + Rural + Urban together.
    residence = lambda r: _norm(r.get("residence") or r.get("urban_rural") or r.get("area_type"))
    total = [r for r in selected if residence(r) in {"total", ""}]
    chosen = total[0] if total else selected[0]

    numeric_fields = {
        "population": "persons",
        "households": "households",
        "male_population": "persons",
        "female_population": "persons",
        "age_0_6": "persons",
        "sc_population": "persons",
        "st_population": "persons",
        "literates": "persons",
        "non_workers": "persons",
    }
    metrics = {}
    for field, unit in numeric_fields.items():
        value = chosen.get(field)
        if value in (None, ""):
            continue
        try:
            n = float(value)
            metrics[field] = {"value": int(n) if n.is_integer() else n, "unit": unit}
        except (TypeError, ValueError):
            continue

    return {
        "status": "matched",
        "source_year": SOURCE_YEAR,
        "matched_rows": len(selected),
        "selected_row_type": residence(chosen) or "unspecified",
        "metrics": metrics,
    }


def ingest_to_evidence(path: str | Path, context: dict[str, Any]) -> dict[str, Any]:
    rows = read_source(path)
    validation = validate_rows(rows)
    summary = summarize_location(rows, context)
    label = context.get("canonical_label") or ", ".join(
        x for x in [context.get("village"), context.get("subdistrict"), context.get("district"), context.get("state")] if x
    )

    if summary["status"] != "matched":
        return {"validation": validation, "summary": summary, "evidence": None}

    evidence = upsert_evidence({
        "id": "census_pca_2011_" + _norm(label),
        "metric": "census_population_profile",
        "value": json.dumps(summary["metrics"], sort_keys=True),
        "unit": "mixed Census PCA indicators",
        "source": "Office of the Registrar General & Census Commissioner, India",
        "dataset": SOURCE_DATASET,
        "source_url": SOURCE_URL,
        "geography": label,
        "geography_level": "village",
        "observed_at": SOURCE_YEAR,
        "resolution": "village",
        "method": "exact canonical village match using official code when available; otherwise normalized hierarchy match",
        "confidence": "High",
        "is_estimate": False,
        "limitations": "Census 2011 is historical baseline evidence and is not a 2026 population estimate. No district-level substitution is performed.",
    })
    return {"validation": validation, "summary": summary, "evidence": evidence}
