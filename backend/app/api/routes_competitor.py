from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.ai.gemini_client import GeminiClient
from app.ai.prompts.competitor_analysis import COMPETITOR_ANALYSIS_PROMPT
from app.schemas.competitor_analysis import CompetitorAnalysis

router = APIRouter()
gemini = GeminiClient()

class CompetitorRequest(BaseModel):
    competitors: List[Dict[str, Any]]

@router.post("/analyze", response_model=CompetitorAnalysis)
async def analyze_competitors(req: CompetitorRequest):
    import json
    context = json.dumps(req.competitors, indent=2)
    prompt = COMPETITOR_ANALYSIS_PROMPT.format(context=context)
    
    response = await gemini.generate_json_async(prompt)
    if not response:
        raise HTTPException(status_code=500, detail="Failed to generate competitor analysis")
        
    try:
        return CompetitorAnalysis(**response)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"AI returned invalid schema: {str(e)}")
