# Phase 5 — Canonical Location Integration

YUKTIFI now treats resolved geography as a shared context instead of allowing each engine to invent or independently interpret a location.

## Flow

`User location -> Location Resolver -> Canonical Location Context -> Market / Livestock / Evidence / Financial Scenario`

The location context contains state, district, sub-district, block, village, official codes, coordinates, resolution method, and match score.

## Safety rule

If an official location master cannot resolve the location, the location-aware dairy endpoint returns `location_unresolved`. It does not silently substitute a district or another nearby geography.

## Endpoint

`POST /api/v2/dairy-demo/location-aware`

Example payload:

```json
{"location":"Chincholi Najik, Akkalkot, Solapur, Maharashtra","margin_capital":100000}
```

The endpoint first resolves the location, then passes one canonical location context to the dairy scenario.

## Data boundary

This phase does not claim village population or livestock numbers merely because a village was resolved. Those metrics remain unavailable until their official datasets are loaded and matched by the canonical geography codes.
