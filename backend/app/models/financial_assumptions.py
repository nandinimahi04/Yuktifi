from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, DateTime, JSON
from datetime import datetime, timezone
from app.core.db import Base
from app.models.core import uid


class ProjectFinancialAssumptions(Base):
    __tablename__ = "project_financial_assumptions"

    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"), unique=True, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    
    # Financial Inputs
    project_cost = Column(Float, nullable=False)
    own_capital = Column(Float, nullable=False)
    loan_amount = Column(Float, nullable=False)
    
    # Revenue & Production Inputs
    is_direct_revenue_mode = Column(Boolean, default=False, nullable=False)
    monthly_revenue = Column(Float, nullable=False)
    selling_price = Column(Float, default=0.0, nullable=False)
    units_per_day = Column(Float, default=0.0, nullable=False)
    operating_days = Column(Integer, default=30, nullable=False)
    
    # Cost Inputs
    variable_cost_per_unit = Column(Float, default=0.0, nullable=False)
    monthly_expenses = Column(Float, nullable=False)
    
    # Financing Inputs
    interest_rate_annual_pct = Column(Float, default=9.0, nullable=False)
    loan_tenure_months = Column(Integer, default=60, nullable=False)
    moratorium_months = Column(Integer, default=0, nullable=False)
    tax_rate_pct = Column(Float, nullable=True)
    
    # Timestamps & Metadata
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class FinancialAssumptionsAudit(Base):
    __tablename__ = "financial_assumptions_audit"

    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)
    version_from = Column(Integer, nullable=False)
    version_to = Column(Integer, nullable=False)
    changed_by = Column(String, default="user", nullable=False)
    old_assumptions = Column(JSON, nullable=True)
    new_assumptions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
