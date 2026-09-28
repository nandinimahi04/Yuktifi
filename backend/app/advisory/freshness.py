from __future__ import annotations
from datetime import datetime, timezone

def assess(observed_at: str | None, max_age_days: int | None = None) -> dict:
    now=datetime.now(timezone.utc)
    if not observed_at: return {"status":"UNKNOWN","observed_at":None,"age_days":None}
    try:
        dt=datetime.fromisoformat(observed_at.replace("Z","+00:00"))
        age=max(0,(now-dt).days)
        return {"status":"FRESH" if max_age_days is None or age<=max_age_days else "STALE","observed_at":observed_at,"age_days":age,"max_age_days":max_age_days}
    except ValueError:
        return {"status":"INVALID","observed_at":observed_at,"age_days":None}
