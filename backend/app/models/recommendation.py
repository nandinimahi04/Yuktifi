from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum, JSON
from datetime import datetime, timezone
from app.core.db import Base
from app.models.core import uid, VerdictEnum


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    yukti_score = Column(Float)
    verdict = Column(Enum(VerdictEnum))
    dimension_breakdown_json = Column(JSON)
    confidence_multiplier = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
