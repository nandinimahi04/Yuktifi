"""POST /explain — AI narration endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from app.schemas.report import ExplainRequest, ExplainResponse
from app.core.db import get_db

from app.ai_layer.context_builder import build_explain_context
from app.ai_layer.llm_client import generate_explanation

router = APIRouter()

@router.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest, db: DBSession = Depends(get_db)):
    context = build_explain_context(db, req.session_id)
    if "error" in context:
        return ExplainResponse(
            answer="Session data not found.",
            source="template",
            confidence="Low"
        )
        
    result = generate_explanation(context, req.question, req.language)
    
    return ExplainResponse(
        answer=result["answer"],
        source=result["source"],
        confidence=result["confidence"]
    )
