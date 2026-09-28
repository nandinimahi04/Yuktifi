"""
Seed script — populates the database with demo locations, business categories,
and scheme data from JSON files on first startup. Idempotent (checks before inserting).
"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from app.core.paths import SEED_DIR
from app.models import (
    Location, BusinessCategory, GovernmentScheme, Source,
    Competitor, MarketMetric, Price, CostModel
)

logger = logging.getLogger(__name__)

def load_json(filename: str):
    """
    Load a seed fixture from `backend/data/seed/`.

    A missing fixture is logged and returns an empty list, but the caller counts
    the rows it actually inserted, so a silently empty seed can no longer be
    mistaken for a successful one (the previous failure mode: DATA_DIR pointed at
    a directory that does not exist, so seeding inserted nothing and every
    dataset query returned []).
    """
    filepath = SEED_DIR / filename
    if not filepath.exists():
        logger.warning("Seed fixture not found: %s", filepath)
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None

def _insert(db: DBSession, model, rows, *, transform=None) -> int:
    """Insert rows that match the model columns, ignoring unknown keys.

    Returns the number actually inserted so seeding can be verified rather than
    assumed. A fixture whose keys do not match the model produces 0 rows, which
    is now visible instead of looking like an empty table.
    """
    if not rows:
        return 0
    cols = {c.name for c in model.__table__.columns}
    count = 0
    for row in rows:
        if transform is not None:
            row = transform(dict(row))
        payload = {k: v for k, v in row.items() if k in cols}
        if not payload:
            continue
        db.add(model(**payload))
        count += 1
    if count:
        db.commit()
    else:
        db.rollback()
    return count


def seed_database(db: DBSession) -> dict[str, int]:
    """Insert seed fixtures if the tables are empty. Idempotent.

    Returns a per-table count so the caller can assert that seeding actually did
    something. Previously the function returned None and the caller could not tell
    an empty database from a failed one.
    """
    # Fast early-exit: if categories are already seeded, nothing to do
    if db.query(BusinessCategory).count() > 0:
        return {}

    def _dt(key):
        return lambda r: {**r, key: parse_date(r.get(key))} if key in r else r

    counts: dict[str, int] = {
        "sources": _insert(db, Source, load_json("data_sources.json")),
        "locations": _insert(db, Location, load_json("locations.json")),
        "categories": _insert(db, BusinessCategory, load_json("categories.json")),
        "competitors": _insert(db, Competitor, load_json("competitors.json"), transform=_dt("last_verified")),
        "market_metrics": _insert(db, MarketMetric, load_json("market_metrics.json"), transform=_dt("effective_date")),
        "prices": _insert(db, Price, load_json("prices.json")),
        "cost_models": _insert(db, CostModel, load_json("cost_models.json")),
        "schemes": _insert(db, GovernmentScheme, load_json("schemes.json"), transform=_dt("effective_from")),
    }
    empty = [k for k, v in counts.items() if v == 0]
    if empty:
        logger.warning("Seed produced no rows for: %s", ", ".join(empty))
    return counts


def seed_status(db: DBSession) -> dict[str, int]:
    """Row counts for the seeded tables, for the health endpoint."""
    return {
        "sources": db.query(Source).count(),
        "locations": db.query(Location).count(),
        "categories": db.query(BusinessCategory).count(),
        "competitors": db.query(Competitor).count(),
        "market_metrics": db.query(MarketMetric).count(),
        "prices": db.query(Price).count(),
        "cost_models": db.query(CostModel).count(),
        "schemes": db.query(GovernmentScheme).count(),
    }


# Note: risks.json has no SQLAlchemy model in this pass. It stays on disk under
# backend/data/seed/ so the risk engine can read it as a fixture.
