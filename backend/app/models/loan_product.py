from sqlalchemy import Column, String, Float, ForeignKey
from app.core.db import Base
from app.models.core import uid


class LoanProduct(Base):
    __tablename__ = "loan_products"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    project_cost = Column(Float)
    loan_amount = Column(Float)
    beneficiary_contribution = Column(Float)
    matched_scheme_id = Column(String, ForeignKey("government_schemes.id"), nullable=True)
