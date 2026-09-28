try:
    import anthropic
except ImportError:  # optional provider; deterministic fallback remains available
    anthropic = None
import json
from app.core.config import settings
from app.ai_layer.numeric_validator import validate_llm_output
from app.ai_layer.prompt_templates import EXPLAIN_TEMPLATE

FALLBACK_TEMPLATE = "Based on the data: {summary} (Detailed AI explanation unavailable right now due to configuration or safety checks)."

def get_client():
    if anthropic is None or not settings.llm_api_key or settings.llm_api_key == "mock":
        return None
    try:
        return anthropic.Anthropic(api_key=settings.llm_api_key)
    except Exception:
        return None

def generate_explanation(context: dict, question: str, language: str = "English") -> dict:
    """Generate an explanation using the LLM, with fallback if it fails or hallucinates numbers."""
    client = get_client()
    
    # If no client (dev mode or missing key), use deterministic fallback
    if not client:
        return {
            "answer": _generate_deterministic_fallback(context, question),
            "source": "template",
            "confidence": "Medium"
        }
        
    prompt = EXPLAIN_TEMPLATE.format(
        language=language, context_json=json.dumps(context), question=question
    )
    
    try:
        resp = client.messages.create(
            model=settings.llm_model, max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text
        
        allowed_numbers = {str(v) for v in _flatten_numbers(context)}
        is_valid, _reason = validate_llm_output(text, allowed_numbers)
        
        if not is_valid:
            # LLM hallucinated numbers not in context
            return {
                "answer": FALLBACK_TEMPLATE.format(summary="The AI generated unverified numbers and was blocked."),
                "source": "template",
                "confidence": "Low"
            }
            
        return {
            "answer": text,
            "source": "ai",
            "confidence": "High"
        }
    except Exception as e:
        return {
            "answer": FALLBACK_TEMPLATE.format(summary=f"Error contacting AI service: {str(e)}"),
            "source": "template",
            "confidence": "Low"
        }

def _generate_deterministic_fallback(context: dict, question: str) -> str:
    """Generate a simple text response from the context dictionary."""
    parts = []
    
    # Very basic text generation
    if "loan" in context:
        parts.append(f"Project Cost: {context['loan'].get('project_cost')}")
    if "financial_projection" in context:
        parts.append(f"Estimated Monthly Net Profit: {context['financial_projection'].get('net_profit')}")
    if "scheme" in context:
        parts.append(f"Eligible Scheme: {context['scheme'].get('name')}")
        
    summary = " | ".join(parts) if parts else "No specific context available."
    return FALLBACK_TEMPLATE.format(summary=summary)

def _flatten_numbers(obj):
    nums = []
    if isinstance(obj, dict):
        for v in obj.values():
            nums.extend(_flatten_numbers(v))
    elif isinstance(obj, list):
        for v in obj:
            nums.extend(_flatten_numbers(v))
    elif isinstance(obj, (int, float)):
        nums.append(obj)
    return nums
