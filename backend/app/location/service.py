from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .resolver import LocationResolver

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data" / "reference" / "location_master_manifest.json"
SAMPLE_MASTER = ROOT / "data" / "reference" / "location_master.sample.csv"

_resolver: LocationResolver | None = None


def load_resolver(path: str | Path) -> LocationResolver:
    global _resolver
    _resolver = LocationResolver.from_file(path)
    return _resolver


def get_resolver() -> LocationResolver:
    global _resolver
    if _resolver is not None:
        return _resolver
    if DEFAULT_MANIFEST.exists():
        manifest = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
        master = manifest.get("master_path")
        if master:
            p = ROOT / master
            if p.exists():
                _resolver = LocationResolver.from_file(p)
                return _resolver
    if SAMPLE_MASTER.exists():
        return LocationResolver.from_file(SAMPLE_MASTER)
    return LocationResolver([])


def resolve_location(query: str | None = None, lat: float | None = None, lng: float | None = None) -> dict[str, Any]:
    return get_resolver().resolve(query=query, lat=lat, lng=lng)
