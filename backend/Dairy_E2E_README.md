# YUKTI Dairy end-to-end path

The first integrated vertical slice is available at:

`POST /api/v2/dairy-demo`

Example body:

```json
{
  "location": "Akkalkot, Solapur, Maharashtra",
  "margin_capital": 100000,
  "annual_interest_rate_pct": 12,
  "tenure_months": 60
}
```

The endpoint executes:

1. Bundled dairy evidence lookup.
2. Evidence provenance registration.
3. Revenue/cost derivation from the bundled dairy template.
4. Canonical project-cost/loan/EMI/DSCR calculation.
5. Five deterministic stress scenarios.
6. Deterministic decision gate.
7. Evidence IDs and explicit limitations.

The bundled legacy records are intentionally labelled as prototype/estimated evidence. They are not presented as a live government feed. Replace them with refreshed Census/LGD/livestock/market/OSM provider data before production use.

RAG remains downstream: government guidelines and methodology documents should be indexed separately and used to explain or support the deterministic result; RAG must not create the numeric financial or market facts.

### Optional official livestock evidence

The dairy endpoint now accepts `livestock_source`. When supplied, the official Maharashtra 20th Livestock Census 2019 resource is ingested and exposed as **supply-context evidence**. It does not alter revenue, milk demand, EMI, DSCR, or loan calculations.

Example payload:

```json
{
  "margin_capital": 100000,
  "annual_interest_rate_pct": 12,
  "tenure_months": 60,
  "livestock_source": "backend/data/raw/livestock/official_livestock.zip"
}
```
