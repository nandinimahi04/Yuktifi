# Final validation record

Date: 2026-09-28
Scope: what was executed, what it produced, and what remains unverified.

This document records **commands that were run and their actual output**. It is
not a claim about what the code probably does. Where something was not
executed, it says so, and where the suite being green does not imply the product
is correct, it says that too.

Read with `docs/FINAL_AUDIT.md` (the audit and its history) and
`docs/FINANCIAL_MODEL.md` (the model itself).

---

## 1. Environment

| | |
| --- | --- |
| Python | 3.13.1 |
| FastAPI | 0.115.0 |
| Pydantic | 2.9.2 |
| SQLAlchemy | 2.0.35 |
| pytest | 8.3.3 |
| httpx | 0.27.2 |
| Node | v22.23.1 |
| Next | 14.2.5 (installed), React 18, TypeScript 5, Tailwind 3.4.1 |
| `pytest-asyncio` | **not installed** — async tests use `asyncio.run()` |

`npm run lint` **cannot be run**: ESLint is not configured and `next lint`
prompts interactively. Every frontend check below is `tsc` or `build`.

---

## 2. Executed checks

### 2.1 Backend suite

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q --no-header -p no:cacheprovider
```

**396 passed, 67 warnings in 57.60s.** No failures, no skips, no errors.

The 67 warnings are 66 × Pydantic `.dict()` deprecation in tests and 1 ×
Starlette/anyio `BlockingPortal` alias. None indicate a wrong result; all are
unaddressed.

### 2.2 Frontend typecheck

```powershell
cd frontend
npx tsc --noEmit
```

**exit 0, no errors.**

### 2.3 Frontend production build

```powershell
cd frontend
npm run build
```

**✓ Compiled successfully, exit 0.**

### 2.4 Launcher

`start_yukti.bat` was repaired to build its own virtualenv, seed `.env` from
`.env.example`, and install frontend dependencies rather than exiting with
"create backend\.venv first".

Verified by parsing it with an immediate `exit /b` injected after `setlocal`, so
that it could be checked without spawning a window or installing anything:
**rc=0, no parse errors.**

That verifies syntax, not the install path. A cold bootstrap on a machine with
no Python and no Node has **not** been run.

### 2.5 Live data-mode disclosure

Both branches were executed against a live `TestClient`:

| Setting | Header | `Cache-Control` |
| --- | --- | --- |
| `DEMO_MODE=true` | `X-YuktiFi-Data-Mode: demo` | `no-store` |
| `DEMO_MODE=false` | `X-YuktiFi-Data-Mode: live` | (unset) |

---

## 3. Suite composition

36 files, 396 tests. The financial-truthfulness suites account for the
largest share:

| File | Tests | Pins |
| --- | --- | --- |
| `test_canonical_financial_contract.py` | 52 | the engine's own contract |
| `test_financial_truth.py` | 36 | what-if levers, tri-state, legacy fields |
| `test_financial_engine_wiring.py` | 26 | category mapping, no silent NULL financials |
| `test_financial_consistency.py` | 26 | one input, many surfaces, one answer |
| `test_financial_engine.py` | 22 | the compatibility adapter |
| `test_capital_sizing.py` | 21 | declared costs are not re-invented |
| `test_stress_matrix.py` | 16 | the matrix, and adapter agreement |
| `test_ranking_truth.py` | 16 | unmeasured ≠ failed |
| `test_simulator_truth.py` | 15 | canonical path vs labelled fallback |
| `test_business_plan_truth.py` | 13 | report figures trace to the engine |
| `test_ai_narration_truth.py` | 10 | the model explains, it does not compute |
| `test_whatif_api_truth.py` | 3 | every engine lever reachable over HTTP |
| `test_demo_mode_disclosure.py` | 5 | non-live data is labelled non-live |

No baseline test was weakened or deleted at any point. Where an assertion I
wrote turned out to be wrong about the model, the assertion was corrected
against the code — twice, both recorded in `FINAL_AUDIT.md` §20.4 — rather than
the model being changed to match the assertion.

---

## 4. What the green suite does **not** establish

Being explicit, because a 396-test green suite is easy to over-read.

**No test proves the model matches reality.** The suite proves the model is
internally consistent, deterministic, and honest about its own inputs. Whether
a ₹15 Vada Pav sells 3,900 a month in Solapur is not a question this codebase
can answer.

**No external provider was exercised.** Census, data.gov.in, Agmarknet, Overpass
and Gemini were not called. Their clients are wired and their failure paths are
tested, but a successful live response has not been observed. In the default
`.env`, `DEMO_MODE=false` with no provider keys, so a real run will make real
calls that return nothing.

**No browser was driven.** The frontend was typechecked and built. No component
was rendered, no click performed, no visual assertion made. The Evidence & Gaps
tab and the demo-mode banner are **unverified in a browser** — they compile and
typecheck, which is not the same as appearing correctly.

**The dynamic simulator's AI narrative was not exercised.** It needs Gemini.

**Phase2 evidence storage is in-memory and per-process.** It does not survive a
restart and is not shared between workers. A multi-worker deployment would show
each worker a different set of records. This is a known design decision, not a
defect, but it is a limitation.

---

## 5. Known open items

Unchanged from `FINAL_AUDIT.md` §20.6, none of them closed by this record:

- **Labelled but not real data:** `advisor/applications`, `advisor/reports`,
  `advisor/analytics` sector charts, `marketplace` vendor cards, the
  `hero/HeroIntelligencePanel` city animation. Each is disclosed on screen; none
  is backed by an endpoint.
- **`action-plan`** renders a static milestone list (`Finalize Lease Agreement
  for location`) not derived from the user's business or location.
- **`GET /schemes`** is a reshaping of existing data, not an addition.
- **`app/phase1/financial.py` — this audit item is stale and is closed.** The
  audit recorded
  `getattr(inp, "price_per_unit", 10000.0)` and
  `getattr(inp, "margin_capital", 10000.0)` in that file. The file no longer
  exists; `app/phase1/` now holds only `__init__.py`, `dairy_demo.py` and
  `service.py`. A repository-wide search for those two defaults now returns one
  hit, in `routes_schemes.py`:
  `getattr(session, "margin_capital", None)` — which defaults to `None`, not to
  a figure. Verified, not assumed.
- **`backend/yukti.db`** is on disk with 127 scratch rows. Gitignored, and
  `init_db()` recreates it, so it does not ship via git — but it is in any copy
  made from the working tree. A backup is at
  `%TEMP%\opencode\yukti.db.bak`; the live file could not be deleted because a
  running uvicorn held it open.
- **67 warnings** unaddressed.
- **ESLint unconfigured**, so `npm run lint` cannot be reported as passing.
- **NPV methodology** needs sign-off: the engine runs a project valuation
  unlevered against a full project-cost outlay. Coherent, but the
  project-versus-equity framing is an undocumented decision.
- **Doc set incomplete:** `DATA_SOURCES.md`, `RAG.md`, architecture, security,
  testing, limitations and scheme docs are unwritten.

---

## 6. Reproduction

```powershell
# backend
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

# frontend
cd frontend
npx tsc --noEmit
npm run build
```

---

**Verdict.** The financial model is deterministic, internally consistent, and
refuses to publish figures that were not declared. Every screen that shows a
number reads that one model, and the What-If API can ask all the questions the
engine can answer. That much is verified by execution.

The product is **not** validated in the sense that matters for a deployment: no
live data source has been observed succeeding, and no screen has been rendered
in a browser. The remaining §5 items are the honest list of what is not yet
true.
