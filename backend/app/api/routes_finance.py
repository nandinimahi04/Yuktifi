from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.schemas.finance import FinanceRequest, FinanceResponse
from app.services.session_service import compute_full_financials
from app.core.db import get_db

router = APIRouter()

@router.post("/calculate-finance", response_model=FinanceResponse)
def calculate_finance(req: FinanceRequest, db: DBSession = Depends(get_db)):
    try:
        result = compute_full_financials(db, req.session_id)
        return FinanceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
