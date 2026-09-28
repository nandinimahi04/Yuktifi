from sqlalchemy import Column, String, DateTime, Integer, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.db import Base
from app.models.core import uid


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    social_category = Column(String, nullable=True)
    business_idea = Column(Text, nullable=True)
    experience_level = Column(String, nullable=True)
    available_capital_inr = Column(Float, nullable=True)
    loan_intent = Column(String, nullable=True)
    business_category = Column(String, nullable=True)
    language_pref = Column(String, default="en")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sessions = relationship("Session", back_populates="user")
