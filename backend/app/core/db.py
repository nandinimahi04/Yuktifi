from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from app.core.paths import BACKEND_DIR

connect_args = {}
is_sqlite = settings.database_url.startswith("sqlite")
if is_sqlite:
    connect_args["check_same_thread"] = False

# A relative `sqlite:///./yukti.db` is interpreted by SQLite relative to the
# process working directory, so the file appeared in the repo root or in
# backend/ depending on how the app was launched. It is rebuilt here as an
# absolute path rooted at backend/ so there is exactly one database file.
_db_path = settings.database_path
if _db_path is not None:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args["timeout"] = 30
    database_target = f"sqlite:///{_db_path.as_posix()}"
else:
    database_target = settings.database_url

engine = create_engine(
    database_target,
    connect_args=connect_args,
    pool_pre_ping=True,  # Detect stale connections before using them
)

# Enable WAL mode and performance PRAGMAs for SQLite
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")   # Allow concurrent reads + writes
        cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes, still safe
        cursor.execute("PRAGMA cache_size=-32000")   # 32MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")   # Temp tables in RAM
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and apply additive column upgrades. Call on startup."""
    from app.models import (  # noqa: F401 — force all models to register
        User, Location, BusinessCategory, Session, Competitor,
        MarketMetric, CostModel, GovernmentScheme, SchemeRule,
        LoanProduct, FinancialProjection, Scenario, Recommendation,
        ConfidenceTag, Source, Price,
    )
    Base.metadata.create_all(bind=engine)
    _apply_additive_columns()


# Columns added after the first release. create_all() never alters an existing
# table, so a checked-in SQLite file would otherwise be missing them. Each entry
# is applied only when absent, making this safe to run on every startup.
_ADDITIVE_COLUMNS = {
    "financial_projections": [
        ("monthly_emi", "FLOAT"),
        ("monthly_interest", "FLOAT"),
        ("financing_gap", "FLOAT"),
        ("payback_months", "FLOAT"),
    ],
}


def _apply_additive_columns():
    for table, columns in _ADDITIVE_COLUMNS.items():
        existing = {
            row[1] for row in engine.connect().execute(
                text(f"PRAGMA table_info({table})")
            ).fetchall()
        }
        if not existing:
            continue
        for column, sql_type in columns:
            if column in existing:
                continue
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
