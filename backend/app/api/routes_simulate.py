from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.schemas.simulation import SimulateRequest, SimulateResponse
from app.engines.simulation_engine import run_simulation
from app.services.session_service import get_base_state
from app.core.db import get_db

from app.schemas.dynamic_simulator import SimulatorRequest, SimulatorResponse, EventInfo, DecisionInfo, FinancialImpact
from app.engines.simulator.simulator_engine import run_dynamic_simulation, event_engine
from app.ai.gemini_client import GeminiClient
from app.ai.prompts.simulator import SIMULATOR_NARRATIVE_PROMPT
import json

router = APIRouter()
gemini = GeminiClient()

@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest, db: DBSession = Depends(get_db)):
    try:
        base_state = get_base_state(db, req.session_id)
        result = run_simulation(
            base_state,
            req.revenue_delta_pct,
            req.cost_delta_pct,
            req.tenure_override_years,
            adjustments=req.to_adjustments(),
        )
        if "error" in result:
            raise HTTPException(status_code=409, detail=result["detail"])
        return StaticSimulateResponse(
            emi=result["emi"],
            dscr=result["dscr"],
            dscr_status=result["dscr_status"],
            break_even_units=result["break_even_units"],
            verdict=result["verdict"],
            net_profit=result["net_profit"],
            simulated_roi=result["simulated_roi"],
            survives_stress=result["survives_stress"],
            survives_stress_applicable=result["survives_stress_applicable"],
            applied_adjustments=result["applied_adjustments"],
            adjustments=result["adjustments"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/dynamic", response_model=SimulatorResponse)
async def simulate_dynamic(req: SimulatorRequest, db: DBSession = Depends(get_db)):
    # Prefer the session's own canonical model. Without it the simulator falls
    # back to a scalar model over the declared baseline, and its DSCR and ROI
    # are computed from revenue-minus-opex rather than from the full
    # projection - a lesser model whose numbers can legitimately differ from
    # the analysis screen. Asking for the session first is what keeps the two
    # screens telling the same story.
    canonical_input = None
    if req.session_id:
        canonical_input = get_base_state(db, req.session_id).get("canonical_input")

    # Compute the deterministic financial impact from the business's own
    # declared baseline. Nothing is assumed here: with no baseline the engine
    # returns an explicit abstention rather than a modelled answer.
    impact_dict = run_dynamic_simulation(
        req.month, req.cash_balance, req.active_events, req.decision,
        req.scenario_parameters, baseline=req.baseline,
        canonical_input=canonical_input,
    )

    # Identify event
    event = event_engine.get_event(req.active_events[0]) if req.active_events else None
    event_desc = event.title if event else "Normal business operations."

    # Risk level is derived from the computed cash position, not declared.
    # This response previously returned `risk_level="medium"` for every possible
    # outcome, so a business that ran its cash negative and one that flourished
    # were reported identically.
    final_cash = impact_dict.get("ending_cash_balance")
    if not impact_dict.get("available") or final_cash is None:
        risk_level = "unknown"
    elif final_cash < 0:
        risk_level = "high"
    else:
        starting = impact_dict.get("starting_cash_balance") or final_cash
        risk_level = "high" if final_cash < starting * 0.25 else "medium" if final_cash < starting * 0.75 else "low"

    # Narrative is optional. The model is asked to explain figures already
    # computed; it is not asked for a number.
    explanation = None
    if impact_dict.get("available"):
        prompt = SIMULATOR_NARRATIVE_PROMPT.format(
            event_description=event_desc,
            user_decision=req.decision,
            financial_impact=json.dumps(impact_dict, indent=2),
        )
        schema = {
            "type": "object",
            "properties": {
                "narrative": {"type": "string"},
                "advice": {"type": "string"},
            },
            "required": ["narrative", "advice"],
        }
        ai_resp = await gemini.generate_json_async(prompt, schema=schema)
        if ai_resp:
            narrative = (ai_resp.get("narrative") or "").strip()
            advice = (ai_resp.get("advice") or "").strip()
            parts = [narrative] if narrative else []
            if advice:
                parts.append(f"Advice: {advice}")
            explanation = "\n\n".join(parts) or None

    return SimulatorResponse(
        month=req.month,
        event=EventInfo(id=event.event_id if event else "none", title=event_desc),
        decision=DecisionInfo(selected=req.decision),
        financial_impact=FinancialImpact(**impact_dict),
        risk_level=risk_level,
        yukti_score=None,
        score_available=False,
        score_note=(
            "No composite score is shown for this scenario. Scoring requires the full canonical "
            "financial projection, which the dynamic simulator does not carry. Use the What-If "
            "simulator for a scored result. The cash figures below are computed deterministically "
            "and are not affected by this."
        ),
        ai_explanation=explanation,
        next_month_available=True,
    )
