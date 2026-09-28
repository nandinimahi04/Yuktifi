from sqlalchemy import Column, String, DateTime
from app.core.db import Base
from app.models.core import uid


class Source(Base):
    __tablename__ = "data_sources"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, nullable=False)
    url = Column(String)
    owner_org = Column(String)
    license = Column(String)
    reliability = Column(String)
