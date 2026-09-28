# YuktiFi — Data Strategy & Data Architecture

### The authoritative specification for: what data YuktiFi uses, where it comes from, how confident we are in it, and how it becomes a number on screen

**Scope:** SIH26091/PSC26091 prototype → stronger college-level build → realistic production system
**Method:** Every source below was checked against a live web search on 2026-09-06. Sources that could not be verified are explicitly marked `UNVERIFIED — RESEARCH REQUIRED`. Nothing here is a guess dressed up as a fact.

**Tag legend (same convention as the Master Blueprint):**
`[VERIFIED-EXTERNAL]` confirmed against a real, checked source · `[YuktiFi-DESIGN]` our decision, not stated anywhere · `[PROTOTYPE-ASSUMPTION]` synthetic/simplified for the demo · `[FUTURE-PRODUCTION]` out of scope now · `[UNVERIFIED]` flagged, not to be relied on until checked further.

---

## Executive Summary

YuktiFi's hardest engineering problem is not the financial engine — that is closed-form arithmetic and can be made perfectly correct. It is **data**. The product promises "hyper-local" intelligence — 5–10 km market reach, village-level competitor density, local purchasing power — for a country where the last full population census is from **2011** [VERIFIED-EXTERNAL], where business-registry data is sparse below the district level, and where the most complete free geospatial dataset (OpenStreetMap) has real but uneven coverage of rural India.

The central finding of this document: **almost nothing YuktiFi needs exists natively at true village/5–10 km granularity from an authoritative, current, free source.** What exists is (a) authoritative but coarse (district/block Census, State Statistical Handbooks), (b) granular but incomplete and unauthoritative (OSM points of interest), (c) granular and modelled rather than measured (WorldPop gridded population), or (d) genuinely local but user-supplied and unverifiable (a village resident telling YuktiFi "there are three tailors near me").

YuktiFi's data architecture is therefore built around one design law, inherited from the Master Blueprint's Section 8 architecture split and made concrete here:

> **Every number is tagged with how it was obtained — Known / Estimated / User-provided / AI-inferred / Unavailable — and the tag is shown to the user, not buried in a log.** No dataset is stretched to claim a granularity it does not have. Where genuine village-level data does not exist, YuktiFi says so, degrades gracefully to the finest *honest* granularity, and never silently fills the gap with a plausible-sounding number.

This document is organized as: (1) what data the product needs, (2) where each piece can actually come from and at what granularity, (3) the pipeline, schema, and confidence system that turns raw sources into trustworthy output, (4) the concrete prototype dataset the team should build for SIH, and (5) a brutal, judge's-eye audit of where this all is genuinely strong and where it is not.

**Headline data credibility score (full justification in Part 16): 54/100** for the "hyper-local" claim as literally stated, rising to a defensible ~80/100 once YuktiFi's own confidence-labelling system is counted as part of the product (i.e., YuktiFi is not claiming to be more certain than the data supports — which is itself the credibility asset).

---

## PART 1 — Data Requirements Traced to PS26091

| Requirement (from PS) | Data needed | Best realistic geo. level | Prototype | Production |
|---|---|---|---|---|
| Location resolution | Village/town/block/district → lat/lon | Village (name lookup), point (geocoded) | MUST | MUST |
| Population in reach | Resident population within ~5–10 km | Village (Census) + grid interpolation (WorldPop) | MUST (curated) | MUST (live) |
| Households | Household count within reach | Village (Census 2011) | SHOULD (curated) | MUST |
| Consumer base / demand proxy | Spending-capable population by category | District/block proxy, no true local measure exists | MUST (heuristic) | SHOULD improve with survey data |
| Business categories | Taxonomy: dairy, retail, textiles, food-processing, etc. | N/A — internal taxonomy | MUST | MUST |
| Existing competitors | Named/typed businesses near the point | Point-level where OSM/Udyam data exists, else absent | MUST (curated + OSM) | MUST (OSM + partner + user-submitted) |
| Competitor density | Competitors per population/area | Derived, not sourced | MUST (calculated) | MUST |
| Market demand | Category-level demand intensity | Not directly measurable locally — must be modelled | MUST (heuristic, labelled) | SHOULD (survey-augmented) |
| Pricing | Product/service price locally | Mandi-level for agri-commodities only; else absent | MUST (regional benchmark + user input) | SHOULD (crowdsourced local prices) |
| Purchasing power | Local income/consumption proxy | District (MOSPI consumption survey), never household-level | MUST (index, labelled estimate) | SHOULD (finer proxies) |
| Distribution channels | Roads, markets, transport hubs | Village/road-segment level via OSM (uneven coverage) | SHOULD | MUST |
| Seasonality | Category demand cycles | Category-level knowledge, not location-specific | MUST (general pattern, labelled) | SHOULD (localised where data exists) |
| Supply chain / local risk | Structural risk factors by category | Category-general; local specifics require user input | MUST (category-general) | SHOULD |
| Business costs | Category cost breakdown | Curated/researched, not location-specific | MUST (curated) | SHOULD (regional cost indices) |
| Government schemes | Eligibility, thresholds, rates | National/state (official) | MUST (verified, versioned) | MUST |
| Financing parameters | 10/90 split, EMI inputs | N/A — deterministic math | MUST | MUST |
| Entrepreneur inputs | Capital, category, experience | User-provided | MUST | MUST |

**Explicitly excluded as "nice but not needed":** satellite footfall analytics, individual credit-bureau data, real-time social-media demand signals — all rejected in Master Blueprint Section 1.D and re-rejected here on data-availability grounds (Part 4).

---

## PART 2–3 — Source Research & Verification

Every row below was checked directly; access method, granularity, and licensing reflect what was actually found, not what would be convenient.

### 2.1 Government / official sources

| Source | Owner | Data | Granularity | Access | Freshness | License | YuktiFi use |
|---|---|---|---|---|---|---|---|
| **data.gov.in** (Open Government Data Platform) | NIC, MeitY, Govt. of India [VERIFIED-EXTERNAL] | 1000s of sectoral datasets (agri, MSME, health, etc.) | Mostly district/state; varies by dataset | Public web + registered-user REST API with API key; many resources have **no live API**, only static CSV/XLS downloads [VERIFIED-EXTERNAL] | Highly variable — some daily (Agmarknet feed), many stale for years | Content owned by respective ministries; site itself is a NDSAP-compliant open platform | Primary catalogue to search category-by-category; treat "has an API" as unverified per-dataset until checked |
| **Census of India 2011** (Registrar General & Census Commissioner) | Govt. of India | Population, households, literacy, occupational structure, amenities (Village Directory) | **Village level exists** (Primary Census Abstract, District Census Handbooks) | Public downloads (censusindia.gov.in), no live query API | **Frozen at 2011** — genuinely the newest full count; Census 2021 was postponed and has not been conducted as of this writing [VERIFIED-EXTERNAL] | Public domain govt data | Best real village-level population/household baseline, but 13+ years stale — must be shown with an explicit "2011 Census, extrapolated" badge, never presented as current |
| **MOSPI** (Ministry of Statistics & Programme Implementation) | Govt. of India | Household Consumption Expenditure Survey (HCES), National Sample Survey rounds, National Accounts | State/sector, sometimes district in survey microdata | Public reports/microdata downloads; no live API | HCES 2022–23 is the latest round [VERIFIED-EXTERNAL] | Public | Best legitimate basis for a purchasing-power *index* — never household-level income |
| **Agmarknet / data.gov.in mandi price feed** | Directorate of Marketing & Inspection, Ministry of Agriculture [VERIFIED-EXTERNAL] | Daily wholesale min/max/modal price + arrivals, 300+ commodities, ~4,000+ APMC markets | **Mandi/market level** — genuinely granular for agri commodities | data.gov.in resource page states **no confirmed public API for this specific resource** (API must be requested); a mirror academic tool (CEDA/Ashoka, agmarknet.ceda.ashoka.edu.in) republishes it monthly with downloadable raw files [VERIFIED-EXTERNAL] | Daily at source; CEDA mirror refreshes monthly | Government-sourced, redistributed for research by CEDA — attribute to Agmarknet/DMI | Only genuinely current, near-local, non-modelled dataset in this whole document — use for dairy/agri-linked categories' pricing input |
| **NSFDC** (National Scheduled Castes Finance & Development Corporation) | MoSJE, Govt. of India [VERIFIED-EXTERNAL] | Scheme rules: Micro Credit Finance (≤₹1.40 lakh project, loan ≤90%/₹1.25 lakh, **6.5%** beneficiary rate, 3-yr tenure incl. 3-month moratorium) and Term Loan (>₹1.40 lakh–₹50 lakh, loan ≤90%/₹45 lakh, **8% (4% CA charge → 8% beneficiary rate on Term Loan tier)**, up to 7-yr tenure) | National scheme, applies uniformly | Static official pages (nsfdc.nic.in, mirrored on devmosje.negd.in) — no API | Confirmed live and matching the Master Blueprint's cited figures at time of check [VERIFIED-EXTERNAL] | Official government scheme text | **This is the single most load-bearing external fact in the entire product** — must be re-verified against nsfdc.nic.in immediately before every demo/submission, not just once |
| **PMEGP** (Prime Minister's Employment Generation Programme) | Ministry of MSME, via KVIC [VERIFIED-EXTERNAL] | Margin-money subsidy 15–35% of project cost depending on category/area; manufacturing cap ₹50 lakh, service/business cap ₹20 lakh; general category 15%(urban)/25%(rural), special category 25%(urban)/35%(rural) | National scheme | kviconline.gov.in — static guideline pages, online application portal, no public data API | Current scheme cycle runs FY2021-22 to FY2025-26 [VERIFIED-EXTERNAL] | Official govt scheme | A **second**, larger-ticket scheme YuktiFi should route to above the NSFDC Term Loan ceiling — see Part 15 flag on the Build Guide's PMEGP figures |
| **CGTMSE** (Credit Guarantee Fund Trust for Micro & Small Enterprises) | Ministry of MSME + SIDBI | Provides a **credit guarantee to lending banks**, not a direct loan and not itself an "interest rate" product | National | Static official pages | Current | Official | Important correction — see Part 15/18 audit; CGTMSE should not appear in a scheme table with its own "interest_rate_pct" field the way the current Build Guide models it |
| **Udyam Registration** (MSME registry) | Ministry of MSME | Registered MSME counts, category, investment/turnover bands | Aggregate dashboards public; **individual business-level registry is not openly downloadable/searchable by the public for competitor mapping** [UNVERIFIED — RESEARCH REQUIRED beyond aggregate dashboards] | Aggregate dashboard only, as far as verified here | Live dashboard | Government, but granular records are not confirmed publicly queryable | Cannot be relied on as a competitor-count source without further, dedicated verification; treat as **not realistically available** for the prototype |
| **NABARD** | Govt. of India (agri/rural finance apex bank) | Rural credit data, All-India Rural Financial Inclusion Survey | State/district in published reports | Report downloads, no live API confirmed | Periodic (survey-based) | Public reports | Background/context source for rural financial-inclusion narrative, not a live feed |
| **State District Statistical Handbooks** | Respective state Directorates of Economics & Statistics | Sectoral employment, local economic indicators | **District** (occasionally block) | PDF downloads, machine-readability varies wildly by state | Annual, but publication lag varies by state (some multi-year behind) | Public, state-specific licensing not always stated | Only usable per-state after manual PDF-table extraction — labour-intensive, not automatable generically |

### 2.2 Geospatial / open sources

| Source | Owner | Data | Granularity | Access | Freshness | License | YuktiFi use |
|---|---|---|---|---|---|---|---|
| **OpenStreetMap via Overpass API** | OSM Foundation / community [VERIFIED-EXTERNAL] | Shops, amenities, roads, POIs with `shop=*`, `amenity=*`, etc. tags | Point-level **where mapped** — coverage in rural India is real but genuinely uneven | Free public Overpass endpoints (overpass-api.de and mirrors); "be-friendly" usage limits apply, not a formal quota — heavy/parallel/commercial-scale use is expected to move to a self-hosted instance or regional extract [VERIFIED-EXTERNAL] | Near-real-time (community edits), but a given rural area may not have been edited in years | **ODbL 1.0** — attribution required, and any produced database that is a "derivative database" must also be shared under ODbL (share-alike); a *produced work* (e.g. a rendered map, or facts extracted and substantially transformed) has lighter obligations, but this line is genuinely a legal-review item, not something to self-certify [VERIFIED-EXTERNAL] | Best free option for real competitor/POI/road data; **must never be silently assumed complete** — sparse OSM coverage in a village must be shown as "no data," not "zero competitors" |
| **Geofabrik regional extracts** | Geofabrik GmbH | Pre-packaged OSM country/region `.osm.pbf` downloads | Same underlying OSM data, packaged for bulk/offline use | Free download | Updated daily | Same ODbL obligations as OSM | Better fit than live Overpass calls for an **offline prototype** — download once, query locally |
| **Natural Earth** | Public-domain cartographic dataset | Coastlines, admin boundaries, physical geography | Coarse (country/state) | Free download | Static/rarely updated | Public domain | Only useful for background basemap context, not local intelligence |
| **WorldPop (gridded population)** | University of Southampton et al., Bill & Melinda Gates Foundation-funded [VERIFIED-EXTERNAL] | Modelled population count per ~100m×100m grid cell, built by disaggregating census totals using ML on satellite/geospatial covariates | **Sub-village grid**, but this is a **model output, not a measurement** — it redistributes the same 2011 (or later UN-adjusted) totals spatially, it does not independently know more than the Census did | Free download (worldpop.org) and via Google Earth Engine | Grids exist through ~2020/2021 vintages; India's underlying counts still trace back to 2011 Census + UN adjustment, not a fresh count | **CC BY 4.0** — free for commercial and non-commercial use with attribution [VERIFIED-EXTERNAL] | Genuinely useful for turning a village-level 2011 count into a *spatial* estimate for the 5–10 km radius calculation (Part 5) — but must be labelled "Estimated (WorldPop model, based on 2011 Census)," never "Known" |
| **Overpass Turbo / QGIS + OSM plugins** | Community tooling | Interactive query/testing front-end for Overpass | — | Free, browser-based | — | Same ODbL terms | Development/debugging tool, not a production dependency |

### 2.3 Commercial / third-party sources

| Source | Cost | API limits | Production suitability |
|---|---|---|---|
| Google Places API | Pay-per-request after free tier; non-trivial at scale | Rate-limited by billing tier | Best real-world business-listing coverage in India including rural areas, but a genuine recurring cost and a ToS that restricts bulk caching/redistribution of results — **[UNVERIFIED — RESEARCH REQUIRED]** exact current caching terms before production commitment |
| Justdial / IndiaMART-style directories | No public API confirmed for bulk competitor extraction | N/A | **UNVERIFIED — RESEARCH REQUIRED**; likely to require a commercial data partnership, not a scrape — scraping ToS-protected listing sites is both a legal risk and unreliable |
| Market-intelligence vendors (e.g., retail analytics platforms) | Enterprise pricing, not published | N/A | Not viable for a hackathon or college-stage budget; noted in Master Blueprint as inspiration only, not a source (Section 2.2 landscape scan) |

### 2.4 Research / academic sources (methodology only — never live data)

- CEDA (Ashoka University) Agmarknet mirror — used above as an *access route* to real government mandi data, not as an independent dataset.
- Published papers on gravity-model retail catchment estimation and WorldPop's own peer-reviewed methodology papers — used to justify the population-interpolation *method* in Part 5, never cited as a live data source.

---

## PART 4 — Data Reality Check (the matrix that keeps YuktiFi honest)

| Data need | A. Directly available | B. Coarser level only | C. Available via API | D. Derivable | E. Estimable (defensible model) | F. Requires user input | G. Not realistically available |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Population at exact point | | ✓ (village/district) | | | ✓ (WorldPop grid interpolation) | | |
| Households | ✓ (village, 2011) | | | | | | |
| Consumer base in 5–10 km | | | | ✓ (from population+grid) | ✓ | | |
| Competitor list | | | ✓ (OSM, partial) | | ✓ (density heuristic to fill OSM gaps) | ✓ (user-reported) | |
| Competitor count — exhaustive/authoritative | | | | | | | ✓ |
| Local demand intensity | | | | | ✓ (heuristic model, Part 10) | ✓ | |
| Local price (specific shop) | | | | | | ✓ | |
| Regional price benchmark (agri) | ✓ (Agmarknet, mandi-level) | | ✓ (via CEDA mirror) | | | | |
| Regional price benchmark (non-agri retail) | | | | | ✓ (category heuristic) | ✓ | |
| Local purchasing power (individual) | | | | | | | ✓ |
| Purchasing power (district index) | | ✓ (MOSPI HCES) | | ✓ (index construction) | | | |
| Roads/transport hubs | | | ✓ (OSM, uneven) | | | | |
| Seasonality (category-general) | ✓ (agronomic/commercial knowledge) | | | | | | |
| Seasonality (this exact village) | | | | | | ✓ | ✓ (mostly) |
| Local supply-chain risk (specific) | | | | | | ✓ | |
| Category cost structure | | ✓ (national/regional research) | | | | ✓ (local adjustment) | |
| Government scheme rules | ✓ (official pages) | | | | | | |
| Scheme eligibility for this user | | | | ✓ (rule engine) | | ✓ (self-declared inputs) | |

**Reading this matrix honestly:** the single cell that matters most for the product's core "hyper-local" promise — *competitor count, exhaustive and authoritative* — is squarely in column **G, not realistically available**, for the vast majority of Indian villages. This is not a flaw to hide; it is the reason the confidence system (Part 6/Part 9 below) exists at all.

---

## PART 5 — The 5–10 km Market Radius, Solved Technically

### 5.1 Geographic center
The village/town centroid is used, not an arbitrary point inside it. For the prototype, centroids are manually looked up once per demo location (from OSM's `place=village`/`place=town` node, cross-checked against the Census village code) and stored as `(lat, lon)` in `locations.json` — **not** re-geocoded live on every request (a live geocoding dependency is an unnecessary demo-day failure point).

### 5.2 Radius
5 km and 10 km are both computed as **great-circle distance**, not straight-line planar distance, because errors compound at rural distances if you naively treat lat/lon as Cartesian.

**Haversine formula** (sufficient at this scale — sub-meter accuracy is not needed, and this avoids introducing PostGIS for the prototype):

```python
import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088  # mean Earth radius, km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
```

**Decision — do we need PostGIS for the prototype? No.** [YuktiFi-DESIGN] At prototype scale (a few hundred competitor points, 2–3 demo locations), a Haversine filter over an in-memory or SQLite list is O(n) and instant. PostGIS earns its complexity only once the competitor table has tens of thousands of rows nationally and needs spatial indexes (`GIST`) for sub-second bounding-box queries — that is a **production** decision (Part 20).

### 5.3 Population inside the radius
Method, in order:
1. Take the 2011 Census village/town population as the anchor value for the named settlement itself [VERIFIED-EXTERNAL, but 2011-dated].
2. Pull the WorldPop 100m grid cells whose centroids fall inside the 5 km/10 km circle (a simple point-in-circle test per grid cell using the same Haversine function) and sum them, **cross-checked** against the named-settlement anchor so the estimate isn't wildly inconsistent with the one real number we have.
3. Where WorldPop access isn't wired up (offline demo mode), fall back to a **documented density heuristic**: rural India's average rural population density (≈ national rural average, itself a published Census figure) × circle area, explicitly labelled "coarse areal estimate, not grid-based."

This is shown to the user as: **"Estimated serviceable population: ~X,000 (Estimated — based on 2011 Census + WorldPop 2020 population grid, radius 5 km)."** Never as a bare, unlabelled number.

### 5.4 Households
Households = population ÷ average household size, where average household size is the **Census 2011 village-level figure** for that exact village (already in the Village Directory) — not a national average, because household size varies meaningfully across states. This is one of the few sub-village facts that genuinely **is** Known, not Estimated, because Census 2011 already published it at village granularity.

### 5.5 Competitors inside the radius
Same Haversine filter applied to the competitor point dataset (Part 6). Output is always paired with a coverage caveat (Part 4/9): "N competitors found in available data — this reflects OSM/curated coverage, not a guaranteed complete count."

### 5.6 Distribution channels
OSM `highway=*` ways and `amenity=marketplace`/`amenity=bus_station` nodes within the radius, where mapped. For the prototype this is manually curated per demo location rather than a live Overpass call (Part 7).

### 5.7 Business density
`density = competitor_count / max(households, 1)` and `competitor_count / area_km2`, both reported side by side — density-per-household is more meaningful for retail-type reach, density-per-area is more meaningful for footfall-type reach. Neither is claimed to be a market-saturation "truth," only a documented heuristic.

### 5.8 Coordinates, geocoding, indexing
- **Coordinates**: WGS84 decimal degrees throughout — the universal GPS standard, matches OSM/WorldPop/Census-derived lat-lon without conversion.
- **Geocoding**: for the prototype, a small **static lookup table** of demo village names → coordinates (curated once, Part 22) — no live geocoding API dependency, which would be both a cost and an offline-mode failure point.
- **GeoJSON**: used as the interchange format for anything shown on the MapLibre frontend (per the Build Guide's Section 29 map choice) — competitors, radius circle, and road segments are all serialized as GeoJSON `FeatureCollection`s.
- **Spatial indexing**: not needed at prototype scale (5.2); a production system would add a `GIST` index on a PostGIS `geography(Point)` column.

---

## PART 6 — Local Business / Competitor Data: The Hardest Problem

### 6.1 Source-by-source verdict

| Source | Coverage | Accuracy | Freshness | Dedup risk | Category classification | Geo. precision | Legal/licensing |
|---|---|---|---|---|---|---|---|
| OSM (Overpass) | Real but genuinely patchy in rural India — good in mapped market towns, thin in small villages | Good where present (community-verified tags) | Variable, edit-dependent | Low (each is a distinct node) | Via OSM `shop=`/`craft=`/`amenity=` tags, needs mapping to YuktiFi's own category taxonomy | Point-level, generally accurate | ODbL — attribution + share-alike for derivative databases (Part 2.2) |
| Udyam Registration (public) | Aggregate dashboards only, per current verification | N/A at business level | N/A | N/A | N/A | N/A | Not usable for competitor mapping without further, dedicated verification — **flag as UNVERIFIED, do not build a pipeline assuming record-level access exists** |
| Local directories (Justdial-type) | Better urban than rural | Self-reported by businesses, variable | Variable | Real risk (multiple listings per business) | Directory's own taxonomy, needs mapping | Often only address-level, not coordinate-level | No confirmed public bulk API — commercial partnership or manual lookup only |
| User-submitted | Whatever the user chooses to report | Unverified by construction | As reported | High if multiple users report the same shop differently | User free-text, needs normalization | User-estimated ("near the temple") | None — must be tagged "User-provided," never elevated to "Known" |
| Manually curated (team-built) | Only for the specific 2–3 demo locations | As accurate as the team's own fieldwork/research | Static until manually refreshed | Low (single authorship) | Assigned directly by the team | As precise as the team records it | None — must carry `"synthetic": true` or `"curated": true` flag, shown in UI |

### 6.2 Competitor pipeline

```text
Source (OSM Overpass export / curated JSON / user form)
        ↓
Raw data (heterogeneous schema per source)
        ↓
Cleaning (strip null coords, normalize whitespace/casing on names)
        ↓
Deduplication (same name + <50m apart across sources → merge, keep highest-confidence source)
        ↓
Geocoding (only for user-submitted text descriptions without coordinates — reverse-lookup against nearest known landmark)
        ↓
Category classification (map source-specific tag/free-text → YuktiFi's fixed category taxonomy)
        ↓
Location filtering (Haversine radius test against the query point, Part 5.5)
        ↓
Confidence scoring (source-based: OSM=Medium, curated-team=Medium/High per field-verification, user-submitted=Low until corroborated)
        ↓
Competitor dataset (versioned, provenance-tagged — Part 8)
        ↓
YuktiFi Market Intelligence Engine
```

---

## PART 7 — OpenStreetMap: An Honest Assessment

**What OSM can realistically provide:** shops (`shop=*`), amenities (`amenity=*` — clinics, schools, banks, marketplaces), road network (`highway=*`), some named settlements and administrative boundaries.

**What it cannot be assumed to provide:** a complete business census. Rural India's OSM coverage is a product of volunteer mapping activity, which correlates with things like connectivity, local mapping-community presence, and prior humanitarian-mapping campaigns (e.g., post-disaster mapping drives) — **not** with actual settlement size or economic activity. A well-mapped town of 5,000 can show more OSM shop nodes than an under-mapped town of 50,000.

**Feasibility for YuktiFi:**
- **Overpass API**: free, no API key, but "be a good citizen" usage limits apply on the public instances rather than a documented hard quota — safe pattern is one query per analysis, cached, not a query-per-page-load [VERIFIED-EXTERNAL].
- **Download options**: Geofabrik regional `.osm.pbf` extracts, updated daily, are the right choice for **offline** prototype use — download once for the demo region(s), filter locally, no live network dependency on demo day.
- **Rate limits**: no fixed published number for the main public instance; heavy/parallel/commercial use is explicitly expected to move to a self-hosted Overpass instance [VERIFIED-EXTERNAL] — irrelevant at prototype query volumes, relevant at production scale.
- **Attribution**: "© OpenStreetMap contributors" must appear wherever OSM-derived data is shown (map view, and arguably the competitor list if it's presented as sourced from OSM).
- **ODbL / derived-data question**: if YuktiFi stores and republishes OSM-derived facts (e.g., "3 grocery shops near Karha") as part of a produced analytical *report* to one end user, this is closer to a "produced work" (lighter obligation) than a redistributed "derivative database." **This distinction should be flagged for legal review before any production launch** (Part 17) — it is not something to self-certify with confidence.

**Prototype vs. production approach:** prototype uses a **static, downloaded, filtered OSM extract** for the 2–3 demo locations, refreshed manually before the demo. Production would run a scheduled Geofabrik-extract ingestion job (Part 25) rather than live Overpass calls per user request, both for cost/rate-limit reasons and for consistent snapshot-based provenance.

**Honest fallback when OSM has nothing:** the UI must show **"No mapped competitors found in this radius"** with a one-line explanation ("this may reflect limited map coverage, not an actual absence of businesses") rather than silently treating an empty result as "zero competitors — great opportunity!", which would be actively misleading (Part 38, failure mode #1).

---

## PART 8 — Population / Consumer Base: Chosen Methodology

Rejecting the blueprint-suggested simple additive formula (village + nearby settlements + grid) as stated, because it double-counts population wherever the grid cells and the named settlements overlap. The corrected method:

```text
1. Anchor: 2011 Census village/town population for the named centroid settlement  [Known, dated]
2. Spatial estimate: sum WorldPop grid cells strictly inside the 5/10 km circle    [Estimated, modelled]
3. Reconciliation: if the WorldPop sum for the anchor settlement's own footprint
   diverges from the Census anchor by more than a documented tolerance,
   flag the discrepancy in the confidence note rather than silently averaging it away
4. Reported figure = WorldPop circle sum (already spatially correct, no double count),
   with the anchor comparison shown as a cross-check, not summed on top
```

**Uncertainty propagation:** the population estimate inherits (a) Census 2011's staleness (a fixed, dateable error — rural populations have grown since 2011, so this is a **conservative under-estimate** in most areas, which is the safer direction for a lending-adjacent product) and (b) WorldPop's modelling error, which the WorldPop project's own documentation does not give as a per-cell confidence interval — so YuktiFi reports this as a **Medium-confidence Estimated** figure, never High, and never a false-precision number like "14,382" (rounded to "~14,000" or a banded range).

---

## PART 9 — Purchasing Power: What Can Honestly Be Claimed

There is **no legitimate way** to know an individual household's income from public data. What exists:

- **MOSPI Household Consumption Expenditure Survey (HCES)**, latest round 2022–23 [VERIFIED-EXTERNAL] — state/sector (rural-urban split) level average monthly per-capita consumption expenditure (MPCE).
- District Statistical Handbooks — sometimes carry district-level per-capita income estimates, quality varies by state.
- Agricultural wage/mandi price data — a legitimate **proxy** for rural cash-flow strength in agriculture-dependent districts, not income itself.

**Design: Estimated Purchasing Power Index (EPPI)** [YuktiFi-DESIGN] — a 0–100 composite of (a) state/rural MOSPI MPCE band, (b) district-level proxy indicators where available (literacy/occupational-structure mix from Census as a weak structural proxy), (c) an explicit downward/upward nudge only from *user-reported* local price observations, never invented. This index is always shown with its own confidence badge and a one-line "how we calculated this" disclosure — this is the exact kind of number a skeptical judge will probe (Part 16), so the methodology note must be reachable in the UI, not just in this document.

**What YuktiFi explicitly does NOT do:** claim to know *this specific household's* purchasing power, or present the EPPI as more precise than a district-level average nudged by weak proxies.

---

## PART 10 — Demand Estimation: Selected Approach

| Approach | Verdict |
|---|---|
| A. Government statistics | Too coarse/lagged alone (Census, HCES) — used as an input, not the whole answer |
| B. Historical market data | Doesn't exist at village level for most categories (Part 4) |
| C. Business-category heuristics | Necessary — e.g. dairy demand scales with rural households + livestock-keeping norms, tailoring with population + festival seasonality |
| D. User-provided information | Necessary corroborating signal, not sufficient alone |
| E. AI inference | **Rejected as a primary method** — the Master Blueprint's Section 8 golden rule (LLM never invents a data point) applies directly; an LLM "estimating" demand from its training data would be indistinguishable from a hallucination to the user |
| **F. Hybrid model — SELECTED** | `demand_index = f(category_heuristic_baseline, population/household proxy, purchasing_power_index, seasonality_factor, user-reported corroboration)` — every term traceable to a labelled source, combined via a **documented, published formula** (a lightweight weighted heuristic, not a black-box model), so a judge can be shown exactly how the 0–100 index was built |

**The LLM's role here is zero calculation.** It may only narrate an already-computed `demand_index` ("demand for tailoring in this area is moderate, driven mainly by the 40,000-person catchment population and typical festival-season spikes") — never produce the number itself.

---

## PART 11 — Pricing Data: Four Categories, Never Conflated

| Category | Definition | Source | UI label |
|---|---|---|---|
| **Observed price** | An actual transacted/quoted price from a live feed | Agmarknet modal price (agri commodities only) | "Observed — Agmarknet, [date]" |
| **Regional benchmark** | A researched typical range for a category/region, not this specific point | Team research from public reports, MOSPI, published cost studies | "Regional benchmark — typical range, not location-specific" |
| **Estimated local price** | Regional benchmark adjusted by the EPPI or user corroboration | Calculated | "Estimated — adjusted from regional benchmark" |
| **AI suggestion** | A pricing *strategy* recommendation (e.g., "price at the lower end of the benchmark to compete with 2 existing shops") | LLM narration layer, reasoning over already-computed benchmark + competitor data | "AI-suggested pricing strategy — not a market fact" |

These four must appear as visually distinct UI treatments (Master Blueprint Section 20 trust-first design direction), never merged into a single unlabelled "Price: ₹X" field.

---

## PART 12 — Business Cost Data

Category-specific cost models (dairy, retail, textiles, food processing, poultry, etc.) are built as a **structured schema**, populated from a blend of sources per component:

| Component | Primary source for prototype |
|---|---|
| Raw material | Category research (industry reports, Agmarknet for agri-linked inputs) — regional benchmark, labelled |
| Labor | Category research / published minimum-wage-adjacent estimates — regional benchmark |
| Rent | Curated, location-tier-adjusted (rural vs. semi-urban tier from `locations.json`) — clearly an assumption, not measured |
| Utilities | Category research — regional benchmark |
| Transport | Category research, adjusted by distance-to-market computed in Part 5 | 
| Inventory / working capital | Derived from the financial engine's own working-capital formula (Master Blueprint's deterministic layer), not sourced externally |
| Maintenance / misc. | Category research — flat percentage-of-revenue assumption, explicitly labelled as an assumption |

**Schema:**
```json
{
  "category": "dairy",
  "component": "raw_material",
  "amount": 18000,
  "unit": "INR_per_month",
  "confidence": "estimated",
  "assumption_note": "Based on 5-cattle unit, regional feed-cost research, not location-specific",
  "source": "team_research_v1",
  "last_verified": "2026-08-15"
}
```

Every cost-model row carries `confidence` and `assumption_note` as **required, not optional**, fields — this is where a demo can be caught out badly if a judge asks "why ₹18,000?" and the team has no traceable answer.

---

## PART 13 — Seasonality

Seasonality is modelled as **category-level general knowledge** (agriculture ties to sowing/harvest cycles, textiles/tailoring to festival and wedding seasons, dairy to lean summer/flush winter milk yield patterns) — sourced from general agronomic/commercial knowledge, not from any location-specific dataset, because none exists at village level for the prototype's timeframe.

**Confidence level: explicitly Medium-to-Low, and labelled "General category pattern — not verified for this specific location."** The Master Blueprint's Part 13 instruction not to call generic category seasonality "hyper-local" is honored literally: the seasonality badge never uses the word "local."

---

## PART 14 — Local Risk Data

| Risk type | Classification |
|---|---|
| Supply-chain dependency (e.g., single input supplier) | Category-general risk (AI-narrated from known category structure) |
| Transportation/access | Derived (from Part 5.6 road/market-access data where OSM coverage exists) |
| Weather/seasonal | Category-general |
| Single-buyer dependency | Category-general, unless user discloses their own buyer structure (then User-provided) |
| Infrastructure gaps | Derived from OSM amenity presence/absence within radius, labelled "based on available map data, not a verified infrastructure audit" |
| Local competition intensity | Derived (from Part 6 competitor density) |
| Demand volatility | Derived from the seasonality index (Part 13) |
| Regulatory | Category-general (AI-narrated from general regulatory knowledge for the category, e.g., FSSAI licensing for food processing) — **never scheme-specific eligibility rules**, which stay in the deterministic scheme engine only |

Every risk shown in the SWOT/threats section of the report must trace to one of: **Measured** (none exist for risk in this product), **Derived**, **Category-general**, or **AI-generated hypothesis** — and the last of these four is used sparingly and always visibly labelled, per Master Blueprint Section 10.

---

## PART 15 — Government Scheme Data: A Versioned, High-Stakes Database

### 15.1 Verified scheme records

| Field | NSFDC Micro Credit Finance | NSFDC Term Loan | PMEGP |
|---|---|---|---|
| Organization | NSFDC (MoSJE) | NSFDC (MoSJE) | KVIC (Ministry of MSME) |
| Project cost range | ≤ ₹1,40,000 | > ₹1,40,000 – ≤ ₹50,00,000 | ≤ ₹50 lakh (manufacturing) / ≤ ₹20 lakh (service) |
| Max loan/subsidy | 90% of cost, max ₹1.25 lakh | 90% of cost, max ₹45 lakh | Margin-money subsidy 15–35% depending on category & area [VERIFIED-EXTERNAL] |
| Beneficiary rate | 6.5% p.a. | ~8% p.a. (NSFDC charges CAs 4%, CAs pass through to beneficiaries) | N/A — subsidy, not an interest-bearing NSFDC-style loan; balance is a normal bank term loan |
| Tenure | ≤ 3 years | ≤ 7 years | Bank-loan-dependent, not fixed by PMEGP itself |
| Moratorium | 3 months | 6 months | Bank-loan-dependent |
| Eligibility gate | Scheduled Caste individual/JLG/society [VERIFIED-EXTERNAL] | Same | Any individual 18+, no prior govt subsidy availed, min. education for larger projects [VERIFIED-EXTERNAL] |
| Official URL | nsfdc.nic.in | nsfdc.nic.in | kviconline.gov.in/pmegpeportal |
| Source confidence | High — cross-confirmed across NSFDC's own site and MoSJE's dev portal | High | High |
| Last verified (this document) | 2026-09-06 | 2026-09-06 | 2026-09-06 |

**⚠️ Correction to the existing Prototype Build Guide (Section 12 `schemes.json`) — required per this document's audit mandate:**
1. The Build Guide's PMEGP entry uses a flat **`"subsidy_pct": 25`** and a fabricated **`"interest_rate_pct": 9.5`**. Real PMEGP subsidy is **category- and area-dependent (15–35%)**, and PMEGP itself does not set an interest rate — the *balance* is a normal bank term loan at the bank's own rate. This field should be restructured, not just re-valued.
2. The Build Guide models **CGTMSE** as a loan product with its own `"interest_rate_pct": 11"`. CGTMSE is a **credit guarantee trust**, not a lender — it guarantees a bank loan, it does not itself charge interest. Including it in the scheme-router table with a direct interest rate is a **structural data-modelling error**, not just a stale number, and should be corrected before this table is used in any judged demo.
3. The Build Guide correctly self-flags these as `"BLUEPRINT-TODO"` placeholders — this document promotes that TODO to a **MUST-FIX**, because scheme-threshold correctness is explicitly named the #3 "must fix" item in the Master Blueprint's own Section 40 brutal score.
4. **Recommended fix:** replace the Build Guide's placeholder `schemes.json` with the NSFDC + PMEGP records verified in the table above, and either drop CGTMSE from the router or remodel it correctly as a "guarantee eligibility flag" attached to whichever bank-loan scheme it applies to, not as a standalone interest-bearing scheme.

### 15.2 Versioned scheme database design
```json
{
  "scheme_id": "NSFDC_MICRO_2026",
  "name": "NSFDC Micro Credit Finance",
  "version": "2026-09-06",
  "effective_date": "unspecified-by-source",
  "last_verified_date": "2026-09-06",
  "source_url": "https://nsfdc.nic.in",
  "source_confidence": "high",
  "fields": { "...": "as in 15.1 table" },
  "superseded_by": null
}
```
**Outdated-rule detection:** every scheme record's `last_verified_date` is checked against a rolling threshold (e.g., 90 days for scheme data, per Part 18 freshness policy); the report UI shows the verification date directly next to any scheme cited, so staleness is visible to the user even before an automated re-check pipeline exists in production.

---

## PART 16 — Data Provenance

```text
Data Point → Source → Source URL → Retrieved At → Effective Date → Transformation → Confidence → YuktiFi Output
```

| Field | Lives in |
|---|---|
| `source_name`, `source_url` | Database (attached to the record) |
| `retrieved_at` | Database |
| `effective_date` | Database |
| `transformation_note` | Database (e.g., "WorldPop grid sum, 5km radius") |
| `confidence_level` | Database, surfaced via API |
| Visible citation | **UI** — every material number gets a small "ⓘ source" affordance, not buried in a footer |
| Full chain | **Report PDF** appendix — "Data Sources & Methodology" page, so a judge or a bank officer reading the printed report can audit it later |
| Raw provenance log | **Logs** — for debugging/dispute resolution, not user-facing |

---

## PART 17 — Confidence System

**Levels:** HIGH (directly sourced, current, reliable) · MEDIUM (derived/regional) · LOW (heuristic/sparse) · UNAVAILABLE (no evidence).

**Composite confidence** for any single output = the **minimum**, not the average, of its four sub-scores — because a number is only as trustworthy as its weakest link:

- **Source confidence** — is the underlying source authoritative? (NSFDC scheme text = High; a single user report = Low)
- **Freshness confidence** — how stale is it relative to its own freshness policy (Part 18)? (2011 Census population = Medium, not High, purely on age)
- **Geographic confidence** — was it measured at this granularity or interpolated/borrowed from a coarser level? (District MOSPI figure applied to a village = Medium at best)
- **Completeness confidence** — how much of the expected data is actually present? (Zero OSM competitor points in a radius = Low completeness, which must not be read as "confirmed zero competitors")

Taking the minimum (not an average) is a deliberate, documented methodology choice — it prevents one strong sub-score (e.g., a highly authoritative but very stale source) from masking a genuinely weak one.

---

## PART 18 — Data Freshness Policy

| Data type | Update frequency (researched, not assumed) | Rationale |
|---|---|---|
| Government scheme rules | **Re-verify every 30–90 days**, and always immediately before any public demo/submission | Highest-stakes category; NSFDC/PMEGP rates and thresholds can change with budget cycles |
| Mandi prices (Agmarknet) | Daily at source; prototype snapshot refreshed weekly is acceptable | Genuinely fast-moving, but YuktiFi's use case (regional benchmark) tolerates a short lag |
| Competitor data (OSM) | Monthly re-extract for production; static for prototype demo window | OSM rural edits are infrequent enough that daily polling has no benefit and wastes Overpass "be-friendly" budget |
| Population/households (Census-based) | Effectively **static until the next full Census** (frozen at 2011 as of this writing) | No update cadence exists for us to follow — this is a structural staleness, not a policy failure, and must be communicated as such |
| WorldPop grids | New vintage roughly per major WorldPop release cycle (multi-year) | Modelled, not measured — treat any single vintage as "current enough" for a Medium-confidence estimate |
| Purchasing power (MOSPI HCES) | Per survey round (multi-year; latest is 2022–23) | Survey-based by design |
| Business cost/category research | Reviewed at each major team iteration (no external cadence to track) | Curated content, not an external feed |
| Static geography (roads, admin boundaries) | Infrequent (annual check-in sufficient) | Low rate of change |

---

## PART 19 — Data Pipeline (Prototype vs. Production)

```text
                 External Sources
                        │
      ┌─────────────────┼─────────────────┐
      ↓                 ↓                 ↓
  Government        Geospatial          Market
  (Census, NSFDC,    (OSM/Geofabrik,   (Agmarknet,
   PMEGP, MOSPI)      WorldPop)         team research)
      │                 │                 │
      └─────────────────┼─────────────────┘
                        ↓
                    INGESTION
                        ↓
                 RAW DATA LAYER
                        ↓
             VALIDATION / CLEANING
                        ↓
                 NORMALIZATION
                        ↓
              GEOSPATIAL PROCESSING (Haversine radius filter, Part 5)
                        ↓
               FEATURE ENGINEERING (demand_index, EPPI, density)
                        ↓
             CONFIDENCE / PROVENANCE TAGGING
                        ↓
                  CURATED DATASET
                        ↓
             ┌──────────┴──────────┐
             ↓                     ↓
       YuktiFi ENGINES            AI LAYER
             │                     │
             └──────────┬──────────┘
                        ↓
                    YuktiFi API
                        ↓
                     FRONTEND
```

**Prototype:** ingestion = a one-time manual/scripted run producing static JSON files (Part 22), not a running service. **Production:** ingestion = scheduled jobs per source (Part 21), each independently versioned and monitored.

---

## PART 20 — Data Storage

| Tier | Choice | Why |
|---|---|---|
| **Prototype** | SQLite (matches Build Guide Section 10/11 exactly) + flat JSON seed files | Zero-setup, perfectly reproducible demo, no server dependency — this document does not override the Build Guide's storage choice, it endorses it |
| **College-level** | PostgreSQL (Supabase, per Build Guide Section 2) | Enables the crowdsourcing form (Master Blueprint Section 9.2) and multi-location scaling without a schema rewrite |
| **Production** | PostgreSQL **+ PostGIS** extension for spatial indexing at national scale, object storage for raw source snapshots (audit trail), no data warehouse or vector database | A data warehouse is unjustified until analytical query volume across many tables/users demands it; a vector database is unjustified because Part 24 concludes YuktiFi does not need RAG in any near-term tier |

---

## PART 21 — Final Data Model

Builds directly on the Build Guide's Section 10 ERD, extending it with the provenance/confidence fields this document requires as MUST (Master Blueprint Section 32 already lists `ConfidenceTag` and `Source` as first-class entities — this is that design, made concrete):

```sql
-- Extends the Build Guide schema; new/changed columns marked NEW
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,                  -- e.g. "NSFDC official site"
    url TEXT,
    owner_org TEXT,
    license TEXT,
    reliability TEXT CHECK (reliability IN ('high','medium','low'))
);

CREATE TABLE market_metrics (              -- NEW: generalizes market_indicators
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    business_category TEXT NOT NULL,
    metric_name TEXT NOT NULL,             -- e.g. "demand_index", "eppi", "competitor_density"
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    confidence TEXT CHECK (confidence IN ('known','estimated','user_provided','ai_inferred','unavailable')),
    source_id INTEGER REFERENCES data_sources(id),
    effective_date DATE,
    retrieved_at TIMESTAMP DEFAULT now(),
    transformation_note TEXT
);

CREATE TABLE competitors (                  -- extends Build Guide's table
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    business_category TEXT NOT NULL,
    name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    estimated_scale INTEGER CHECK (estimated_scale BETWEEN 1 AND 5),
    source_id INTEGER REFERENCES data_sources(id),   -- NEW
    confidence TEXT DEFAULT 'medium',                 -- NEW
    last_verified DATE,                               -- NEW
    synthetic BOOLEAN DEFAULT false                   -- NEW
);

CREATE TABLE prices (                       -- NEW
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    product TEXT NOT NULL,
    location_id INTEGER REFERENCES locations(id),
    value DOUBLE PRECISION NOT NULL,
    unit TEXT,
    price_type TEXT CHECK (price_type IN ('observed','regional_benchmark','estimated_local','ai_suggestion')),
    source_id INTEGER REFERENCES data_sources(id),
    date DATE
);

CREATE TABLE cost_models (                  -- NEW
    id SERIAL PRIMARY KEY,
    business_category TEXT NOT NULL,
    component TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    unit TEXT,
    confidence TEXT,
    assumption_note TEXT,
    last_verified DATE
);

CREATE TABLE schemes (                      -- extends Build Guide's table
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    min_project_cost DOUBLE PRECISION NOT NULL,
    max_project_cost DOUBLE PRECISION NOT NULL,
    subsidy_pct DOUBLE PRECISION,
    max_loan_amount DOUBLE PRECISION,
    interest_rate_pct DOUBLE PRECISION,     -- nullable: not every scheme (e.g. a guarantee product) has one
    max_tenure_months INTEGER,
    eligibility_summary TEXT NOT NULL,
    source_url TEXT NOT NULL,               -- NEW, required
    last_verified_date DATE NOT NULL,       -- NEW, required
    version TEXT NOT NULL                    -- NEW
);
```

Relationships mirror the Build Guide's ERD (`locations 1—N competitors`, `locations 1—N market_metrics`, `schemes 1—N analyses`), with `data_sources` now a shared lookup table every fact-bearing row references.

---

## PART 22–24 — Prototype Data Strategy

### 22.1 Sizing (re-evaluated, not copied from the Build Guide)

The Build Guide's existing prototype dataset (Section 12: 2 locations, 4 competitors total, 3 market-indicator rows) is **too thin to survive follow-up questioning** — a judge who asks to see a third category or a slightly different location will hit an empty result. Recommended minimum for a credible demo:

| Item | Build Guide (current) | Recommended |
|---|---|---|
| Locations | 2 | **3** (one rural/sparse-data, one semi-urban/richer-data, one mid-point — deliberately including one "honest abstention" location per Master Blueprint Section 10.3) |
| Business categories | Implicit, ~2 used | **5** (dairy, retail/grocery, textiles/tailoring, food processing, one services category) — matching the PS's named categories plus one extra |
| Competitors | 4 | **25–35** across all locations/categories — enough that a live map view doesn't look empty, sourced as a mix of real OSM points (where they exist for the chosen real village) plus clearly flagged curated additions |
| Market metric rows | 3 | **15** (locations × categories, fully populated, not sparse) |
| Price records | 0 | **10–15**, split across the four price-type categories in Part 11 |
| Cost model records | 0 (implied inside financial engine only) | **~30** (5 categories × ~6 cost components each) |
| Scheme records | 2 (placeholder, flagged for correction) | **2–3 real, verified** (NSFDC Micro Credit Finance, NSFDC Term Loan, optionally PMEGP) per Part 15's corrected table |
| Risk records | 0 (implicit in AI narration) | **~10–15** structured rows (category-general risk statements per category, tagged per Part 14) |

### 22.2 Real vs. synthetic — Option scoring (Part 24)

| Option | Credibility | Dev effort | Offline capable | Demo quality | Legal risk | Scalability | SIH appeal | Total |
|---|---|---|---|---|---|---|---|---|
| A. Fully synthetic | 2 | 5 | 5 | 3 | 5 | 2 | 2 | 24 |
| **B. Hybrid (real public data + curated local detail) — SELECTED** | **4** | **3** | **4** | **5** | **4** | **3** | **5** | **28** |
| C. Mostly real (live APIs) | 5 | 1 | 1 (breaks offline) | 4 (risky if live call fails) | 3 | 4 | 4 | 22 |

**Selected: Option B.** It matches the Master Blueprint's own Section 9.2 prototype-tier design and the Build Guide's `DEMO_MODE` offline requirement, while fixing the Build Guide's actual weakness — thinness, not the wrong *kind* of data.

### 22.3 Recommended prototype dataset (Part 25 — actionable)

- **Location 1 — "Karha" (real village, Solapur district, Maharashtra)**, kept from the Build Guide. Real coordinates, real 2011 Census village population/household figures (looked up once, cited), real OSM extract for the surrounding 10 km (Geofabrik Maharashtra extract, filtered), team-curated additions clearly flagged `synthetic: true` for categories where OSM has nothing.
- **Location 2 — "Akkalkot" (real town, same district)**, kept from the Build Guide as the semi-urban comparison point, same real+curated blend.
- **Location 3 — a deliberately sparse rural village** with genuinely thin OSM coverage, used specifically to **demonstrate the Unavailable/Low-confidence path** live — this directly satisfies Master Blueprint Section 40's "TOP 5 THINGS WE MUST ADD #3" (a second sparse-data demo location) and its "TOP 5 THINGS WE MUST FIX #5" (a rehearsed honest low-confidence moment).
- **Fields, sample size, acquisition, processing, confidence, license, update process, fallback:** each fully specified per-file in Part 26 below.

---

## PART 23 — Synthetic Data Policy

- **Generation:** curated manually by the team, based on category research (Part 12) and, for competitor scale/type, plausible local reasoning — never machine-generated random numbers presented as data.
- **Labelling:** every synthetic record carries `"synthetic": true` at the JSON level and a **visible "Demo Data" badge** in the UI (matches Build Guide Section 26 design system requirement) — this is a MUST, not a nice-to-have.
- **Storage:** same tables as real data, distinguished by the `synthetic`/`confidence` columns (Part 21) — not a separate shadow schema, so the confidence-labelling logic doesn't need two code paths.
- **Display:** synthetic competitor counts, demand indices, and prices are never shown without their confidence badge; the report PDF's methodology appendix (Part 16) explicitly lists which figures in that specific report were synthetic.

---

## PART 26 — Real Data Acquisition Instructions

| Dataset | Official URL | Download/API | Auth | Format | Transform |
|---|---|---|---|---|---|
| Census 2011 Village Directory (population, households) | censusindia.gov.in | Static downloads (District Census Handbooks, per state) | None | XLS/PDF tables | Manual extraction of the target village's row → JSON |
| WorldPop population grid | worldpop.org (or via Google Earth Engine) | Direct GeoTIFF download, or `ee.ImageCollection("WorldPop/GP/100m/pop")` via Earth Engine | Earth Engine requires a free account; direct download does not | GeoTIFF | Clip to radius polygon, sum cell values (rasterio/numpy) |
| OSM extract | Geofabrik (download.geofabrik.de) | Direct `.osm.pbf` download for Maharashtra/India-relevant region | None | PBF (binary OSM) | Filter with `osmium`/`pyosmium` for `shop=*`/`amenity=*` within bounding box, then radius-filter with Haversine |
| Agmarknet mandi prices | data.gov.in resource page / agmarknet.ceda.ashoka.edu.in | data.gov.in: request API key, resource-specific API availability **not confirmed — verify per resource before relying on it**; CEDA mirror: direct CSV download, confirmed working | data.gov.in requires free registration; CEDA mirror does not | CSV | Filter to relevant commodity/district, take latest modal price |
| NSFDC scheme text | nsfdc.nic.in | Manual read of official scheme pages (no API) | None | HTML | Manually transcribe into the `schemes` table per Part 15, re-verify before each use |
| PMEGP guidelines | kviconline.gov.in | Manual read of official guideline PDF/pages | None | HTML/PDF | Manually transcribe |
| MOSPI HCES | mospi.gov.in | Report/microdata download | Some MOSPI microdata requires registration — **verify per release** | PDF report / microdata files | Extract relevant state rural MPCE figure |

**No fabricated URLs or endpoints appear above.** Anywhere access could not be independently confirmed as a live API (data.gov.in's per-resource API availability, MOSPI microdata registration terms), it is stated as such rather than assumed.

---

## PART 27 — Data Ingestion Scripts (structure)

```text
scripts/
├── ingest/
│   ├── ingest_census_village.py       # parses a manually-downloaded District Census Handbook table → JSON
│   ├── ingest_worldpop_grid.py        # clips WorldPop GeoTIFF to a radius polygon, sums population
│   ├── ingest_osm_extract.py          # filters a Geofabrik .osm.pbf to shop/amenity nodes in a bbox
│   └── ingest_agmarknet.py            # pulls latest CEDA mirror CSV, filters to target commodities/district
├── transform/
│   ├── build_competitor_dataset.py    # runs the Part 6.2 pipeline: clean → dedup → geocode → classify → filter → score
│   └── build_market_metrics.py        # computes demand_index, EPPI, density per Part 8-10 formulas
├── validate/
│   └── validate_dataset.py            # runs the Part 29 checks before any dataset is marked "ready"
└── seed/
    └── seed_demo_db.py                # loads all resulting JSON into SQLite (extends Build Guide's seed.py)
```

---

## PART 28 — Geospatial Processing (Implementation Choice)

**Chosen: Haversine, in plain Python, no GeoPandas/Shapely/PostGIS dependency for the prototype.** [YuktiFi-DESIGN] Justification: the only spatial operations needed are point-to-point distance and point-in-circle membership testing against, at most, a few hundred points — GeoPandas/Shapely would add a non-trivial dependency (GDAL binaries, a common Windows setup pain point per the Build Guide's own PowerShell-first environment) for zero functional gain at this scale. `pyosmium`/`osmium` is still needed for the one-time OSM `.pbf` filtering step (Part 26/27), since that's a genuine binary-format parsing task Haversine can't replace. Production, at national multi-thousand-competitor scale, adds PostGIS purely for its spatial index (`ST_DWithin` queries), not for any formula PostGIS can compute that Haversine cannot.

---

## PART 29 — Data Quality Checks

| Check | Rule |
|---|---|
| Missing coordinates | Reject row if `lat`/`lon` is null or `0,0` |
| Out-of-range coordinates | Reject if `lat` not in [6, 38] or `lon` not in [68, 98] (India's rough bounding box) |
| Duplicate businesses | Flag if same normalized name within 50m of another record from a different source |
| Invalid prices | Reject if `value <= 0` |
| Negative costs | Reject if `amount < 0` |
| Stale schemes | Flag if `last_verified_date` older than the Part 18 freshness threshold |
| Conflicting sources | Flag (don't auto-resolve) if two sources disagree on the same metric by more than a documented tolerance — routed to Part 30's fusion hierarchy |
| Category mismatches | Reject if `business_category` not in the fixed taxonomy enum |
| Outliers | Flag (not auto-reject) if a metric value is >3 standard deviations from its category's other recorded values, for manual review |

---

## PART 30 — Data Fusion / Source-Priority Hierarchy

```text
Official government source (NSFDC, PMEGP, Census)
        >
Verified partner data (none yet in prototype — future tier)
        >
Structured public data (OSM, Agmarknet)
        >
Team-curated/researched estimate
        >
Community/user-submitted data
        >
Heuristic model output (demand_index, EPPI)
```

**Conflict resolution:** the higher-priority source wins for the stored "primary" value; the lower-priority value is retained in the record (not discarded) as a cross-check note, so disagreements are auditable rather than silently overwritten. Government scheme data conflicting across two of the government's own pages (e.g., NSFDC's own site vs. a mirrored government portal) is treated as a **flag for manual re-verification**, never auto-resolved, given the stakes (Part 15).

---

## PART 31 — Data → YuktiFi Intelligence (worked example)

```text
Population (WorldPop-derived, Medium confidence)
+ Households (Census 2011, Medium confidence — dated)
+ Competitor list (OSM + curated, Medium/Low confidence — coverage caveat)
+ EPPI (MOSPI-derived, Medium confidence)
+ Category cost model (curated, Medium confidence)
+ User's own capital (User-provided, High confidence — it's their own number)
        ↓
Market features (demand_index, competitor_density, EPPI)
        ↓
Business viability (rule-based feasibility engine, per Build Guide Section 14 — deterministic)
        ↓
Financial model (project cost = capital ÷ 0.10; loan/EMI — fully deterministic, Build Guide Section 16)
        ↓
Recommendation (YuktiFi Score, Build Guide Section 15 — deterministic composite)
```

For the **YuktiFi Score specifically** (the single most scrutinized number): raw inputs = feasibility sub-scores + market features; transformation = the documented weighted formula (Build Guide Section 15); confidence = the **minimum** of all contributing metrics' confidence (Part 17); final UI output = score + a visible confidence badge + a one-tap breakdown showing each contributing sub-score and its own source.

---

## PART 32 — Data → AI: The Structured Context Contract

The LLM receives exactly this shape and nothing else — no raw database access, no ability to query external sources itself:

```json
{
  "location": { "name": "Karha", "district": "Solapur", "tier": "rural" },
  "market": { "demand_index": 62, "confidence": "medium", "competitor_density": 0.4 },
  "competitors": { "count": 5, "confidence": "medium", "coverage_note": "OSM + curated, may be incomplete" },
  "financials": { "project_cost": 140000, "loan_amount": 125000, "emi": 4267, "dscr": 1.8 },
  "scheme": { "code": "NSFDC_MICRO_2026", "eligible": true, "reasoning": "project cost within ₹1.40L threshold" },
  "confidence": { "overall": "medium", "weakest_link": "competitor_data_completeness" }
}
```

This mirrors the Master Blueprint Section 8 golden rule directly: the LLM narrates this JSON into prose (SWOT, plain-language explanation, report executive summary) and is architecturally incapable of introducing a number that isn't already in this payload — enforced by a numeric-consistency validator that checks any number appearing in the LLM's output text against this source payload before it's shown to the user (per Master Blueprint Section 40's "must actually reject a bad LLM output in a rehearsed test").

---

## PART 33 — RAG Decision

| Tier | RAG needed? | Why |
|---|---|---|
| V1 (SIH prototype) | **No** | Scheme rules are 2–3 small structured records (Part 15), not a document corpus — a lookup table beats a vector store on both reliability and simplicity (matches Build Guide Section 20's own conclusion) |
| College version | **No** | Even broadening to 5–10 schemes across NSFDC/PMEGP/state schemes is still a structured table, not unstructured document retrieval |
| Production | **Maybe, narrowly** | If YuktiFi later ingests full scheme *guideline PDFs* (not just threshold numbers) to answer open-ended eligibility questions in natural language, a small retrieval layer over that specific, versioned document set could be justified — but only for that narrow use, not as YuktiFi's general knowledge layer, and only once the structured-table approach has demonstrably run out of headroom |

**Vector databases are not introduced merely to sound sophisticated** (per this document's own Final Quality Requirement #16) — the current and near-term data is structured and small enough that a relational lookup outperforms embeddings-based retrieval on both accuracy and explainability, which matters more for a financial-decision product than for a general chatbot.

---

## PART 34 — Offline Demo Data Architecture

```text
Local SQLite database (pre-seeded, Part 22 dataset)
+ Local curated JSON files (source of truth for the seed)
+ Deterministic engines (financial, scheme, scoring — zero network calls)
+ Optional AI narration (only enhancement layer, never load-bearing)
        ↓
Offline YuktiFi demo
```

**What can be cached locally:** everything in the Part 22 prototype dataset — locations, competitors, market metrics, prices, cost models, schemes, risks. **What must never be a critical live dependency:** the AI narration call. If the Anthropic API is unreachable during judging, the deterministic engines still produce the full numeric report; only the prose narration degrades (to a pre-written fallback template per category, another curated asset), matching the Build Guide's `DEMO_MODE=true` requirement exactly.

---

## PART 35 — Data Update Architecture (Production, Not Prototype)

Scheduled ingestion (per Part 27 script, cron/Airflow-style), source monitoring (alert if a scheduled source fails to update within its Part 18 freshness window), versioning (every scheme/dataset change creates a new version row, never an in-place overwrite), rollback (keep N previous versions queryable), validation (Part 29 gate before any new version is promoted to "live"), provenance (Part 16 fields populated automatically by the ingestion job), alerts (scheme-data staleness alerts routed to a human reviewer, never auto-silenced). **None of this is built for the prototype** — the prototype's "pipeline" is a one-time manual script run, and that is the correct scope, not a shortcut to be embarrassed about.

---

## PART 36 — Legal / Licensing / Ethical Considerations

| Source | Consideration |
|---|---|
| OpenStreetMap | ODbL attribution required everywhere OSM data is shown; share-alike obligation for any "derivative database" — **flag for legal review** whether YuktiFi's produced report/analysis counts as a lighter-obligation "produced work" versus a redistributed derivative database, rather than self-certifying |
| Government open data (data.gov.in, Census, NSFDC, PMEGP) | Public-domain/government-owned content; still cite ministry ownership per data.gov.in's own stated policy (content is owned by the respective Ministry/Department, not by the platform itself) |
| WorldPop | CC BY 4.0 — attribution required, commercial use explicitly permitted |
| Commercial map/business APIs (Google Places etc.) | Caching/redistribution terms are provider-specific and change — **do not build a production caching layer against any commercial API's data without re-reading its current ToS**, not the version referenced during initial research |
| Scraping directory sites | Not pursued as a data-acquisition method in this document, precisely because ToS and legal risk were not verifiable as acceptable |
| User-submitted data | Location data from users is personal/sensitive — minimize collection (Part 37), get explicit consent for any "community-confirmed" flag that shares a user's report with other users |

**This document does not provide legal advice.** The ODbL derivative-vs-produced-work question and any commercial API's current caching terms are the two items most in need of an actual legal read before production, not a hackathon-stage self-certification.

---

## PART 37 — Data Security

- **Minimize collection:** the prototype needs no login (per Build Guide Section 1) — collect only what the current session needs (location choice, capital amount, business category, optional age/experience), nothing else.
- **What should not be stored:** no government ID numbers, no bank account details, no precise home address beyond the village/block the user selects from a list — the product needs a *market area*, not a home pin.
- **Location privacy:** the analyzed location is the village/block centroid (Part 5.1), not the user's live GPS position — no location tracking is needed or performed.
- **Financial information:** only the self-declared capital amount is collected; no bank statements, no credit history.
- **Session data / logs:** session data may be retained for the demo/analytics purpose stated to the user; API secrets (Anthropic key, any future commercial API keys) live in environment variables only, never in client-side code or committed to the repo — matches Build Guide Section 33.

---

## PART 38 — Data Failure Modes (20+, with response design)

| # | Failure | Detection | UI behavior | Confidence effect |
|---|---|---|---|---|
| 1 | No competitors found in OSM for a radius | Empty result set | "No mapped competitors found — may reflect map coverage, not actual absence" | Completeness confidence forced to Low |
| 2 | Stale competitor data (OSM edit years old) | Compare OSM node's `timestamp` metadata to freshness policy | Freshness badge shown alongside competitor count | Freshness confidence lowered |
| 3 | Incomplete OSM coverage generally | Coverage heuristic (node density vs. expected for population) | General coverage caveat shown on every OSM-sourced map view | Geographic/completeness confidence capped at Medium |
| 4 | Conflicting prices across sources | Part 29 conflict check | Both values shown with sources, not silently averaged | Confidence flagged, routed to Part 30 |
| 5 | Missing population data for an unlisted village | No WorldPop/Census match found | Explicit "location not in curated dataset" message, not a fabricated fallback number | Unavailable |
| 6 | Wrong/imprecise geocoding | Manual QA on the static lookup table (prototype); reverse-check against Census village code | Static table avoids live geocoding failure entirely in prototype | N/A in prototype; production would validate against multiple gazetteers |
| 7 | Outdated scheme threshold | `last_verified_date` exceeds freshness window | Scheme card shows verification date; stale schemes flagged for review before use | Source confidence lowered |
| 8 | Sparse locality overall (Location 3, Part 22) | By design | Deliberately demonstrates the honest-abstention UI path | Explicitly Low/Unavailable across the board — this is the point |
| 9 | Fake-looking synthetic data | Team QA review before demo | Clearly labelled "Demo Data" badge, never hidden | N/A — labelled, not hidden |
| 10 | Regional data mistaken for local | Code-level enforcement: metrics computed at district level carry `geo_level: "district"` metadata, never silently relabeled `"village"` | UI shows the actual geographic level the figure applies to | Geographic confidence set correctly at source, not patched later |
| 11 | Duplicate competitor records from two sources | Part 29 dedup check | Merged into one record, higher-confidence source's fields kept | N/A |
| 12 | Negative/invalid financial input from user | Input validation on the intake form | Inline validation error, request corrected input | N/A — not a data-source issue |
| 13 | WorldPop grid clip returns zero cells (edge case near a boundary) | Bounds check on the clip operation | Fall back to the areal-density heuristic (Part 5.3 step 3) | Confidence explicitly downgraded to reflect the fallback |
| 14 | Agmarknet/CEDA mirror unreachable at ingestion time | HTTP failure on scheduled pull | Keep last successfully ingested snapshot, flag its age | Freshness confidence lowered proportionally to elapsed time |
| 15 | Overpass API rate-limited mid-query | HTTP 429 response (documented, real behavior per Part 7 research) | Prototype avoids this entirely via static Geofabrik extracts; production retries with backoff, then falls back to last good extract | N/A in prototype |
| 16 | A category has no researched cost-model data yet | Missing row in `cost_models` | Category excluded from ranking/comparison with an explicit "not yet supported" message, never a zero-filled cost | Unavailable |
| 17 | User-submitted competitor report conflicts with curated data | Part 29/30 conflict logic | Shown as "user-reported (unverified)" alongside the curated entry, not merged silently | Low confidence retained on the user-submitted entry |
| 18 | Scheme eligibility edge case exactly at ₹1.40 lakh boundary | Unit-tested boundary values (Build Guide Section 32, this document's Part 15 table) | Deterministic, tested — this is the #3 "must fix" from the Master Blueprint's brutal score, treated as a hard requirement here too | N/A — correctness, not confidence |
| 19 | AI narration references a number not present in the Part 32 payload | Numeric-consistency validator (Part 32) | Output rejected/regenerated before reaching the user | N/A — a code-quality gate, not a data-confidence label |
| 20 | Demo device has no internet at all | `DEMO_MODE=true` (Build Guide) | Full deterministic flow works; only AI prose degrades to a pre-written fallback | N/A |
| 21 | Two government sources disagree (e.g., a scheme mirror page vs. the primary site) | Manual cross-check at ingestion (Part 15 method) | Primary official source wins per Part 30 hierarchy; discrepancy logged for review | Source confidence flagged, not silently resolved |
| 22 | Census village name doesn't match OSM's spelling/transliteration | Manual curation catches this for the fixed prototype set; production would need a fuzzy-match + human review step | N/A for prototype (curated) | N/A |

---

## PART 39 — Data Credibility in Front of SIH Judges

For every major on-screen number, the rehearsed, one-sentence, sourced answer:

| Output | "Where did this come from?" |
|---|---|
| Competitor count | "From a combination of OpenStreetMap's mapped businesses and our own field-researched additions for this demo location — shown with a coverage caveat because rural OSM mapping is genuinely incomplete." |
| Population/consumer base | "The 2011 Census count for this village, spatially distributed using WorldPop's population grid model to estimate how many of those people fall inside a 5 km radius — shown as an Estimate, not a live count, because India's last full census was 2011." |
| Demand | "A documented formula combining the population estimate, our purchasing-power index, and category-specific seasonal patterns — never invented by the AI; the formula and its inputs are shown in the breakdown." |
| Price | "Either an actual government mandi price (for agri-linked categories) or a researched regional benchmark, adjusted by local purchasing power — never a made-up number, and always labelled which of the four price types it is." |
| Purchasing power | "An index built from the government's own household consumption survey at the state/rural level, because no public source gives individual household income — and we say so." |
| Project cost | "Purely arithmetic: your stated capital divided by the scheme's 10% contribution requirement — not looked up, calculated live in front of you." |
| Scheme eligibility | "A rule match against the National Scheduled Castes Finance and Development Corporation's own published thresholds, re-verified against nsfdc.nic.in before this demo." |
| Risk flags | "A mix of category-general business risk (labelled as such) and anything derived from the market data above — never presented as a location-specific measurement unless it genuinely is one." |
| Viability/YuktiFi Score | "A deterministic weighted formula over the feasibility and market sub-scores above — tap the score to see every contributing number and its own source." |

---

## PART 40 — Final Data Architecture

*(as diagrammed in Part 19 — reproduced once, not duplicated, per this document's own no-padding standard)*

---

## PART 41 — Final Data Schema

See Part 21 for the complete SQL. ER relationships: `locations 1—N competitors`, `locations 1—N market_metrics`, `locations 1—N prices`, `schemes 1—N analyses`, `data_sources 1—N {competitors, market_metrics, prices, cost_models, schemes}` (every fact-bearing table references a source). Indexes: `idx_competitors_location` (existing), add `idx_market_metrics_location_category`, `idx_prices_location_category`. All timestamp columns default to `now()`; all fact tables carry `confidence` and, where applicable, `synthetic`.

---

## PART 42 — Final Prototype Data Files

```text
backend/app/data/
├── locations.json          # 3 locations (Part 22), real coordinates + Census-sourced population/household anchors
├── categories.json         # 5 business categories, fixed taxonomy
├── competitors.json        # 25–35 records, mixed OSM-sourced + curated, each tagged source_id + confidence
├── market_metrics.json     # demand_index, competitor_density, EPPI per location×category (Part 21 schema)
├── prices.json             # 10–15 records across the 4 price types (Part 11)
├── cost_models.json        # ~30 records, 5 categories × ~6 components (Part 12)
├── schemes.json            # 2–3 REAL, verified scheme records (Part 15) — replaces the Build Guide's placeholder file
├── risks.json              # ~10–15 category-general + derived risk statements (Part 14)
└── data_sources.json       # NEW — the lookup table every other file's source_id points into
```

Each file's purpose, sample record shape, source, confidence, and synthetic-flag are already fully specified in Parts 6, 8–15, 21–23 above — not repeated here to avoid the padding this document explicitly warns against.

---

## PART 43 — Production Evolution

| Domain | Prototype | College version | Production |
|---|---|---|---|
| Population | Curated 2011 Census + WorldPop, 3 locations | Same method, broader district coverage | Automated per-request WorldPop clip + periodic Census/NFHS-style survey refresh where available |
| Competitors | Static curated + one-time OSM extract | Live Overpass queries + a basic user-submission form | Multi-source fusion (OSM + a real commercial listings partnership + user network), PostGIS-indexed |
| Pricing | Static Agmarknet snapshot + curated benchmarks | Scheduled Agmarknet/CEDA re-pull | Full scheduled multi-source pipeline with anomaly detection |
| Purchasing power | Static EPPI from MOSPI HCES 2022-23 | Same, refreshed per new HCES round | Finer proxies if/when better rural income data becomes available (formal partnership, not scraping) |
| Schemes | 2–3 manually verified records | Broader set incl. relevant state schemes | Versioned, periodically re-verified scheme database with change alerts |
| Risk/seasonality | Category-general, curated | Same, expanded categories | Localised where genuine data partnerships (SRLM/SHG federations, per Master Blueprint Section 9.2) make it possible |

---

## PART 44 — Data Implementation Plan (dependency-ordered, not copied from the Build Guide's dev-phase plan)

1. **Freeze the extended schema** (Part 21) — everything downstream depends on `data_sources`/`confidence` existing as first-class columns from day one, not retrofitted.
2. **Build and verify the scheme table** (Part 15) — highest stakes, smallest scope, must be correct before anything else is built on top of it; explicitly fixes the Build Guide's flagged PMEGP/CGTMSE error.
3. **Acquire and process Location 1 & 2's real data** (Census lookup, OSM extract, Agmarknet pull) per Part 26/27 scripts.
4. **Build the competitor pipeline** (Part 6.2) and run it against Locations 1–2.
5. **Curate Location 3 deliberately sparse**, run the same pipeline, confirm it correctly produces Low/Unavailable outputs rather than errors.
6. **Populate cost_models and prices** (Parts 11–12) via team research.
7. **Compute market_metrics** (demand_index, EPPI, density) via the Part 8–10 formulas — this is the first point where the "curated dataset" is actually complete.
8. **Run Part 29 validation** against the full dataset before wiring it to any engine.
9. **Wire the deterministic engines** (market intelligence, feasibility, financial, scheme router — per Build Guide Sections 13–17) against this now-validated dataset.
10. **Wire the AI narration layer** against the Part 32 structured payload, with the numeric-consistency validator active from the first integration test, not added later.
11. **Rehearse the Part 39 "where does this come from" answers** against the actual running demo, not against this document in the abstract.

Each phase's definition of done: the relevant JSON/DB tables pass Part 29 validation and every record has a non-null `confidence` and `source` (or `synthetic: true`).

---

## PART 45 — Final Data Checklist

**SOURCE RESEARCH** — [MUST] Verify NSFDC/PMEGP scheme text directly · [MUST] Confirm Census 2011 as current ceiling for population data · [SHOULD] Check state-specific handbook availability for demo districts · [NICE] Survey additional state schemes · [FUTURE] Formal SRLM/SHG data partnership research

**DATA ACQUISITION** — [MUST] Geofabrik OSM extract for demo region · [MUST] Census village-level lookup for 3 demo locations · [SHOULD] Agmarknet/CEDA pull for at least one agri-linked category · [FUTURE] Commercial listings API integration

**DATA CLEANING** — [MUST] Part 29 checks implemented and run before every demo · [SHOULD] Automated dedup across OSM+curated competitor sources

**DATA MODEL** — [MUST] Part 21 schema with `data_sources`/`confidence` as first-class · [MUST] Scheme table carries `source_url`/`last_verified_date`/`version`

**GEOSPATIAL** — [MUST] Haversine radius filter · [MUST] WorldPop clip-and-sum for population · [FUTURE] PostGIS migration

**MARKET DATA** — [MUST] demand_index formula documented and implemented · [SHOULD] EPPI documented and implemented

**COMPETITOR DATA** — [MUST] Pipeline per Part 6.2 · [MUST] Coverage caveat shown whenever OSM-sourced · [SHOULD] User-submission form (college-tier)

**PRICING** — [MUST] Four-way price-type separation enforced in schema and UI · [SHOULD] Real Agmarknet-sourced prices for ≥1 category

**COST MODELS** — [MUST] All 5 categories populated, each component `confidence`-tagged

**SCHEME DATA** — [MUST] NSFDC records correct and boundary-tested · [MUST] Build Guide's PMEGP/CGTMSE error corrected · [SHOULD] PMEGP added as a second real scheme

**PROVENANCE** — [MUST] Every fact-bearing row references `data_sources` · [MUST] Report PDF methodology appendix

**CONFIDENCE** — [MUST] Four-factor minimum-based composite implemented · [MUST] UI badge on every material number

**VALIDATION** — [MUST] Part 29 checks as a CI/pre-demo gate

**INGESTION** — [SHOULD] Scripts per Part 27 runnable end-to-end for the 3 demo locations · [FUTURE] Scheduled production jobs

**PROTOTYPE DATA** — [MUST] 3 locations incl. one deliberately sparse · [MUST] All 8 data files in Part 42 present and validated

**OFFLINE MODE** — [MUST] `DEMO_MODE=true` produces full numeric output with zero network calls (Build Guide requirement, endorsed here)

**TESTING** — [MUST] Boundary-value tests on the ₹1.40 lakh/₹50 lakh thresholds · [MUST] One deliberately Low-confidence path rehearsed live

**PRODUCTION ROADMAP** — [FUTURE] Everything in Part 35/43

---

## PART 46 — Brutal Data Audit

**Acting as a skeptical SIH judge, a data scientist, and a government data expert:**

1. **Can YuktiFi genuinely claim to be hyper-local?** Partially, and only if it's honest about which parts. Financial calculations are exact. Scheme eligibility is exact. Population/household figures are genuinely village-level, just dated. Competitor counts and demand are the weak point — "hyper-local" there means "the finest granularity we could honestly get to, clearly labelled," not "we know exactly what's happening in your village."
2. **Which outputs can actually be supported by data?** Financial math, scheme thresholds, 2011 village population/household counts, mandi commodity prices, OSM-mapped competitors (where mapped).
3. **Which outputs are estimates?** Consumer base within a radius, demand index, purchasing power index, cost-model line items, seasonality, most risk flags.
4. **Which outputs require user input?** Local price corroboration, self-reported competitor sightings, self-declared capital/experience.
5. **Which outputs should YuktiFi refuse to generate?** An exhaustive, confident competitor count for a village with no OSM coverage and no curated data; an individual household income figure; any scheme eligibility claim based on identity-category gating without direct NSFDC/MoSJE partnership (already excluded per Master Blueprint Section 40).
6. **Where are we most likely to be challenged?** The competitor count and demand index — any judge who knows rural India will immediately ask "how do you actually know that." The honest answer (Parts 4, 6, 39) is the defense, not a weakness to hide.
7. **What data would most improve YuktiFi?** A real, even narrow, data partnership with a State Rural Livelihood Mission or SHG federation for even one district — genuine local verification beats any amount of clever modelling of the same coarse public data.
8. **What data should we NOT waste time collecting?** Satellite footfall imagery, individual credit history, anything requiring a paid enterprise data partnership before the college/production tier — all correctly already excluded in the Master Blueprint.
9. **What is the biggest credibility risk?** Presenting an Estimated or curated number with the same visual weight as a Known one. The confidence-tagging system (Part 17) is not a nice UI feature — it is the entire defense against this risk, and it fails completely if implemented inconsistently.
10. **What is the strongest data-driven differentiator?** The NSFDC/PMEGP scheme grounding (Part 15) combined with a visibly honest confidence system — no surveyed competitor product in the Master Blueprint's own landscape scan (Section 2.2) does either of these, let alone both.

### DATA CREDIBILITY SCORE: 54/100 (as a literal "hyper-local" claim) → 78/100 (once the confidence-labelling system is judged as part of the product, which is how a real judge should judge it)

**Justification:** the raw local-data availability for rural India is genuinely thin — this is a fact about India's data landscape, not a flaw in this design (Part 4's matrix makes this unambiguous). A score in the 50s on raw data availability is the honest ceiling for *any* team attempting this problem statement with public data alone. What moves the number to a genuinely competitive ~78 is that YuktiFi's architecture (Master Blueprint Section 8's layer separation, this document's Part 17 confidence system, Part 39's rehearsed sourcing answers) turns "our local data is imperfect" from a hidden weakness into a demonstrated, disclosed design discipline — which is precisely the differentiator no competing product in the landscape scan offers.

---

*End of YuktiFi Data Strategy & Data Architecture. Every source cited above was checked on 2026-09-06; scheme rates and thresholds in particular should be re-verified against nsfdc.nic.in and kviconline.gov.in immediately before any live demo or submission, since these are exactly the numbers a judge is most likely to test.*
