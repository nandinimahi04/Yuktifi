from sqlalchemy import Column, String, Float, ForeignKey, Integer, DateTime, Boolean
from app.core.db import Base
from app.models.core import uid


class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(String, primary_key=True, default=uid)
    location_id = Column(String, ForeignKey("locations.id"))
    category_id = Column(String, ForeignKey("business_categories.id"))
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False, default=0.0)
    longitude = Column(Float, nullable=False, default=0.0)
    estimated_scale = Column(Integer)
    source_id = Column(String, ForeignKey("data_sources.id"))
    confidence = Column(String, default='medium')
    last_verified = Column(DateTime)
    synthetic = Column(Boolean, default=False)
