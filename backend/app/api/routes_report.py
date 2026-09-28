from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone
from app.schemas.report import ReportRequest, ReportResponse
from app.core.db import get_db

from app.reports.report_builder import generate_html_report

router = APIRouter()

@router.post("/report", response_model=ReportResponse)
def report(req: ReportRequest, db: DBSession = Depends(get_db)):
    try:
        html_content = generate_html_report(db, req.session_id)
        if "<p>Session not found.</p>" in html_content:
            raise ValueError(f"Session {req.session_id} not found")
        return ReportResponse(
            session_id=req.session_id,
            html_content=html_content,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
