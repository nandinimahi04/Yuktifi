# Phase 6 — Census Population & Household Evidence

YUKTI now supports an official Census 2011 Primary Census Abstract (PCA) population pipeline.

## Official source

**Basic Population Figures of India/State/District/Sub-District/Village — 2011**

https://censusindia.gov.in/nada/index.php/catalog/42554

The Census Population Finder states that its PCA tables provide indicators for districts, sub-districts, towns, villages and wards, including households, sex-disaggregated population, age groups and work status.

## Flow

```text
Canonical location
      ↓
Official Census PCA file
      ↓
Exact village/code match
      ↓
Population + household profile
      ↓
Evidence DB + provenance
      ↓
Market / feasibility engines
```

## Critical rule

Census 2011 is historical evidence. It must be labelled with `observed_at=2011` and must not be presented as a current 2026 population count.

If the exact canonical village is absent, YUKTI returns `unavailable`. It does **not** silently replace it with district or state population.

## Ingestion

```bash
python -c "from app.data_ingestion.census_population import ingest_to_evidence; print(ingest_to_evidence('PATH_TO_OFFICIAL_CENSUS_FILE', LOCATION_CONTEXT))"
```

API:

```http
POST /api/v2/census/population/ingest
```

Payload:

```json
{
  "path": "backend/data/raw/census/2011-IndiaStateDistSbDistVill-0000.xlsx",
  "location_context": {
    "canonical_label": "<village>, <subdistrict>, <district>, Maharashtra",
    "state": "Maharashtra",
    "district": "Solapur",
    "subdistrict": "Akkalkot",
    "village": "<village>",
    "codes": {
      "village_code": "<official code>"
    }
  }
}
```

The original government download should remain untouched under `backend/data/raw/census/`; normalized/derived records belong in the evidence layer.
