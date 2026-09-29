# Universal Dataset Catalog (UYDF-1.0)
**Problem Statement:** SIH 2026 PS 26091 — *YuktiFi Universal Data Layer*

---

## 1. Overview & Dataset Categories

The YuktiFi Universal Data Layer ingests, normalizes, and catalogs 79 official datasets and 5 strategic monographs from official Indian statistical authorities, remote sensing organizations, and survey bureaus.

Each dataset is assigned a standardized category code:

1. `OFFICIAL_STATISTICAL`: Census PCA, DCHB (District Census Handbooks), SECC, Livestock Census.
2. `OFFICIAL_GEOGRAPHIC`: LGD (Local Government Directory) Master Tables, Administrative Boundaries.
3. `OFFICIAL_MARKET`: MoSPI HCES (Household Consumption Expenditure Survey), Agmarknet APMC mandi prices.
4. `REMOTE_SENSING`: ISRO Bhuvan land use / land cover, WorldPop 1km population density GeoTIFFs.
5. `SURVEY`: NFHS-5 (National Family Health Survey), NSSO surveys.
6. `OPEN_GEOSPATIAL`: OpenStreetMap POIs, OpenDRI, PMGSY rural road network rasters.
7. `RESEARCH`: ICAR, WRI, NABARD, and RBI official monographs and evaluation studies.

---

## 2. Core Datasets in the Canonical Collection

### A. District Census Handbooks (DCHB) - Solapur District (2730)
- **Source:** Office of the Registrar General & Census Commissioner, India (ORGI).
- **Format:** 62 DCHB Village & Town Directory Excel tables covering all 11 Talukas (North Solapur, South Solapur, Barshi, Akkalkot, Mohol, Pandharpur, Malshiras, Sangole, Mangalvedhe, Karmala, Madha).
- **Core Indicators Extracted:**
  - `DCHB_VD_001`: Total Village Population, Male/Female breakdown, SC/ST proportions.
  - `DCHB_VD_002`: Cultivable Land Area, Irrigated Area (Canal, Well, Borewell, Tank), Forest Area.
  - `DCHB_VD_003`: Educational Facilities (Primary, Middle, Secondary Schools, ITI, Colleges).
  - `DCHB_VD_004`: Medical Facilities (PHC, Sub-centres, Veterinary Hospitals, Dispensaries).
  - `DCHB_VD_005`: Drinking Water Sources & Electrification Status (Domestic, Agricultural, Commercial).
  - `DCHB_VD_006`: Banking, Post Offices, ATM coverage, and Credit Societies.
  - `DCHB_VD_007`: Road Connectivity (National Highways, State Highways, Major District Roads, Pucca Roads).

### B. Census 2011 Primary Census Abstract (PCA)
- **Source:** Ministry of Home Affairs / Census India.
- **Dataset Code:** `CENSUS_PCA_2011_SOLAPUR`
- **Granularity:** Village / Ward / Subdistrict / District.
- **Key Parameters:** Total Households, Total Population, Literate Population, Main Workers, Cultivators, Agricultural Labourers, Household Industry Workers, Other Workers.

### C. Local Government Directory (LGD) Master Tables
- **Source:** Ministry of Panchayati Raj (MoPR).
- **Dataset Code:** `LGD_VILLAGE_DIRECTORY_MH` / `LGD_SUBDISTRICT_DIRECTORY_MH`
- **Coverage:** Complete mapping of 6-digit LGD Village Codes, 4-digit Sub-district Codes, 3-digit District Codes (`2730` Solapur, `2729` Pune, `2731` Satara, `2732` Sangli, `2733` Kolhapur, `2728` Ahilyanagar/Ahmadnagar).
- **Administrative Aliases:** Automatic resolution of renamed administrative jurisdictions (e.g. `Ahmadnagar` ↔ `Ahilyanagar`, `Aurangabad` ↔ `Chhatrapati Sambhajinagar`, `Osmanabad` ↔ `Dharashiv`).

### D. MoSPI Household Consumption Expenditure Survey (HCES 2022-23 & 2023-24)
- **Source:** National Sample Survey Office (NSSO), Ministry of Statistics and Programme Implementation.
- **Datasets:** `Report_591_HCES_2022-23.pdf`, `Factsheet_HCES_2022-23.pdf`, `HCES_2023-24_Data.xlsx`.
- **Key Parameters:** Monthly Per Capita Consumption Expenditure (MPCE), Food vs. Non-Food expenditure shares, rural durable goods expenditure, milk/dairy demand curves.

### E. Remote Sensing & High-Resolution Gridded Demographics
- **Source:** WorldPop / ISRO Bhuvan / Copernicus.
- **Dataset:** `ind_ppp_2025_1km_Aggregated.tif` (1km gridded population projection for India 2025).
- **Dataset:** `4_Bhuvan_Data_Content_And_Map_Standards.pdf` (ISRO Spatial Cartographic and Thematic Layer Standards).
- **Application:** Exact geospatial boundary verification, catchment population calculations, and competitor spatial proximity radii (500m, 1km, 3km, 5km).

### F. Health & Socio-Demographic Surveys
- **Source:** Ministry of Health and Family Welfare (MoHFW) / IIPS.
- **Dataset:** `NFHS-5 District Factsheet - Solapur (30-NFHS-5_Solapur.pdf)`.
- **Key Parameters:** Household electricity coverage, clean fuel adoption, bank account penetration among women (92.4%), internet usage literacy, female micro-entrepreneurship readiness.

---

## 3. Dataset Catalog Metadata Schema

Every dataset in the catalog implements the canonical `DatasetMetadata` schema:

```json
{
  "dataset_id": "DCHB_SOLAPUR_2730_TABLE_01",
  "title": "Solapur District Census Handbook 2011 - Village and Town Directory (Table 01)",
  "category": "OFFICIAL_STATISTICAL",
  "publisher": "Office of the Registrar General & Census Commissioner, India (ORGI)",
  "publisher_type": "CENTRAL_GOVERNMENT",
  "publication_date": "2014-06-15",
  "effective_start_date": "2011-01-01",
  "effective_end_date": "2031-12-31",
  "spatial_granularity": "VILLAGE",
  "spatial_coverage": ["MAHARASHTRA", "SOLAPUR"],
  "update_frequency": "DECENNIAL",
  "licensing": "GOVERNMENT_OPEN_DATA_LICENSE_INDIA (GODL)",
  "source_sha256": "4b6845217424ad993883713d2f9ef282711684c98f48039d6771d9a2ad93eeb4",
  "quality_score": 0.98,
  "verification_status": "VERIFIED_OFFICIAL"
}
```

---

## 4. Querying the Dataset Catalog

The catalog is queryable via REST API:
- `GET /api/data/catalog` — List all registered datasets.
- `GET /api/data/catalog?category=OFFICIAL_STATISTICAL` — Filter by category.
- `GET /api/data/catalog?publisher=MoSPI` — Filter by issuing authority.
