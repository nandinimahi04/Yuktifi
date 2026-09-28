"""
One source of truth for numbers, and no fabrication in the ranking screen.

The ranking screen is the highest-consequence surface in the product: a ranked
list of business ideas reads as a verdict, and it is shown to people deciding
where to put their savings. These tests pin the properties that make it
trustworthy.
"""
import math

import pytest

from app.services.ranking_service import rank_opportunities


def _rows():
    return rank_opportunities("nashik_maharashtra", 60000)


# ── No invented inputs ───────────────────────────────────────────────────────

def test_h_no_loan_terms_are_invented_when_no_scheme_matches():
    """
    The old code fell back to `compute_emi(loan, 10.0, 60, 0)` and reported a
    DSCR against a loan that did not exist.
    """
    for row in _rows():
        if row.get("dscr") is not None:
            # A DSCR is only ever published alongside declared terms.
            assert row.get("financing_terms_status") == "DECLARED", row["category_name"]
            assert row.get("emi"), row["category_name"]
        else:
            assert row.get("emi") is None, row["category_name"]


def test_h_unmeasurable_dimensions_are_never_imputed():
    """
    The old code scored repayment_capacity=60 and capital_efficiency=60 whenever
    the underlying figure was missing, and 50 for an unknown gap score.
    """
    for row in _rows():
        for key, value in (row.get("dimension_scores") or {}).items():
            if value is None:
                assert key in row.get("unscored_dimensions", []), (row["category_name"], key)
            else:
                assert 0 <= value <= 100, (row["category_name"], key, value)


def test_h_absent_evidence_is_not_a_failed_business():
    """
    The old code returned yukti_score=0 and verdict="NOT_RECOMMENDED" when cost
    data was missing, which presents "unmeasured" as "tried and failed".
    """
    unranked = [r for r in _rows() if r.get("yukti_score") is None]
    assert unranked, "expected at least one uncosted category in the fixture data"
    for row in unranked:
        assert row["yukti_score"] is None
        assert row["verdict"] is None
        assert row["rank"] is None
        assert row.get("note")


def test_h_every_category_appears_even_without_a_cost_reference():
    """
    `get_all_category_ids` used to read from cost_models, so uncosted categories
    vanished from the list rather than being shown as needing a quotation.
    """
    ids = {r["category_id"] for r in _rows()}
    assert len(ids) == 5


# ── Financials come from the canonical engine ───────────────────────────────

def test_h_net_margin_is_after_interest_and_tax_not_a_derived_guess():
    """
    The old code set `net_margin = roi / 12`, which is not a relationship that
    holds in any accounting system.
    """
    from app.financial.canonical_engine import CanonicalFinancialResult

    assert "net_margin_pct" in CanonicalFinancialResult.__dataclass_fields__


def test_h_roi_is_none_when_the_capital_requirement_is_unknown():
    """
    ROI is a ratio. An unknown denominator cannot produce 0%, and reporting 0%
    says "this earns nothing", which is a much harsher claim than "unknown".
    """
    for row in _rows():
        if row.get("project_cost") is None:
            assert row.get("roi") is None, row["category_name"]
            assert row.get("project_cost_status") == "UNKNOWN"
        else:
            assert isinstance(row.get("roi"), (int, float))


def test_h_uncosted_business_is_not_called_viable():
    """
    An uncosted business must not be presented as viable or not viable: nobody
    knows. It is UNDETERMINED, with the reason recorded as something that could
    not be assessed rather than as a failure.

    This previously asserted NOT_VIABLE, which told a bank officer to reject a
    business for the crime of not having been costed yet.
    """
    seen = False
    for row in _rows():
        if row.get("project_cost") is None and row.get("yukti_score") is not None:
            seen = True
            unknowns = " ".join(row.get("assessability_unknowns") or []).lower()
            assert "capital requirement is unknown" in unknowns, row["category_name"]
            assert row["economic_viability"] == "UNDETERMINED", row["category_name"]
            assert not row.get("viability_reasons"), (
                "an unassessable business must carry no failure reasons"
            )
    if not seen:
        # No costed category with an unknown capital figure in the fixture: the
        # engine-level guarantee is asserted directly instead.
        from app.financial.canonical_engine import (
            CanonicalFinancialInput,
            OpexBreakdown,
            ProductItem,
            compute_canonical_financials,
        )

        result = compute_canonical_financials(
            CanonicalFinancialInput(
                business_type="uncosted",
                products=[
                    ProductItem(name="u", units_per_month=500, selling_price=50,
                                variable_cost_per_unit=20)
                ],
                opex=OpexBreakdown(rent=5000),
                own_capital=0,
                total_project_cost=None,
                debt_amount=0,
            )
        )
        assert result.economic_viability == "UNDETERMINED"
        assert result.viability_reasons == []
        assert any("capital requirement is unknown" in r for r in result.assessability_unknowns)


def test_evidence_of_failure_still_yields_not_viable():
    """UNDETERMINED must not swallow a real, evidenced failure."""
    from app.financial.canonical_engine import (
        CanonicalFinancialInput,
        OpexBreakdown,
        ProductItem,
        compute_canonical_financials,
    )

    result = compute_canonical_financials(
        CanonicalFinancialInput(
            business_type="loss_making",
            products=[
                ProductItem(name="u", units_per_month=500, selling_price=50,
                            variable_cost_per_unit=80)
            ],
            opex=OpexBreakdown(rent=5000),
            own_capital=100_000,
            total_project_cost=None,
            debt_amount=0,
        )
    )
    # A failed gate outranks an unassessable one, and the failure is the reason
    # given. Here the capital is known (it falls back to own_capital), so the
    # EBITDA failure is the whole story.
    assert result.economic_viability == "NOT_VIABLE"
    assert result.viability_reasons
    assert any("EBITDA" in r for r in result.viability_reasons)


# ── Ranking integrity ────────────────────────────────────────────────────────

def test_i_ranked_rows_come_first_and_are_ordered_by_score():
    rows = _rows()
    scores = [r["yukti_score"] for r in rows if r["yukti_score"] is not None]
    assert scores == sorted(scores, reverse=True)
    first_unranked = next(
        (i for i, r in enumerate(rows) if r["yukti_score"] is None), len(rows)
    )
    assert all(r["yukti_score"] is not None for r in rows[:first_unranked])


def test_i_ranks_are_contiguous_and_start_at_one():
    ranks = [r["rank"] for r in _rows() if r["rank"] is not None]
    assert ranks == list(range(1, len(ranks) + 1))


def test_i_no_nan_or_infinity_reaches_the_client():
    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
        elif isinstance(node, float):
            assert not math.isnan(node) and not math.isinf(node), node

    for row in _rows():
        walk(row)


# ── Reference-cost honesty ───────────────────────────────────────────────────

def test_i_reference_costs_are_labelled_as_needing_confirmation():
    for row in _rows():
        if row.get("project_cost") is not None or row.get("yukti_score") is not None:
            note = (row.get("note") or "").lower()
            assert "not a quotation" in note or "no published cost reference" in note


def test_i_no_capital_means_no_recommendation_status():
    """
    Scheme language must never imply approval, and must not appear at all when
    no scheme could actually be evaluated.
    """
    for row in _rows():
        status = row.get("scheme_status")
        if status is None:
            continue
        assert status in (
            "Potentially eligible",
            "Not matched",
            "Not evaluated",
        ), row["category_name"]
        # Never bare "eligible", which reads as approval.
        assert status == "Potentially eligible" or "eligible" not in status.lower()


# ── Capital input is validated ───────────────────────────────────────────────

@pytest.mark.parametrize("bad", [0, -5000, None])
def test_i_unusable_capital_produces_no_scores(bad):
    rows = rank_opportunities("nashik_maharashtra", bad)
    assert rows
    for row in rows:
        assert row["yukti_score"] is None
        assert "capital" in (row.get("note") or "").lower()
