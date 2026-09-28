"""
POST /generate — business plan.

The plan is a hybrid document: the deterministic engine owns every number, and
the language model owns the prose. That split is enforced here rather than
requested in a prompt.

What this route used to do: it sent a prompt asking for a full business plan
with no schema, and constructed the response with `BusinessPlan(**response)`.
So Gemini authored, among other things:

* `project_cost.total_project_cost / own_contribution / financing_required`
* `profitability_analysis.roi / dscr / break_even`
* `revenue_projection`, `cash_flow_projection`, `operating_expenses`,
  `financial_structure`, `financing_readiness` - all free-form dicts
* `data_sources`, i.e. the model wrote its own `source` and `confidence` for
  each field

That last one is the most serious. A fabricated figure accompanied by
`{"value": 450000, "source": "Census 2011", "confidence": "High"}` is not
merely wrong, it is a forged citation, and a bank officer reading the document
has no way to detect it. Pydantic validated the *shape* of the response, not
the truth of any value; the comment claiming "strictly typed Pydantic output
validation ensures safety" was not accurate.

The numeric sections are now computed by `compute_canonical_financials` from the
declared inputs, and the model's response is stripped of every numeric field
before it reaches the client. Prose fields are still model-written, because
prose is the part a language model is actually for.

`DataSource` entries are attached by the server from the declared inputs, so
every citation in the document points at something real.
"""
from typing import Any, Dict, List, Optional
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.gemini_client import GeminiClient
from app.ai.context_builder import ContextBuilder
from app.ai.prompts.business_plan import BUSINESS_PLAN_SYSTEM_PROMPT
from app.schemas.business_plan import (
    BusinessPlan,
    DataSource,
    ProjectCost,
    ProfitabilityAnalysis,
    ProposalMetadata,
)
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)

router = APIRouter()
gemini = GeminiClient()
context_builder = ContextBuilder()

#: Sections the engine owns. Anything the model returns for these is discarded.
_NUMERIC_SECTIONS = (
    "project_cost",
    "profitability_analysis",
    "revenue_projection",
    "cash_flow_projection",
    "operating_expenses",
    "financial_structure",
    "financing_readiness",
    "scheme_information",
    "data_sources",
    "infrastructure_and_equipment",
    "key_metrics",
    "proposal_metadata",
)

#: Sections the model may write. Prose only: the engine owns every number.
_NARRATIVE_SECTIONS = (
    "executive_summary",
    "entrepreneur_profile",
    "proposed_business",
    "local_market_analysis",
    "competition_analysis",
    "products_and_services",
    "risk_analysis",
    "swot_analysis",
    "marketing_strategy",
    "implementation_plan",
    "ninety_day_action_plan",
    "required_documents",
    "assumptions",
    "conclusion",
)


class BusinessPlanRequest(BaseModel):
    location: str
    category: str
    market_data: Dict[str, Any] = {}
    financial_data: Dict[str, Any] = {}
    risk_data: Dict[str, Any] = {}


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _run_canonical(financial_data: Dict[str, Any]) -> Any:
    """
    Compute the numeric sections from the declared inputs.

    Returns None when the unit economics needed to model the business are not
    present, so that the plan reports the gap rather than carrying model-invented
    figures.
    """
    units = _num(financial_data.get("monthly_units"))
    price = _num(financial_data.get("price_per_unit") or financial_data.get("selling_price"))
    variable = _num(
        financial_data.get("variable_cost_per_unit")
        or financial_data.get("variable_cost_monthly")
    )
    fixed = _num(financial_data.get("fixed_cost_monthly"))

    if not units or not price or variable is None or fixed is None:
        return None

    return compute_canonical_financials(
        CanonicalFinancialInput(
            business_type=financial_data.get("category", "Business"),
            products=[
                ProductItem(
                    name="Primary line",
                    units_per_month=units,
                    selling_price=price,
                    variable_cost_per_unit=variable,
                )
            ],
            # `fixed_cost_monthly` is an undifferentiated aggregate, so it is
            # carried in `other` rather than `rent` - labelling total fixed cost
            # as rent would put a specific, wrong cost line in a bank document.
            opex=OpexBreakdown(other=fixed),
            own_capital=_num(financial_data.get("own_capital")) or 0.0,
            total_project_cost=_num(financial_data.get("total_project_cost")),
            debt_amount=_num(financial_data.get("debt_amount")) or 0.0,
            interest_rate_annual_pct=_num(financial_data.get("interest_rate_annual_pct")) or 0.0,
            tenure_months=int(_num(financial_data.get("tenure_months")) or 60),
            tax_rate_pct=_num(financial_data.get("tax_rate_pct")),
        )
    )


def _proposal_id(req: BusinessPlanRequest) -> str:
    """
    A stable, reproducible identifier for this exact plan request.

    Not a UUID: a bank officer comparing two plans for the same business should
    see the same ID, and re-running an unchanged plan should not mint a new
    document identity.
    """
    material = "|".join(
        str(x)
        for x in (
            req.location.strip().lower(),
            req.category.strip().lower(),
            *(f"{k}={v}" for k, v in sorted(req.financial_data.items())),
        )
    )
    return "YKT-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:12].upper()


def _data_confidence(sources: List[DataSource], canonical: Any) -> str:
    """
    Confidence in the plan's own inputs, stated by the server.

    Every figure the user supplied is a declaration. Nothing in this pipeline
    verifies an applicant's capital, prices or costs against a primary source,
    so the honest rating is capped below "verified" no matter how complete the
    form is. Previously the model wrote this field and could rate its own
    fabrications "High".
    """
    if canonical is None:
        return "INSUFFICIENT_DATA"
    if not sources:
        return "NO_DECLARED_INPUTS"
    return "DECLARED_NOT_VERIFIED"


def _server_data_sources(financial_data: Dict[str, Any]) -> List[DataSource]:
    """
    Provenance for the declared inputs, written by the server.

    This replaces the model's own citations. Every entry is either a value the
    applicant supplied (USER_SUPPLIED) or a figure this engine computed
    (DERIVED), so a reader can tell exactly which is which.
    """
    out: List[DataSource] = []
    for key, value in financial_data.items():
        if _num(value) is None:
            continue
        out.append(
            DataSource(
                field=key,
                value=value,
                source="Applicant declaration" if key not in (
                    "total_project_cost", "debt_amount", "own_capital"
                ) else "Applicant declaration (financing)",
                confidence="DECLARED_NOT_VERIFIED",
                source_kind="USER_SUPPLIED",
                note=(
                    "Supplied by the applicant. Not independently verified by this system, and "
                    "a scheme or lender will require documentary evidence."
                ),
            )
        )
    return out


@router.post("/generate", response_model=BusinessPlan)
async def generate_business_plan(req: BusinessPlanRequest):
    context = context_builder.build_comprehensive_context(
        req.location, req.category, req.market_data, req.financial_data, req.risk_data
    )
    prompt = BUSINESS_PLAN_SYSTEM_PROMPT.format(context=context)

    response = await gemini.generate_json_async(prompt)

    if not response:
        raise HTTPException(
            status_code=503,
            detail=(
                "Business plan narrative is unavailable: the language model was not reachable. "
                "No partial plan is issued, because the deterministic sections alone do not "
                "constitute a plan, and a plan with model-invented numbers is worse than none."
            ),
        )

    # Strip every numeric section from the model response before it is validated.
    # Anything the model produced for these keys is discarded, not merged.
    narrative = {k: v for k, v in response.items() if k in _NARRATIVE_SECTIONS}
    dropped = sorted(set(response) & set(_NUMERIC_SECTIONS))

    canonical = _run_canonical(req.financial_data)

    if canonical is not None:
        project_cost = ProjectCost(
            total_project_cost=canonical.total_project_cost,
            own_contribution=canonical.own_capital,
            financing_required=canonical.debt_amount,
            financing_gap=canonical.financing_gap,
        )
        profitability = ProfitabilityAnalysis(
            roi=canonical.roi_on_total_project_pct,
            dscr=canonical.dscr,
            dscr_status=canonical.dscr_status,
            break_even=canonical.break_even_units_monthly,
            net_margin_pct=canonical.net_margin_pct,
            payback_months=canonical.payback_months,
            payback_status=canonical.payback_status,
            npv=canonical.npv,
            economic_viability=canonical.economic_viability,
        )
        revenue_projection = {
            "monthly_revenue": canonical.monthly_revenue,
            "annual_revenue": canonical.annual_revenue,
            "monthly_units": _num(req.financial_data.get("monthly_units")),
            "price_per_unit": _num(req.financial_data.get("price_per_unit")),
        }
        operating_expenses = {
            "monthly_variable_cost": canonical.monthly_variable_costs,
            "monthly_fixed_cost": canonical.monthly_opex,
            "monthly_operating_profit": canonical.monthly_ebitda,
            "tax_status": canonical.tax_status,
        }
        cash_flow_projection = {
            "monthly_operating_cash_flow": canonical.monthly_operating_cash_flow,
            "cfads_monthly": canonical.cfads_monthly,
            "monthly_debt_service": canonical.monthly_emi,
            "annual_debt_service": canonical.annual_debt_service,
            "net_working_capital": canonical.net_working_capital,
            "first_12_months": canonical.cashflow_projection_12m,
        }
    else:
        # No usable unit economics: the numeric sections are explicitly empty
        # and the gap is named, rather than being filled in by the model.
        project_cost = ProjectCost()
        profitability = ProfitabilityAnalysis()
        revenue_projection = {}
        operating_expenses = {}
        cash_flow_projection = {}

    missing = [
        key for key in ("monthly_units", "price_per_unit", "variable_cost_per_unit",
                        "fixed_cost_monthly")
        if _num(req.financial_data.get(key)) is None
    ]

    server_sources = _server_data_sources(req.financial_data)

    payload = {
        **narrative,
        "proposal_metadata": ProposalMetadata(
            proposal_id=_proposal_id(req),
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            location=req.location,
            business_category=req.category,
            data_confidence=_data_confidence(server_sources, canonical),
        ),
        "project_cost": project_cost,
        "profitability_analysis": profitability,
        "revenue_projection": revenue_projection,
        "operating_expenses": operating_expenses,
        "cash_flow_projection": cash_flow_projection,
        # Server-written provenance replaces the model's citations entirely.
        "data_sources": server_sources,
    }

    if dropped:
        payload.setdefault("assumptions", []).append(
            "Numeric sections of this plan are computed by the deterministic financial engine. "
            f"Model-supplied values for {', '.join(dropped)} were discarded and replaced."
        )
    if missing:
        payload.setdefault("assumptions", []).append(
            "No financial figures are asserted because these inputs are missing: "
            f"{', '.join(missing)}. Supply them to obtain a modelled plan."
        )

    try:
        return BusinessPlan(**payload)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"AI returned an invalid narrative structure: {str(e)}",
        )
