# Data Provenance

How each external figure reaches the screen, and what it is allowed to claim.

This document exists because the project's central risk is a number that looks
authoritative and cannot be checked. Every provider below is therefore described
by what it **actually does in this build**, not by what its documentation says
it could do.

## The rule

A figure may only be attributed to a source that produced it. The
attribution names the *method*, not an organisation, whenever the method is a
fallback or an approximation. No provider here is credited with a number it did
not compute.

## Attribution vocabulary

| Label | Meaning |
| --- | --- |
| `VERIFIED` | Retrieved from a configured source, within range, provenance recorded |
| `ESTIMATED` | Computed from cited inputs; the derivation is recorded |
| `INFERRED` | Computed from a national or coarse average; carries no information about this location |
| `STALE` | Older than the freshness threshold; confidence penalised |
| `CONFLICTING` | Inputs disagree |
| `MISSING` | No measurement was obtained; the value is `None` |
| `UNAVAILABLE` | No measurement is possible; the value is `None` |

`MISSING` and `UNAVAILABLE` are not interchangeable in meaning, but both mean
"not a number". Neither is ever rendered as `0`.

## Providers

### OpenStreetMap Overpass — competitors

- **Module:** `app/api_clients/overpass_client.py`
- **State:** working, network required
- **Produces:** mapped businesses within `CATCHMENT_RADIUS_M` (5,000 m)

Two properties matter and are tested in
`tests/test_provider_truthfulness.py`.

**A failed survey is not a survey that found nothing.** The client returns
`{"status": "ok" | "failed", "records", "error"}`. A timeout, DNS failure or
HTTP 504 is `"failed"`, and `DataRetrieval.get_competitors` then reports
`count: None` with `evidence_state: MISSING` and a note saying the survey could
not be run. It used to return `[]` for both cases, so a network error surfaced
to the founder as "no competitors are mapped near you" — a measured fact about
the market when nothing had been measured.

A survey that completed and found nothing is reported differently: `count: 0`,
`evidence_state: UNAVAILABLE`, and a note that this is a statement about OSM
coverage rather than about the market.

**The client waits longer than the server is asked to work.** The query's
`[timeout:N]` and the HTTP timeout both derive from
`settings.overpass_timeout_seconds`. The HTTP wait is that budget plus
`RESPONSE_MARGIN_S`. They used to be 25 s and 5 s respectively, so the server
was told it had 25 seconds to answer a query nobody was waiting for.

**Coverage caveat, always attached.** OSM records only businesses volunteers
have mapped. Coverage of unregistered and informal micro businesses in rural
India is very low, so a count from this source is a **lower bound**, never an
estimate of actual competition. The word "mapped" appears in every note.

### WorldPop / gridded population — `local_population`

- **Module:** `app/api_clients/worldpop_client.py`
- **State:** no gridded source configured (`GRID_ENDPOINT = ""`)

`get_population_record` returns one of:

- `INFERRED` — the areal estimate, for valid coordinates and radius
- `UNAVAILABLE` — bad coordinates, or radius outside `[0.5, 25.0]` km

The absence of a gridded source is **not** an `UNAVAILABLE` outcome. Every valid
request takes the areal path. An earlier docstring claimed otherwise.

The areal estimate is `circle area × rural mean density`, where the density is
Census of India 2011 national totals over land area. It uses **no information
about the actual place**: a densely settled village and a sparse one receive the
same figure. That is why it is `INFERRED`, capped at `MEDIUM` confidence, and
carries the phrase `COARSE AREAL ESTIMATE, NOT A GRID-BASED COUNT` in its
`limitations`. `density_basis()` exposes the constants for the assumptions
panel, including the 2011 reference year.

This module previously computed a number from a hand-written metro bounding-box
switch and let the caller label it `data_origin: "WorldPop Spatial API"` — a
fabricated figure carrying a real organisation's name. That is the failure mode
this project exists to prevent, and the module docstring records it.

### Census India — demographics

- **Module:** `app/api_clients/census_client.py`
- **State:** **not implemented. A stub.**
- **Produces:** nothing. `get_demographics` always returns `None`.

There is no URL, no request construction and no response parsing, with or
without a key. The API key is now passed through from
`settings.census_api_key`; it previously was not, so the client reported "no key
provided" even when one was configured.

The earlier version logged `Falling back to next data source` on every call,
which reads as a working client degrading gracefully. It is not one, and the
fallback is the caller's decision. `DataRetrieval` treats the `None` as "no
census figure available" and says so, rather than as a transport failure worth
retrying.

Implementing this properly requires resolving a coordinate to a Census Village
Code first, because data.gov.in census tables are keyed by village code and not
by latitude. Until that exists, the log says the client is not implemented.

Population currently reaches the product through the areal path above, labelled
as an estimate rather than as a census count.

## Evidence persistence

Phase 2 stores `EvidenceRecord` objects per-process and in memory only
(`app/evidence/`). It is **not** durable, and this is stated in the module
rather than inferred: a restart loses it. `EvidenceState`, `validated`,
`finite` and `compute_coverage` are the shared vocabulary.

## Confidence scoring

`app/financial/gates.py` scores confidence by mean source weight, then
multiplies for deductions, recording the reason for each in `basis`:

| Condition | Effect |
| --- | --- |
| No provenance recorded | score `0.25`, capped at `LOW` |
| Stale inputs (`freshness_days > FRESHNESS_HALFLIFE_DAYS`) | `× STALE_CONFIDENCE_MULTIPLIER` (0.80) |
| Contradictory inputs | `× (1 − 0.15 × n)` |
| Missing or unmodelled fields | `× (1 − 0.05 × n)` |
| Any input at `SEVERITY_ERROR` | score capped at `0.05` |

Source weights live in `SOURCE_CONFIDENCE_WEIGHT`: user-provided `1.00`,
source-derived `0.85`, template default `0.60`, estimate `0.40`, model
assumption `0.30`, demo data `0.20`. The staleness threshold is read from
`FRESHNESS_HALFLIFE_DAYS`; it used to be a hardcoded `365` at the use site,
sitting beside a constant declaring the same policy.

A confidently-measured loss is still a loss, and a profitable projection on
template defaults is not evidence of anything. That is why the confidence score
is separate from the verdict.

## Retrieval (RAG)

- **Module:** `app/rag/`
- **Storage:** SQLite tables `yukti_rag_documents` and `yukti_rag_chunks`,
  created on demand
- **Ranking:** token overlap with body coverage, a `TITLE_MATCH_WEIGHT` (0.5)
  title premium, and a small length-concentration factor. The title weight was
  previously 50, which let one shared word in a title outrank a document
  matching the whole query in its body.

`grounded` is only `True` when the answer cites a retrieved source by an index
that was actually in the retrieval set. Cases:

| Situation | `answer` | `grounded` | `answer_basis` |
| --- | --- | --- | --- |
| No corpus match | the "no indexed source" message | `False` | `no_retrieval_match` |
| LLM unavailable | `None` (sources still returned) | `False` | `llm_unavailable` |
| `use_llm=False` | raw excerpts | `True` | `retrieval_only_no_llm` |
| Answer with a valid citation | generated text | `True` | `llm_cited` |
| Answer with no citation, or one out of range | generated text | `False` | `llm_uncited` |

When the LLM was unavailable the service used to return the concatenated source
chunks *as the answer* with `grounded: True`, and it asserted `grounded: True`
unconditionally whenever hits existed — so a fabricated answer citing nothing, or
citing `[SOURCE 9]` out of a five-source retrieval, was reported as grounded.

**Ingestion allowlist.** `POST /api/rag/ingest` reads only from
`RAG_DOCUMENTS_DIR`, `SEED_DIR`, `RAW_DIR` and `DATA_DIR`, and only for
`.txt .md .csv .json .pdf`. The path is resolved before the containment test, so
neither `..` traversal nor a symlink can escape. A relative path is anchored to
`RAG_DOCUMENTS_DIR`, not the process working directory. This endpoint was
previously an arbitrary file read: the `404` check confirmed the named file
existed, which is the opposite of a guard.

## Demo mode

`DEMO_MODE` is disclosed per response via the `X-YuktiFi-Data-Mode` header
(`live` | `demo`), and the frontend renders a banner from it. The frontend mode
starts as `null`, not presumed live, so nothing flashes as real before the
header arrives.

Demo mode does **not** tag returned values with `InputSource.DEMO_DATA`. That
enum member exists and carries a confidence weight of `0.20`, but nothing
assigns it. The disclosure is per-response, not per-field. `config.py` used to
claim it tagged every demo value.

`DEMO_ALLOW_NETWORK=true` permits provider calls while `demo_mode` is on, so the
header reports `live` for whatever was actually fetched. It follows the
providers' own behaviour, which is the honest definition available at the
response level.

## Not verified in this build

- Live Census, data.gov.in, Agmarknet, Overpass and WorldPop calls.
- Gemini generation and citation behaviour against the real API.
- Cold bootstrap of the first request.
- Durability of Phase 2 evidence beyond the process.
