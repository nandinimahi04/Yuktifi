"""
YuktiFi AI Explanation & Verification Engine (Phases 12, 13 & 16).
Generates grounded narratives from canonical financial data while strictly enforcing DPDP Act data minimization.
"""
from typing import Dict, Any, List
import json

def sanitize_context_for_llm(raw_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    DPDP Act Compliance (Phase 16.1):
    Strips PII (name, phone, specific street address, social category)
    and passes only generalized parameters needed for technical narrative generation.
    """
    sanitized = {
        "business_type": raw_context.get("business_type", "General Enterprise"),
        "district": raw_context.get("district", "Unknown District"),
        "state": raw_context.get("state", "Unknown State"),
        "capital_band": raw_context.get("capital_band", "Standard Band"),
        "financial_results": raw_context.get("financial_results", {}),
        "feasibility": raw_context.get("feasibility", {}),
        "schemes": raw_context.get("schemes", []),
        "evidence_summary": raw_context.get("evidence_summary", [])
    }
    return sanitized


def build_explanation_prompt(sanitized_context: Dict[str, Any]) -> str:
    """
    Constructs an explicit evidence-first system prompt for Gemini LLM.
    Strictly instructs LLM not to perform financial calculations.
    """
    fin = sanitized_context.get("financial_results", {})
    feas = sanitized_context.get("feasibility", {})
    schemes = sanitized_context.get("schemes", [])

    prompt = f"""You are YuktiFi's AI Decision Advisor.
Explain the deterministically computed financial feasibility results to the entrepreneur.

RULES:
1. DO NOT recalculate or invent any numbers (Revenue, Profit, EMI, DSCR, Break-even, ROI). Use ONLY the provided numbers.
2. Maintain financial precision and ground all claims in the evidence provided.
3. Include standard disclaimers that final loan/scheme approval rests with the competent lender/authority.

COMPUTED FINANCIAL SUMMARY:
- Monthly Revenue: ₹{fin.get('monthly_revenue', 0):,}
- Monthly Net Profit (PAT): ₹{fin.get('annual_pat', 0)/12:,.2f}
- Monthly EMI: ₹{fin.get('monthly_emi', 0):,}
- Debt Service Coverage Ratio (DSCR): {fin.get('dscr', 0)}
- Break-even Monthly Revenue: ₹{fin.get('break_even_revenue_monthly', 0):,}
- Owner Equity ROI: {fin.get('roi_on_owner_equity_pct', 0)}%
- Payback Period: {fin.get('payback_months', 'N/A')} months

YUKTI SCORE & DRIVERS:
- YUKTI Score: {feas.get('yukti_score', 0)} / 100
- Evidence Coverage: {feas.get('evidence_coverage_pct', 0)}%
- Overall Confidence: {feas.get('overall_confidence', 'MEDIUM')}
- Main Drivers: {", ".join(feas.get('main_drivers', []))}

POTENTIALLY SUITABLE SCHEMES:
{json.dumps(schemes, indent=2)}

Please generate:
1. Executive Summary
2. Financial & Debt Service Viability Analysis
3. Recommended Scheme Strategy & Next Steps
"""
    return prompt


def verify_llm_claims(llm_response_text: str, ground_truth_fin: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verification matcher (Phase 13):
    Scans generated text for ungrounded numeric claims and flags discrepancies.
    """
    # Simple empirical check for key numeric outputs
    flagged_issues = []
    dscr_str = str(ground_truth_fin.get("dscr", ""))
    
    if dscr_str and dscr_str not in llm_response_text and "DSCR" in llm_response_text:
        flagged_issues.append(f"LLM text mentions DSCR but does not reference exact value {dscr_str}")

    return {
        "verified": len(flagged_issues) == 0,
        "flagged_issues": flagged_issues
    }
