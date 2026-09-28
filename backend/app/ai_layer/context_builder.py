"""Builds structured context for the LLM based on session state."""
from sqlalchemy.orm import Session as DBSession
from app.models import Session, Location, BusinessCategory, LoanProduct, FinancialProjection, GovernmentScheme
from app.data_layer.retrieval import DataRetrieval

data_layer = DataRetrieval()

def build_explain_context(db: DBSession, session_id: str) -> dict:
    """Gather all relevant data for a session to pass to the LLM."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        return {"error": "Session not found"}
        
    location = db.query(Location).filter(Location.id == session.location_id).first()
    category = db.query(BusinessCategory).filter(BusinessCategory.id == session.category_id).first()
    loan = db.query(LoanProduct).filter(LoanProduct.session_id == session_id).first()
    projection = db.query(FinancialProjection).filter(FinancialProjection.session_id == session_id).first()
    
    context = {
        "user_margin_capital": session.margin_capital,
        "location": {
            "district": location.district,
            "state": location.state,
            "data_richness": location.data_richness,
        } if location else {},
        "business_category": {
            "name": category.name if category else "Unknown",
        } if category else {},
    }
    
    if loan:
        context["loan"] = {
            "project_cost": loan.project_cost,
            "loan_amount": loan.loan_amount,
            "beneficiary_contribution": loan.beneficiary_contribution,
        }
        if loan.matched_scheme_id:
            scheme = db.query(GovernmentScheme).filter(GovernmentScheme.id == loan.matched_scheme_id).first()
            if scheme:
                context["scheme"] = {
                    "name": scheme.name,
                    "interest_rate": scheme.interest_rate,
                    "tenure_months": scheme.tenure_months,
                }
                
    if projection:
        context["financial_projection"] = {
            "monthly_revenue": projection.monthly_revenue,
            "monthly_opex": projection.monthly_opex,
            "net_profit": projection.net_profit,
            "break_even_units": projection.break_even_units,
            "dscr": projection.dscr,
            "roi": projection.roi,
        }
        
    # Get market intelligence if category and location exist
    if location and category:
        market_reach = data_layer.get_demographics(location.id)
        if market_reach and market_reach.get("value"):
            context["market_reach"] = market_reach["value"]

        # Pricing is only available asynchronously (Agmarknet). It is not
        # included in this synchronous context rather than being invented,
        # and the explanation layer must state that prices were unavailable
        # instead of implying a price was known.
        cost_profile = data_layer.get_cost_profile(location.id, category.id)
        if cost_profile and cost_profile.get("value"):
            context["cost_profile"] = cost_profile["value"]
        else:
            context["pricing"] = None
            context["pricing_status"] = "UNAVAILABLE"
            context["pricing_note"] = cost_profile.get("note") if cost_profile else None

    return context
