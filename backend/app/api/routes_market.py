"""
Market Intelligence API Routes (Phase 1 + Phase 2).

Exposes:
- GET & POST /api/market/snapshot: Unified Market Snapshot (Census + WorldPop + Overture + OSM + HCES 2023-24 + Consumer Affairs + AGMARKNET)
- GET /api/market/consumer-profile: HCES 2023-24 state/sector consumer expenditure benchmark
- GET /api/market/retail-prices: Department of Consumer Affairs daily retail price metrics
- GET /api/market/mandi-prices: AGMARKNET wholesale APMC mandi price dynamics
- GET /api/market/price-trends: Historical daily price series for charting
- GET /api/market/input-cost-pressure: Business-specific weighted input inflation & risk
- POST /analyze-market: Backwards-compatible market intelligence orchestrator endpoint
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Response, Query
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.schemas.market import (
    MarketRequest, MarketResponse, MarketSnapshotResponse,
    ConsumerProfileInfo, RetailPricesInfo, MandiPricesInfo, InputCostPressureInfo
)
from app.engines.market_intelligence import run_full_market_analysis_async_cached
from app.engines.market_intelligence.snapshot_engine import compute_market_snapshot
from app.engines.market_intelligence.consumer_profile_engine import compute_consumer_profile
from app.engines.market_intelligence.retail_price_engine import (
    get_retail_basket_for_category, get_retail_timeseries, get_commodity_retail_metrics
)
from app.engines.market_intelligence.mandi_price_engine import (
    get_mandi_basket_for_category, get_commodity_mandi_metrics
)
from app.engines.market_intelligence.input_cost_pressure_engine import compute_input_cost_pressure

router = APIRouter(tags=["market-intelligence"])

CATEGORY_NAMES = {
    "retail_kirana": "Kirana / Grocery Store",
    "retail_shop": "Retail & Kirana Store",
    "tea_snacks": "Tea & Snacks Shop",
    "tea_stall": "Tea Stall & Snacks",
    "food_beverage": "Food & Beverage",
    "dairy": "Dairy",
    "tailoring": "Tailoring",
    "flour_mill": "Flour Mill",
    "poultry": "Poultry",
}

@router.get("/api/market/snapshot", response_model=MarketSnapshotResponse)
@router.get("/market/snapshot", response_model=MarketSnapshotResponse)
def get_market_snapshot(
    location: Optional[str] = Query(None, description="Location text or coordinates e.g. 'Solapur City' or '17.6599, 75.9064'"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude"),
    category_id: str = Query("retail_kirana", description="Category ID e.g. 'retail_kirana' or 'tea_snacks'"),
    radius_km: Optional[float] = Query(None, description="Custom catchment radius in km (optional)"),
):
    """
    Returns unified Market Intelligence Snapshot across Phase 1 and Phase 2.
    """
    try:
        snapshot = compute_market_snapshot(
            location_query=location,
            lat=lat,
            lon=lon,
            category_id=category_id,
            radius_km=radius_km,
        )
        return MarketSnapshotResponse(**snapshot)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market snapshot computation failed: {str(e)}")

@router.post("/api/market/snapshot", response_model=MarketSnapshotResponse)
@router.post("/market/snapshot", response_model=MarketSnapshotResponse)
def post_market_snapshot(
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    category_id: str = "retail_kirana",
    radius_km: Optional[float] = None,
):
    """POST variant for Market Snapshot."""
    return get_market_snapshot(location=location, lat=lat, lon=lon, category_id=category_id, radius_km=radius_km)

@router.get("/api/market/consumer-profile", response_model=ConsumerProfileInfo)
@router.get("/market/consumer-profile", response_model=ConsumerProfileInfo)
def get_consumer_profile_endpoint(
    state: str = Query("Maharashtra", description="State name"),
    sector: str = Query("rural", description="Sector: 'rural' or 'urban'"),
    category_id: Optional[str] = Query("retail_kirana", description="Business category ID")
):
    """
    MoSPI HCES 2023-24 Consumer Spending and Consumption Profile Benchmark.
    """
    try:
        profile = compute_consumer_profile(state=state, sector=sector, category_id=category_id)
        return ConsumerProfileInfo(**profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch consumer profile: {str(e)}")

@router.get("/api/market/retail-prices", response_model=RetailPricesInfo)
@router.get("/market/retail-prices", response_model=RetailPricesInfo)
def get_retail_prices_endpoint(
    category_id: str = Query("retail_kirana", description="Business category ID"),
    market_centre: Optional[str] = Query("Solapur", description="Market centre name e.g. Solapur, Pune, Mumbai")
):
    """
    Department of Consumer Affairs (PMS) daily retail price metrics for the category basket.
    """
    try:
        basket = get_retail_basket_for_category(category_id=category_id, market_centre=market_centre)
        return RetailPricesInfo(**basket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch retail prices: {str(e)}")

@router.get("/api/market/mandi-prices", response_model=MandiPricesInfo)
@router.get("/market/mandi-prices", response_model=MandiPricesInfo)
def get_mandi_prices_endpoint(
    category_id: str = Query("retail_kirana", description="Business category ID"),
    lat: Optional[float] = Query(None, description="Latitude for nearest mandi resolution"),
    lon: Optional[float] = Query(None, description="Longitude for nearest mandi resolution"),
    preferred_market: Optional[str] = Query(None, description="Specific APMC market name")
):
    """
    AGMARKNET / eNAM wholesale mandi price dynamics and proximity resolution.
    """
    try:
        mandi_basket = get_mandi_basket_for_category(category_id=category_id, lat=lat, lon=lon, preferred_market=preferred_market)
        return MandiPricesInfo(**mandi_basket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch mandi prices: {str(e)}")

@router.get("/api/market/price-trends")
@router.get("/market/price-trends")
def get_price_trends_endpoint(
    commodity: str = Query("rice", description="Canonical commodity ID or name e.g. rice, wheat, sugar, milk"),
    market_centre: Optional[str] = Query("Solapur", description="Market centre name"),
    days: int = Query(90, description="Number of historical days to return (e.g. 30, 90, 180)")
):
    """
    Historical daily price time-series for visual trend analysis.
    """
    try:
        return get_retail_timeseries(commodity_id_or_name=commodity, market_centre=market_centre, days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price trends: {str(e)}")

@router.get("/api/market/input-cost-pressure", response_model=InputCostPressureInfo)
@router.get("/market/input-cost-pressure", response_model=InputCostPressureInfo)
def get_input_cost_pressure_endpoint(
    category_id: str = Query("retail_kirana", description="Business category ID"),
    market_centre: Optional[str] = Query("Solapur", description="Market centre name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude")
):
    """
    Business-specific weighted input cost inflation pressure and procurement risk.
    """
    try:
        pressure = compute_input_cost_pressure(category_id=category_id, market_centre=market_centre, lat=lat, lon=lon)
        return InputCostPressureInfo(**pressure)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute input cost pressure: {str(e)}")

@router.post("/analyze-market", response_model=MarketResponse)
async def analyze_market(req: MarketRequest, response: Response, db: DBSession = Depends(get_db)):
    cat_name = req.category_name or CATEGORY_NAMES.get(req.category_id, req.category_id.replace("_", " ").title())

    # Save category to session if session exists
    try:
        from app.models import Session
        session = db.query(Session).filter(Session.id == req.session_id).first()
        if session:
            session.category_id = req.category_id
            db.commit()
    except Exception:
        pass

    result = await run_full_market_analysis_async_cached(
        req.location_id, 
        req.category_id, 
        cat_name,
        budget=req.budget,
        experience=req.experience,
        idea_details=req.idea_details
    )
    
    response.headers["Cache-Control"] = "public, max-age=1800"
    return MarketResponse(**result)
