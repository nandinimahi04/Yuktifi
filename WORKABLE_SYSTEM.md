# YUKTIFI — Workable System Runbook

## 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `/docs` for the API.

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000`.

## 3. Official data

The system never silently invents official population or location data. Download the Census 2011 village PCA from the official Census catalog and run:

```bash
python scripts/download_official_sources.py
python scripts/check_data_ready.py
python scripts/ingest_census_population.py <path-to-census-file> --state Maharashtra --district Solapur --village "YOUR VILLAGE"
```

If the network download is unavailable, download manually from the official Census catalog:
https://www.censusindia.gov.in/nada/index.php/catalog/42559

The Population Finder documents village/sub-district/district PCA indicators and provides village-level population and household data.

## 4. Run a real advisory

`POST /api/v3/advisory` requires business economics unless `use_demo_assumptions=true`. This prevents hidden defaults from being presented as facts.

Example body:

```json
{
  "business_id":"dairy",
  "location":{"query":"Chincholi Najik, Akkalkot, Solapur, Maharashtra","population":5000,"households":1100},
  "promoter_margin":100000,
  "monthly_units":727,
  "price_per_unit":55,
  "variable_cost_per_unit":20,
  "fixed_cost_monthly":15000,
  "annual_rate_pct":12,
  "tenure_months":60,
  "use_demo_assumptions":false,
  "profile":{"social_category":"OBC"}
}
```

## 5. Production guard

Set `YUKTI_API_KEY` and explicit `CORS_ORIGINS`. The API then requires `X-YUKTI-API-KEY` on non-public endpoints.

## 6. Architecture

**Database calculates → evidence records provenance → RAG retrieves documents → LLM explains.** The LLM is not allowed to manufacture population, prices, competitor counts, EMI, DSCR, or scheme eligibility.

## Demo location data

A tiny `location_master.sample.csv` is included only so the resolver can be exercised immediately. It is **not** a complete government master. For production, replace it with normalized LGD data and keep the raw government download under `backend/data/raw/`.
