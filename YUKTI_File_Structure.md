# YuktiFi — Prototype File Structure

Monorepo, two deployable services (Next.js frontend + FastAPI backend), matching the architecture in Section 22 and the API/DB design in Sections 23–24 of the blueprint. Every folder below is annotated with **which blueprint section it implements** and **what NOT to put there** — the "LLM never does arithmetic" rule (Section 8) is enforced structurally by keeping `engines/` pure-Python/deterministic and isolating the AI layer into its own package that can only call engines, never replace them.

```
yukti/
├── README.md                          # Setup, env vars, how to run both services, demo script link
├── .env.example
├── docker-compose.yml                 # Local: postgres + backend + frontend, one command for demo day
│
├── backend/                                    # FastAPI (Section 25)
│   ├── pyproject.toml / requirements.txt
│   ├── alembic/                                # DB migrations (versioned schema, Section 23)
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                             # FastAPI app, router registration, CORS
│   │   ├── core/
│   │   │   ├── config.py                       # env, DB URL, LLM API key, feature flags
│   │   │   └── db.py                           # SQLAlchemy engine/session
│   │   │
│   │   ├── models/                             # SQLAlchemy ORM — 1 file per DB entity (Section 23)
│   │   │   ├── user.py
│   │   │   ├── location.py
│   │   │   ├── business_category.py
│   │   │   ├── session.py
│   │   │   ├── competitor.py
│   │   │   ├── market_metric.py
│   │   │   ├── cost_model.py
│   │   │   ├── government_scheme.py
│   │   │   ├── scheme_rule.py
│   │   │   ├── loan_product.py
│   │   │   ├── financial_projection.py
│   │   │   ├── scenario.py
│   │   │   ├── recommendation.py
│   │   │   ├── confidence_tag.py               # polymorphic — attaches to any entity
│   │   │   └── source.py
│   │   │
│   │   ├── schemas/                            # Pydantic request/response contracts (Section 24)
│   │   │   ├── profile.py
│   │   │   ├── ranking.py
│   │   │   ├── market.py
│   │   │   ├── finance.py
│   │   │   ├── scheme.py
│   │   │   ├── simulation.py
│   │   │   ├── recommendation.py
│   │   │   └── report.py
│   │   │
│   │   ├── api/                                # One router per endpoint row in Section 24's table
│   │   │   ├── routes_profile.py               # POST /profile
│   │   │   ├── routes_rank.py                  # POST /rank-opportunities
│   │   │   ├── routes_market.py                # POST /analyze-market
│   │   │   ├── routes_finance.py               # POST /calculate-finance
│   │   │   ├── routes_schemes.py               # GET /schemes, POST /match-scheme
│   │   │   ├── routes_simulate.py              # POST /simulate
│   │   │   ├── routes_recommend.py             # POST /recommend
│   │   │   ├── routes_explain.py               # POST /explain
│   │   │   └── routes_report.py                # POST /generate-report
│   │   │
│   │   ├── engines/                            # ⚠️ DETERMINISTIC ONLY — no LLM calls allowed in this package
│   │   │   ├── location_service.py             # geocode + admin-boundary matching (Section 22 component)
│   │   │   │
│   │   │   ├── market_intelligence/            # Section 11
│   │   │   │   ├── market_reach.py             # 5–10km radius consumer base calc
│   │   │   │   ├── opportunity_gaps.py
│   │   │   │   ├── swot.py
│   │   │   │   ├── threats.py
│   │   │   │   ├── competitor_density.py
│   │   │   │   └── pricing.py
│   │   │   │
│   │   │   ├── financial_engine.py             # Section 14/15/17 — PC/loan formulas, EMI, DSCR,
│   │   │   │                                   #   break-even, ROI, boundary-value logic (17.1)
│   │   │   ├── scheme_engine.py                # Section 16 — pure rule-table lookup, NEVER LLM
│   │   │   ├── recommendation_engine.py        # Section 12/13 — hard gates, YuktiFi Score, verdict banding
│   │   │   │
│   │   │   └── simulation_engine.py            # Section 15 — recalculation chain for What-If sliders
│   │   │
│   │   ├── data_layer/                         # Section 9/26 — Data/RAG Retrieval Layer
│   │   │   ├── retrieval.py                    # fetches structured facts + attaches citations
│   │   │   ├── confidence_tagging.py           # Section 10 — High/Medium/Low logic, "data_origin" field
│   │   │   └── datasets/                       # curated demo data (Section 26)
│   │   │       ├── location_1_solapur/
│   │   │       │   ├── demographics.json
│   │   │       │   ├── competitors.json        # data_origin: public_source | prototype_curated
│   │   │       │   ├── pricing.json
│   │   │       │   └── cost_profiles.json
│   │   │       ├── location_2_sparse/          # deliberately thin data — proves honest abstention
│   │   │       └── schemes/
│   │   │           └── nsfdc_schemes.json      # the two verified NSFDC scheme rows (Section 16.1)
│   │   │
│   │   ├── ai_layer/                           # Section 18 — ONLY package allowed to call the LLM
│   │   │   ├── intent_classifier.py
│   │   │   ├── context_builder.py              # pulls already-computed values, never invents
│   │   │   ├── prompt_templates.py             # the constrained "use ONLY these numbers" prompts
│   │   │   ├── llm_client.py                   # hosted LLM API wrapper
│   │   │   └── numeric_validator.py            # ⚠️ Section 18.4 — rejects any output number not in context
│   │   │
│   │   ├── report/                             # Section 29
│   │   │   ├── report_builder.py               # assembles session data → template
│   │   │   ├── templates/
│   │   │   │   └── report.html.jinja
│   │   │   └── pdf_export.py
│   │   │
│   │   └── services/                           # thin orchestration layer between api/ and engines/
│   │       ├── ranking_service.py              # calls financial_engine + market_intelligence per category
│   │       └── session_service.py
│   │
│   └── tests/
│       ├── test_boundary_values.py             # ⚠️ Section 17.1 table, encoded as literal test cases
│       ├── test_scheme_engine.py               # ₹1.40L / ₹50L edge cases
│       ├── test_financial_engine.py
│       ├── test_numeric_validator.py           # feed a deliberately-wrong LLM output, assert rejection
│       └── test_recommendation_engine.py
│
├── frontend/                                    # Next.js (Section 25)
│   ├── package.json
│   ├── app/                                    # one route per screen in Section 21's inventory
│   │   ├── page.tsx                            # Landing
│   │   ├── profile/page.tsx                    # Profile/Location
│   │   ├── capital/page.tsx                    # Capital Entry
│   │   ├── fork/page.tsx                       # Ranking vs single-category fork (Section 6)
│   │   ├── results/page.tsx                    # Ranking Results
│   │   ├── category/[id]/page.tsx              # Category Selection → Feasibility Report
│   │   ├── financial-structuring/page.tsx
│   │   ├── scheme-match/page.tsx
│   │   ├── emi/page.tsx                        # EMI/Moratorium
│   │   ├── simulator/page.tsx                  # What-If Simulator (the demo centerpiece)
│   │   ├── score/page.tsx                      # Score & Verdict
│   │   ├── next-steps/page.tsx
│   │   └── report/page.tsx                     # Report/Export
│   │
│   ├── components/
│   │   ├── ConfidenceBadge.tsx                 # ONE reusable component, used identically everywhere (20.2)
│   │   ├── SourceTooltip.tsx                   # the tappable "ⓘ" source disclosure
│   │   ├── VerdictBanner.tsx                   # GO/CAUTION/ALTERNATIVE/NOT_RECOMMENDED colour states
│   │   ├── ScoreDial.tsx
│   │   ├── WhatIfSlider.tsx                    # sub-second recompute UX (must feel live)
│   │   ├── EMITable.tsx
│   │   ├── MapRadiusOverlay.tsx                # OSM/Mapbox 5-10km overlay
│   │   ├── CopilotOverlay.tsx                  # contextual chat, available from any screen
│   │   └── ProgressStepper.tsx                 # linear journey nav (20.2)
│   │
│   ├── lib/
│   │   ├── api-client.ts                       # typed wrappers for every Section 24 endpoint
│   │   └── formatters.ts                       # ₹ formatting, plain-language number phrasing
│   │
│   └── public/
│
├── data/                                        # raw source files before curation (kept OUT of git if large)
│   └── sources/                                # NSFDC scrapes, district census extracts, OSM exports
│
└── docs/
    ├── demo_script_3min.md                     # Section 27.2
    ├── demo_script_5min.md                     # Section 27.3
    ├── judge_qna_prep.md                       # Section 35
    └── data_provenance.md                      # Section 26.4 — what's real vs prototype_curated
```

## Why this shape (the parts worth defending to a judge)

1. **`engines/` has a hard boundary with `ai_layer/`.** This is the single architectural claim the whole blueprint rests on (Section 8: "LLM never does arithmetic"). Physically separating the packages means a code reviewer — or a judge asking "show me where the AI touches the numbers" — gets a one-line answer: it doesn't; `ai_layer/numeric_validator.py` checks it after the fact.
2. **`services/` is thin on purpose.** `api/` routes should stay dumb (validate → call service → return), `engines/` should stay pure and unit-testable without a DB or HTTP context. This is what makes `tests/test_boundary_values.py` possible as a fast, no-mocking test suite you can run live if a judge challenges the ₹1.40L/₹50L edges.
3. **`data_layer/datasets/` mirrors Section 26 exactly** — two folders (`location_1_solapur`, `location_2_sparse`), because the low-confidence demo path (Section 10.3) is a checklist item you can literally lose points for skipping (Section 40, "Top 5 things we must add," #3).
4. **Frontend routes map 1:1 to the screen table in Section 21.** This isn't just tidy — during a hackathon, whoever owns "Scheme Match" or "What-If Simulator" should be able to `cd` straight to their screen without hunting through a component tree.

## Practical build-order suggestion (maps to your Critical Path, Section 39)

Start backend-only, no frontend, no LLM:
1. `models/` + `alembic` migration → freeze schema first (this is your Day-1 task; changing it later cascades everywhere).
2. `engines/financial_engine.py` + `tests/test_boundary_values.py` — write the test table from Section 17.1 *before* the implementation. This one file is your strongest live-demo defense.
3. `engines/scheme_engine.py` + `data_layer/datasets/schemes/nsfdc_schemes.json`.
4. Only then wire `api/` routes, then frontend, then `ai_layer/` last — narration is the least judge-risky part to leave until Day 2/3.

## One monetization note worth filing away

Since NSFDC/MoSJE is the anchor client for this PS, the most realistic post-hackathon revenue path isn't B2C (rural users won't pay) — it's **B2G/B2B2C**: license the deterministic engine (`engines/` + `data_layer/`) as an assessment layer that State Channelizing Agencies or NBFC-MFIs plug into their own loan-origination flow, charging per-assessment or as an annual SaaS seat. The confidence-tagging system becomes the actual product moat there, because a lender cares more about "which of these applications have thin data and need manual review" than about the rural-facing UI.
