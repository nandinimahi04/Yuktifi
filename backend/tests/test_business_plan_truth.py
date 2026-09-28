"""
Regressions for the business plan: the model must not author any number.

The failure these lock down was not hypothetical. `generate_business_plan`
validated the model response with `BusinessPlan(**response)`, so ROI, DSCR,
break-even, project cost, the whole cash-flow projection and every `data_sources`
citation were Gemini's output. A forged figure wearing a Census citation is worse
than a missing one, so these tests check both halves: the engine supplies the
numbers, and the model's claims about them are discarded.

`asyncio.run` is used directly because the project has no pytest-asyncio plugin.
"""
import asyncio

import pytest
from fastapi import HTTPException

from app.ai_layer.business_matcher import match_business_category
from app.engines.feasibility_engine import compute_why_not_analysis
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    OpexBreakdown,
    ProductItem,
    compute_canonical_financials,
)
from app.schemas.business_plan import DataSource

CATEGORY = "kirana"

FINANCIALS = {
    "category": CATEGORY,
    "monthly_units": 900,
    "price_per_unit": 120,
    "variable_cost_per_unit": 84,
    "fixed_cost_monthly": 30000,
    "own_capital": 250000,
    "total_project_cost": 500000,
    "debt_amount": 250000,
    "interest_rate_annual_pct": 10.0,
    "tenure_months": 60,
}

NARRATIVE = {
    "executive_summary": {
        "business_overview": "A neighbourhood provision store.",
        "opportunity": "Steady local demand.",
        "recommendation": "Proceed subject to the figures below.",
        "key_metrics": {},
    },
    "conclusion": {"text": "Recommended."},
}

HOSTILE_NUMBERS = {
    "project_cost": {
        "total_project_cost": 12000000.0,
        "own_contribution": 900000.0,
        "financing_required": 11100000.0,
    },
    "profitability_analysis": {"roi": 87.5, "dscr": 4.2, "break_even": 11.0},
    "revenue_projection": {"year_1": 99999999},
    "cash_flow_projection": {"year_1": 88888888},
    "operating_expenses": {"rent": 7777777},
    "financial_structure": {"equity_debt_ratio": "80:20"},
    "financing_readiness": {"bank_ready": True},
    "scheme_information": {"pmegsy_subsidy": 500000},
    "infrastructure_and_equipment": {"machinery_cost": 6666666},
}


def _expected():
    """The same business, computed by the engine - the only source of truth."""
    return compute_canonical_financials(
        CanonicalFinancialInput(
            business_type=CATEGORY,
            products=[ProductItem("Primary line", 900, 120, 84)],
            opex=OpexBreakdown(other=30000),
            own_capital=250000,
            total_project_cost=500000,
            debt_amount=250000,
            interest_rate_annual_pct=10.0,
            tenure_months=60,
        )
    )


def _plan(monkeypatch, model_response, financials=None):
    from app.api import routes_business_plan as rbp

    async def fake_generate(prompt, **kwargs):
        return model_response

    monkeypatch.setattr(rbp.gemini, "generate_json_async", fake_generate)
    return asyncio.run(
        rbp.generate_business_plan(
            rbp.BusinessPlanRequest(
                location="Ward 42",
                category=CATEGORY,
                financial_data=dict(FINANCIALS if financials is None else financials),
            )
        )
    )


def test_model_cannot_own_the_financial_numbers(monkeypatch):
    """The model returns numbers. None of them may survive into the response."""
    plan = _plan(monkeypatch, {**NARRATIVE, **HOSTILE_NUMBERS})
    expected = _expected()

    assert plan.project_cost.total_project_cost == expected.total_project_cost
    assert plan.project_cost.total_project_cost == 500000.0
    assert plan.profitability_analysis.roi == expected.roi_on_total_project_pct
    assert plan.profitability_analysis.dscr == expected.dscr
    assert plan.profitability_analysis.break_even == expected.break_even_units_monthly
    assert plan.profitability_analysis.net_margin_pct == expected.net_margin_pct
    assert plan.profitability_analysis.computed_by == "canonical_financial_engine"
    assert plan.project_cost.computed_by == "canonical_financial_engine"

    # Not one model-supplied figure reaches the response.
    body = plan.model_dump_json()
    for invented in (
        "99999999", "88888888", "7777777", "6666666",
        "11100000", "900000", "12000000", "87.5", "4.2",
    ):
        assert invented not in body, f"model-supplied value {invented} reached the response"


def test_narrative_is_still_model_written(monkeypatch):
    """Stripping numbers must not strip the prose, which is the model's job."""
    plan = _plan(monkeypatch, {**NARRATIVE, **HOSTILE_NUMBERS})
    assert "neighbourhood provision store" in plan.executive_summary.business_overview
    assert plan.conclusion == {"text": "Recommended."}


def test_model_supplied_citations_are_replaced_by_server_provenance(monkeypatch):
    """A model must not be able to attach a source to a number."""
    plan = _plan(
        monkeypatch,
        {
            **NARRATIVE,
            "data_sources": [
                {
                    "field": "monthly_units",
                    "value": 900,
                    "source": "Census 2011",
                    "confidence": "High",
                }
            ],
        },
    )

    sources = {s.field: s for s in plan.data_sources}
    assert "monthly_units" in sources
    citation = sources["monthly_units"]
    assert citation.source_kind == "USER_SUPPLIED"
    assert "Census" not in (citation.source or "")
    # A declaration is not a verification and must not be dressed up as one.
    assert citation.confidence == "DECLARED_NOT_VERIFIED"


def test_missing_unit_economics_yield_no_numbers_at_all(monkeypatch):
    """
    With no unit economics the plan must be empty of figures and say why.

    The schema previously demanded a float for roi/dscr/break_even, so a business
    with no declared inputs still produced a plan - the model simply invented
    three ratios, including a DSCR for a business with no declared loan.
    """
    plan = _plan(
        monkeypatch, NARRATIVE, financials={"category": CATEGORY, "own_capital": 200000}
    )

    assert plan.profitability_analysis.roi is None
    assert plan.profitability_analysis.dscr is None
    assert plan.profitability_analysis.break_even is None
    assert plan.project_cost.total_project_cost is None
    assumptions = " ".join(plan.assumptions)
    assert "monthly_units" in assumptions
    assert "price_per_unit" in assumptions


def test_debtless_business_reports_no_dscr_instead_of_inventing_one(monkeypatch):
    plan = _plan(
        monkeypatch, NARRATIVE, financials={**FINANCIALS, "debt_amount": 0.0}
    )
    assert plan.profitability_analysis.dscr is None
    assert plan.profitability_analysis.dscr_status == "NOT_APPLICABLE_NO_DEBT"


def test_narrative_unavailable_yields_503_not_a_half_plan(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        _plan(monkeypatch, None)
    assert exc.value.status_code == 503


def test_data_source_defaults_are_unattributed():
    """A DataSource with no source must not read as verified."""
    ds = DataSource(field="roi", value=12.0)
    assert ds.source is None
    assert ds.confidence is None
    assert ds.source_kind == "UNATTRIBUTED"


def test_why_not_abstains_without_capital_requirements():
    """
    Alternatives must not be ruled on by thresholds invented in code.

    The old implementation hardcoded six capital figures, defaulted anything
    unlisted to 300,000, and issued "Pass" / "Fail (Capital Gap)" against an
    undocumented `capital >= required * 0.10` test.
    """
    out = compute_why_not_analysis(50000, "kirana", ["dairy", "vada_pav"])
    assert out, "alternatives should still be listed"
    for row in out:
        assert row["capital_fit"] == "Not assessed"
        assert row["capital_required"] is None
        assert row["evidence_state"] == "MISSING"
        assert "Fail" not in row["capital_fit"]


def test_why_not_abstains_when_applicant_capital_is_unknown():
    out = compute_why_not_analysis(
        None, "kirana", ["dairy"], cost_models={"dairy": {"capital_required": 350000.0}}
    )
    assert out[0]["capital_fit"] == "Not assessed"
    assert out[0]["capital_required"] == 350000.0


def test_why_not_reports_a_funded_share_not_a_verdict():
    out = compute_why_not_analysis(
        100000, "kirana", ["dairy"], cost_models={"dairy": {"capital_required": 400000.0}}
    )
    row = out[0]
    assert row["capital_required"] == 400000.0
    assert row["applicant_capital_share_pct"] == 25.0
    assert "25.0%" in row["capital_fit"]
    assert "Pass" not in row["capital_fit"] and "Fail" not in row["capital_fit"]


def test_why_not_skips_the_recommended_category():
    out = compute_why_not_analysis(100000, "dairy", ["dairy", "kirana"])
    assert [r["business_category"] for r in out] == ["kirana"]


def test_matcher_refuses_to_substitute_a_default_category(monkeypatch):
    """
    An unreachable model must not yield a confident "retail_shop".

    The category selects the cost profile, price band, competitor set and every
    score, so the old fallback modelled every unrecognised idea as a kirana store
    at confidence 0.5 - the most expensive failure in the product.
    """
    from app.ai_layer import business_matcher as bm

    class _NoModel:
        async def generate_json_async(self, prompt, schema=None, **kwargs):
            return None

    monkeypatch.setattr(bm, "GeminiClient", _NoModel)

    result = asyncio.run(match_business_category(area_of_interest="", suggested_idea="aquaponic fish farming", detailed_idea="", experience=""))
    assert result["matched_category_id"] is None
    assert result["confidence"] is None
    assert result["category_source"] == "UNAVAILABLE"

    # An explicit user choice still works with no model at all.
    explicit = asyncio.run(
        match_business_category(
            area_of_interest="Dairy Farming & Collection",
            suggested_idea="aquaponic fish farming",
            detailed_idea="",
            experience="",
        )
    )
    assert explicit["matched_category_id"] == "dairy"
    assert explicit["confidence"] is None
    assert explicit["category_source"] == "USER_SELECTED"


def test_matcher_does_not_keep_confidence_for_a_hallucinated_category(monkeypatch):
    from app.ai_layer import business_matcher as bm

    class _HallucinatingModel:
        async def generate_json_async(self, prompt, schema=None, **kwargs):
            return {
                "matched_category_id": "underwater_basket_weaving",
                "matched_subcategory": "niche",
                "confidence": 0.93,
                "reason": "Closest match.",
            }

    monkeypatch.setattr(bm, "GeminiClient", _HallucinatingModel)

    result = asyncio.run(match_business_category(area_of_interest="", suggested_idea="weaving", detailed_idea="", experience=""))
    assert result["matched_category_id"] is None
    assert result["confidence"] is None
    assert result["category_source"] == "UNMATCHED"
    assert result["unmatched_category_id"] == "underwater_basket_weaving"
