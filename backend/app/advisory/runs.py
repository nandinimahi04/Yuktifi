from __future__ import annotations
import json
from datetime import datetime, timezone
from app.core.db import engine
from sqlalchemy import text

SCHEMA = """
CREATE TABLE IF NOT EXISTS advisory_runs (
 id TEXT PRIMARY KEY,
 created_at TEXT NOT NULL,
 business_id TEXT NOT NULL,
 location_label TEXT,
 decision TEXT,
 confidence REAL,
 result_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_advisory_runs_created ON advisory_runs(created_at);
"""

def ensure_schema():
    with engine.begin() as conn:
        for statement in SCHEMA.split(';'):
            if statement.strip(): conn.execute(text(statement))

def save(result: dict) -> dict:
    ensure_schema()
    location = result.get('location', {})
    label = ', '.join(str(x) for x in [location.get('village'), location.get('district'), location.get('state')] if x) or str(location.get('query') or '')
    row = {
      'id': result['run_id'], 'created_at': result['generated_at'], 'business_id': result['business']['id'],
      'location_label': label, 'decision': result['decision']['decision'],
      'confidence': float(result['decision']['confidence']['overall']), 'result_json': json.dumps(result, ensure_ascii=False)
    }
    with engine.begin() as conn:
        conn.execute(text('INSERT OR REPLACE INTO advisory_runs (id,created_at,business_id,location_label,decision,confidence,result_json) VALUES (:id,:created_at,:business_id,:location_label,:decision,:confidence,:result_json)'), row)
    return row

def get(run_id: str) -> dict | None:
    ensure_schema()
    with engine.begin() as conn:
        row = conn.execute(text('SELECT result_json FROM advisory_runs WHERE id=:id'), {'id': run_id}).scalar_one_or_none()
    return json.loads(row) if row else None

def recent(limit: int = 20) -> list[dict]:
    ensure_schema()
    with engine.begin() as conn:
        rows = conn.execute(text('SELECT id,created_at,business_id,location_label,decision,confidence FROM advisory_runs ORDER BY created_at DESC LIMIT :limit'), {'limit': min(max(limit,1),100)}).mappings().all()
    return [dict(r) for r in rows]
