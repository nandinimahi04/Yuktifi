from sqlalchemy import Column, String, Float, ForeignKey, DateTime
from datetime import datetime
from app.core.db import Base
from app.models.core import uid


class MarketMetric(Base):
    """Stores computed market metrics for a location+category pair."""
    __tablename__ = "market_metrics"
    id = Column(String, primary_key=True, default=uid)
    location_id = Column(String, ForeignKey("locations.id"))
    category_id = Column(String, ForeignKey("business_categories.id"))
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String)
    confidence = Column(String)
    source_id = Column(String, ForeignKey("data_sources.id"))
    effective_date = Column(DateTime)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    transformation_note = Column(String)
