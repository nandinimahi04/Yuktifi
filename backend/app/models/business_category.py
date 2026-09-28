from sqlalchemy import Column, String
from app.core.db import Base
from app.models.core import uid


class BusinessCategory(Base):
    __tablename__ = "business_categories"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, unique=True)
    parent_category = Column(String, nullable=True)
    cost_profile_ref = Column(String, nullable=True)
    description = Column(String, nullable=True)
