"""
Session Service — manages user sessions and builds base_state for simulation.
Orchestrates API → Service → Engine flow.
"""
from typing import Optional

from sqlalchemy.orm import Session as DBSession
from app.models import Session, Location, BusinessCategory, LoanProduct, FinancialProjection
from app.models.core import uid
from app.data_layer.retrieval import DataRetrieval
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    ProductItem,
    OpexBreakdown,
    WorkingCapitalConfig,
    compute_canonical_financials,
)
from app.engines.scheme_engine import match_scheme
from app.engines.scoring_engine import compute_all_dimensions
from app.templates.business_templates import get_business_template
# NOTE: run_full_market_analysis is intentionally NOT imported here.
# Dimension scores are computed purely from financial metrics to avoid
# triggering the expensive Gemini + Overpass pipeline on every /recommend call.

data_layer = DataRetrieval()


def create_session(
    db: DBSession,
    user_id: str,
    location_id: str,
    margin_capital: float,
    category_id: str | None = None,
) -> Session:
    """Create a new session and return it."""
    session = Session(
        id=uid(),
        user_id=user_id,
        location_id=location_id,
        margin_capital=margin_capital,
        category_id=category_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session_category(db: DBSession, session_id: str, category_id: str) -> Session:
    """Update the selected business category for a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")
    session.category_id = category_id
    db.commit()
    db.refresh(session)
    return session


def build_canonical_input(
    category_id: str,
    margin_capital: float,
    cost: dict | None,
    overrides: dict | None = None,
) -> tuple[CanonicalFinancialInput, dict]:
    """
    Builds the one canonical financial input for a session.

    Capital has to size the business, otherwise the earning capacity is
    unrelated to what the entrepreneur invests and every return figure is
    meaningless. The chain is explicit and auditable:

        project cost   = margin / promoter contribution share   (scheme norm)
        annual revenue = project cost x capital turnover ratio (sector norm)
        monthly revenue= annual revenue / 12
        COGS / opex    = revenue x the template's declared percentages

    A supplied cost profile overrides the revenue and cost lines because it is
    observed data, but the project cost still comes from the profile's declared
    setup cost when it has one. Any shortfall against available funding is
    reported as a financing gap rather than absorbed into a larger loan.
    """
    tmpl = get_business_template(category_id)

    declared_setup_cost = None
    if cost is not None:
        declared_setup_cost = cost.get("total_setup_cost") or cost.get("startup_cost")

    # Project cost: the profile's own figure, else margin sized by the declared
    # promoter contribution share for this sector.
    #
    # `promoter_contribution_pct` is null for templates that do not declare one.
    # Dividing by it raised `TypeError: unsupported operand type(s) for /:
    # 'NoneType' and 'float'`, which surfaced as a 500 on /recommend and /simulate
    # for any session in such a sector. An undeclared contribution share is not a
    # reason to crash and not a reason to assume 25%: without it the project
    # cost is simply unknown, and everything sized from it stays unsized.
    contribution_pct = tmpl.promoter_contribution_pct
    # The promoter's own money has to be a real number before it can size
    # anything. A session that has not declared capital used to reach
    # `None / 0.25` here and return a 500 from /recommend and /simulate.
    has_margin = margin_capital is not None and float(margin_capital) > 0
    can_size_from_capital = has_margin and (
        contribution_pct is not None and float(contribution_pct) > 0
    )

    if declared_setup_cost:
        total_project_cost = float(declared_setup_cost)
    elif can_size_from_capital:
        total_project_cost = margin_capital / (float(contribution_pct) / 100.0)
    else:
        total_project_cost = None

    if cost is not None and cost.get("estimated_monthly_units") and cost.get("selling_price_per_unit"):
        # Observed data wins for the operating lines.
        monthly_units = float(cost["estimated_monthly_units"])
        price_per_unit = float(cost["selling_price_per_unit"])
        var_cost_per_unit = float(cost.get("variable_cost_per_unit") or 0.0)
        fixed_costs = float(cost.get("fixed_cost_monthly") or 0.0)
        revenue_source = "cost_profile"
    elif total_project_cost is not None:
        # Size the operation from the investment using declared sector norms.
        monthly_revenue = total_project_cost * tmpl.annual_revenue_per_invested_rupee / 12.0
        price_per_unit = tmpl.typical_unit_value
        monthly_units = monthly_revenue / price_per_unit if price_per_unit else 0.0
        var_cost_per_unit = price_per_unit * (tmpl.typical_cogs_pct / 100.0)
        fixed_costs = monthly_revenue * (tmpl.typical_opex_pct / 100.0)
        revenue_source = "capital_sized_from_template"
    else:
        # Neither an observed profile nor a sizeable project cost. Units, price
        # and cost are left at zero *and flagged*, because a zero here means "not
        # modelled", not "a business with no revenue".
        monthly_units = 0.0
        price_per_unit = 0.0
        var_cost_per_unit = 0.0
        fixed_costs = 0.0
        revenue_source = "not_modelled_missing_project_cost"

    overrides = overrides or {}
    operating_days = int(overrides.get("operating_days", 30))
    if "project_cost" in overrides:
        total_project_cost = float(overrides["project_cost"])
        revenue_source = "User Input"
    if "own_capital" in overrides:
        margin_capital = float(overrides["own_capital"])
        has_margin = True
    if "monthly_expenses" in overrides:
        fixed_costs = float(overrides["monthly_expenses"])
    if "selling_price" in overrides:
        price_per_unit = float(overrides["selling_price"])
        var_cost_per_unit = price_per_unit * (tmpl.typical_cogs_pct / 100.0)
        revenue_source = "User Input"
    if "units_per_day" in overrides:
        monthly_units = float(overrides["units_per_day"]) * operating_days
        revenue_source = "User Input"
    if "monthly_revenue" in overrides:
        monthly_revenue = float(overrides["monthly_revenue"])
        price_per_unit = price_per_unit if price_per_unit > 0 else monthly_revenue
        monthly_units = monthly_revenue / price_per_unit if price_per_unit > 0 else 0.0
        var_cost_per_unit = price_per_unit * (tmpl.typical_cogs_pct / 100.0)
        revenue_source = "User Input"

    wc_cfg = WorkingCapitalConfig(
        inventory_days=tmpl.default_inventory_days,
        receivable_days=tmpl.default_receivable_days,
        payable_days=tmpl.default_payable_days,
    )

    fin_input = CanonicalFinancialInput(
        business_type=category_id,
        products=[ProductItem(
            name=tmpl.name,
            units_per_month=monthly_units,
            selling_price=price_per_unit,
            variable_cost_per_unit=var_cost_per_unit,
        )],
        # The whole of the fixed cost goes on `other`.
        #
        # This used to be split 50/30/20 across rent, salaries and electricity
        # purely so the opex block had some lines in it. Nobody declared that
        # split: a founder who entered "17,500 a month" was shown a rent of
        # 8,750, salaries of 5,250 and electricity of 1,750, and every downstream
        # surface - the cost breakdown, the AI explanation, the report - repeated
        # those three figures as though they had been stated. The total was right
        # and the composition was fiction, which is the harder kind of wrong to
        # notice, because the number the founder checked is the one that matches.
        #
        # The cost model has one field for this, `fixed_cost_monthly`, documented
        # as "rent, salary, insurance" - an aggregate, not three readings. So
        # there is no declared component to carry on its own line, and the honest
        # place for the figure is `other`. Adding a rent field to the cost model
        # is the way to get a rent line back, and it should arrive as data rather
        # than as a ratio applied to a total.
        opex=OpexBreakdown(other=fixed_costs),
        own_capital=margin_capital if has_margin else 0.0,
        total_project_cost=total_project_cost,
        # Only the equipment and fixtures share of the project cost depreciates.
        # Without this the engine charges no depreciation at all and overstates
        # profit, NPV, IRR and payback. Guarded because total_project_cost is
        # None when no project cost could be established - a None asset_cost
        # means "not modelled", not "nothing to depreciate".
        asset_cost=(
            total_project_cost * tmpl.depreciable_asset_share
            if total_project_cost is not None
            else None
        ),
        useful_life_years=tmpl.asset_useful_life_years,
        # The scheme may be approached only once a project cost is actually
        # declared and exceeds the promoter's own money, so the loan funds a
        # real shortfall rather than an assumed percentage. With no project cost
        # there is no shortfall to fund, so no debt is derived.
        derive_debt_from_scheme=(
            has_margin
            and total_project_cost is not None
            and total_project_cost > float(margin_capital)
        ) if "loan_amount" not in overrides else False,
        debt_amount=float(overrides["loan_amount"]) if "loan_amount" in overrides else None,
        interest_rate_annual_pct=float(overrides["interest_rate"]) if "interest_rate" in overrides else 9.0,
        tenure_months=int(overrides["loan_tenure"]) if "loan_tenure" in overrides else 60,
        working_capital_cfg=wc_cfg,
    )
    return fin_input, {
        "monthly_units": monthly_units,
        "fixed_costs": fixed_costs,
        "has_setup_cost": declared_setup_cost is not None,
        "has_declared_capital": has_margin,
        "project_cost_source": ("cost_profile" if declared_setup_cost else ("capital_sized_from_template" if can_size_from_capital else None)),
        "revenue_source": revenue_source,
        "capital_turnover_ratio": tmpl.annual_revenue_per_invested_rupee,
        "promoter_contribution_pct": tmpl.promoter_contribution_pct,
    }


def compute_full_financials(
    db: DBSession,
    session_id: str,
) -> dict:
    """
    Compute the full financial snapshot for a session via Canonical Financial Engine.
    Stores results in DB.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise ValueError(f"Session {session_id} not found")

    location_id = session.location_id
    category_id = session.category_id or "retail_kirana"
    margin_capital = session.margin_capital

    cost_result = data_layer.get_cost_profile(location_id, category_id) if category_id else {"value": None}
    cost = cost_result.get("value")
    
    overrides = getattr(session, "financial_overrides", {})

    fin_input, derived = build_canonical_input(category_id, margin_capital, cost, overrides=overrides)

    canon_res = compute_canonical_financials(fin_input)
    res_dict = canon_res.to_dict()

    project_cost = res_dict["total_project_cost"]
    loan_amount = res_dict["approved_loan_amount"]
    contribution = res_dict["own_capital"]

    scheme = match_scheme(project_cost, own_contribution=contribution)

    # Upsert loan product
    loan = db.query(LoanProduct).filter(LoanProduct.session_id == session_id).first()
    if loan:
        loan.project_cost = project_cost
        loan.loan_amount = loan_amount
        loan.beneficiary_contribution = contribution
    else:
        loan = LoanProduct(
            id=uid(),
            session_id=session_id,
            project_cost=project_cost,
            loan_amount=loan_amount,
            beneficiary_contribution=contribution,
            matched_scheme_id=None,
        )
        db.add(loan)

    # Upsert projection
    projection = db.query(FinancialProjection).filter(
        FinancialProjection.session_id == session_id
    ).first()
    if projection:
        projection.monthly_revenue = res_dict["monthly_revenue"]
        projection.monthly_opex = res_dict["monthly_opex"]
        projection.net_profit = res_dict["monthly_pat"]
        projection.break_even_units = res_dict["break_even_units_monthly"] or 0.0
        projection.dscr = res_dict["dscr"]
        projection.roi = res_dict["roi_on_total_project_pct"]
        projection.monthly_emi = res_dict["monthly_emi"]
        projection.monthly_interest = res_dict["monthly_interest"]
        projection.financing_gap = res_dict["financing_gap"]
        projection.payback_months = res_dict["payback_months"]
    else:
        projection = FinancialProjection(
            id=uid(),
            session_id=session_id,
            monthly_revenue=res_dict["monthly_revenue"],
            monthly_opex=res_dict["monthly_opex"],
            net_profit=res_dict["monthly_pat"],
            break_even_units=res_dict["break_even_units_monthly"] or 0.0,
            dscr=res_dict["dscr"],
            roi=res_dict["roi_on_owner_equity_pct"],
            monthly_emi=res_dict["monthly_emi"],
            monthly_interest=res_dict["monthly_interest"],
            financing_gap=res_dict["financing_gap"],
            payback_months=res_dict["payback_months"],
        )
        db.add(projection)
    db.commit()

    return {
        "canonical_input": fin_input,
        "project_cost": project_cost,
        "loan_amount": loan_amount,
        "beneficiary_contribution": contribution,
        "other_funding": res_dict["other_funding"],
        "financing_gap": res_dict["financing_gap"],
        "financing_reconciled": res_dict["financing_reconciled"],
        "scheme": scheme.__dict__,
        "scheme_name": scheme.scheme_name,
        "interest_rate_pct": fin_input.interest_rate_annual_pct,
        "tenure_months": fin_input.tenure_months,
        "moratorium_months": fin_input.moratorium_months,
        "emi": res_dict["monthly_emi"],
        "monthly_revenue": res_dict["monthly_revenue"],
        "monthly_cogs": res_dict["monthly_cogs"],
        "monthly_opex": res_dict["monthly_opex"],
        "monthly_ebitda": res_dict["monthly_ebitda"],
        "monthly_interest": res_dict["monthly_interest"],
        "monthly_tax": res_dict["monthly_tax"],
        "monthly_depreciation": res_dict["monthly_depreciation"],
        "net_profit": res_dict["monthly_pat"],
        "dscr": res_dict["dscr"],
        "dscr_status": res_dict["dscr_status"],
        "debt_service_status": res_dict["debt_service_status"],
        "break_even_units": res_dict["break_even_units_monthly"],
        "break_even_revenue": res_dict["break_even_revenue_monthly"],
        "margin_of_safety_pct": res_dict["margin_of_safety_pct"],
        "economic_viability": res_dict["economic_viability"],
        "viability_reasons": res_dict["viability_reasons"],
        "assessability_unknowns": res_dict["assessability_unknowns"],
        # ROI is reported on total project cost, the standard appraisal basis.
        # Return on the promoter's own equity is materially larger purely
        # because equity is the smaller slice of the same project, so it is
        # published separately and labelled rather than presented as "the" ROI.
        "roi": res_dict["roi_on_total_project_pct"],
        "roi_on_total_project_pct": res_dict["roi_on_total_project_pct"],
        "roi_on_owner_equity_pct": res_dict["roi_on_owner_equity_pct"],
        "capital_turnover_ratio": derived.get("capital_turnover_ratio"),
        "revenue_source": derived.get("revenue_source"),
        "cost_confidence": cost_result.get("confidence", "Low"),
        "cashflow_projection": res_dict["cashflow_projection_12m"],
        "loan_schedule": res_dict["loan_schedule"],
        "pnl_statement": {
            "revenue": res_dict["monthly_revenue"],
            "cogs": res_dict["monthly_cogs"],
            "gross_profit": res_dict["monthly_gross_profit"],
            "gross_margin_pct": res_dict["gross_margin_pct"],
            "operating_expenses": res_dict["monthly_opex"],
            "ebitda": res_dict["monthly_ebitda"],
            "depreciation": res_dict["monthly_depreciation"],
            "ebit": res_dict["monthly_ebit"],
            "interest": res_dict["monthly_interest"],
            "tax": res_dict["monthly_tax"],
            "tax_status": res_dict["tax_status"],
            "net_profit": res_dict["monthly_pat"]
        },
        "working_capital": {
            "net_working_capital": res_dict["net_working_capital"],
            "inventory_requirement": res_dict["inventory_requirement"],
            "receivables": res_dict["receivables_requirement"],
            "payables": res_dict["payables_requirement"],
            "cash_conversion_cycle_days": res_dict["cash_conversion_cycle_days"]
        },
        "payback_period": {
            "payback_months": res_dict["payback_months"],
            "payback_achieved": res_dict["payback_achieved"]
        },
        "assumptions_provenance": res_dict["assumptions_provenance"],
    }


def get_base_state(db: DBSession, session_id: str) -> dict:
    """
    Build the base_state dict needed by the simulation engine.
    Retrieves stored financial data or recomputes.

    Always carries `canonical_input` so the what-if simulator re-runs the
    identical model rather than reconstructing figures from a summary.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        # Unknown session. This previously returned an invented business: a
        # ₹9,00,000 loan at 10% over 60 months, ₹1,20,000 monthly revenue,
        # ₹70,000 monthly opex, and dimension scores of 89/92/88/91/68. Any
        # client that called /recommend or /simulate with an unknown
        # session_id therefore received a ~90/100 score and a confident verdict
        # for a business that did not exist, with no way to tell the difference.
        #
        # The empty state is now honest: nothing is known, so nothing is
        # reported, and `state_status` says why.
        return {
            "state_status": "NO_SESSION",
            "note": (
                f"No session '{session_id}' exists, so there is no business to assess. "
                f"Complete the intake flow before requesting a recommendation."
            ),
            "principal": None,
            "rate": None,
            "tenure_months": None,
            "moratorium_months": None,
            "monthly_revenue": None,
            "monthly_opex": None,
            "break_even_units": None,
            "canonical_input": None,
            "dimension_scores": compute_all_dimensions(),
            "confidence_multiplier": 1.0,
        }
    projection = db.query(FinancialProjection).filter(
        FinancialProjection.session_id == session_id
    ).first()
    loan = db.query(LoanProduct).filter(
        LoanProduct.session_id == session_id
    ).first()

    if not projection or not loan:
        result = compute_full_financials(db, session_id)
        return {
            "state_status": "RECOMPUTED",
            "note": "No stored projection existed, so the canonical model was re-run.",
            "principal": result["loan_amount"],
            "rate": result["interest_rate_pct"],
            "tenure_months": result["tenure_months"],
            "moratorium_months": result["moratorium_months"],
            "monthly_revenue": result["monthly_revenue"],
            "monthly_opex": result["monthly_opex"],
            "break_even_units": result["break_even_units"],
            "canonical_input": result["canonical_input"],
            "dimension_scores": _default_dimension_scores(result["dscr"], result["roi"], result["break_even_units"], result["monthly_revenue"], session.location_id, session.category_id, session.category_id),
            "confidence_multiplier": 0.85,
        }

    from app.models.financial_assumptions import ProjectFinancialAssumptions
    assumptions_record = db.query(ProjectFinancialAssumptions).filter(
        ProjectFinancialAssumptions.session_id == session_id
    ).first()

    if assumptions_record:
        tmpl = get_business_template(session.category_id or "retail_kirana")
        if assumptions_record.is_direct_revenue_mode:
            monthly_rev = assumptions_record.monthly_revenue
            price = assumptions_record.selling_price if assumptions_record.selling_price > 0 else tmpl.typical_selling_price
            units_m = (monthly_rev / price) if price > 0 else 1.0
            var_cost = assumptions_record.variable_cost_per_unit if assumptions_record.variable_cost_per_unit > 0 else (price * (tmpl.typical_cogs_pct / 100.0))
        else:
            price = assumptions_record.selling_price
            units_m = assumptions_record.units_per_day * assumptions_record.operating_days
            var_cost = assumptions_record.variable_cost_per_unit
            monthly_rev = price * units_m

        wc_cfg = WorkingCapitalConfig(
            inventory_days=tmpl.default_inventory_days,
            receivable_days=tmpl.default_receivable_days,
            payable_days=tmpl.default_payable_days,
        )

        canonical_input = CanonicalFinancialInput(
            business_type=session.category_id or "retail_kirana",
            products=[ProductItem(
                name=tmpl.name,
                units_per_month=units_m,
                selling_price=price,
                variable_cost_per_unit=var_cost,
            )],
            opex=OpexBreakdown(other=assumptions_record.monthly_expenses),
            own_capital=assumptions_record.own_capital,
            total_project_cost=assumptions_record.project_cost,
            asset_cost=assumptions_record.project_cost * tmpl.depreciable_asset_share if assumptions_record.project_cost else None,
            useful_life_years=tmpl.asset_useful_life_years,
            derive_debt_from_scheme=False,
            debt_amount=assumptions_record.loan_amount,
            interest_rate_annual_pct=assumptions_record.interest_rate_annual_pct,
            tenure_months=assumptions_record.loan_tenure_months,
            moratorium_months=assumptions_record.moratorium_months,
            tax_rate_pct=assumptions_record.tax_rate_pct,
            working_capital_cfg=wc_cfg,
        )
        rate = assumptions_record.interest_rate_annual_pct
        tenure_months = assumptions_record.loan_tenure_months
        moratorium_months = assumptions_record.moratorium_months
        financing_status = "DECLARED"
        financing_note = f"Declared loan terms: {rate}% over {tenure_months} months."
    else:
        # Rebuild the canonical input from the cost profile so the simulator
        # applies shocks to the same declared cost lines.
        cost_result = data_layer.get_cost_profile(
            session.location_id, session.category_id or "retail_kirana"
        )
        canonical_input, _ = build_canonical_input(
            session.category_id or "retail_kirana",
            session.margin_capital,
            cost_result.get("value"),
            overrides=getattr(session, "financial_overrides", {}),
        )

        scheme = match_scheme(
            loan.project_cost,
            own_contribution=loan.beneficiary_contribution,
        )
        # LoanProduct stores no interest rate, so it can only come from a matched
        # scheme. Absent a scheme, financing terms are unknown and stay None.
        if scheme.matched and scheme.rate is not None and scheme.tenure_years:
            rate = scheme.rate
            tenure_months = scheme.tenure_years * 12
            financing_status = "DECLARED"
            financing_note = (
                f"Terms from matched scheme '{scheme.scheme_name}': {rate}% over "
                f"{scheme.tenure_years} years."
            )
        else:
            rate = None
            tenure_months = None
            financing_status = "UNKNOWN"
            financing_note = (
                "No scheme matched, so no interest rate or tenure is known. Repayment "
                "capacity cannot be assessed until loan terms are supplied."
            )
        moratorium_months = scheme.moratorium_months if scheme.matched else 0

    return {
        "state_status": "STORED",
        "financing_terms_status": financing_status,
        "financing_note": financing_note,
        "principal": loan.loan_amount,
        "rate": rate,
        "tenure_months": tenure_months,
        "moratorium_months": moratorium_months,
        "monthly_revenue": projection.monthly_revenue,
        "monthly_opex": projection.monthly_opex,
        "break_even_units": projection.break_even_units,
        "canonical_input": canonical_input,
        "dimension_scores": _default_dimension_scores(projection.dscr, projection.roi, projection.break_even_units, projection.monthly_revenue, session.location_id, session.category_id, session.category_id),
        "confidence_multiplier": 0.85,
    }



def _default_dimension_scores(
    dscr: Optional[float], roi: Optional[float], break_even: Optional[float],
    monthly_revenue: Optional[float],
    location_id: str = "", category_id: str = "", category_name: str = ""
) -> dict:
    """
    Score only the dimensions that the financial projection can actually support.

    This deliberately does NOT call run_full_market_analysis, which would trigger
    the full provider pipeline on every /recommend and /simulate request.

    It previously also avoided that call by inventing the market inputs:
    `competitor_count = 2`, `population = 5000`, `threats_count = 1`,
    `confidence = "medium"`, `net_margin = roi / 12` and
    `monthly_units = monthly_revenue / 100`. None of those is a measurement. The
    first four were constants presented as observations, and the last two are
    dimensionally meaningless - margin is a ratio, so deriving it from an annual
    ROI divided by twelve has no interpretation, and revenue divided by 100
    produces a number that is not a unit count.

    All market-derived inputs are now passed as None. The score card abstains on
    those dimensions, so the published composite rests only on real financial
    figures and states its own coverage.
    """
    return compute_all_dimensions(
        roi=roi,
        dscr=dscr,
        # No net margin is available from the projection alone, so it is not
        # invented. Financial viability is scored on ROI only and says so.
        net_margin=None,
        break_even_units=break_even,
        # Break-even cannot be expressed as a share of sales without a genuine
        # revenue figure; a projection without revenue yields None, not a guess.
        monthly_units=None,
        competitor_count=None,
        population=None,
        overall_confidence=None,
        threats_count=None,
    )

