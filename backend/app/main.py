import contextlib
import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import init_db, SessionLocal
from app.core.config import settings
from app.core.seed import seed_database
from app.api import (
    routes_profile, routes_rank, routes_market, routes_recommend,
    routes_explain, routes_report, routes_finance, routes_schemes, routes_simulate,
    routes_copilot, routes_business_plan, routes_marketing, routes_competitor,
    routes_analysis, routes_locations, routes_phase, routes_rag, routes_location_resolver, routes_census, routes_advisory
)

logger = logging.getLogger("yukti")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    logger.info("YuktiFi backend started successfully.")
    yield


app = FastAPI(title="YuktiFi API", lifespan=lifespan)

# Origins come from settings.cors_origin_list, not from a second parse of the raw
# string. This block previously re-implemented the parsing inline and compared the
# raw value to "*" directly, which bypassed the `allow_wildcard_cors` and
# development-only guards that settings.cors_origin_list enforces - so the
# hardened helper in config.py was never called by the only code that matters, and
# CORS_ORIGINS="*" would have been honoured in production regardless of both
# flags.
_cors_origins = settings.cors_origin_list

if _cors_origins == ["*"]:
    # A wildcard origin and credentials cannot be combined: the response would
    # carry `Access-Control-Allow-Origin: *` together with
    # `Access-Control-Allow-Credentials: true`, which the CORS specification
    # forbids and browsers reject. So the wildcard path drops credentials rather
    # than emitting a combination that fails closed for every caller.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.warning(
        "CORS is set to wildcard with credentials disabled. Use an explicit "
        "CORS_ORIGINS list for any deployment that serves authenticated requests."
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    # Optional production guard. Leave YUKTI_API_KEY empty for local development.
    if settings.api_key and request.url.path not in {"/health", "/docs", "/openapi.json", "/redoc"}:
        supplied = request.headers.get("X-YUKTI-API-KEY", "")
        if supplied != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing X-YUKTI-API-KEY"})
    return await call_next(request)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000)
    logger.info(
        "%s %s → %d (%dms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.middleware("http")
async def disclose_data_mode(request: Request, call_next):
    """
    Say out loud, on every response, whether the data behind it is live.

    `DEMO_MODE=true` switches off outbound network in the provider clients, so
    prices, competitor counts and population come from bundled fixtures instead.
    That is the right behaviour, but it was invisible: the screen looked exactly
    the same as a live run, and a founder had no way to know the numbers behind
    the recommendation had not been fetched. A figure that is not live must be
    labelled as not live.

    The header is the only channel that works here, because the disclosure has
    to travel with *every* response rather than with one endpoint the UI might
    forget to call.
    """
    response = await call_next(request)
    # `network_allowed` is the same property the provider clients consult, so the
    # disclosure cannot drift from the behaviour it is disclosing.
    live = settings.network_allowed
    response.headers["X-YuktiFi-Data-Mode"] = "live" if live else "demo"
    # A response that says the data is not live must not be cached and reused as
    # though it were.
    if not live:
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(routes_profile.router)
app.include_router(routes_rank.router)
app.include_router(routes_market.router)
app.include_router(routes_recommend.router)
app.include_router(routes_explain.router)
app.include_router(routes_report.router)
app.include_router(routes_finance.router)
app.include_router(routes_schemes.router)
app.include_router(routes_simulate.router)
app.include_router(routes_simulate.router, prefix="/api", tags=["simulate"])
app.include_router(routes_copilot.router, prefix="/api/copilot", tags=["copilot"])
app.include_router(routes_business_plan.router, prefix="/api/business-plan", tags=["business-plan"])
app.include_router(routes_marketing.router, prefix="/api/marketing", tags=["marketing"])
app.include_router(routes_competitor.router, prefix="/api/competitor", tags=["competitor"])
app.include_router(routes_analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(routes_locations.router, prefix="/api/locations", tags=["locations"])
app.include_router(routes_phase.router)
app.include_router(routes_rag.router)
app.include_router(routes_location_resolver.router)
app.include_router(routes_census.router)
app.include_router(routes_advisory.router)
from app.api import routes_privacy
app.include_router(routes_privacy.router)
from app.api import routes_financial_assumptions
app.include_router(routes_financial_assumptions.router)
from app.api import routes_analytics
app.include_router(routes_analytics.router)


@app.get("/health")
def health_check():
    """Lightweight health probe — verifies DB is reachable."""
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "4.0.0-phases1-18",
        "architecture": {"phase1": "canonical_finance_decision", "phase2": "evidence_provenance", "rag": "grounded_document_retrieval", "advisory": "phases7-18-integrated", "api_key_guard": bool(settings.api_key)},
        "database": db_status,
    }
