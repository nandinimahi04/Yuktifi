from sqlalchemy import Column, String, Float, Integer, DateTime
from datetime import datetime, timezone
from app.core.db import Base
from app.models.core import uid


class GovernmentScheme(Base):
    __tablename__ = "government_schemes"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String)
    min_project_cost = Column(Float)
    max_project_cost = Column(Float)
    financing_pct = Column(Float)
    max_loan_amount = Column(Float)
    interest_rate = Column(Float)
    tenure_months = Column(Integer)
    moratorium_months = Column(Integer)
    source_url = Column(String)
    version = Column(String)
    effective_from = Column(DateTime, nullable=True)
    last_verified = Column(DateTime, default=lambda: datetime.now(timezone.utc))
