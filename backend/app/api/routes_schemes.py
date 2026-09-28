from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.schemas.scheme import SchemeMatchRequest, SchemeMatchResponse
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
