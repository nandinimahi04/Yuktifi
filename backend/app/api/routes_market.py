"""POST /analyze-market — run full market intelligence for a category."""
from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session as DBSession
from app.core.db import get_db
from app.schemas.market import MarketRequest, MarketResponse
from app.engines.market_intelligence import run_full_market_analysis_async_cached

router = APIRouter()

CATEGORY_NAMES = {
    "dairy": "Dairy",
    "retail_kirana": "Retail / Kirana Store",
    "tailoring": "Tailoring",
    "flour_mill": "Flour Mill",
    "poultry": "Poultry",
}


@router.post("/analyze-market", response_model=MarketResponse)
async def analyze_market(req: MarketRequest, response: Response, db: DBSession = Depends(get_db)):
    cat_name = req.category_name or CATEGORY_NAMES.get(req.category_id, req.category_id.replace("_", " ").title())

    # Save category to session
    from app.models import Session
    session = db.query(Session).filter(Session.id == req.session_id).first()
    if session:
        session.category_id = req.category_id
        db.commit()

    result = await run_full_market_analysis_async_cached(
        req.location_id, 
        req.category_id, 
        cat_name,
        budget=req.budget,
        experience=req.experience,
        idea_details=req.idea_details
    )
    
    # Inform downstream caches (if any) that this POST response is cacheable for 30 mins
    response.headers["Cache-Control"] = "public, max-age=1800"
    
    return MarketResponse(**result)
