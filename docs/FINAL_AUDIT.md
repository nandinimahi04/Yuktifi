# YUKTIFI — FINAL PROJECT AUDIT

Audit date: 2026-09-28
Auditor scope: full repository, pre-hardening state.
Method: static reading of every backend module, frontend route/component, dataset,
script and test; live execution of the backend test suite, the frontend typecheck,
and direct database inspection.

**No architectural change was made before this document was completed.**

---

## 0. BASELINE VERIFICATION (executed, not assumed)

| Check | Command | Result |
|---|---|---|
| Backend tests | `backend/.venv/Scripts/python.exe -m pytest tests -q` | **148 passed**, 1 warning, 56.6s |
| Frontend typecheck | `cd frontend; npx tsc --noEmit` | **exit 0**, no errors |
| Python | `--version` | 3.13.1 |
| Node | `next` 14.2.5, React 18 | — |
| Seed DB state | sqlite inspection of `backend/yukti.db` | see §14 — **effectively empty** |

Frontend production `build` and `lint` were **not** run during the audit phase and
were therefore not part of the baseline. They are executed in the hardening phase.

---

## 1. REPOSITORY STRUCTURE

```
work/
├── backend/            FastAPI + SQLAlchemy + Jinja2
│   ├── app/             128 Python modules
│   ├── data/            source/ processed/ reference/ raw/ manifests/ rag_documents/
│   ├── tests/           18 test modules, 148 tests
│   ├── .env             ← CONTAINS A REAL API KEY (see §13.1)
│   ├── .env.example     placeholders only — good
│   ├── yukti.db         430 KB runtime DB (shipped by accident)
│   └── Dockerfile, requirements.txt
├── frontend/           Next.js 14 App Router, next-intl
│   ├── app/[locale]/    27 routes
│   ├── components/     38 components
│   ├── lib/            api-client.ts, store.tsx, formatters.ts
│   └── .next/, node_modules/, tsconfig.tsbuildinfo  ← must not ship
├── archive/static_data/  10 legacy JSON datasets (see §14.2)
├── docs/               4 EMPTY files
├── scripts/            6 ingestion/build scripts
├── start_yukti.bat     hard-fails without a pre-made .venv (§32.1)
└── 5 root markdown design documents + rename_script.py + tree.py
```

## 2. BACKEND MODULE INVENTORY (128 modules)

| Area | Modules |
|---|---|
| `app/financial/` | `canonical_engine.py` (679 lines) — **the only real financial engine** |
| `app/engines/` | `financial_engine.py` (compat), `scheme_engine`, `scoring_engine`, `feasibility_engine`, `simulation_engine`, `stress_engine`, `recommendation_engine`, `location_service`, `market_intelligence/` (6 files), `simulator/` (3 files) |
| `app/services/` | `session_service.py` (418 lines), `ranking_service.py`, `data_service.py` |
| `app/data_layer/` | `retrieval`, `normalizer`, `validation`, `feature_engineering`, `geospatial`, `confidence_tagging`, `schemas` |
| `app/api_clients/` | `overpass_client`, `agmarknet_client`, `census_client`, `worldpop_client`, `geocoding_client` |
| `app/api/` | 22 route modules |
| `app/ai/` + `app/ai_layer/` | **Two competing LLM stacks** (§8.1) |
| `app/rag/` | `ingest`, `store` (SQLite token-overlap retrieval), `service`, `seed_corpus` |
| `app/phase1/` `app/phase2/` | canonical-finance decision wrapper + evidence table |
| `app/advisory/` | `national.py` orchestrator + 9 sub-modules + template registry |
| `app/reports/` | `report_builder` (Jinja2), `dossier_generator` (24 sections), `html_reporter` |
| `app/templates/` | `business_templates.py` (9 sectors) |
| `app/models/` `app/schemas/` | 18 SQLAlchemy models, 16 Pydantic schemas |
| `app/core/` | `config`, `db`, `seed`, `mode` |

## 3. FRONTEND ROUTES (27) AND COMPONENTS (38)

Routes: `/`, `/about`, `/action-plan`, `/advisor/analytics`, `/advisor/applications`,
`/advisor/applications/[id]`, `/advisor/reports`, `/advisory`, `/capital`,
`/category/[categoryId]`, `/compare`, `/dashboard`, `/discover`, `/documents`,
`/financials`, `/how-it-works`, `/market-intelligence/[categoryId]`, `/marketplace`,
`/plans`, `/profile`, `/report`, `/results`, `/score/[categoryId]`, `/settings`,
`/simulator`, `/support`.

Localisation: `next-intl`, `messages/` present, `[locale]` segment. Locale switching
is wired and must be preserved.

**Frontend calculation audit: PASS.** A grep for `dscr`, `/ emi`, `* 12`, `roi_pct`,
`break_even`, `Math.round` across `app/`, `components/`, `lib/` returns only
(i) display formatters (`toFixed`, `toLocaleString`) and (ii) TypeScript interface
field names. The frontend computes no financial figure. This is correct and must
stay that way.

## 4. DUPLICATE / OVERLAPPING IMPLEMENTATIONS

| # | Duplication | Location A | Location B | Impact |
|---|---|---|---|---|
| D1 | Financial arithmetic | `app/financial/canonical_engine.py` | `app/services/ranking_service.py:70-95` | **HIGH** — ranking computes DSCR from net profit, ROI without interest/depreciation/tax, using `compute_dscr`/`compute_roi` helpers. A different answer from the dashboard for the same business. |
| D2 | Financial arithmetic | `canonical_engine.py` | `app/engines/financial_engine.py:309-357` (`compute_payback_period`) | **HIGH** — second payback algorithm; double-counts working capital. |
| D3 | Payback algorithm | `canonical_engine.py:532` | `financial_engine.py:328` | Two paybacks returned to the same screen (5 vs 6 months in the worked example). |
| D4 | LLM stack | `app/ai/gemini_client.py` (Gemini, httpx) | `app/ai_layer/llm_client.py` (Anthropic SDK) | **MEDIUM** — two providers, two config keys, two failure modes. |
| D5 | Explanations | `app/advisory/explanation.py` (deterministic) | `app/ai/explanation_engine.py` (LLM) | **MEDIUM** — no single "explain the decision" contract. |
| D6 | Business templates | `app/templates/business_templates.py` (9) | `app/advisory/templates/registry.py` (8) | **MEDIUM** — different ids (`retail_kirana` vs `kirana`), different fields, different numbers for the same sector. Bridged by `ALIAS_MAP`. |
| D7 | Scoring | `app/engines/scoring_engine.py` (5 dims, flat mean) | `app/engines/recommendation_engine.py` (5 dims, weighted + gate) | **HIGH** — two different YUKTI scores for the same inputs. |
| D8 | YUKTI score | `app/engines/feasibility_engine.py:compute_yukti_score` | `app/engines/recommendation_engine.py:compute_yukti_score` | **HIGH** — same function name, different signature and different formula. |
| D9 | Working capital | `canonical_engine.py:449` (365-day) | `financial_engine.py:217` (30-day divisor) | LOW — 30 vs 30.42 days/month. |
| D10 | Market orchestrator | `app/engines/market_intelligence/__init__.py` (async, live) | `app/engines/market_intelligence/*.py` sync wrappers | LOW — legacy sync shims still exported. |
| D11 | Evidence store | `app/phase2/service.py` (`yukti_evidence_records`) | `app/models/confidence_tagging.py` (`confidence_tags`) | LOW — two evidence representations, one unused. |

Dead / stub code confirmed:
- `app/api_clients/base_provider.py` — **0 bytes**.
- `app/api_clients/census_client.py:get_demographics` — always returns `None`; a stub
  with a misleading docstring.
- `app/report/pdf_export.py`, `app/report/report_builder.py` — **0 bytes**.
- `app/phase1/dairy_demo.py` (200 lines) — demo-only, hardcodes Akkalkot.
- `rename_script.py` — hardcodes `d:\yukti\...` absolute paths; one-shot tool, dead.
- `docs/*.md` — all four files are **0 bytes**.

## 5. FINANCIAL CALCULATION PATHS (all of them)

```
Path A  /api/analysis/generate
          → routes_analysis.py:110 run_financial_engine
          → financial_engine.py:441 (dataset-driven, solapur_combined.json)
          → canonical_engine.compute_canonical_financials          ✅ canonical

Path B  /calculate-finance
          → session_service.build_canonical_input:57 (template-driven)
          → canonical_engine.compute_canonical_financials          ✅ canonical

Path C  /rank-opportunities
          → ranking_service.rank_opportunities:70-95
          → compute_net_profit / compute_dscr / compute_roi       ❌ NOT canonical

Path D  /api/v2/decision
          → phase1.decision → phase1.financial.calculate
          → canonical_engine.compute_canonical_financials          ✅ canonical

Path E  /api/v3/advisory
          → advisory.national.run_advisory → advisory.finance.calculate
          → canonical_engine.compute_canonical_financials          ✅ canonical

Path F  /simulate, /api/v2/*, stress_engine
          → canonical_engine.compute_canonical_financials          ✅ canonical
```

5 of 6 paths are canonical. **Path C is the outlier** and is the highest-priority
architectural fix.

## 6. MARKET / COMPETITOR CALCULATION PATHS

| Path | Source | Produces |
|---|---|---|
| `routes_analysis.py` | `solapur_combined.json` `competitor_market_data.competitor_count` | 9 for retail_shop — real, from the curated dataset |
| `market_intelligence/_get_competitors_async` | live Overpass | **BUG: always 0** (see §11.1) |
| `data_layer/retrieval.get_competitors` | live Overpass, sync | `count = len(records)`, 0 on error |
| `market_intelligence/competitor_density.py` | wraps the above | correct: `count_estimate: None` when no records |
| `advisory/competitors.py` | supplied mapped list | `coverage: "Low"` when empty, explicit "does not establish absence" |
| `retrieval.get_category_data` fallback | **fabricated** | `competitor_count: 2`, `target_customer_base: 5000` (see §11.2) |
| `scoring_engine.calculate_market_opportunity` | population / competitor count | treats 0 competitors as density → score 100 |

## 7. SCHEME / ELIGIBILITY CALCULATION PATHS

| Path | Basis | Verdict quality |
|---|---|---|
| `scheme_engine.match_scheme` | project-cost bands against NSFDC ceilings | Rule-based, sourced to nsfdc.nic.in. **Correct.** |
| `advisory/schemes.py` | 3 hardcoded `VERIFY` rules | Conservative, all UNKNOWN. Honest but useless. |
| `routes_schemes.match-scheme` | calls `match_scheme(project_cost)` with no contribution | Returns no funded amount (correct abstention). |
| `models/government_schemes` + `archive/static_data/schemes.json` | seeded at startup | **Never seeds — see §14.2.** |

`PMEGP` is declared in `SCHEMES` with `rate: None` but is **unreachable**:
`match_scheme` only ever returns Micro Credit Finance or Term Loan.

## 8. AI / LLM / RAG PATHS

### 8.1 Two LLM stacks
- `app/ai/gemini_client.py` — Gemini over httpx. `GEMINI_API_KEY`. Async + sync,
  prompt-hash cache. Used by: `routes_analysis` (insights), `routes_copilot`,
  `routes_simulate`, `market_intelligence/*`, `agmarknet_client`.
- `app/ai_layer/llm_client.py` — Anthropic SDK. `LLM_API_KEY`. Used by
  `routes_explain` only. **Has a real numeric validator** (`numeric_validator.py`).

### 8.2 CRITICAL: LLM is used to author business economics
`app/engines/market_intelligence/__init__.py:_get_cost_profile_async` prompts Gemini
for `fixed_cost_monthly`, `variable_cost_per_unit`, `selling_price_per_unit`,
`estimated_monthly_revenue`, `estimated_monthly_units` and returns them with
`confidence: "High"`. These are prices and costs presented to the user as
`confidence: High`. Direct violation of §12 and §23.

### 8.3 CRITICAL: LLM is used to author commodity prices
`app/api_clients/agmarknet_client.py:_fallback_pricing_async` prompts Gemini for
wholesale prices when the API key is absent or the call fails, and if Gemini also
fails, returns a hardcoded dictionary (`Wheat 2200, Rice 3500, Milk 55, …`). Both
paths return a plain dict with no estimate flag. Direct violation of §12 and §38.

### 8.4 RAG
`app/rag/store.py` — SQLite, character chunking (1800/250 overlap), token-overlap
scoring. No embeddings. `app/rag/service.py` — retrieve, then optionally narrate via
Gemini with a hard "answer only from excerpts" prompt. **RAG is already correctly
separated from the financial engine**; it cannot reach `compute_canonical_financials`.

## 9. DATA PROVIDERS

| Provider | Client | Live? | Honest on failure? |
|---|---|---|---|
| OpenStreetMap Overpass | `overpass_client.py` | Yes | **No** — returns `[]` on error, indistinguishable from zero results |
| WorldPop | `worldpop_client.py` | **No** | **No** — see §9.1 |
| AGMARKNET / data.gov.in | `agmarknet_client.py` | Yes (needs key) | **No** — invents prices (§8.3) |
| Census India | `census_client.py` | **No** — stub, always `None` | Yes (returns None) |
| Geocoding | `geocoding_client.py` | Yes | not audited in depth |
| LGD location master | `app/location/resolver.py` + `reference/location_master.sample.csv` | Bundled sample | Yes — abstains with `INSUFFICIENT_LOCATION_EVIDENCE` |
| Curated district dataset | `backend/data/processed/solapur_combined.json` | Bundled, real | Yes — Solapur only |

### 9.1 CRITICAL: `worldpop_client` fabricates population
`get_population_estimate` performs **no network call**. It multiplies
`π · 5² · density` where density is `5500` if the coordinate falls inside one of four
hardcoded metro bounding boxes (Mumbai/Pune, Bangalore, Delhi, Hyderabad) and `650`
otherwise. It then reports `data_origin: "WorldPop Spatial API"` and
`confidence: "Medium"` in `retrieval.get_demographics_at`.

A fabricated number is being attributed to a real, named, external dataset. This is
the single most serious data-integrity defect in the repository and must be removed.

## 10. FALLBACK / DEMO DATASETS

| Dataset | Location | Labelled as demo? |
|---|---|---|
| `solapur_combined.json` | `backend/data/processed/` | **No** — presented as live district data |
| `solapur_business_dataset_{strict,detailed}.json` | `backend/data/source/` | **No** |
| `location_master.sample.csv` | `backend/data/reference/` | Partially (README) |
| `archive/static_data/*.json` (10 files) | `archive/` | **No** |
| `app/phase1/dairy_demo.py` | code | Yes (endpoint name) |
| Gemini/LLM inline fallbacks | 6+ locations | **No** — presented as `confidence: High` or `Medium` |

There is **no `DEMO_MODE` flag anywhere in the codebase** (verified by grep). Every
fabricated fallback is invisible to the user and to the API response.

## 11. OSM / COMPETITOR SAFETY

### 11.1 BUG — competitor count is always 0
`market_intelligence/__init__.py`:
```python
comp_val = {
    "count": comp_result.get("value", {}).get("count", 0),   # ← .get("value") never exists
    "records": comp_result.get("value", {}).get("records", [])
}
```
`_get_competitors_async` returns `{"records": [...], "count": n, "confidence": ...}` —
there is no `"value"` key. So `count` is **always 0**, even when Overpass returns 50
POIs. Downstream, `analyze_opportunity_gaps_async(consumer_base, 0, ...)` takes the
`competitor_count == 0` branch and returns a fabricated `gap_score: 70`
("massive unmet demand"). The market page is therefore reporting high opportunity
with zero competition for every business in every location.

### 11.2 Fabrication in the dataset fallback
`retrieval.get_category_data` fallback returns `competitor_count: 2`,
`market_reach.estimated_target_customer_base: 5000`, `total_setup_cost: 200000`,
`price_unit = 100.0`, and `monthly_units = typical_cogs_pct * 10.0`. All invented.

### 11.3 OSM zero interpreted as zero competitors
- `retrieval.get_competitors`: `"note": f"{len(records)} live competitors found in area."`
  → on failure reads "0 live competitors found in area."
- `market_intelligence/_get_competitors_async` exception handler: returns
  `{"count": 0, "confidence": "Medium"}` — no distinction between "API down" and
  "no competitors".
- `routes_analysis.py` passes this straight into the score.

Contrast: `advisory/competitors.py` and `market_intelligence/competitor_density.py`
handle this correctly. The correct pattern already exists in the codebase and needs
to be propagated.

## 12. PRICE DATA SAFETY

No price-priority ladder exists. `AgmarknetClient` is all-or-nothing. The curated
`prices.json` / `pricing_margins` in `solapur_combined.json` are used on Path A but
carry no `is_estimate` flag, no unit, no reference date at the point of use.
`routes_analysis` returns `average_margin_pct` as a bare number with no provenance.

## 13. SECURITY ISSUES

### 13.1 CRITICAL — live API key committed
`backend/.env` contains a populated `GEMINI_API_KEY` and `LLM_API_KEY` (the same
64-character value in both). The value is deliberately **not reproduced here**; it
can be read at `backend/.env` lines 5–6.

This file is inside the submission tree. **The key must be revoked/rotated and the
file removed.** `backend/.env.example` is correctly blank.

A secret scan across `app/`, `tests/`, `frontend/`, `scripts/`, `docs/`, `archive/`
and all root `*.md`/`*.bat`/`*.yml`/`*.py` found **no** other key material, no
private keys, no AWS/GitHub tokens. `rename_script.py` contains only the path
`d:\yukti\...`.

### 13.2 CORS is `*` by default
`core/config.py:12` → `cors_origins: str = "*"`, and `main.py:38` passes it through.
`allow_credentials=True` with `allow_origins=["*"]` is rejected by browsers anyway, so
this is a misconfiguration rather than an exploitable one — but it must not ship.

### 13.3 Other
- No rate limiting on any endpoint.
- `/api/rag/ingest` accepts an arbitrary server filesystem `path` and reads it
  (`.txt/.md/.csv/.json/.pdf/.docx`) with no allowlist. **Arbitrary file read on the
  server.** High severity.
- `api_key_guard` is off by default (`api_key: str = ""`).
- SQLite at `backend/yukti.db` shipped in the submission.
- `Dockerfile`s and `docker-compose.yml` reference `/app/runtime_data` — verify build
  context correctness in packaging.
- PII: `advisory` evidence records store a `user_id`; `_CONSENT_REGISTRY` and
  `_DELETION_LOG` in `routes_privacy.py` are in-memory and are lost on restart, so
  the DPDP "COMPLETED" deletion claim is not durable. The privacy notice claims
  "permanently erased" — that is an overstatement.

## 14. PORTABILITY ISSUES

### 14.1 CRITICAL — the seed/data directory does not exist
`app/core/seed.py:15` and `app/services/data_service.py:6` both compute
`DATA_DIR = backend/app/data`. That directory is **not in the repository**.

Consequences, verified by sqlite inspection:

| Table | Rows |
|---|---|
| `business_categories` | 0 |
| `competitors` | 0 |
| `cost_models` | 0 |
| `data_sources` | 0 |
| `government_schemes` | 0 |
| `market_metrics` | 0 |
| `prices` | 0 |
| `locations` | 0 (1 test row only) |
| `sessions` | 0 |

Therefore:
- `seed_database()` is a no-op on every startup.
- `data_service.get_dataset(...)` returns `[]` for every dataset.
- `ranking_service.get_all_category_ids()` returns `[]` → `/rank-opportunities`
  returns an **empty ranking list for every user**.
- `retrieval.get_schemes()` returns `[]`.

The data exists — in `archive/static_data/` (10 files, `categories.json`,
`cost_models.json`, `schemes.json`, `prices.json`, `competitors.json`,
`data_sources.json`, `locations.json`, `market_metrics.json`, `risks.json`).
It has simply been moved out of the path the code reads.

### 14.2 `start_yukti.bat` cannot bootstrap
It requires `backend\.venv\Scripts\python.exe` to already exist and exits with an
error if not. It does not create the venv, does not install dependencies, does not
check Node, does not print URLs. It uses `%~dp0` (relative) — no hardcoded absolute
path, which is correct.

### 14.3 `scripts/start_yukti.sh` does not exist.

### 14.4 Non-portable absolute paths
- `app/location/resolver.py:71` → `Path("/tmp") / f"yukti_location_..."` — hardcoded
  POSIX temp path; fails on Windows.
- `rename_script.py` → `d:\yukti\...` (dead tool, must not ship).
- `frontend/tsconfig.tsbuildinfo` (142 KB), `frontend/.next/`, both
  `backend/.venv/` and `backend/app/**/__pycache__/`, `backend/.pytest_cache/`,
  `backend/yukti.db`, `backend/test_api_log.txt` are all present and must be
  excluded from the ZIP.

### 14.5 Packaging gaps
- No root `.gitignore`.
- No root `.env.example` (the file exists but is **0 bytes**).
- No `scripts/final_check.py`.
- No `docs/ARCHITECTURE.md`, `FINANCIAL_MODEL.md`, `DATA_SOURCES.md`, `RAG.md`,
  `SCHEME_RULES.md`, `SECURITY.md`, `DEMO.md`, `TESTING.md`, `LIMITATIONS.md`.
- `backend/pyproject.toml` is **0 bytes**.
- `requirements.txt` lists `anthropic` and `pypdf`/`python-docx` unpinned; `cachetools`
  is imported by `market_intelligence` with an `ImportError` fallback but is **not
  in requirements.txt**.

## 15. TEST INVENTORY

18 modules, 148 tests, all passing.

| Module | Covers |
|---|---|
| `test_canonical_financial_engine.py` | waterfall, amortisation, DSCR None, break-even None, financing gap |
| `test_financial_truth.py` | 21 KB — the most substantive suite; reconciliation, no-manufactured-debt invariants |
| `test_financial_engine.py` | compat-layer helpers |
| `test_capital_sizing.py` | template sizing chain |
| `test_boundary_values.py` | zero/negative/None boundaries |
| `test_scheme_engine.py` | band routing, ceilings |
| `test_recommendation_engine.py` | score bands, DSCR gate |
| `test_rag_evaluation.py` | retrieval quality |
| `test_phase1_phase2_rag.py` | evidence upsert + RAG |
| `test_report_rendering.py` | report + dossier render |
| `test_location_resolver.py`, `test_national_location_support.py` | LGD resolution, abstention |
| `test_census_population_pipeline.py` | ingestion |
| `test_location_aware_dairy.py` | end-to-end location→finance |
| `test_practical_e2e_workflow.py` | workflow |
| `test_v3_workable.py`, `test_phases7_18.py` | advisory |
| `test_numeric_validator.py` | LLM number blocking |

**Coverage gaps against the acceptance criteria:**
- No test asserts **one source of truth** across dashboard / API / report / simulator / AI context.
- No test asserts the §5 matrix (A–I: zero revenue, negative cash flow, impossible
  economics, underfunding, demand/cost/interest shocks) as specified.
- No test for **provenance surviving transformation**.
- No **data-quality** tests (API timeout, 500, malformed, empty, stale, conflicting).
- No test for `DEMO_MODE`.
- No test that asserts **no LLM import** inside the canonical engine.
- No test covering `ranking_service` (Path C) at all.

## 16. CANONICAL ENGINE DEFECTS (found during the earlier formula review)

These are mathematical, not architectural:

| # | Defect | Location | Effect |
|---|---|---|---|
| F1 | Working capital counted twice in payback | `financial_engine.py:552` passes `own + NWC`; `compute_payback_period:328` adds NWC again | Payback 6 months instead of 5; outlay inflated |
| F2 | Rounding amplification | `financial_engine.py:430-438` invents a 500 000-unit scale, rounds per-unit cost to 2 dp (0.455→0.46) | Dataset variable cost ₹227 500 → ₹230 000 (+₹30 000/yr); gross margin 35% → 34.29% |
| F3 | Moratorium cash ignored | `compute_cashflow_projection:145` charges ₹0 | 12-month projection understates outflow by ~₹22 000 on a 6-month moratorium |
| F4 | NPV horizon shorter than loan | `npv_horizon_years=5` vs `tenure_months=84` | 24 months of debt service excluded → NPV/IRR overstated |
| F5 | Depreciation on 100% of project cost | `financial_engine.py:510-512` ignores `depreciable_asset_share` | Charges depreciation on ₹4 L of inventory; overstated |
| F6 | Per-category WC days never used on Path A | hardcoded 10/7/14 | Tea stall modelled with 10 inventory days instead of 2; agri machinery with 10 instead of 30 |
| F7 | Seasonal indices not revenue-neutral | `financial_engine.py:35-41` — dairy sums to 11.50, poultry 11.80 | Implicit 4.2% / 1.7% revenue haircut vs the flat PAT/ROI |
| F8 | Gross margin passed as net margin to the scorer | `routes_analysis.py:139` | Financial-viability score overstated |
| F9 | `dscr`/`roi` fabricated when no projection exists | `routes_recommend.py:27-33` → `dscr=1.0, roi=15.0` | Invents financial data; also `max(0.5, projection.dscr)` clamps real DSCR upward |
| F10 | Hardcoded score | `routes_simulate.py:72` → `yukti_score=74` | Invents a score |
| F11 | `None` DSCR crashes the advisory decision | `advisory/decision.py:6` `if dscr >= 1.25` | `TypeError` for any zero-debt advisory run |
| F12 | HIGH confidence unreachable on Path A | `feasibility_engine.py:137` requires `tax_status == "MODELED"`, but Path A never sets a tax rate | Confidence is capped at MEDIUM forever |
| F13 | Break-even "units" are rupees | `_units_from_margin` | 276 041.7 "units" for a kirana store; `typical_unit_value` unused on this path |
| F14 | 30-day month divisor | `financial_engine.py:237` vs 365/12 | 1.4% WC difference |
| F15 | `run_full_market_analysis` uses `asyncio.get_event_loop()` | `market_intelligence/__init__.py` | Deprecated on 3.12, removed in 3.14; breaks under an active loop on Python 3.13 |

## 17. SUMMARY OF FINDINGS BY SEVERITY

**CRITICAL (8)**
1. Live API key in `backend/.env` (§13.1)
2. `worldpop_client` fabricates population and attributes it to WorldPop (§9.1)
3. LLM authors business economics at `confidence: High` (§8.2)
4. LLM authors commodity prices, plus a hardcoded price dictionary (§8.3)
5. Seed/data directory missing → entire DB layer and ranking flow are dead (§14.1)
6. Competitor count always 0 → fabricated `gap_score: 70` (§11.1)
7. Arbitrary file read via `/api/rag/ingest` (§13.3)
8. No `DEMO_MODE`; every fallback is invisible (§10)

**HIGH (12)**
9–15. `ranking_service` bypasses the canonical engine (D1)
16. Double payback algorithm + WC double-count (D2/D3/F1)
17. Two different YUKTI score functions (D7/D8)
18. OSM zero-result safety missing in 3 of 5 competitor paths (§11.3)
19. Fabricated dataset fallback: competitor_count 2, market reach 5000 (§11.2)
20. `routes_recommend` fabricates DSCR/ROI (F9)
21. Hardcoded `yukti_score=74` (F10)
22. Gross margin scored as net margin (F8)
23. NPV horizon < loan tenure (F4)
24. `advisory/decision.py` TypeError on zero-debt (F11)

**MEDIUM (14)**
25–38. Two LLM stacks, two template registries, rounding amplification, moratorium
cash, depreciation base, WC days, seasonal neutrality, break-even units, confidence
ceiling, asyncio event loop, `base_provider.py`/`pdf_export.py` zero-byte stubs,
CORS `*`, missing `cachetools` in requirements.

**LOW (10)**
39–48. Empty docs, 0-byte `pyproject.toml`, `/tmp` hardcode, dead `rename_script.py`,
shipped `yukti.db`, `tsbuildinfo`, in-memory DPDP registry, `.env.example` empty,
`test_api_log.txt`, PMEGP unreachable.

## 18. WHAT MUST NOT CHANGE

- All 148 existing tests must continue to pass.
- The 5 canonical financial paths stay canonical.
- All 9 `business_templates.py` templates and all 8 `advisory/templates/registry.py`
  templates stay.
- All 27 frontend routes and next-intl localisation stay.
- Existing API response shapes stay backward compatible (fields may be **added**,
  not removed or retyped).
- `canonical_engine.py` must never import an LLM client.

---

## 19. REMEDIATION STATUS (appended after the audit; §1–18 are the pre-hardening record)

This section is appended, not merged. Sections 1–18 describe the repository as it
stood on the audit date and are deliberately left unedited, so the baseline remains
readable. Nothing here is marked complete on the strength of an intended change.

**Suite: 248 passed, 67 warnings.** The 18 baseline modules of §15 were re-run
individually and still pass (152 — 148 at audit time plus 4 added during earlier
remediation); the remaining 96 are new truthfulness suites. No baseline test was
weakened or deleted.

### 19.1 The three-state viability contract (new this pass)

`CanonicalFinancialResult` now distinguishes three outcomes, because the third was
being conflated with one of the first two:

| State | Meaning |
|---|---|
| `VIABLE` | every gate evaluated and cleared |
| `NOT_VIABLE` | at least one gate evaluated and failed → `viability_reasons` |
| `UNDETERMINED` | nothing failed, but a gate could not be evaluated → `assessability_unknowns` |

A business with no cost reference was reported `NOT_VIABLE`. The only evidence
held was the *absence* of a project cost, and a bank officer reading
`NOT_VIABLE` is being told to reject a business for the crime of not having been
costed yet. An earlier comment on that same code block said the opposite — "not
VIABLE, because that would be a judgement about a business nobody has costed" —
and the code then made that judgement anyway. Both states are conclusions; the
honest state is the third.

Consequences, all of which were verified against `rank_opportunities`:

- `viability_reasons` is now **empty** for an unassessable business. A data gap
  listed alongside real failures would tell the reader the business failed those
  gates. `assessability_unknowns` is the separate field for gaps.
- A failed gate still outranks an unknown: a loss-making business stays
  `NOT_VIABLE` and the gap, if any, is recorded alongside it.
- `feasibility_engine` previously said "debt service coverage not applicable (no
  debt assumed)" whenever DSCR was `None`. Only one of the three cases that
  produce no DSCR actually has no debt; for the others it denied the existence of
  debt that was present and unpayable. The engine's own `dscr_status` is now
  reported.
- `feasibility_engine` previously emitted **no driver at all** for
  `UNDETERMINED`, so a list of drivers read as complete while something material
  was outstanding. It now emits an explicit `?` line.

### 19.2 Capital-dependent figures withheld when the cost is unknown

`canonical_engine` withheld ROI when the capital requirement was unknown, but
still computed NPV, IRR and payback. Against a project cost of zero, NPV is the
discounted sum of the inflows with nothing subtracted, so a single response
carried this:

> "The capital requirement is unknown, so return on capital, payback and net
> present value cannot be assessed." — three fields from `"npv": 475137.21`

A positive NPV of that size is a strong-looking result, not a missing one. NPV,
IRR and payback are now withheld together when the outlay is unknown, with
`payback_status = NOT_COMPUTABLE_NO_PROJECT_COST`, and remain fully computed for
costed models. Covered by `test_viability_states.py`.

### 19.3 FINDING — the frontend stated scheme terms the backend marks unverified **(fixed)**

`frontend/app/[locale]/market-intelligence/[categoryId]/page.tsx` rendered its
schemes tab from **hardcoded JSX, not from `/schemes` or `/match-scheme`**. Two
cards asserted official terms in present tense behind a pulsing "Highly
Recommended" badge:

- Pradhan Mantri MUDRA Yojana — "Up to ₹10 Lakhs collateral-free loan",
  "Subsidized interest rates via partner banks"
- Prime Minister Employment Generation Programme — "Up to 35% subsidy on project
  cost for rural areas", "Funding up to ₹50 Lakhs for manufacturing, ₹20L for
  services", "Administered by KVIC at national level"

`scheme_engine` marks the same class of figure `UNVERIFIED`, with
`effective_from: null` and the note that no dated circular is stored in this
repository. The backend and the UI therefore disagreed about whether a specific
subsidy figure was a verified current term, and the UI is the side a user reads.
MUDRA is not in the rule table at all, so the tab was advertising a scheme the
backend had never heard of. No frontend route consumed `/schemes`, which is why
the typecheck never saw it.

Recorded as **CRITICAL (9)**. Fix:

- The tab now fetches `/schemes` and renders one card per rule, showing the
  display name, rule id and version, evaluation status, the verification
  banner, the effective-date state, and a link to the official source. The
  pulsing "Highly Recommended" badge is gone — it asserted a relevance the
  product cannot compute. A failed fetch renders an explicit unavailable state
  rather than falling back to remembered numbers.
- `GET /schemes` now merges in `scheme_name`, `rule_verification` and
  `effective_date_state`. None of these are new claims: the name is the
  `SCHEMES` key, the verification block is the same `RULE_VERIFICATION`
  `/match-scheme` already returns, and the date state is derived from
  `effective_from`. The endpoint previously supplied none of them, which is
  precisely why the card had to invent them.
- **Terms are gated on `implemented`, not on `max_loan !== null`.** PMEGP holds
  a `max_loan` in the rule table while this build declines to evaluate it, so a
  null-check would have printed a ceiling for a scheme the engine refused to
  assess — the one figure the abstention exists to withhold.
- `SchemeRule` in `api-client.ts` was written against a response that did not
  exist, inventing `authority`, `checked_against_circular` and
  `effective_date_state` as non-optional fields; the card read
  `rule_verification.effective_date_state` and would have thrown at runtime
  while typechecking clean. The interface now matches the response and
  `authority` was dropped rather than invented.
- Regressions: `test_schemes_listing_carries_every_field_a_scheme_card_has_to_render`
  and `test_a_scheme_the_build_does_not_evaluate_carries_no_quotable_terms`.

§18 also requires response shapes stay backward compatible. `GET /schemes` was
changed from a bare scheme-keyed dict to an envelope (`schemes`, `verification`,
`disclaimer`). Nothing consumes it, so nothing breaks, but it is a reshaping
rather than an addition and remains open until reconciled.

The other 87 numeric literals in the frontend are unreviewed for the same
hardcoding pattern; only the scheme cards were confirmed fabricated.

### 19.4 Frontend fabrications, second pass

The §19.3 fix proved the scheme tab was not an isolated slip, so the frontend was
re-triaged. Numbers were classified by whether they appear in **user-visible
text** rather than in `className`/`width`/`opacity`, and then by whether the page
**labels them as sample data** — several pages that looked worst on the first
pass (e.g. `advisor/applications/[id]`, which shows a score, DSCR and ROI) already
carry an explicit "figures are illustrative, not computed" disclosure and are
acceptable. A string scan cannot see a disclaimer, so labelling was checked
separately before anything was called a defect.

Fixed (all unlabelled, all contradicted or unsupported):

| Page | Was | Now |
|---|---|---|
| `documents/page.tsx` | "NSFDC Term Loan — **Matched based on your profile**", rate "6% - 8% p.a.", margin money "5% - 10%", tenure "**10 Years**", and a "Begin Application" button | Renders the rule from `/schemes`. **Tenure was contradicted outright** — the engine holds `tenure_years: 7`, not 10. Margin money does not exist in the rule table at all; the rate is a single unverified `8.0`, not a range. No match is claimed, and the button is disabled unless the rule loaded. |
| `advisor/analytics/page.tsx` | Pulsing green "**LIVE DATA**" badge over four hardcoded metric cards, plus "**Algorithm detects** a 34% surge … **Recommended to allocate** surplus NSFDC funds" | "SAMPLE DATA" badge, a not-live banner, and the panel retitled "SAMPLE INSIGHT — NOT COMPUTED". Asserting a source is a stronger claim than a wrong number: a bad figure can be checked, a "LIVE" badge says it needn't be. |
| `marketplace/page.tsx` | "Vendors with the green 'Verified' badge are **pre-approved by the government**. Purchasing from them **automatically qualifies you for a 5% GST rebate**" | Banner states the listings are unverified samples and that no purchase affects eligibility. The green shield captioned "NSFDC Verified Vendor" is removed rather than relabelled. |
| `about/page.tsx` | "powered by **real-time** district consumer demand …"; stats "700+ districts", "2,400+ opportunities", "15,000+ reports", "**35% average subsidy matched**" | Provenance sentence rewritten. The four statistics are removed and the band explains what the build can actually state. Three seeded locations cannot support "700+ districts", and "average subsidy matched" claims a statistic never collected. |
| `how-it-works/page.tsx` | "Government scheme **registration**", "Verified local vendor network", "PMEGP / **Mudra** subsidy match" | Rewritten to describe routing by band with an unverified marker, and supplier listings as unverified samples. Mudra is not in the rule table. |

### 19.5 Client-side fallbacks that fabricate inputs to the backend

The §19.3/19.4 work was about pages that display invented numbers. A worse variant
was then found by scanning for `||` fallbacks **inside arguments to `api.*` calls**:
a client default silently undoes the backend's abstention before the request is
ever sent, so the engine is asked to compute confidently and has no way to know the
input was invented. Fixed:

| Site | Was | Now |
|---|---|---|
| `app/[locale]/page.tsx` | Onboarding form pre-filled `location: "Solapur, Maharashtra"`, `education: "10th"` | Both empty. This is where the declared profile originates — a user who pressed through was assigned a district and a qualification, and every later location lookup answered about Solapur. |
| `app/[locale]/results/page.tsx` | `margin_capital: marginCapital \|\| 50000`, `location_id: locationId \|\| "loc_1"`, and a header rendering `Capital: … : "₹75,000"` | All three removed. The header displayed **₹75,000 while the request scored against ₹50,000** — two invented capitals, inconsistent with each other, neither entered by the user. The page now asks for capital rather than ranking without it. |
| `app/[locale]/simulator/page.tsx` | `location: { district: "solapur", state: "maharashtra" }`, `capital: { available: state.marginCapital \|\| 100000 }` | Both removed. **Every simulation in the product ran against Solapur** regardless of user. A stress test is the page where a user checks what a demand shock would do to their business, and it was answering about a different district. |
| `components/CopilotOverlay.tsx` | `location_id: state.locationId \|\| "Solapur"` | Removed. The copilot is the one place a wrong input becomes the *subject of generated prose*: a Nagpur user asking about local competition would have received a fluent, specific, invented answer about Solapur, and the numeric guard passes, because a city name is not a checkable number. |
| `app/[locale]/market-intelligence/[categoryId]/page.tsx` | `const scoreNum = scores?.overall \|\| 50;` and hardcoded `lat = 17.6715; lng = 75.9080;` | Score is `number \| null`, so absent renders absent (and `||` no longer turns a genuine 0 into a 50). A fabricated mid-range score is the most dangerous placeholder on that page — it reads as a real mediocre result. The map is not rendered without resolved coordinates. |
| `app/[locale]/advisory/page.tsx` | Form seeded with `units: 727`, `price: 55`, `variable: 20`, `fixed: 15000`, `rate: 12`, `tenure: 60`, `margin: 100000`, `businessId: "dairy"`, `location: "Solapur, Maharashtra"`, and the request sent **`use_demo_assumptions: false`** | The pre-filled planner is kept, but a field counts as the user's only once edited, `use_demo_assumptions` now reflects that, and the result is labelled an illustration until every input is replaced. The page's own subtitle read "**No hidden financial defaults**" directly above a form made almost entirely of them. The flag was not cosmetic: `advisory/national.py` records `input_quality.used_demo_assumptions` and appends a `business_economics_demo_assumptions` evidence row with `is_estimate: true` and the limitation "Replace with user-entered or sourced business economics before decision use" — so `false` was recording eight invented numbers as verified declarations. |

### 19.6 Security items closed

| Item | State found | Fix |
|---|---|---|
| **Arbitrary file read** (§13.3, CRITICAL 7) | `POST /api/rag/ingest` did `p = Path(req.path)`, checked `p.exists()`, and read it. Any path on the host — `backend/.env`, an SSH key, a mounted credential — passed the existence check, was chunked and embedded, then became retrievable through `/api/rag/query`. The existence check made it an *oracle* as well as a read. | Ingestion is confined to `data/rag_documents`, `data/seed`, `data/raw` and `data`, resolved through `core/paths.py` so it stays portable. Containment is tested on the **resolved** path and then verified with `is_relative_to`, so neither `..` nor a symlink escapes. An extension allowlist (`.txt .md .csv .json .pdf`) is checked **before** containment, deliberately: testing containment first would confirm whether a named in-tree file exists. Relative paths are anchored to the corpus directory rather than the process CWD, so the allowlist cannot mean different things per deployment. 10 regressions. |
| **CORS** (§13.2) | The wildcard guard in `config.py` was dead code. `main.py` re-implemented the parsing inline and compared the raw string to `"*"`, never consultinging `allow_wildcard_cors` or the environment check — so `CORS_ORIGINS="*"` was honoured in production regardless of both flags. It also paired `allow_origins=["*"]` with `allow_credentials=True`, a combination the CORS spec forbids and browsers reject. | `main.py` now consumes `settings.cors_origin_list`. The wildcard path drops credentials and logs a warning rather than emitting a spec-invalid pair. |
| **`.gitignore`** | No `.gitignore` anywhere in the repository. | Added at the root: secrets (`*.pem`, `*.key`, `id_rsa`, `credentials.json`), Python/Node artefacts, `*.db` (including the shipped `backend/yukti.db`), logs, editor and OS files. |
| **Root `.env.example`** | Existed but was **0 bytes**. | Filled in with the two variables the frontend actually reads (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CARTO_ACCESS_TOKEN`), the demo flag, and a note that the `NEXT_PUBLIC_` prefix means the token is shipped to every visitor. Points at `backend/.env.example` for the backend set. |
| **Secret scan** | — | Regex sweep for known key prefixes (`AIza`, `sk-`, `ghp_`, `AKIA`, `xox*`) and for high-entropy assignments across the tree, excluding `node_modules`/`.venv`/`.next`/caches. Two candidates, both false positives (`api_key=settings.llm_api_key`, a code reference). **No live credential present.** The previously exposed key still requires owner-side rotation. |
| **Dead component with a fabricated score** | `components/hero/YuktiFiScoreCard.tsx` took no props and hardcoded `const score = 84` inside the ring maths. Unused, so it displayed nothing — but wiring it up would have shown every user an invented 84/100. | Deleted. The dashboard's own score card is the live one and now renders the API value. |
| **Dashboard `?? 0` score** | `score={yuktiScore ?? 0}` in two places, two lines below a comment reading "never use a fake fallback score". A missing score rendered as 0/100 — the worst possible value on an evaluation product. The card also recomputed its own verdict bands (`>= 80` strong, `>= 60` moderate, `else < 40` risky) in the client, so a 72 could read "Moderate" here while the API reported the verdict withheld for low coverage. | `score: number \| null`, with a "Not scored" state carrying the engine's `not_scored_reason`. Verdict comes from `scores.verdict`; a score with a withheld verdict now says exactly that. `MetricCard` no longer appends `/100` to an absent value. |
| **Compare page fabricated table** | When fewer than two real opportunities existed, the page substituted three invented businesses — Food Processing 87, Local Retail 76, Transport 72 — with invented demand, competition, capital-fit and risk. A visitor with no data saw a confident comparison of businesses that do not exist. The "Top Pick" badge was awarded by **array index** (`i === 0`), so it crowned whichever row was first rather than the highest score. | Fallback array deleted. "Top Pick" is computed from the maximum score actually present, with unscored rows excluded from selection rather than treated as 0. Added an empty state that explains a comparison needs a ranked opportunity. |
| **Simulator assumed Maharashtra** | The request sent `state: "maharashtra"` alongside the real district. The session store has no region field, so the value was invented and silently scoped every simulation to one state regardless of the district chosen. | Omitted rather than guessed, so any state-level figure the engines cannot source is reported unavailable. |
| **Capital step pre-filled** | The capital input was initialised to `"50000"`. Opening the step and pressing the button declared ₹50,000 as margin capital without the user choosing it, and that figure then propagated into the financial engine, scheme eligibility and every viability gate. An untouched form was indistinguishable from a real declaration. | Field starts empty; a capital already declared in the session is restored. Placeholder kept as a visible formatting hint. |
| **Unenforced min/max claim** | The capital page stated "Min: ₹10,000 / Max: ₹5,00,000". No backend constraint enforces either figure; the only real cap in the system is `TERM_LOAN_MAX_LOAN = 4_500_000`. | Removed. |
| **Demo endpoint assumed a margin** | `POST /api/v2/dairy-demo` and `/dairy-demo/location-aware` both did `payload.get('margin_capital', 100000)`. A caller posting nothing received EMI, DSCR, payback and loan-sizing for an assumed ₹1 lakh margin, with nothing recording it. The only caveat was a prose `limitations` array a client has to know to parse. | The payload now carries `is_demo: true`, `data_status: "DEMO DATA / NOT LIVE"`, an `assumed_inputs` block restating the assumed figures as assumptions, `scenario.margin_capital_is_assumed`, and `inputs_supplied.margin_capital`. The location-aware variant resolves the district canonically but carries the identical disclosure. 6 regressions. |

| **Financial engine produced no figures for any business** | `CATEGORY_MAP` in `business_matcher.py` translated the ten dropdown labels into IDs from the *business template* registry (`dairy`, `kirana`, `tailoring`, `small_hospitality`, …) while the only dataset carrying economics, `data/processed/solapur_combined.json`, keys its categories differently (`retail_shop`, `manufacturing`, `agri_business`, …). The sets shared five IDs and not one was reachable from the map, so `get_category_data()` always missed, `total_setup_cost` came back `None`, and `run_financial_engine` correctly refused to invent a cost. The endpoint returned **HTTP 200 with `financials: null` and `data_available: false` for every option in the onboarding dropdown** — a successful-looking response containing no financials. The four options with no map entry at all (Handicrafts, Logistics, Education, Fashion) additionally abstained on the model path, returning `INSUFFICIENT_INFORMATION` with no API key. `ALLOWED_CATEGORIES` had the mirror-image defect: the model was instructed to return `dairy`/`tailoring`, and every such answer was then discarded as unsupported. | `CATEGORY_MAP` now holds the ten real dataset IDs, matched case-insensitively on whitespace-collapsed labels. `ALLOWED_CATEGORIES` covers the dataset and every template-backed id. Legacy labels still named by the advisory registry and RAG corpus are kept in a separate `LEGACY_LABEL_ALIASES` table, documented as template-only (declared assumptions, not observed data) so the two evidence tiers stay distinguishable. 26 regressions, including one per dropdown option asserting a real project cost and EMI. |

### 19.7 Still open

Not done, and not to be presented as done:

- Sample-data pages that are now labelled but not yet converted to real data:
  `advisor/applications`, `advisor/reports`, `advisor/analytics` sector charts,
  `marketplace` vendor cards, and the `hero/HeroIntelligencePanel` city animation.
  Each is disclosed; none is backed by an endpoint.
- `discover`, `capital` and `action-plan` reviewed for the default-value pattern
  and clean; `action-plan` still renders a static milestone list
  (`Finalize Lease Agreement for location`) that is not derived from the user's
  business or location.
- `GET /schemes` is a reshaping rather than an addition (§19.3), against §18.
- `DEMO_MODE` offline fixtures. The demo dairy payload is now labelled
  (§19.6), but there is no `DEMO_MODE` provider layer and no frontend
  `DEMO DATA / NOT LIVE` badge, so the flag currently switches off network calls
  without anything on screen saying the data is not live.
- The required UI: evidence drawer, coverage, assumptions/provenance,
  why/why-not, comparison, gaps, unavailable states.
- `scripts/start_yukti.sh`, `scripts/final_check.py`, `start_yukti.bat` repair.
- `docs/FINAL_VALIDATION.md`, `FINANCIAL_MODEL.md`, `DATA_SOURCES.md`, `RAG.md`,
  architecture, security, demo, testing, limitations, scheme docs.
- NPV methodology sign-off: the engine runs a project valuation unlevered
  (interest added back, then removed once inside debt service) against a full
  project-cost outlay. That is coherent, but the project-versus-equity framing
  needs a documented decision before sign-off.
- Legacy `app/phase1/financial.py` still has `getattr(inp, "price_per_unit",
  ... 10000.0)` and `getattr(inp, "margin_capital", 10000.0)` fallbacks behind
  it, reachable from the phase-1 decision route. Narrower than the paths fixed
  above but the same class of default. — **STALE, closed:** the file no longer
  exists; `app/phase1/` is now only `__init__.py`, `dairy_demo.py`,
  `service.py`. A repository-wide search for those defaults returns one hit, in
  `routes_schemes.py`, and it defaults to `None`.
- `backend/yukti.db` and other runtime artifacts still on disk (now ignored by
  git, but still present in the working tree and in any copy made from it); 67
  warnings (Pydantic `.dict()` in tests, one Starlette/anyio deprecation)
  unaddressed.
- **ESLint is not configured** (`next lint` prompts interactively on first run),
  so `npm run lint` cannot be reported as passing. This is a pre-existing gap
  the audit noted; `tsc --noEmit` (exit 0) is the only frontend check that runs.

**Readiness: not met.** The suite is green (266 passed) and the confirmed
fabrications and security items in §19.3–19.6 are closed, but §19.7 each
independently prevents `FINAL SUBMISSION READY`.

---

## 20. CANONICAL-MODEL CONSOLIDATION (appended; §1–18 pre-audit, §19 first pass)

This section records the pass that made `app/financial/` the only place a
financial figure is computed, and brought the reader surfaces onto it.

**Suite: 391 passed, 67 warnings.** `npx tsc --noEmit` exit 0; `npm run build`
compiled successfully. `npm run lint` still cannot run (§19.7, ESLint absent).

### 20.1 What was consolidated, and what it cost before

Each of these was a real disagreement between two screens showing numbers to the
same user, not a code-style issue.

| Surface | Defect | Now |
|---|---|---|
| `financial_engine` | omitted seasonality, gates, confidence, tax status, working capital from its contract | full canonical passthrough, 95 result fields |
| `financial_engine` | `daily_cash_needed` variously = opex/30, = net WC/30, = monthly OCF/trading days | `monthly_operating_cash_flow / operating_days_per_month`; weekly × 7 |
| `stress_engine` | kept its own 4-scenario matrix that had drifted from the canonical 7 | iterates `STRESS_SCENARIOS`, no second definition |
| `stress_engine` | `combined_severe` omitted the price cut, overstating worst-case EBITDA by ~₹1,600/mo on the Vada Pav fixture | matches the canonical compound shock |
| `simulation_engine` | built its own shocked input, scaling units and variable cost by hand | `apply_what_if` / `apply_shock` |
| `simulation_engine` | `survives_stress = dscr is not None and dscr >= 1.0` reported **every debtless business as failing** a stress test | tri-state, `None` + `survives_stress_applicable` |
| `simulator_engine` | scalar fallback computed DSCR/ROI from revenue-minus-opex, disagreeing with the analysis screen | canonical path, fallback explicitly labelled |
| `financials/page.tsx` | re-derived margins, break-even and loan totals in TypeScript | renders canonical fields, derives nothing |

### 20.2 Invented opex composition — the one worth reading

A founder entered one figure: `fixed_cost_monthly = 17,500`, documented as
"rent, salary, insurance". The opex block split it 50/30/20 into rent 8,750,
salaries 5,250 and electricity 1,750.

**The total was correct.** That is what made it survive review — the founder's
check is the total, and the total matched. The composition was invented, and
the cost breakdown, the AI explanation and the PDF report all repeated those
three numbers in the present tense, as though the founder had stated them.

The cost model has one field for this and it is an aggregate. There was no
declared rent to carry, so the whole figure now sits on `opex.other` and the
cost profile says what it actually records. An intermediate attempt asserted a
`monthly_rent` line that the data model does not contain; that test was wrong
and was removed rather than satisfied by adding a fabricated field. See
`docs/FINANCIAL_MODEL.md` §8.

### 20.3 The What-If endpoint could not ask most of its questions

`WhatIfAdjustments` has thirteen levers. `SimulateRequest` had three fields, of
which two were shocks. **Eleven levers — including own capital, debt, interest
rate, tax rate and supplier terms — existed only in Python.**

The consequence was not slow answers; it was confidently wrong ones. A founder
who wanted to know "what if I put in more of my own money" could only express it
as a revenue cut, and the screen would report a smaller profit: a real number for
a scenario nobody was considering. All thirteen are now reachable over HTTP, the
three legacy fields are *translated into levers* so both forms run one path, and
responses carry `applied_adjustments` (previous / applied / change per lever) so
a caller can confirm the request was honoured. `test_whatif_api_truth.py` fails
if a lever is ever added to the engine and not to the schema.

`revenue_delta_pct` remains a **volume** shock. Reinterpreting it as a price cut
would change every existing client's answer in the flattering direction, because
a demand fall takes variable cost down with it and a price cut does not.

### 20.4 Two places where the model is right and the intuition is not

Recorded so a later reader does not "fix" them:

- **A longer tenure lowers both the EMI and the profit.** 60 → 120 months cuts
  the payment ~39% and more than doubles lifetime interest; year-one interest
  rises slightly because the balance declines more slowly. Presenting only the
  lower EMI is the misleading half.
- **A 20% volume cut costs more than 20% of profit.** Revenue and the variable
  cost that scales with it both fall 20%; fixed cost does not move. Operating
  leverage, and the reason a small demand miss is more dangerous than it looks.

Both were initially written as "bug" assertions before the schedule was read.
`test_financial_truth.py` now pins the real relationship.

### 20.5 Closed from §19.7

- `docs/FINANCIAL_MODEL.md` — **written**, derived from the code and verified
  against it (gate names, benchmark values, scenario table, lever list, the four
  gate states, and the shape of `financial_status` / `financial_confidence` were
  each checked against the running engine rather than written from memory).
- `contribution_per_unit` and `break_even_units` are withheld when a plan has
  aggregate revenue but no per-unit price and cost; `break_even_revenue` is
  published instead. Deriving a unit price from a margin assumption produces an
  unfalsifiable "you need 2,187 units a month".

### 20.6 Still open from §19.7

Unchanged and still blocking: the labelled-but-not-real sample-data pages;
`action-plan`'s static milestone list; `GET /schemes` being a reshaping;
`DEMO_MODE` with no on-screen `NOT LIVE` badge; the required UI (evidence
drawer, provenance, why/why-not, gaps, unavailable states); `start_yukti.sh` /
`final_check.py` / `start_yukti.bat`; NPV methodology sign-off; `backend/yukti.db`
on disk; 67 warnings; ESLint unconfigured.

`FINANCIAL_MODEL.md` is one document. `FINAL_VALIDATION.md`, `DATA_SOURCES.md`,
`RAG.md` and the rest of the doc set remain unwritten.

**Readiness: still not met.** The canonical-model work is complete and its
numbering is consistent across surfaces, but §20.6 is untouched.

---

## 21. REQUIRED UI STATES AND DATA-MODE DISCLOSURE

Two items from §19.7 that were not code but *absences* — the engine had been
computing the right things for some time and nothing was showing them.

**Suite: 396 passed, 67 warnings.** `tsc --noEmit` exit 0; `npm run build`
compiled.

### 21.1 The engine explained itself; the screen did not

`financial_engine` has always returned `input_provenance`,
`assumptions_provenance`, `assessability_unknowns`, `viability_reasons`,
`gate_benchmarks`, `unit_metrics_note` and `payback_status`. A survey of
`financials/page.tsx` found **none of them rendered** — only
`decision_gates`, `explainability`, `validation_issues`, `financial_status`,
`financial_confidence` and the status strings.

So the provenance of every figure was computed and discarded, and the list of
what the system still needed was computed and discarded. A founder could not
tell which numbers they had supplied and which the system had inferred, and a
missing number read as a zero.

The new **Evidence & Gaps** tab renders:

- **confidence**, with the engine's own stated basis, and the explicit note
  that confidence describes evidence rather than performance;
- **what is still unknown** (`assessability_unknowns`) and **what failed**
  (`viability_reasons`) in *separate* panels — an unassessable gate is not a
  failed one, and putting them in one list would repeat the conflation the
  three-state viability contract exists to prevent;
- **unavailable figures with the engine's stated reason** for each, so a null
  carries its cause instead of looking like a bug;
- **provenance tables** for declared figures and for engine assumptions, with
  an explicit `UNKNOWN` badge for a source that could not be established — an
  unknown source is a finding, not a formatting problem.

### 21.2 DEMO_MODE was invisible

`DEMO_MODE=true` switches off outbound network in the provider clients, so
prices, competitor counts and population figures come from bundled fixtures.
That is correct behaviour. It was also completely invisible: no response header,
no frontend state, nothing on screen. A demo run and a live run were
indistinguishable, and someone reading a recommendation had no way to know the
competitor count behind it had not been looked up.

- `main.py` sets `X-YuktiFi-Data-Mode: live|demo` on **every** response, derived
  from `settings.network_allowed` — the same property the clients consult, so
  the label cannot drift from the behaviour it describes — and adds
  `Cache-Control: no-store` when the data is not live.
- `api-client.ts` records the mode on every response and publishes it through
  `onDataModeChange`. It is initialised to `null`, **not** `"live"`: the safe
  reading of an absent label is unknown.
- `DataModeBanner` renders nothing in production, and in demo mode states
  plainly that the market inputs are not current while the model and arithmetic
  are real. A second `DataModeUnknownNotice` covers the window before the first
  response.

Both branches were executed against a live `TestClient`; the four-case
`test_demo_mode_disclosure.py` pins the header to the setting, including the
`DEMO_MODE=true, DEMO_ALLOW_NETWORK=true` case, where labelling "live" from
`demo_mode` alone would have been wrong.

### 21.3 A stale audit finding, corrected

§19.7 and §20.6 both listed `app/phase1/financial.py` as retaining
`getattr(inp, "price_per_unit", 10000.0)`. **That file no longer exists.**
`app/phase1/` now contains only `__init__.py`, `dairy_demo.py` and
`service.py`, and a repository-wide search for those two defaults returns one
hit — `getattr(session, "margin_capital", None)` in `routes_schemes.py`, which
defaults to `None`. The finding was checked rather than copied forward, and is
marked stale in place.

### 21.4 Not closed

`FINAL_VALIDATION.md` is written and records what was executed — including the
things a green suite does *not* establish. `DATA_SOURCES.md`, `RAG.md` and the
architecture, security, testing, limitations and scheme docs remain unwritten.
The labelled-but-not-real sample-data pages are untouched. `backend/yukti.db` is
still on disk: a running uvicorn held it open, and stopping the user's server
was not a decision to take unasked.

**Readiness: still not met**, for the §21.4 reasons rather than for any financial
reason.

---

*Audit complete. Hardening began in §19; §20 canonical-model consolidation;
§21 required UI states and data-mode disclosure. `docs/FINAL_VALIDATION.md`
records what was executed.*
