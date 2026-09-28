from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from enum import Enum

class ProfileRequest(BaseModel):
    name: str
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Literal["male", "female", "other", "prefer_not_to_say"]
    social_category: Literal["general", "obc", "sc", "st", "minority", "prefer_not_to_say"]
    language: str = "en"
    location_input: str
    business_category: Optional[str] = None
    business_idea: Optional[str] = Field(None, max_length=500)
    experience_level: Optional[str] = None
    available_capital_inr: Optional[float] = Field(None, gt=0)
    loan_intent: Optional[Literal["no", "yes", "not_sure"]] = None

    @validator("business_idea")
    def validate_business_idea(cls, v):
        if v is not None:
            return v.strip()
        return v

class ProfileResponse(BaseModel):
    user_id: str
    location_id: str
    location_name: str
    state: str
    lat: float
    lng: float
    data_richness: str

class BusinessMatchRequest(BaseModel):
    text: str

class BusinessMatchResponse(BaseModel):
    detected_business: Optional[str] = None
    category: Optional[str] = None
    confidence: float = 0.0
    alternatives: list[str] = []

class OnboardingParseRequest(BaseModel):
    text: str

class OnboardingParseResponse(BaseModel):
    business_category: Optional[str] = None
    location: Optional[str] = None
    capital_in_inr: Optional[int] = None
    experience_level: Optional[str] = None
