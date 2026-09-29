from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.schemas.scheme import (
    SchemeMatchRequest,
    SchemeMatchResponse,
    SchemeEvaluationRequest,
    SchemeEvaluationResponse,
)
from app.engines.scheme_engine import match_scheme, SCHEMES, NOT_EVALUATED, DISCLAIMER
from app.core.db import get_db

router = APIRouter()


@router.get("/schemes")
def list_schemes():
    """
    The rule table, with the fields a user must not treat as verified.

    Previously this returned the bare dict, so `rate: 6.5` reached the client
    with no rule id, no version, no effective date and no indication that
    nothing in this repository had re-checked it against a circular.

    The scheme display name, the per-rule verification block and the
    effective-date state are merged in here. They are not new claims: the name is
    the SCHEMES key, the verification block is the same RULE_VERIFICATION the
    match endpoint returns, and the effective-date state is derived from the
    `effective_from` the rules already carry. A consumer that rendered a scheme
    card from this response without them had to invent them.
    """
    from app.engines.scheme_engine import RULE_VERIFICATION

    return {
        "schemes": [
            {
                "scheme_name": name,
                **rule,
                "implemented": rule["implemented"],
                "evaluation_status": (
                    "ROUTED_BY_THIS_BUILD" if rule["implemented"] else "NOT_EVALUATED"
                ),
                "not_evaluated_reason": NOT_EVALUATED.get(name),
                "rule_verification": RULE_VERIFICATION,
                "effective_date_state": (
                    "DATED" if rule.get("effective_from") else "UNDATED_IN_THIS_REPOSITORY"
                ),
            }
            for name, rule in SCHEMES.items()
        ],
        "verification": {
            "status": RULE_VERIFICATION["status"],
            "note": RULE_VERIFICATION["note"],
        },
        "disclaimer": DISCLAIMER,
    }


@router.post("/match-scheme", response_model=SchemeMatchResponse)
def match(req: SchemeMatchRequest, db: DBSession = Depends(get_db)):
    """
    Route a project to a scheme band.

    The applicant's own contribution is taken from the session when the request
    does not carry it. The session_id was previously required and then dropped on
    the floor, so this endpoint could never compute the funding gap and always
    answered max_loan=None.
    """
    from app.models import Session

    own_contribution = req.own_contribution
    project_cost = req.project_cost

    session = db.query(Session).filter(Session.id == req.session_id).first()
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Session {req.session_id} not found. A scheme match needs a real "
                f"session: the funding gap depends on the applicant's declared capital."
            ),
        )

    if own_contribution is None:
        margin = getattr(session, "margin_capital", None)
        own_contribution = float(margin) if margin is not None else None

    if project_cost is None:
        # There is nothing to fall back to: neither Session nor FinancialProjection
        # stores a project cost (the columns are margin_capital, revenue, opex,
        # profit, break-even, DSCR, ROI and the EMI). Defaulting to 0 would route
        # the business into the smallest scheme band on a fabricated number, so
        # the engine is called with None and abstains with a stated reason.
        return SchemeMatchResponse(
            **match_scheme(None, own_contribution=own_contribution).to_dict()
        )

    return SchemeMatchResponse(**match_scheme(project_cost, own_contribution=own_contribution).to_dict())


@router.post("/schemes/evaluate", response_model=SchemeEvaluationResponse)
def evaluate_schemes(
    req: SchemeEvaluationRequest,
    db: DBSession = Depends(get_db)
):
    """
    RAG-grounded multi-scheme evaluator tailored to applicant's profile and enterprise plan.
    Calculates exact subsidy %, loan amount, own margin requirement, and attaches
    official RAG citations.
    """
    from app.engines.scheme_evaluator import evaluate_applicant_schemes
    from app.models import Session, User

    social_cat = req.social_category or "General"
    gender = req.gender or "Male"
    loc_type = req.location_type or "Rural"
    state = req.state or "Maharashtra"
    district = req.district or "Solapur"
    cat_id = req.category_id or "retail_kirana"
    proj_cost = req.project_cost or 200000.0
    own_contrib = req.own_contribution

    if req.session_id:
        session = db.query(Session).filter(Session.id == req.session_id).first()
        if session:
            if session.category_id:
                cat_id = session.category_id
            if session.margin_capital and own_contrib is None:
                own_contrib = float(session.margin_capital)
            if session.user_id:
                user = db.query(User).filter(User.id == session.user_id).first()
                if user:
                    if getattr(user, "social_category", None):
                        social_cat = str(user.social_category)
                    elif getattr(user, "caste_category", None):
                        social_cat = str(user.caste_category)
                    if getattr(user, "gender", None):
                        gender = str(user.gender)
                    if getattr(user, "location_type", None):
                        loc_type = str(user.location_type)
                    if getattr(user, "state", None):
                        state = str(user.state)
                    if getattr(user, "district", None):
                        district = str(user.district)

    result = evaluate_applicant_schemes(
        social_category=social_cat,
        gender=gender,
        location_type=loc_type,
        state=state,
        district=district,
        category_id=cat_id,
        project_cost=proj_cost,
        own_contribution=own_contrib,
    )

    return SchemeEvaluationResponse(**result)


@router.get("/schemes/evaluate", response_model=SchemeEvaluationResponse)
def evaluate_schemes_get(
    social_category: str = "General",
    gender: str = "Male",
    location_type: str = "Rural",
    state: str = "Maharashtra",
    district: str = "Solapur",
    category_id: str = "retail_kirana",
    project_cost: float = 200000.0,
    own_contribution: Optional[float] = None,
    session_id: Optional[str] = None,
    db: DBSession = Depends(get_db)
):
    """GET endpoint for simple scheme evaluation lookup."""
    req = SchemeEvaluationRequest(
        session_id=session_id,
        social_category=social_category,
        gender=gender,
        location_type=location_type,
        state=state,
        district=district,
        category_id=category_id,
        project_cost=project_cost,
        own_contribution=own_contribution,
    )
    return evaluate_schemes(req=req, db=db)

