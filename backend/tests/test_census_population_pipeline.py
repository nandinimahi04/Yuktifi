from pathlib import Path
import csv

from app.data_ingestion.census_population import read_source, validate_rows, summarize_location, ingest_to_evidence


def _write(path: Path):
    rows = [
        {"State": "Maharashtra", "District": "Solapur", "Sub-District": "Akkalkot", "Village": "Chincholi (Najik)", "Village Code": "562788", "Residence": "Total", "Number of Households": 321, "Total Population": 1456, "Total Population Males": 752, "Total Population Females": 704, "Literates (Persons)": 1012},
        {"State": "Maharashtra", "District": "Solapur", "Sub-District": "Akkalkot", "Village": "Other Village", "Village Code": "999999", "Residence": "Total", "Number of Households": 50, "Total Population": 200},
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)


def test_exact_village_match(tmp_path):
    p = tmp_path / "pca.csv"; _write(p)
    rows = read_source(p)
    assert validate_rows(rows)["numeric_population_rows"] == 2
    ctx = {"state":"Maharashtra","district":"Solapur","subdistrict":"Akkalkot","village":"Chincholi (Najik)","codes":{"village_code":"562788"}}
    summary = summarize_location(rows, ctx)
    assert summary["status"] == "matched"
    assert summary["metrics"]["population"]["value"] == 1456
    assert summary["metrics"]["households"]["value"] == 321


def test_no_district_substitution(tmp_path):
    p = tmp_path / "pca.csv"; _write(p)
    rows = read_source(p)
    ctx = {"state":"Maharashtra","district":"Solapur","subdistrict":"Akkalkot","village":"Missing Village","codes":{"village_code":"111111"}}
    assert summarize_location(rows, ctx)["status"] == "unavailable"


def test_evidence_created_for_exact_match(tmp_path):
    p = tmp_path / "pca.csv"; _write(p)
    ctx = {"canonical_label":"Chincholi (Najik), Akkalkot, Solapur, Maharashtra","state":"Maharashtra","district":"Solapur","subdistrict":"Akkalkot","village":"Chincholi (Najik)","codes":{"village_code":"562788"}}
    result = ingest_to_evidence(p, ctx)
    assert result["evidence"]["metric"] == "census_population_profile"
    assert result["evidence"]["is_estimate"] is False
