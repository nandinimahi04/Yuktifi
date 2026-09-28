from sqlalchemy import Column, String, Float, Enum
from app.core.db import Base
from app.models.core import uid, AdminLevel


class Location(Base):
    __tablename__ = "locations"
    id = Column(String, primary_key=True, default=uid)
    village = Column(String, nullable=True)
    block = Column(String, nullable=True)
    district = Column(String)
    state = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    admin_level = Column(Enum(AdminLevel))
    data_richness = Column(String, default="rich")  # "rich" | "sparse" — drives confidence
