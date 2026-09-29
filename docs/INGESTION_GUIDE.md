# Data Ingestion & Pipeline Operations Guide (UYDF-1.0)
**Problem Statement:** SIH 2026 PS 26091 — *YuktiFi Universal Data Layer*

---

## 1. Overview

This guide provides end-to-end instructions for running, extending, and maintaining the **Universal Yukti Data Pipeline** across new districts, state-level census repositories, or new survey publications.

---

## 2. Prerequisites & Environment Setup

Ensure Python 3.11+ is installed with dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Verify optional geospatial and tabular dependencies:
```bash
pip install openpyxl pandas pydantic fastapi sqlalchemy
```

---

## 3. Running the Universal Pipeline

To scan, parse, normalize, and build the canonical data artifacts from a raw source directory (e.g. `Documents SIH 26`):

```bash
# From repository root
python data_pipeline/build_universal_dataset.py --source-dir "D:\Ai workshop\Documents SIH 26" --output-dir "data/universal"
```

### Output Summary:
The pipeline produces the canonical artifact tree in `data/universal/`:
- `inventory/inventory_manifest.json` — Discovered files & SHA-256 hashes.
- `catalog/dataset_catalog.json` — Normalized dataset metadata.
- `evidence/evidence_records.json` — UYEC-1.0 evidence records.
- `geography/geography_hierarchy.json` — LGD geographic directory.
- `spatial/spatial_inventory.json` — GeoTIFF & remote sensing assets.
- `documents/document_chunks.json` — Semantic RAG chunks.
- `mappings/business_mappings.json` — Business category demand matrices.
- `validation/validation_report.json` — Quality validation & quarantine report.
- `manifest.json` — Complete execution manifest.

---

## 4. Seeding the RAG Knowledge Store

To index official scheme guidelines, subsidy rules, and technical manuals into the SQLite knowledge store:

```bash
# Seed official corpus and ingested project documents
python -m app.rag.seed_corpus
```

---

## 5. Running the Test Suite

Run the full automated test suite to verify end-to-end integrity:

```bash
# Run Universal Data Layer, RAG, and Evidence tests
python -m pytest backend/tests/test_universal_data_layer.py backend/tests/test_rag_evaluation.py backend/tests/test_phase1_phase2_rag.py -v
```

Expected output:
```
============================= 20 passed in 7.71s ==============================
```

---

## 6. Adding a New Dataset Parser

To add support for a new data format or government portal:
1. Create a parser module in `data_pipeline/parsers/your_parser.py`.
2. Implement the standard parsing interface:
   ```python
   def parse_your_format(file_path: Path, dataset_id: str) -> list[UniversalEvidenceRecord]:
       # Extract, normalize, and yield UniversalEvidenceRecord objects
       ...
   ```
3. Register the parser in `data_pipeline/build_universal_dataset.py`.
4. Run validation and update regression tests in `backend/tests/test_universal_data_layer.py`.
