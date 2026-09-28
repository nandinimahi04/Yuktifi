from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Enum
from datetime import datetime, timezone
from app.core.db import Base
from app.models.core import uid, VerdictEnum


class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    revenue_delta_pct = Column(Float, default=0)
    cost_delta_pct = Column(Float, default=0)
    tenure_override = Column(Integer, nullable=True)
    resulting_dscr = Column(Float)
    resulting_verdict = Column(Enum(VerdictEnum))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
