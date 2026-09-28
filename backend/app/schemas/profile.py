from pydantic import BaseModel
from typing import Optional


class ProfileRequest(BaseModel):
    name: str
    language: str = "en"
    location_input: str  # e.g. "Solapur" — resolved by location_service


class ProfileResponse(BaseModel):
    user_id: str
    location_id: str
    location_name: str
    state: str
    lat: float
    lng: float
    data_richness: str


class OnboardingParseRequest(BaseModel):
    text: str


class OnboardingParseResponse(BaseModel):
    business_category: Optional[str] = None
    location: Optional[str] = None
    capital_in_inr: Optional[int] = None
    experience_level: Optional[str] = None
