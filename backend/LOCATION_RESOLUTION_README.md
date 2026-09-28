# YUKTI Canonical Location Resolver

## What this adds

YUKTI now has a deterministic location-resolution layer:

`user text / lat-lon -> canonical location master -> state -> district -> sub-district -> block -> village -> government codes`

The resolver does not invent geography. If the master cannot support a match, it returns `unresolved` or `needs_reverse_geocode` rather than silently choosing a broader geography.

## Official source strategy

**LGD is the production administrative master.** Use the Government of India's Local Government Directory for current districts, sub-districts, villages, development blocks and village-to-Gram-Panchayat mappings.

Official download page:
https://lgdirectory.gov.in/demo/downloadDirectory.do

**Census 2011 is a historical cross-check**, not a replacement for current LGD. The Solapur PCA TV resource exposes district, sub-district, village and town identities/codes.

https://censusindia.gov.in/nada/index.php/catalog/6717

## Build the normalized master

After downloading an official LGD export:

```bash
python scripts/build_location_master.py <official-file> data/reference/location_master.csv
```

Keep the original government file under `data/raw/` and the normalized CSV under `data/reference/`.

## API

### Resolve by place text

```http
GET /api/v2/location/resolve?query=Chincholi%20Najik,%20Akkalkot,%20Solapur,%20Maharashtra
```

### Resolve by coordinates

```http
GET /api/v2/location/resolve?lat=17.0&lng=75.0
```

Coordinates can be resolved directly only when the canonical master contains coordinates. Otherwise the response explicitly says `needs_reverse_geocode`; a later integration can call the reverse geocoder and then match the returned administrative names against LGD.

### Load a master at runtime

```http
POST /api/v2/location/master/load
Content-Type: application/json

{"path":"data/reference/location_master.csv"}
```

## Critical data rule

A village-level request must never be silently replaced by district-level population, demand, livestock, competitor or income data. Every downstream metric must carry the resolved geography and evidence resolution.
