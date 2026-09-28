# Canonical location master

YUKTI uses a government-derived location master for deterministic resolution.

## Preferred production source

Download the required LGD entities from the Government of India's Local Government Directory:
- All districts of a state
- All sub-districts of a state
- All villages of a state
- Development blocks of a state
- Gram Panchayat mapping to village

Official download page: https://lgdirectory.gov.in/demo/downloadDirectory.do

## Historical cross-check

The Census of India Solapur PCA TV resource is useful for validating village/sub-district/district names and codes:
https://censusindia.gov.in/nada/index.php/catalog/6717

## Accepted master format

CSV or XLSX with at least:

```text
state,district,village
```

Recommended:

```text
state,district,subdistrict,block,village,state_code,district_code,subdistrict_code,block_code,village_code,lat,lng,admin_level
```

Do not hand-create production administrative codes. Keep the original downloaded government file under `data/raw/` and create a normalized master separately.
