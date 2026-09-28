from fastapi import APIRouter, HTTPException
from app.phase1.service import run_decision
from app.phase2.service import list_evidence, upsert_evidence
from app.phase1.dairy_demo import build_dairy_demo

router=APIRouter(prefix='/api/v2', tags=['YUKTI Phase 1/2'])

@router.post('/decision')
def decision(payload: dict):
    try: return run_decision(payload)
    except ValueError as e: raise HTTPException(status_code=422, detail=str(e))

@router.post('/evidence')
def evidence(payload: dict):
    try: return upsert_evidence(payload)
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@router.get('/evidence')
def evidence_list(geography: str|None=None, metric: str|None=None, limit: int=100):
    return {'records':list_evidence(geography, metric, limit)}


@router.post('/dairy-demo')
def dairy_demo(payload: dict | None = None):
    payload = payload or {}
    # `margin_capital` used to be defaulted straight to 100000 with no record of
    # that having happened. The figure then fed EMI, DSCR, payback and loan
    # sizing, so a caller who sent nothing received a complete-looking plan for
    # a margin they never declared. The default is kept (the endpoint is a demo
    # and its signature predates this check) but it is now declared as an
    # assumption in the response rather than passing as real input.
    margin_capital_supplied = 'margin_capital' in payload
    try:
        result = build_dairy_demo(
            location=payload.get('location', 'Akkalkot, Solapur, Maharashtra'),
            margin_capital=float(payload.get('margin_capital', 100000)),
            annual_interest_rate_pct=float(payload.get('annual_interest_rate_pct', 12.0)),
            tenure_months=int(payload.get('tenure_months', 60)),
            livestock_source=payload.get('livestock_source'),
            census_source=payload.get('census_source'),
        )
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    result['inputs_supplied'] = {'margin_capital': margin_capital_supplied}
    return result

@router.post('/livestock/ingest')
def livestock_ingest(payload: dict):
    from app.data_ingestion.livestock import ingest_to_evidence
    try:
        return ingest_to_evidence(
            payload['path'],
            district=payload['district'],
            block=payload['block'],
            village=payload.get('village'),
        )
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Missing field: {e.args[0]}")
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post('/dairy-demo/location-aware')
def dairy_demo_location_aware(payload: dict):
    """Run the dairy scenario only after deterministic canonical location resolution."""
    from app.location.service import resolve_location
    from app.location.context import build_location_context
    try:
        query = payload.get('location')
        lat = payload.get('lat')
        lng = payload.get('lng')
        resolved = resolve_location(query=query, lat=lat, lng=lng)
        if resolved.get('status') != 'resolved':
            return {
                'status': 'location_unresolved',
                'location_resolution': resolved,
                'next_action': 'Load an official LGD/Census-derived location master and retry.'
            }
        context = build_location_context(resolved)
        # Same disclosure as the plain demo route: this endpoint resolves the
        # location canonically, but it still assumes a ₹1 lakh margin when the
        # caller omits one, so the response says which fields were real.
        margin_capital_supplied = 'margin_capital' in payload
        result = build_dairy_demo(
            location=context['canonical_label'],
            margin_capital=float(payload.get('margin_capital', 100000)),
            annual_interest_rate_pct=float(payload.get('annual_interest_rate_pct', 12.0)),
            tenure_months=int(payload.get('tenure_months', 60)),
            livestock_source=payload.get('livestock_source'),
            census_source=payload.get('census_source'),
            canonical_location=context,
        )
        result['location_resolution'] = resolved
        result['location_context'] = context
        result['inputs_supplied'] = {'margin_capital': margin_capital_supplied}
        return result
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
