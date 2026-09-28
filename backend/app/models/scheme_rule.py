from sqlalchemy import Column, String, Float, ForeignKey
from app.core.db import Base
from app.models.core import uid


class SchemeRule(Base):
    """Eligibility rules for a government scheme — deterministic conditions."""
    __tablename__ = "scheme_rules"
    id = Column(String, primary_key=True, default=uid)
    scheme_id = Column(String, ForeignKey("government_schemes.id"))
    rule_type = Column(String)             # e.g. "project_cost_range", "category_eligible"
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    string_value = Column(String, nullable=True)
    description = Column(String, nullable=True)
