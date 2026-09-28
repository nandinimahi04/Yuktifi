"""Simple heuristic/LLM-based intent classification for routing questions."""

def classify_intent(question: str) -> str:
    """
    Classify the user's question into one of the main categories:
    - financial
    - market
    - scheme
    - general
    
    For the prototype, we use simple keyword heuristics to avoid a slow LLM call here,
    but this can be upgraded to an LLM classifier.
    """
    q_lower = question.lower()
    
    financial_keywords = ["profit", "cost", "revenue", "margin", "emi", "loan", "dscr", "roi", "break even"]
    market_keywords = ["competitor", "market", "demand", "customer", "price", "pricing", "population", "swot", "threat"]
    scheme_keywords = ["scheme", "government", "subsidy", "grant", "eligibility"]
    
    if any(k in q_lower for k in financial_keywords):
        return "financial"
    if any(k in q_lower for k in scheme_keywords):
        return "scheme"
    if any(k in q_lower for k in market_keywords):
        return "market"
        
    return "general"
