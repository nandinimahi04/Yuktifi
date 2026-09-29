# Business Taxonomy & Evidence Mapping Matrix (UYDF-1.0)
**Problem Statement:** SIH 2026 PS 26091 — *YuktiFi Universal Data Layer*

---

## 1. Overview & Objectives

Rural micro-entrepreneurs operate across diverse small-scale business categories. The Universal Data Layer maps raw government datasets (Census PCA, DCHB tables, MoSPI HCES consumption baskets, Agmarknet commodity prices, and ICAR manuals) to canonical micro-enterprise categories.

---

## 2. Business Category Taxonomy

Implemented in `backend/app/data_layer/universal/business_mapping.py`:

| Business ID | Display Name | NIC 2008 Code | Primary Input Datasets | Key Metric Indicators |
| :--- | :--- | :--- | :--- | :--- |
| `kirana_general_store` | Kirana & Daily Needs Grocery | `47110` | DCHB Village Population, HCES MPCE, NFHS-5 | Village Catchment, Non-Food MPCE, Electricity Availability |
| `dairy_farming_milk` | Dairy & Livestock Farming | `01411` | DCHB Irrigated Area, Livestock Census, Agmarknet | Cow Milk Yield (L/day), Green Fodder Land, Mandi Milk Price |
| `tea_snack_stall` | Tea, Snacks & Rural Eatery | `56302` | DCHB Road Connectivity, Bus Stop Presence, Traffic | National/State Highway Proximity, Daily Commuter Footfall |
| `flour_mill_atta_chakki` | Atta Chakki & Grain Processing | `10611` | DCHB Agricultural Land, 3-Phase Commercial Power | Power Connection Reliability, Village Cereal Harvest Output |
| `tailoring_garments` | Tailoring, Embroidery & Boutique | `14101` | DCHB Female Literacy, HCES Clothing MPCE | Female Population % in Village, Clothing Expenditure Share |
| `poultry_farming` | Layer / Broiler Poultry Unit | `01461` | DCHB Water Supply, Agmarknet Feed Prices | Water Sources, Broiler Feed Price (₹/kg), Veterinary Proximity |
| `agro_services_custom_hiring`| Tractor & Agri Machinery Hiring | `01610` | DCHB Cultivable Land, Total Small & Marginal Farmers| Cropping Intensity, Irrigated Area %, Farmer Population |
| `mobile_electronics_repair` | Mobile Recharge & Repair Kiosk | `95120` | NFHS-5 Mobile Penetration, Electricity Hours | Smartphone Literacy %, Power Supply Reliability |

---

## 3. Evidence Mapping Rules

Each micro-enterprise category specifies required and optional evidence parameters:

### Example: Kirana & Grocery Store (`kirana_general_store`)
```json
{
  "business_id": "kirana_general_store",
  "category_name": "Kirana & Grocery Retail",
  "primary_demand_drivers": [
    "VILLAGE_TOTAL_POPULATION",
    "TOTAL_HOUSEHOLDS",
    "MONTHLY_PER_CAPITA_EXPENDITURE_FOOD",
    "ROAD_CONNECTIVITY_PUCCA"
  ],
  "operational_constraints": [
    "ELECTRICITY_HOURS_COMMERCIAL",
    "EXISTING_COMPETITOR_COUNT_1KM"
  ],
  "scheme_alignment": [
    "MUDRA_SHISHU",
    "MUDRA_KISHORE",
    "PM_SVANIDHI"
  ]
}
```

### Example: Small Dairy Processing (`dairy_farming_milk`)
```json
{
  "business_id": "dairy_farming_milk",
  "category_name": "Small Dairy & Milk Collection",
  "primary_demand_drivers": [
    "MILK_PRICE_PER_LITRE_MANDI",
    "LIVESTOCK_BREEDING_POPULATION",
    "IRRIGATED_FODDER_HECTARES"
  ],
  "operational_constraints": [
    "VETERINARY_HOSPITAL_DISTANCE_KM",
    "POWER_3PHASE_AVAILABLE"
  ],
  "scheme_alignment": [
    "NSFDC_TERM_LOAN",
    "PMFME_MICRO_FOOD_PROCESSING",
    "STAND_UP_INDIA"
  ]
}
```

---

## 4. Downstream Consumption

When an advisory session is initialized with a given business category and village/taluka LGD code:
1. The `EvidenceRetrievalService` fetches the matched demand drivers and constraints from the Universal Data Store.
2. The `FinancialEngine` populates realistic local baseline revenues and operational cost models from verifiable evidence rather than hardcoded assumptions.
3. The `MarketIntelligenceEngine` calculates saturation scores and catchment penetration ratios.
4. The `RAGService` retrieves relevant central and state subsidy schemes mapped to the category.
