"""
YuktiFi Advisory Report Builder.
Connects the advisory pipeline outputs directly into the 24-section Auditable Decision Dossier & HTML Printable Reporter.
"""
from typing import Dict, Any
from app.reports.dossier_generator import generate_auditable_dossier
from app.reports.html_reporter import render_dossier_to_html

def build_report(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the 24-section JSON Auditable Decision Dossier.

    `own_capital` previously defaulted to 50,000.0 and `category_id` to
    "kirana", so any result without a financial block produced a dossier
    asserting the applicant had 50,000 rupees and ran a kirana store - the two
    facts a bank officer reads first, invented from nothing. Both now pass
    through as None and are recorded in the dossier's unavailable_fields list.
    """
    profile = {
        "own_capital": (result.get("financial") or {}).get("promoter_margin"),
        "category_id": (result.get("business") or {}).get("id"),
    }
    location = result.get("location", {})
    business_template = result.get("business", {})
    financial_result = result.get("financial", {})
    stress_result = {"scenarios": result.get("risk", {})}
    feasibility_result = result.get("decision", {})
    why_not_result = result.get("decision", {}).get("why_not", [])
    schemes = result.get("schemes", [])

    return generate_auditable_dossier(
        profile=profile,
        location=location,
        business_template=business_template,
        financial_result=financial_result,
        stress_result=stress_result,
        feasibility_result=feasibility_result,
        why_not_result=why_not_result,
        schemes=schemes
    )

def build_html_report(result: Dict[str, Any]) -> str:
    """Build printable HTML document with print CSS layout."""
    dossier = build_report(result)
    return render_dossier_to_html(dossier)
