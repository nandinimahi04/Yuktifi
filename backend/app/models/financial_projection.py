from sqlalchemy import Column, String, Float, ForeignKey
from app.core.db import Base
from app.models.core import uid


class FinancialProjection(Base):
    __tablename__ = "financial_projections"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    monthly_revenue = Column(Float)
    monthly_opex = Column(Float)
    net_profit = Column(Float)
    break_even_units = Column(Float)
    dscr = Column(Float)
    roi = Column(Float)
    monthly_emi = Column(Float, nullable=True)
    monthly_interest = Column(Float, nullable=True)
    financing_gap = Column(Float, nullable=True)
    payback_months = Column(Float, nullable=True)
