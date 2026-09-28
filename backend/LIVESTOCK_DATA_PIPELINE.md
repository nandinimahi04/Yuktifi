# YUKTI official livestock data pipeline

## Source

YUKTI now has an ingestion adapter for the official Maharashtra 20th Livestock Census 2019 village-wise resource:

- https://kerala.data.gov.in/resource/maharashtra-20th-livestock-census-2019-village-wise

The source is published by the Maharashtra Animal Husbandry, Dairy Development and Fisheries Department.

## Why this dataset is used

It provides **supply-context evidence** for livestock-oriented business templates. It must not be converted directly into current milk demand, revenue, profit, or loan eligibility.

## Import

1. Download the official resource from the OGD page.
2. Keep the original file unchanged under `backend/data/raw/livestock/`.
3. If the download is a ZIP, the ingestion adapter can read the first CSV/XLSX member.
4. POST to `/api/v2/livestock/ingest`:

```json
{
  "path": "backend/data/raw/livestock/<official-file>.zip",
  "district": "Solapur",
  "block": "Akkalkot",
  "village": "<exact village name>"
}
```

The adapter normalizes common source column names, validates numeric counts, aggregates species totals, and writes a provenance record into the YUKTI evidence store.

## Evidence contract

The resulting evidence explicitly records:

- source dataset and official URL
- 2019 observation year
- village/block geography
- direct aggregation method
- `is_estimate=false`
- limitation that the census is historical and is not a 2026 count

## Production rule

`Database calculates -> Evidence stores provenance -> RAG retrieves documents -> LLM explains.`

No LLM is allowed to invent livestock counts or transform census counts into financial facts.
