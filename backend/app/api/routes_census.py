from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v2/census", tags=["census-evidence"])


@router.post("/population/ingest")
def ingest_population(payload: dict):
    from app.data_ingestion.census_population import ingest_to_evidence
    try:
        path = payload["path"]
        context = payload.get("location_context")
        if not context:
            raise ValueError("location_context is required; resolve the location first")
        return ingest_to_evidence(path, context)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=f"Missing field: {exc.args[0]}")
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
