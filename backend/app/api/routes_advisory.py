from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ConfigDict

from app.advisory.national import run_advisory
from app.advisory.templates.registry import list_templates
from app.advisory.explanation import build_explanation
from app.advisory.report import build_report, build_html_report
from app.advisory.security import status
from app.advisory.runs import save, get, recent

router = APIRouter(prefix="/api/v3", tags=["YUKTIFI Advisory"])

class AdvisoryRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    business_id: str = Field(default="dairy", min_length=2)
    location: dict[str, Any] = Field(default_factory=dict)
    promoter_margin: float = Field(gt=0)
    monthly_units: float | None = Field(default=None, ge=0)
    price_per_unit: float | None = Field(default=None, gt=0)
    variable_cost_per_unit: float | None = Field(default=None, ge=0)
    fixed_cost_monthly: float | None = Field(default=None, ge=0)
    annual_rate_pct: float = Field(default=12, ge=0, le=100)
    tenure_months: int = Field(default=60, ge=1, le=360)
    spatial_population: float | None = Field(default=None, ge=0)
    mapped_competitors: list[dict[str, Any]] | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    demand_rate_per_1000_people: float | None = Field(default=None, ge=0)
    use_demo_assumptions: bool = False
    financing_pct: float = Field(default=0.90, gt=0, lt=1)

@router.get("/business-templates")
def business_templates():
    return {"templates": list_templates()}

@router.post("/advisory")
def advisory(payload: AdvisoryRequest):
    try:
        result = run_advisory(**payload.model_dump())
        result["explanation"] = build_explanation(result)
        save(result)
        return result
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

@router.post("/report")
def report(payload: AdvisoryRequest):
    return build_report(advisory(payload))

@router.post("/report/html", response_class=HTMLResponse)
def report_html(payload: AdvisoryRequest):
    return build_html_report(advisory(payload))

@router.get("/security/status")
def security_status():
    return status()


@router.get("/advisory/{run_id}")
def advisory_run(run_id: str):
    result = get(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Advisory run not found")
    return result

@router.get("/advisory-runs")
def advisory_runs(limit: int = 20):
    return {"runs": recent(limit)}
