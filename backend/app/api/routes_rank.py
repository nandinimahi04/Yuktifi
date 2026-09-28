"""POST /rank-opportunities — evaluate and rank all business categories."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.schemas.ranking import RankRequest, RankResponse, RankedCategory
from app.core.db import get_db
from app.services.ranking_service import rank_opportunities

router = APIRouter()


@router.post("/rank-opportunities", response_model=RankResponse)
def rank(req: RankRequest, db: DBSession = Depends(get_db)):
    if req.margin_capital <= 0:
        raise HTTPException(status_code=400, detail="Margin capital must be greater than 0.")

    rankings = rank_opportunities(req.location_id, req.margin_capital)

    # Ensure a session exists in DB for this flow
    from app.models import Session

    session = db.query(Session).filter(Session.id == req.session_id).first()
    if not session:
        session = Session(
            id=req.session_id,
            user_id=req.session_id,
            location_id=req.location_id,
            margin_capital=req.margin_capital,
        )
        db.add(session)
    else:
        session.margin_capital = req.margin_capital
        session.location_id = req.location_id
    db.commit()

    ranked_count = sum(1 for r in rankings if r.get("yukti_score") is not None)

    # No scheme is matched at the top level.
    #
    # This previously called `compute_project_cost(req.margin_capital)` and then
    # `match_scheme(pc)`, i.e. it treated the entrepreneur's own savings as if
    # they were the total project cost. Schemes are banded on project cost, so
    # that could surface a scheme the business does not actually qualify for -
    # the entrepreneur has ₹60,000 of margin and the scheme needs ₹8-20 lakh of
    # project cost, but the request answered "matched". Scheme matching per
    # category, against each category's real project cost, is done in
    # ranking_service and reported on each row.
    return RankResponse(
        session_id=req.session_id,
        rankings=[RankedCategory(**r) for r in rankings],
        ranked_count=ranked_count,
        unranked_count=len(rankings) - ranked_count,
        scheme_matched=False,
        scheme_name=None,
        scheme_status="Not evaluated",
        scheme_note=(
            "Schemes are matched against each category's declared project cost, not "
            "against the margin capital. See the per-category scheme_status field."
        ),
    )
