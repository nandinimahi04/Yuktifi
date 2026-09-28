import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from app.ai.gemini_client import GeminiClient
from app.ai.context_builder import ContextBuilder
from app.ai.prompts.copilot import COPILOT_SYSTEM_PROMPT
from app.ai.prompts.explain import EXPLAIN_DECISION_PROMPT
from app.ai_layer.numeric_validator import validate_llm_output

router = APIRouter()
logger = logging.getLogger(__name__)
gemini = GeminiClient()
context_builder = ContextBuilder()

class ChatRequest(BaseModel):
    message: str
    location_id: str
    category_id: str
    # In a real app, these would come from the session state
    market_data: Dict[str, Any] = {}
    financial_data: Dict[str, Any] = {}
    score_data: Dict[str, Any] = {}

class ExplainRequest(BaseModel):
    question: str
    location_id: str
    category_id: str
    market_data: Dict[str, Any] = {}
    financial_data: Dict[str, Any] = {}
    score_data: Dict[str, Any] = {}


def _allowed_numbers(*blocks: Any) -> set:
    """
    Every number the model is permitted to state.

    Taken from the context actually supplied to it. A copilot reply is free
    text, so the numeric claim "your DSCR will be 1.8" is invisible to schema
    validation - which is why the two endpoints below check the prose itself.
    """
    return {str(v) for v in _flatten_numbers(blocks)}


def _flatten_numbers(obj: Any):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_numbers(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _flatten_numbers(v)
    elif isinstance(obj, bool):
        return
    elif isinstance(obj, (int, float)):
        yield obj


def _numeric_claim_check(text: str, allowed: set) -> str | None:
    """
    Return the offending number if the narration states one that is not in the
    supplied context, else None.

    `llm_client.generate_explanation` already applies this guard to the other
    explanation endpoint; the copilot was the one narration path without it, and
    it is the one users quote back to a bank officer.
    """
    if not text:
        return None
    ok, reason = validate_llm_output(text, allowed)
    return None if ok else reason


@router.post("/chat")
async def copilot_chat(req: ChatRequest):
    context = context_builder.build_copilot_context(
        req.location_id, req.category_id, req.market_data, req.financial_data, req.score_data
    )
    prompt = COPILOT_SYSTEM_PROMPT.format(context=context) + f"\\n\\nUser: {req.message}\\nCopilot:"

    schema = {
        "type": "object",
        "properties": {
            "reply": {"type": "string"}
        },
        "required": ["reply"]
    }

    response = await gemini.generate_json_async(prompt, schema=schema)
    if not response:
        raise HTTPException(status_code=500, detail="Failed to get response from Gemini")

    reply = (response.get("reply") or "").strip()
    if not reply:
        reply = "I am unable to process that right now."

    allowed = _allowed_numbers(req.market_data, req.financial_data, req.score_data, context)
    violation = _numeric_claim_check(reply, allowed)
    if violation:
        # The reply is withheld rather than repaired: silently deleting one
        # invented figure from a paragraph leaves the rest of a paragraph that
        # was reasoned from it intact and untrustworthy.
        logger.warning("[COPILOT] Blocked reply with unsupported numeric claim: %s", violation)
        return {
            "reply": (
                "I can't answer that in my own words yet. My answer stated a figure that "
                "is not supported by the data for this business, so it has been withheld "
                "rather than shown. The computed figures are on your analysis screen, and "
                "I can explain any of those."
            ),
            "blocked": True,
            "blocked_reason": violation,
        }

    return {"reply": reply, "blocked": False}


@router.post("/explain")
async def copilot_explain(req: ExplainRequest):
    context = context_builder.build_copilot_context(
        req.location_id, req.category_id, req.market_data, req.financial_data, req.score_data
    )
    prompt = EXPLAIN_DECISION_PROMPT.format(context=context, question=req.question)

    schema = {
        "type": "object",
        "properties": {
            "explanation": {"type": "string"}
        },
        "required": ["explanation"]
    }

    response = await gemini.generate_json_async(prompt, schema=schema)
    if not response:
        raise HTTPException(status_code=500, detail="Failed to get response from Gemini")

    explanation = (response.get("explanation") or "").strip()
    if not explanation:
        explanation = "I am unable to explain that right now."

    allowed = _allowed_numbers(req.market_data, req.financial_data, req.score_data, context)
    violation = _numeric_claim_check(explanation, allowed)
    if violation:
        logger.warning("[COPILOT/EXPLAIN] Blocked explanation with unsupported number: %s", violation)
        return {
            "explanation": (
                "The generated explanation stated a figure that is not present in the data "
                "for this business, so it was withheld. The explanation shown on your "
                "analysis screen is computed from your verified inputs."
            ),
            "blocked": True,
            "blocked_reason": violation,
        }

    return {"explanation": explanation, "blocked": False}
