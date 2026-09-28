from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.ai.gemini_client import GeminiClient
from app.ai.context_builder import ContextBuilder
from app.ai.prompts.marketing import MARKETING_STRATEGY_SYSTEM_PROMPT

router = APIRouter()
gemini = GeminiClient()
context_builder = ContextBuilder()

class MarketingRequest(BaseModel):
    location: str
    category: str
    market_data: Dict[str, Any] = {}
    financial_data: Dict[str, Any] = {}
    risk_data: Dict[str, Any] = {}

@router.post("/generate")
async def generate_marketing_strategy(req: MarketingRequest):
    context = context_builder.build_comprehensive_context(
        req.location, req.category, req.market_data, req.financial_data, req.risk_data
    )
    prompt = MARKETING_STRATEGY_SYSTEM_PROMPT.format(context=context)
    
    schema = {
        "type": "object",
        "properties": {
            "target_customers": {"type": "array", "items": {"type": "string"}},
            "marketing_actions": {"type": "array", "items": {"type": "string"}},
            "thirty_day_plan": {"type": "object"},
            "promotional_copy": {"type": "object"}
        },
        "required": ["target_customers", "marketing_actions", "thirty_day_plan", "promotional_copy"]
    }
    
    response = await gemini.generate_json_async(prompt, schema=schema)
    if not response:
        raise HTTPException(status_code=500, detail="Failed to generate marketing strategy")
        
    return response
