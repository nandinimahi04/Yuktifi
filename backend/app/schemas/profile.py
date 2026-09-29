from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Any, List

class ProfileRequest(BaseModel):
    name: str = "Entrepreneur"
    age: Optional[int] = Field(30)
    gender: str = "male"
    social_category: str = "general"
    language: str = "en"
    location_input: str
    business_category: Optional[str] = None
    business_industry: Optional[str] = None
    business_idea: Optional[str] = Field(None, max_length=500)
    experience_level: Optional[str] = None
    business_experience: Optional[str] = None
    available_capital_inr: Optional[float] = None
    loan_intent: Optional[str] = "not_sure"

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, v: Any) -> str:
        if not v:
            return "male"
        s = str(v).strip().lower()
        if "fem" in s:
            return "female"
        if "male" in s:
            return "male"
        if "prefer" in s:
            return "prefer_not_to_say"
        return "other"

    @field_validator("social_category", mode="before")
    @classmethod
    def normalize_social_category(cls, v: Any) -> str:
        if not v:
            return "general"
        s = str(v).strip().lower()
        if s in ["sc", "st", "obc", "general", "minority"]:
            return s
        if s in ["other", "prefer_not_to_say", "prefer not to say"]:
            return "prefer_not_to_say"
        return "general"

    @field_validator("age", mode="before")
    @classmethod
    def normalize_age(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return 30
        try:
            val = int(v)
            if val < 1 or val > 120:
                return 30
            return val
        except (ValueError, TypeError):
            return 30

    @field_validator("business_idea", mode="before")
    @classmethod
    def validate_business_idea(cls, v: Any) -> Optional[str]:
        if v is not None:
            return str(v).strip()
        return v

    @field_validator("available_capital_inr", mode="before")
    @classmethod
    def normalize_capital(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return 75000.0
        try:
            val = float(v)
            return val if val > 0 else 75000.0
        except (ValueError, TypeError):
            return 75000.0

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
    alternatives: List[str] = []

class OnboardingParseRequest(BaseModel):
    text: str

class OnboardingParseResponse(BaseModel):
    business_category: Optional[str] = None
    location: Optional[str] = None
    capital_in_inr: Optional[int] = None
    experience_level: Optional[str] = None
