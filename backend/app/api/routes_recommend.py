from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.schemas.recommendation import (
    DimensionScore,
    DimensionScores,
    RecommendRequest,
    RecommendResponse,
)
from app.services.session_service import get_base_state
from app.engines.recommendation_engine import compute_yukti_score
from app.engines.scoring_engine import compute_all_dimensions, generate_next_steps
from app.core.db import get_db

router = APIRouter()

#: Keys in the score card's dimension map, in the order the schema declares them.
_DIMENSION_KEYS = (
    "financial_viability",
    "repayment_capacity",
    "market_opportunity",
    "capital_efficiency",
    "risk_exposure",
)


@router.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest, db: DBSession = Depends(get_db)):
    try:
        base_state = get_base_state(db, req.session_id)

        from app.models import FinancialProjection

        projection = (
            db.query(FinancialProjection)
            .filter(FinancialProjection.session_id == req.session_id)
            .first()
        )

        # No projection means no financial evidence. The previous code invented
        # `dscr = 1.0` and `roi = 15.0` in that case. A DSCR of exactly 1.0 is the
        # textbook borderline case - cash flow just covering debt service - so
        # every recommendation for a business with no data at all was issued
        # with precisely borderline repayment capacity and a healthy 15% return.
        if projection is not None:
            dscr = projection.dscr
            roi = projection.roi
            # The canonical engine reports negative CFADS as dscr=None with a
            # status, but FinancialProjection is a flat column, so a negative
            # value can still be stored. A negative ratio is not a coverage
            # figure; it is re-derived here as an absence.
            if dscr is not None and dscr < 0:
                dscr_status = "NEGATIVE_CFADS"
                dscr = None
            elif dscr is not None:
                dscr_status = "AVAILABLE"
            else:
                dscr_status = "NOT_COMPUTED"
            roi_status = "AVAILABLE" if roi is not None else "NOT_COMPUTED"

            # Everything the projection already holds is passed to the scoring
            # engine. Not doing this was leaving three of five dimensions
            # abstaining while the figures sat unused in the same row.
            monthly_revenue = projection.monthly_revenue
            net_profit = projection.net_profit
            if monthly_revenue and net_profit is not None:
                net_margin = round(net_profit / monthly_revenue * 100.0, 2)
            else:
                net_margin = None
            break_even_units = projection.break_even_units
        else:
            dscr = None
            dscr_status = "UNAVAILABLE_NO_PROJECTION"
            roi = None
            roi_status = "UNAVAILABLE_NO_PROJECTION"
            net_margin = None
            break_even_units = None

        # One card, computed from this request's evidence, is the single source
        # for the score, the per-dimension detail and the next steps.
        #
        # The score used to be computed from `base_state["dimension_scores"]` -
        # the card cached on the session at an earlier point in the flow - while
        # the fresh card was built only to generate next steps. The response
        # therefore showed a score and a set of reasons describing two different
        # states of the business, and editing a projection's DSCR could leave the
        # headline number unmoved while the detail beneath it changed.
        card = compute_all_dimensions(
            roi=roi,
            dscr=dscr,
            net_margin=net_margin,
            break_even_units=break_even_units,
            monthly_units=None,
            competitor_count=None,
            population=None,
            overall_confidence=base_state.get("overall_confidence"),
            threats_count=None,
            has_debt=bool(projection is not None and projection.monthly_emi),
        )
        card_dict = card.to_dict()

        score_result = compute_yukti_score(
            # The whole card, not `card_dict["dimensions"]`: _as_dimension_map
            # unwraps the nested {"dimensions": {...}} shape and takes each
            # entry's "score", while passing the inner dict hands it a
            # {key: {score, known, ...}} mapping it tries to cast to float.
            dimension_scores=card_dict,
            confidence_multiplier=base_state["confidence_multiplier"],
            dscr=dscr,
        )

        # Per-dimension detail, so the user can see which dimensions are real.
        by_key = {d.key: d for d in getattr(card, "dimensions", [])}
        dimension_payload = {
            key: DimensionScore(
                score=by_key[key].score if key in by_key else None,
                known=by_key[key].known if key in by_key else False,
                label=by_key[key].label if key in by_key else key,
                reason=by_key[key].reason if key in by_key else "Not computed.",
            )
            for key in _DIMENSION_KEYS
        }

        next_steps = generate_next_steps(card_dict, {}, {})

        return RecommendResponse(
            session_id=req.session_id,
            yukti_score=score_result.final_score,
            raw_score=score_result.raw_score,
            confidence_multiplier=base_state["confidence_multiplier"],
            verdict=score_result.verdict,
            dimension_scores=DimensionScores(**dimension_payload),
            dscr=dscr,
            dscr_status=dscr_status,
            roi=roi,
            roi_status=roi_status,
            next_steps=next_steps,
            confidence="MEDIUM" if score_result.final_score is not None else "UNAVAILABLE",
            unscored_dimensions=score_result.unscored,
            note=score_result.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
