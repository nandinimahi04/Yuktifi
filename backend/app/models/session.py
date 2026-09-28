from sqlalchemy import Column, String, Float, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.db import Base
from app.models.core import uid


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("margin_capital > 0"),)
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.id"))
    location_id = Column(String, ForeignKey("locations.id"))
    margin_capital = Column(Float)
    category_id = Column(String, ForeignKey("business_categories.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="sessions")
    location = relationship("Location")
    category = relationship("BusinessCategory")
