from sqlalchemy import Column, String, Float, ForeignKey
from app.core.db import Base
from app.models.core import uid

class Price(Base):
    """Pricing data: observed, regional_benchmark, estimated_local, ai_suggestion."""
    __tablename__ = "prices"
    id = Column(String, primary_key=True, default=uid)
    location_id = Column(String, ForeignKey("locations.id"))
    category_id = Column(String, ForeignKey("business_categories.id"))
    price_type = Column(String, nullable=False) # e.g. 'observed', 'regional_benchmark', 'estimated_local', 'ai_suggestion'
    value = Column(Float, nullable=False)
    unit = Column(String)
    confidence = Column(String)
    source_id = Column(String, ForeignKey("data_sources.id"))
    transformation_note = Column(String)
