from sqlalchemy import Column, String, Enum
from app.core.db import Base
from app.models.core import uid, ConfidenceLevel


class ConfidenceTag(Base):
    __tablename__ = "confidence_tags"
    id = Column(String, primary_key=True, default=uid)
    referenced_entity_type = Column(String)
    referenced_entity_id = Column(String)
    level = Column(Enum(ConfidenceLevel))
    method_note = Column(String)
