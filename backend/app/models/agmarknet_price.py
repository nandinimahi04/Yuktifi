from sqlalchemy import Column, String, Float, DateTime, Date
from sqlalchemy.sql import func
from app.core.db import Base
from app.models.core import uid

class AgmarknetPrice(Base):
    __tablename__ = "agmarknet_prices"

    id = Column(String, primary_key=True, default=uid)
    commodity = Column(String(150), nullable=False)
    commodity_id = Column(String(100), nullable=True)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=True)
    market = Column(String(150), nullable=False)
    variety = Column(String(150), nullable=True)
    grade = Column(String(100), default="FAQ")
    arrival_date = Column(Date, nullable=False)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    modal_price = Column(Float, nullable=False)
    unit = Column(String(50), default="INR/quintal")
    source = Column(String(100), default="AGMARKNET / eNAM (MoA)")
    source_url = Column(String, nullable=True)
    confidence = Column(String(20), default="HIGH")
    retrieved_at = Column(DateTime, server_default=func.now())
