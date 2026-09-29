# Universal Yukti Data & Evidence Architecture (UYDF-1.0)
**Problem Statement:** SIH 2026 PS 26091 — *AI-Driven Hyper-Local Business Advisory and Financial Structuring Assistant for Rural Micro-Entrepreneurs*

---

## 1. Executive Summary & Core Principle

The **Universal Yukti Data & Evidence Layer (UYDF-1.0)** is the single, canonical, immutable foundation for all external, official, geographic, statistical, remote sensing, and market datasets ingested into the YuktiFi platform.

### The Canonical Operational Pipeline:
```
┌──────────────────────────┐
│   OFFICIAL DATA REPO     │ (Census, LGD, MoSPI, NFHS, WorldPop GeoTIFF, ISRO Bhuvan)
└────────────┬─────────────┘
             │ Ingest & Parse
             ▼
┌──────────────────────────┐
│   DATA & EVIDENCE LAYER  │ (Normalizers, Quality Validators, Deduplication, Canonical Catalogs)
└────────────┬─────────────┘
             │ Retrieves Verified Facts (Population, Land, Schemes, Infrastructure)
             ▼
┌──────────────────────────┐
│  DETERMINISTIC ENGINES   │ (Financial Engine, Market Snapshot, Risk Engine, Feasibility)
└────────────┬─────────────┘
             │ Mathematical Decisions & Projections (DSCR, EMI, Payback, Break-even)
             ▼
┌──────────────────────────┐
│       LLM LAYER          │ (Explains recommendations in local languages without inventing facts)
└──────────────────────────┘
```

> **CORE LAW OF YUKTIFI:**  
> `DATABASE CALCULATES → RAG RETRIEVES → DETERMINISTIC ENGINES DECIDE → LLM EXPLAINS`.  
> Generative AI / Large Language Models must **never** calculate financial metrics, invent demographic numbers, fabricate interest rates, or hallucinate competitor densities.

---

## 2. Architectural Pillars

The Universal Data Layer is structured around 5 core modules:

1. **Deterministic Data Pipeline (`data_pipeline/`)**:
   - Automated inventory scanning with SHA-256 fingerprinting.
   - Format-specific parsers for CSV, XLS/XLSX (including HTML tables), XML (MoSPI/Agri), PDF (semantic monographs), and GeoTIFF (ISRO/WorldPop rasters).
   - Standardizing normalizers for Currency (`INR`, `Lakhs`, `Crores`), Temporal (`YEAR`, `FINANCIAL_YEAR`, `CENSUS_ROUND`), and Geography (`LGD_VILLAGE`, `LGD_SUBDISTRICT`, `LGD_DISTRICT`).
   - Automated quality validation (schema conformity, range checks, null bounds, confidence scoring).

2. **Universal Yukti Evidence Contract (`UYEC-1.0`)**:
   - Strongly typed Pydantic models guaranteeing immutable provenance, audit trails, and strict data lineage down to source document page/row/cell.
   - Distinct classification of `ValueOrigin`: `DIRECT_OBSERVATION`, `STATISTICAL_ESTIMATE`, `DETERMINISTIC_CALCULATION`, `REMOTE_SENSING_DERIVED`, and `SURVEY_SAMPLE`.

3. **Canonical Catalogs & Master Directories**:
   - **Dataset Catalog (`dataset_catalog.py`)**: Structured metadata for 79+ official datasets and 5 monographs across 7 standard categories.
   - **Geography Catalog (`geography_catalog.py`)**: Canonical hierarchy covering LGD State, District, Sub-district (Taluka/Tehsil), and Village levels, complete with administrative aliases (e.g., Ahilyanagar ↔ Ahmadnagar).
   - **Business Mapping Taxonomy (`business_mapping.py`)**: Standard NIC/micro-enterprise sector taxonomy connecting official datasets to practical rural micro-enterprises.

4. **Hybrid RAG Knowledge Store (`backend/app/rag/`)**:
   - SQLite-backed BM25 document and chunk retrieval engine with term-frequency length normalization, query coverage boosting, and title matching multipliers.
   - Seeds official scheme rules, ICAR dairy manuals, PMEGP/MUDRA/PMFME guidelines, and Bhuvan spatial standards.

5. **Universal REST API & Retrieval Services (`/api/evidence/...`)**:
   - High-performance, cached query endpoints for instant parameter lookup, spatial summaries, dataset catalogs, quality audits, and scheme guidelines.

---

## 3. Directory Layout & Organization

```
d:/Nandini/Agents/SIH/work/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes_universal_evidence.py   # Universal evidence REST API endpoints
│   │   │   └── ...
│   │   ├── data_layer/
│   │   │   └── universal/
│   │   │       ├── evidence_contract.py       # UYEC-1.0 Data & Evidence Contract
│   │   │       ├── dataset_catalog.py         # 79-Dataset Master Metadata Catalog
│   │   │       ├── geography_catalog.py       # LGD Geography Master Directory
│   │   │       ├── business_mapping.py        # Micro-Enterprise NIC Mappings
│   │   │       └── retrieval_service.py       # Fast Cached In-Memory & Storage Service
│   │   ├── rag/
│   │   │   ├── store.py                       # BM25 RAG SQLite Knowledge Store
│   │   │   ├── service.py                     # Grounded RAG Query Service
│   │   │   ├── ingest.py                      # Recursive PDF/Document Ingest Engine
│   │   │   └── seed_corpus.py                 # Official Scheme Corpus Auto-Seeder
│   │   └── ...
│   └── tests/
│       ├── test_universal_data_layer.py       # 10/10 Comprehensive UYDF Test Suite
│       ├── test_rag_evaluation.py             # Grounded RAG Retrieval Benchmarks
│       └── test_phase1_phase2_rag.py          # Evidence Roundtrip & Integration Suite
├── data/
│   └── universal/                             # Canonical Generated Artifacts
│       ├── inventory/inventory_manifest.json  # SHA-256 Fingerprinted Source Inventory
│       ├── catalog/dataset_catalog.json       # Canonical Dataset Catalog
│       ├── evidence/evidence_records.json     # 2,192 Standardized Evidence Records
│       ├── geography/geography_hierarchy.json # Canonical LGD Geographic Entities
│       ├── spatial/spatial_inventory.json     # Remote Sensing & GeoTIFF Metadata
│       ├── documents/document_chunks.json     # 204 Semantic RAG Knowledge Chunks
│       ├── mappings/business_mappings.json    # Business Category Evidence Matrices
│       ├── validation/validation_report.json  # Data Quality & Quarantine Reports
│       └── manifest.json                      # Master Pipeline Execution Manifest
├── data_pipeline/                             # Universal Pipeline Source Code
│   ├── build_universal_dataset.py             # Main Pipeline Build Executable
│   ├── inventory_scanner.py                   # File Discovery & SHA-256 Hasher
│   ├── parsers/                               # CSV, XLS, XML, PDF, GeoTIFF Parsers
│   ├── normalizers/                           # Unit, Time, Geography Normalizers
│   └── validators/                            # Quality & Duplicate Validators
└── docs/                                      # Full Architecture & Design Manuals
```

---

## 4. Architectural Guarantees & Non-Negotiables

| Requirement | Implementation Guarantee |
| :--- | :--- |
| **No Invented Facts** | Every numeric fact returned by the API is linked to a `UniversalEvidenceRecord` with SHA-256 provenance hash, source document name, citation, and confidence score. |
| **Financial Determinism** | Projections (DSCR, ROI, EMI, Payback) are strictly calculated by `FinancialEngine` using standardized decimal arithmetic. |
| **Backward Compatibility** | Existing endpoints (`/api/market/...`, `/api/financial/...`, `/api/schemes/...`) continue operating without breakage while consuming the Universal Data Layer. |
| **Fault Tolerant Ingestion** | Zero-byte or corrupt files are automatically quarantined with explicit error logging in `validation_report.json` rather than crashing the ingestion pipeline. |
| **Sub-50ms Retrieval** | In-memory indexing and fast SQLite caching ensure sub-millisecond retrieval times for hyper-local advisory workflows. |
