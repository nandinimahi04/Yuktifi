"""
SWOT Analysis API Route.
Generates and returns AI-powered SWOT assessments using Gemini API.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.ai_layer.swot_generator import generate_swot_analysis

router = APIRouter(prefix="/api/ai", tags=["AI Strategic Analysis"])

class SwotRequest(BaseModel):
    category_id: str = Field(..., description="Canonical category ID, e.g. 'agri_business', 'poultry', 'retail_kirana'")
    category_name: str = Field(..., description="Display business name, e.g. 'Poultry Farming (Broiler/Layer)'")
    location_name: Optional[str] = Field(default="Solapur, Maharashtra", description="Target district and state")
    financials: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Revenue, net profit, ROI, project cost")
    market_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Catchment population, competition count")
    scores: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Viability score and dimension scores")

@router.post("/swot")
async def get_swot_analysis(req: SwotRequest):
    """
    Generate dynamic, hyper-local SWOT analysis using Gemini API.
    """
    result = await generate_swot_analysis(
        category_id=req.category_id,
        category_name=req.category_name,
        location_name=req.location_name or "Solapur, Maharashtra",
        financials=req.financials,
        market_data=req.market_data,
        scores=req.scores
    )
    return result
