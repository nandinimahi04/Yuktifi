"""
Gemini AI SWOT Analysis Engine.
Generates comprehensive Strengths, Weaknesses, Opportunities, and Threats (SWOT) analysis
for micro-enterprises using Gemini API with deterministic ground-truth fallbacks.
"""
import logging
from typing import Dict, Any, List, Optional
from app.ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

SWOT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "strengths": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "impact": {"type": "STRING", "enum": ["HIGH", "MODERATE"]}
                },
                "required": ["title", "description", "impact"]
            }
        },
        "weaknesses": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "mitigation": {"type": "STRING"}
                },
                "required": ["title", "description", "mitigation"]
            }
        },
        "opportunities": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "potential": {"type": "STRING", "enum": ["HIGH", "MODERATE"]}
                },
                "required": ["title", "description", "potential"]
            }
        },
        "threats": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "contingency": {"type": "STRING"}
                },
                "required": ["title", "description", "contingency"]
            }
        },
        "strategic_summary": {
            "type": "STRING",
            "description": "A 2-sentence executive summary of the strategic posture for this business."
        }
    },
    "required": ["strengths", "weaknesses", "opportunities", "threats", "strategic_summary"]
}


DEFAULT_SWOT_PROFILES: Dict[str, Dict[str, Any]] = {
    "agri_business": {
        "strengths": [
            {
                "title": "High Local Protein & Meat Demand",
                "description": "Consistent weekly demand from local retail butchers, weekly rural haats, and eateries.",
                "impact": "HIGH"
            },
            {
                "title": "Fast Working Capital Turnover",
                "description": "Short production cycles (35-42 days for broilers) enable frequent cash-flow realization.",
                "impact": "HIGH"
            },
            {
                "title": "Low Fixed Overheads",
                "description": "Minimal shopfront rent requirements in semi-urban and rural village catchments.",
                "impact": "MODERATE"
            }
        ],
        "weaknesses": [
            {
                "title": "Feed Cost Sensitivity",
                "description": "Soymeal and maize feed prices represent 65-70% of total operational cost structure.",
                "mitigation": "Establish direct bulk contracts with regional feed mills and maintain 14-day safety inventory."
            },
            {
                "title": "Biosecurity & Mortality Risk",
                "description": "Vulnerability to seasonal disease outbreaks without rigorous vaccination schedules.",
                "mitigation": "Implement strict sanitary footbaths, proper ventilation, and tie up with local veterinary officers."
            }
        ],
        "opportunities": [
            {
                "title": "Government Subventions & NLM Support",
                "description": "Capital subsidy eligibility under National Livestock Mission and Mudra Kishore credit.",
                "potential": "HIGH"
            },
            {
                "title": "Direct B2B Hospitality Off-Take",
                "description": "Long-term supply contracts with local dhabas, marriage halls, and catering vendors.",
                "potential": "HIGH"
            }
        ],
        "threats": [
            {
                "title": "Extreme Summer Heat Spikes",
                "description": "High ambient temperatures cause heat stress and elevated flock mortality rates.",
                "contingency": "Install sprinkler cooling mats and thatch roof insulations during peak summer months."
            },
            {
                "title": "Mandi Farmgate Price Fluctuations",
                "description": "Volatile farmgate live-bird prices driven by seasonal fasting periods.",
                "contingency": "Plan batch placements to align harvesting with high-demand festival seasons."
            }
        ],
        "strategic_summary": "The proposed enterprise leverages rapid capital cycle velocity and robust local off-take demand. Sustained profitability hinges on tight feed procurement control and disciplined biosecurity management."
    },
    "food_beverage": {
        "strengths": [
            {
                "title": "Daily Cash-Flow Velocity",
                "description": "Immediate consumer cash receipts eliminate debtor credit risk and ensure strong daily liquidity.",
                "impact": "HIGH"
            },
            {
                "title": "High Gross Margin Product Mix",
                "description": "Beverages and fried snacks yield 55-65% gross margin over raw ingredient costs.",
                "impact": "HIGH"
            }
        ],
        "weaknesses": [
            {
                "title": "Perishable Raw Material Spoilage",
                "description": "Dairy and vegetable freshness window requires precise daily inventory forecasting.",
                "mitigation": "Order fresh milk and vegetables daily on a Just-In-Time replenishment schedule."
            },
            {
                "title": "Footfall & Location Dependency",
                "description": "Sales volumes fluctuate based on pedestrian transit corridors and market hours.",
                "mitigation": "Secure prime frontage near bus stations, college hubs, or commercial markets."
            }
        ],
        "opportunities": [
            {
                "title": "Packaged Snack & Catering Expansion",
                "description": "Supply bulk evening snack boxes to offices, bank branches, and small local events.",
                "potential": "HIGH"
            },
            {
                "title": "Digital UPI Payment Adoption",
                "description": "Attract younger consumers and maintain seamless transaction accounting via QR codes.",
                "potential": "HIGH"
            }
        ],
        "threats": [
            {
                "title": "Input Commodity Price Surges",
                "description": "Spikes in commercial cooking gas (LPG) and edible oils squeeze operating margins.",
                "contingency": "Form small-portion menu bundles and optimize oil recycling with temperature-controlled fryers."
            },
            {
                "title": "Hyper-Local Competitor Density",
                "description": "Low barriers to entry allow informal roadside competitors to open nearby.",
                "contingency": "Differentiate through strict hygiene standards, distinctive chutney recipes, and branded packaging."
            }
        ],
        "strategic_summary": "High transaction velocity and strong cash gross margins make this a resilient micro-enterprise. Success relies on consistent product taste, strict hygiene, and proactive inventory shrinkage management."
    },
    "retail_shop": {
        "strengths": [
            {
                "title": "Essential Inelastic Demand",
                "description": "Household staple groceries and daily provisions enjoy recurring non-discretionary purchase cycles.",
                "impact": "HIGH"
            },
            {
                "title": "Sticky Neighborhood Customer Loyalty",
                "description": "Proximity and personalized credit relationship with local families build high retention.",
                "impact": "HIGH"
            }
        ],
        "weaknesses": [
            {
                "title": "High Working Capital Lockup",
                "description": "Broad SKU inventory requirements tie up capital across slow-moving FMCG goods.",
                "mitigation": "Focus capital on top 20% high-velocity SKUs (atta, oil, sugar, tea, dals) with weekly stock audits."
            },
            {
                "title": "Thin Retail Product Margins",
                "description": "Branded FMCG items offer modest 8-15% retail margins.",
                "mitigation": "Introduce high-margin unbranded dry fruits, spices, and loose staples with clean packaging."
            }
        ],
        "opportunities": [
            {
                "title": "WhatsApp Order & Home Delivery",
                "description": "Offer local doorstep delivery within a 2 km radius to capture busy household spend.",
                "potential": "HIGH"
            },
            {
                "title": "Distributor Credit Terms Optimization",
                "description": "Negotiate 15-day supplier credit terms based on consistent payment track record.",
                "potential": "MODERATE"
            }
        ],
        "threats": [
            {
                "title": "Organized Quick-Commerce & Supermarts",
                "description": "Discounting from regional marts can pressure retail price realizations.",
                "contingency": "Provide flexible micro-credit, split quantities, and immediate emergency deliveries."
            },
            {
                "title": "Inventory Damage & Pest Shrinkage",
                "description": "Storage loss from humidity or rodents directly erodes monthly profit margins.",
                "contingency": "Store grains in elevated plastic pallets with moisture-proof food-grade bins."
            }
        ],
        "strategic_summary": "The kirana model provides rock-solid baseline revenue through recurring consumer demand. Long-term margin growth requires curated high-margin loose provisions and prompt doorstep service."
    }
}


async def generate_swot_analysis(
    category_id: str,
    category_name: str,
    location_name: str = "Solapur, Maharashtra",
    financials: Optional[Dict[str, Any]] = None,
    market_data: Optional[Dict[str, Any]] = None,
    scores: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates tailored SWOT analysis for an enterprise using Gemini API.
    """
    gemini = GeminiClient()
    cat_key = (category_id or "").lower().strip()
    
    fin = financials or {}
    mkt = market_data or {}
    sc = scores or {}

    prompt = f"""
    You are an expert rural and micro-enterprise financial strategist for YuktiFi (Government of India initiative).
    Generate a rigorous, highly specific, and actionable SWOT Analysis for the following enterprise proposal:

    BUSINESS PROFILE:
    - Category ID: {category_id}
    - Business Name: {category_name}
    - Operating Location: {location_name}
    
    FINANCIAL BASELINE:
    - Monthly Net Profit: ₹{fin.get('net_profit') or fin.get('monthly_net_profit') or '20,000'}
    - Monthly Revenue: ₹{fin.get('monthly_revenue') or '1,50,000'}
    - Return on Investment (ROI): {fin.get('roi_pct') or '28.4'}%
    - Total Project Cost: ₹{fin.get('total_project_cost') or fin.get('project_cost') or '3,00,000'}
    - Debt Service Coverage Ratio (DSCR): {fin.get('dscr') or '2.1'}x

    MARKET CONTEXT:
    - Catchment Population: {mkt.get('catchment_population') or mkt.get('target_customer_base') or '48,500'}
    - Competitor Count: {mkt.get('competitor_count') or '3'} mapped competitors in 5km radius
    - Viability Score: {sc.get('overall') or sc.get('yukti_score') or '88'}/100

    INSTRUCTIONS:
    1. STRENGTHS: 2-3 specific internal competitive advantages based on these numbers and local trade mechanics.
    2. WEAKNESSES: 2 actionable internal vulnerabilities with pragmatic mitigation tactics for a micro-entrepreneur.
    3. OPPORTUNITIES: 2 external market expansion or government scheme avenues (mention relevant schemes like PMEGP, Mudra, NLM, PMFME).
    4. THREATS: 2 external risks (commodity inflation, seasonal weather, competition) with clear contingency plans.
    5. STRATEGIC SUMMARY: Exactly 2 clear sentences synthesizing the business's strategic posture.

    Output strict JSON adhering to the specified schema.
    """

    ai_result = None
    if gemini.api_key:
        try:
            ai_result = await gemini.generate_json_async(prompt, schema=SWOT_SCHEMA)
        except Exception as e:
            logger.warning(f"Failed to generate SWOT from Gemini API: {e}")

    if ai_result and isinstance(ai_result, dict) and "strengths" in ai_result:
        return {
            **ai_result,
            "ai_generated": True,
            "model_used": gemini.model,
            "category_id": category_id,
            "category_name": category_name,
            "location": location_name
        }

    # Fallback to category archetype template
    fallback_key = "agri_business"
    if any(k in cat_key for k in ("food", "tea", "snack", "cafe", "dhaba", "restaurant", "vada")):
        fallback_key = "food_beverage"
    elif any(k in cat_key for k in ("kirana", "retail", "shop", "grocery", "store")):
        fallback_key = "retail_shop"

    profile = DEFAULT_SWOT_PROFILES.get(fallback_key, DEFAULT_SWOT_PROFILES["agri_business"])
    return {
        **profile,
        "ai_generated": False,
        "model_used": "deterministic_ground_truth",
        "category_id": category_id,
        "category_name": category_name,
        "location": location_name
    }
