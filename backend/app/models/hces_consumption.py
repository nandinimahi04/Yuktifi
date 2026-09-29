from sqlalchemy import Column, String, Float, Boolean, DateTime, Date
from sqlalchemy.sql import func
from app.core.db import Base
from app.models.core import uid

class HCESConsumption(Base):
    __tablename__ = "hces_consumption"

    id = Column(String, primary_key=True, default=uid)
    survey_year = Column(String(20), nullable=False, default="2023-24")
    state_code = Column(String(20), nullable=True)
    state_name = Column(String(100), nullable=False)
    sector = Column(String(20), nullable=False)  # rural / urban / all
    metric = Column(String(100), nullable=False)  # MPCE / expenditure_share / quantity
    commodity_group = Column(String(150), nullable=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False, default="INR/person/month")
    source = Column(String(100), default="MoSPI HCES 2023-24 (Report No. 592)")
    source_url = Column(String, nullable=True)
    observed_from = Column(Date, nullable=True)
    observed_to = Column(Date, nullable=True)
    is_estimate = Column(Boolean, default=False)
    confidence = Column(String(20), default="HIGH")
    retrieved_at = Column(DateTime, server_default=func.now())
