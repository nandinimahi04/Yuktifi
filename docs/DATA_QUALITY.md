# Data Quality, Validation & Integrity Framework (UYDF-1.0)
**Problem Statement:** SIH 2026 PS 26091 — *YuktiFi Universal Data Layer*

---

## 1. Quality & Integrity Objectives

To prevent garbage-in garbage-out decisions in rural financial modeling, the Universal Data Layer enforces strict data hygiene, outlier detection, range constraints, and automated quarantine mechanisms.

---

## 2. Multi-Stage Validation Pipeline

```
Raw File Discovery ──► SHA-256 Fingerprint ──► Format Parser
                                                     │
                                                     ▼
Schema & Type Validation ◄── Null Bounds & Outlier Checks
        │
        ▼
Geographic LGD Hierarchy Resolution (Aliases & Codes)
        │
        ▼
Deduplication & Canonical Merging (Hash & Key Matrix)
        │
        ├── [FAIL / CORRUPT] ──► Quarantine (validation_report.json)
        └── [PASS] ──────────► Universal Evidence Store (evidence_records.json)
```

---

## 3. Validation Rules & Bounds

Implemented in `data_pipeline/validators/quality_validator.py`:

| Parameter | Type | Valid Range / Format | Validation Rule |
| :--- | :--- | :--- | :--- |
| `POPULATION` | Integer | $\ge 0 \text{ and } \le 10,000,000$ | Must be non-negative; villages $>50,000$ flagged for urban review. |
| `PERCENTAGE` | Float | $0.0 \le x \le 100.0$ | Clamped and normalized to percentage points. |
| `LATITUDE` | Float | $6.0 \le \text{lat} \le 38.0$ | Indian territorial envelope bounding box. |
| `LONGITUDE` | Float | $68.0 \le \text{lon} \le 98.0$ | Indian territorial envelope bounding box. |
| `LGD_CODE` | String/Int | 6 digits (Village), 4 digits (Taluka), 3 digits (District) | Validated against Ministry of Panchayati Raj master tables. |
| `CURRENCY` | Float | $\ge 0$ | Standardized to Indian Rupees (`INR`). |

---

## 4. Deduplication & Conflict Resolution

Implemented in `data_pipeline/validators/duplicate_detector.py`:
- **Identity Key:** `entity_id` + `metric_name` + `temporal_reference` (e.g., `562300:TOTAL_POPULATION:2011`).
- **Conflict Resolution Rule:**
  1. Official Census (`DIRECT_OBSERVATION`) takes precedence over sample surveys (`SURVEY_SAMPLE`).
  2. Higher publication date takes precedence for market prices.
  3. Non-null records overwrite null records.
  4. Lower confidence scores do not overwrite higher confidence scores.

---

## 5. Automated Quarantine Log

Zero-byte files, truncated downloads, or corrupt archives are automatically quarantined without halting pipeline execution:

Example quarantine record in `data/universal/validation/validation_report.json`:
```json
{
  "file_name": "download.csv",
  "status": "QUARANTINED",
  "reason": "ZERO_BYTE_EMPTY_FILE",
  "action_taken": "SKIPPED_PARSING_AND_LOGGED",
  "timestamp": "2026-09-30T02:30:00Z"
}
```

---

## 6. Real-Time Quality Audit API

The quality audit state is accessible via REST endpoint:
- `GET /api/data/quality`

Returns:
- Total datasets ingested & verified.
- Evidence record pass rate (e.g., $99.8\%$).
- Quarantined file count and reasons.
- Confidence score distribution (High / Medium / Low).
