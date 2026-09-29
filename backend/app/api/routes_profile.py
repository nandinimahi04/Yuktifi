"""POST /profile — create user + resolve location."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.schemas.profile import ProfileRequest, ProfileResponse, OnboardingParseRequest, OnboardingParseResponse, BusinessMatchRequest, BusinessMatchResponse
from app.core.db import get_db
from app.models import User, Location
from app.models.core import uid
from app.engines.location_service import resolve_location, get_location_metadata
from app.ai_layer.onboarding_parser import parse_onboarding_text

router = APIRouter()


@router.post("/profile", response_model=ProfileResponse)
def create_profile(req: ProfileRequest, db: DBSession = Depends(get_db)):
    # Resolve location
    location_id = resolve_location(req.location_input)
    if not location_id:
        raise HTTPException(status_code=400, detail="Could not resolve location. Try 'Solapur' or 'Remote'.")

    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        try:
            lat_str, lon_str = location_id.split(",")
            from app.models.core import AdminLevel
            location = Location(
                id=location_id,
                village=req.location_input.split(",")[0],
                district="Dynamic",
                state="Dynamic",
                lat=float(lat_str),
                lng=float(lon_str),
                admin_level=AdminLevel.village,
                data_richness="sparse"
            )
            db.add(location)
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logging.getLogger(__name__).error(f"Failed to insert location: {e}")
            raise HTTPException(status_code=404, detail=f"Location '{location_id}' not found in database. Error: {e}")

    # Create user
    user = User(
        id=uid(), 
        name=req.name, 
        age=req.age,
        gender=req.gender,
        social_category=req.social_category,
        business_idea=req.business_idea,
        experience_level=req.experience_level,
        available_capital_inr=req.available_capital_inr,
        loan_intent=req.loan_intent,
        business_category=req.business_category,
        language_pref=req.language
    )
    db.add(user)
    db.commit()

    meta = get_location_metadata(location_id)
    return ProfileResponse(
        user_id=user.id,
        location_id=location_id,
        location_name=f"{location.district}, {location.state}",
        state=location.state,
        lat=meta.get("lat", location.lat),
        lng=meta.get("lng", location.lng),
        data_richness=meta.get("data_richness", location.data_richness),
    )

@router.post("/business/match", response_model=BusinessMatchResponse)
async def match_business(req: BusinessMatchRequest):
    text = req.text.lower()
    if not text:
        return BusinessMatchResponse(detected_business=None, category=None, confidence=0.0, alternatives=[])
    
    # Very basic deterministic matcher based on CATEGORY_MAP in business_matcher
    from app.ai_layer.business_matcher import CATEGORY_MAP
    
    best_match = None
    best_score = 0.0
    best_cat = None
    
    # We map keywords to categories
    KEYWORDS = {
        "retail_shop": ["grocery", "kirana", "mart", "hardware", "tools", "pooja", "shop", "store", "retail"],
        "manufacturing": ["paper", "plate", "cup", "spice", "masala", "powerloom", "towel", "manufacturing", "factory"],
        "agri_business": ["dairy", "milk", "poultry", "mushroom", "farming", "agriculture"],
        "services_tech": ["csc", "seva", "repair", "garage", "mobile", "tech", "service"],
        "food_beverage": ["kitchen", "tiffin", "mill", "chakki", "snacks", "bakery", "food", "cafe", "restaurant"],
        "handicrafts_artisanal": ["handloom", "tailoring", "bamboo", "furniture", "pottery", "clay", "handicraft", "artisan"],
        "logistics_delivery": ["courier", "delivery", "transport", "moving", "logistics"],
        "education_training": ["computer", "typing", "tuition", "coaching", "training", "education", "school"],
        "healthcare_wellness": ["medicine", "pharmacy", "diagnostic", "beauty", "salon", "parlour", "health", "wellness"],
        "fashion_apparel": ["garment", "uniform", "jewellery", "cosmetics", "apparel", "fashion", "clothes"]
    }
    
    words = set(text.split())
    for cat_id, kws in KEYWORDS.items():
        matches = len(words.intersection(kws))
        if matches > 0:
            score = min(1.0, matches * 0.4)
            if score > best_score:
                best_score = score
                best_cat = cat_id
                best_match = kws[0] # Just a simple representation
                
    if best_score >= 0.4:
        return BusinessMatchResponse(
            detected_business=best_match.capitalize(),
            category=best_cat,
            confidence=best_score,
            alternatives=[]
        )
    
    return BusinessMatchResponse(detected_business=None, category=None, confidence=0.0, alternatives=[])

@router.post("/parse-onboarding", response_model=OnboardingParseResponse)
async def parse_onboarding(req: OnboardingParseRequest):
    """
    Parses unstructured text during onboarding to extract business details.
    """
    try:
        parsed_data = await parse_onboarding_text(req.text)
        return OnboardingParseResponse(**parsed_data)
    except Exception as e:
        # Fallback empty response handled by Pydantic defaults
        import logging
        logging.getLogger(__name__).error(f"Error in parse_onboarding route: {e}")
        return OnboardingParseResponse()
