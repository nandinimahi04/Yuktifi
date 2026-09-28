from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.location.service import load_resolver, resolve_location
from app.location.context import build_location_context

router = APIRouter(prefix="/api/v2/location", tags=["location-resolution"])


@router.get("/resolve")
def resolve(query: str | None = None, lat: float | None = None, lng: float | None = None):
    if query is None and (lat is None or lng is None):
        raise HTTPException(status_code=422, detail="Provide query or both lat and lng")
    return resolve_location(query=query, lat=lat, lng=lng)


@router.post("/master/load")
def load_master(payload: dict):
    path = payload.get("path")
    if not path:
        raise HTTPException(status_code=422, detail="Missing path")
    try:
        resolver = load_resolver(path)
        return {"status": "loaded", "rows": len(resolver.rows), "path": path}
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/context")
def location_context(query: str | None = None, lat: float | None = None, lng: float | None = None):
    if query is None and (lat is None or lng is None):
        raise HTTPException(status_code=422, detail="Provide query or both lat and lng")
    result = resolve_location(query=query, lat=lat, lng=lng)
    if result.get("status") != "resolved":
        return result
    return build_location_context(result)
