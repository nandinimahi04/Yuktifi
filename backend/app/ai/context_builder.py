"""
Context Builder for the AI module.
Converts YUKTI's structured data (from engines and data layer) into clean, 
text-based context strings that can be reliably passed to Gemini.
"""

class ContextBuilder:
    def __init__(self):
        pass

    def build_copilot_context(self, location: str, category: str, market_data: dict, financial_data: dict, score_data: dict = None) -> str:
        """
        Builds the context string for the Copilot based on structured inputs.
        """
        # Example implementation, to be expanded based on exact engine outputs
        context_parts = []
        context_parts.append(f"Location: {location}")
        context_parts.append(f"Business Category: {category}")
        
        if market_data:
            context_parts.append("\\n--- Market Intelligence ---")
            context_parts.append(f"Competitors Found: {market_data.get('competitor_count', 'Unknown')}")
            if 'market_reach' in market_data:
                reach = market_data['market_reach'].get('estimated_target_customer_base', 'Unknown')
                context_parts.append(f"Market Reach (Est. Customer Base): {reach}")
                
        if financial_data:
            context_parts.append("\\n--- Financial Projections ---")
            if 'unit_economics' in financial_data:
                econ = financial_data['unit_economics']
                context_parts.append(f"Expected Monthly Revenue: {econ.get('expected_monthly_revenue', 'Unknown')} {econ.get('currency', 'INR')}")
                context_parts.append(f"Net Operating Income: {econ.get('net_operating_income', 'Unknown')} {econ.get('currency', 'INR')}")

        if score_data:
            context_parts.append("\\n--- YUKTI Score ---")
            context_parts.append(f"Score: {score_data.get('score', 'Unknown')}")

        return "\n".join(context_parts)

    def build_comprehensive_context(self, location: str, category: str, market_data: dict, financial_data: dict, risk_data: dict) -> str:
        """
        Builds a comprehensive context string for Business Plan and Marketing generation.
        """
        import json
        context_dict = {
            "location": location,
            "business_category": category,
            "market_intelligence": market_data,
            "financial_projections": financial_data,
            "risk_and_swot": risk_data
        }
        return json.dumps(context_dict, indent=2)
