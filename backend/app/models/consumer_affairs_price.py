from sqlalchemy import Column, String, Float, DateTime, Date
from sqlalchemy.sql import func
from app.core.db import Base
from app.models.core import uid

class ConsumerAffairsPrice(Base):
    __tablename__ = "consumer_affairs_prices"

    id = Column(String, primary_key=True, default=uid)
    commodity = Column(String(150), nullable=False)
    commodity_id = Column(String(100), nullable=True)
    market_centre = Column(String(150), nullable=False)
    state = Column(String(100), nullable=False)
    price_type = Column(String(30), default="retail")  # retail / wholesale
    price = Column(Float, nullable=False)
    unit = Column(String(50), default="INR/kg")
    observed_at = Column(Date, nullable=False)
    source = Column(String(100), default="Department of Consumer Affairs (PMS)")
    source_url = Column(String, nullable=True)
    quality = Column(String(30), default="Standard/FAQ")
    confidence = Column(String(20), default="HIGH")
    retrieved_at = Column(DateTime, server_default=func.now())
