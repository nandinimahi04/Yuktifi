# Universal Yukti Evidence Contract (UYEC-1.0)
**Problem Statement:** SIH 2026 PS 26091 — *YuktiFi Universal Data Layer*

---

## 1. Specification Overview

The **Universal Yukti Evidence Contract (UYEC-1.0)** defines the canonical schema for every verifiable fact, parameter, metric, or observation used across the YuktiFi decision and advisory engine.

Every piece of evidence consumed by the downstream financial engine, market intelligence engine, or LLM explanation layer must conform to this schema.

---

## 2. Core Schema Structure

```
UniversalEvidenceRecord
├── evidence_id: str (Deterministic UUID/hash: ev_...)
├── dataset_id: str (Foreign key to DatasetCatalog: DCHB_SOLAPUR_2730_TABLE_01)
├── entity_context: EntityContext
│   ├── entity_type: str (VILLAGE | TALUKA | DISTRICT | STATE | SCHEME | COMMODITY)
│   ├── entity_id: str (e.g. 562300, 2730, PMEGP, MILK_COW)
│   ├── entity_name: str (e.g. "Kasegaon", "Solapur", "Pandharpur")
│   ├── state_code: str ("MH" / "27")
│   ├── district_code: str ("2730")
│   ├── subdistrict_code: str ("04589")
│   ├── village_code: str ("562300")
│   └── coordinates: GeoCoordinates (lat, lon, bbox)
├── observation_payload: ObservationPayload
│   ├── metric_name: str (e.g. "TOTAL_POPULATION", "MILK_PRICE_INR_LITRE", "INTEREST_RATE_PA")
│   ├── metric_category: str (DEMOGRAPHY | INFRASTRUCTURE | FINANCIAL | MARKET | AGRICULTURAL)
│   ├── numeric_value: float | None
│   ├── unit: str (COUNT | PERSONS | INR | PERCENT | LITRES | HECTARES)
│   ├── currency: str ("INR")
│   ├── raw_text_value: str | None
│   └── structured_attributes: dict (Key-value breakdowns)
├── provenance_context: ProvenanceContext
│   ├── source_file: str ("Table_01_Solapur.xlsx")
│   ├── source_sha256: str (64-char hexadecimal hash)
│   ├── document_page: int | None
│   ├── table_reference: str | None ("Table 1, Row 14, Col C")
│   ├── publisher: str ("Directorate of Census Operations, Maharashtra")
│   ├── publication_year: int (2014)
│   ├── official_url: str ("https://censusindia.gov.in")
│   └── citation: str ("Census of India 2011, District Census Handbook Solapur, Village Directory")
└── quality_context: QualityContext
    ├── value_origin: ValueOrigin (DIRECT_OBSERVATION | STATISTICAL_ESTIMATE | DETERMINISTIC_CALCULATION | REMOTE_SENSING_DERIVED | SURVEY_SAMPLE)
    ├── confidence_score: float (0.0 to 1.0)
    ├── confidence_level: ConfidenceLevel (HIGH | MEDIUM | LOW | PROVISIONAL)
    ├── validation_status: str ("PASSED" | "ADJUSTED" | "IMPUTED")
    └── ingested_at: str (ISO 8601 UTC timestamp)
```

---

## 3. Pydantic Implementation Reference

The contract is implemented in `backend/app/data_layer/universal/evidence_contract.py`:

```python
class ValueOrigin(str, Enum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"          # Official Census / Direct Gov register
    STATISTICAL_ESTIMATE = "STATISTICAL_ESTIMATE"      # NSSO / HCES weighted survey estimate
    DETERMINISTIC_CALCULATION = "DETERMINISTIC_CALCULATION" # Exact formula (e.g. density = pop / area)
    REMOTE_SENSING_DERIVED = "REMOTE_SENSING_DERIVED"  # WorldPop / ISRO Bhuvan raster aggregation
    SURVEY_SAMPLE = "SURVEY_SAMPLE"                    # NFHS / Sample study sample mean

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"               # Official census / statutory notification (Confidence >= 0.90)
    MEDIUM = "MEDIUM"           # Large-sample official survey / MoSPI HCES (0.75 <= Confidence < 0.90)
    LOW = "LOW"                 # Small sample / imputed proxy (0.50 <= Confidence < 0.75)
    PROVISIONAL = "PROVISIONAL" # Draft release / unverified open source (Confidence < 0.50)
```

---

## 4. Contract Guarantees

1. **Immutable Audit Trail:**  
   Every evidence record contains a SHA-256 fingerprint of the original source document. If the source file changes by even 1 bit, the system flags the integrity mismatch.

2. **Explicit Uncertainty Handling:**  
   When census data is projected to the current year (2026), `value_origin` changes from `DIRECT_OBSERVATION` to `STATISTICAL_ESTIMATE`, and `confidence_score` reflects the compound annual growth rate (CAGR) variance model.

3. **No Stringly-Typed Units:**  
   Currencies are strictly ISO-standard (`INR`), land areas are normalized to `HECTARES`, and interest rates are normalized to `PERCENT_PER_ANNUM`.

4. **Bi-directional Geography Mapping:**  
   Records can be queried either by geographic hierarchy (`state -> district -> subdistrict -> village`) or by canonical LGD 6-digit codes.
