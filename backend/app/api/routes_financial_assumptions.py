from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.db import get_db
from app.models.session import Session
from app.models.financial_assumptions import ProjectFinancialAssumptions, FinancialAssumptionsAudit
from app.models.loan_product import LoanProduct
from app.models.financial_projection import FinancialProjection
from app.schemas.financial_assumptions import (
    FinancialAssumptionsInput,
    FinancialAssumptionsDTO,
    FinancialRecalculateRequest,
    FinancialRecalculateResponse,
    ValidationWarning,
)
from app.templates.business_templates import get_business_template
from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    ProductItem,
    OpexBreakdown,
    WorkingCapitalConfig,
    compute_canonical_financials,
)
from app.engines.scheme_engine import match_scheme
from app.engines.scoring_engine import compute_all_dimensions
from app.engines.financial_engine import compute_seasonal_revenue, compute_revenue_scenarios
from app.data_layer.retrieval import DataRetrieval

router = APIRouter(prefix="/api/financials", tags=["financial-assumptions"])
logger = logging.getLogger("yukti.financial_assumptions")
data_layer = DataRetrieval()


IST = timezone(timedelta(hours=5, minutes=30))


def _to_ist_str(dt: Optional[datetime]) -> str:
    if not dt:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d %b %Y, %I:%M:%S %p IST")


def _check_warnings(
    selling_price: float,
    variable_cost: float,
    units_per_day: float,
    operating_days: int,
    monthly_revenue: float,
    is_direct_mode: bool
) -> List[ValidationWarning]:
    warnings: List[ValidationWarning] = []
    
    # 1. Unit ambiguity check
    if not is_direct_mode and selling_price > 0 and monthly_revenue > 0:
        if selling_price >= monthly_revenue:
            warnings.append(ValidationWarning(
                field="selling_price",
                message=f"Selling price per unit (₹{selling_price:,.2f}) is as large as or exceeds total monthly revenue (₹{monthly_revenue:,.2f}). Please verify unit dimensions.",
                code="UNIT_AMBIGUITY"
            ))
            
    # 2. Negative/Zero contribution margin check (applies in both direct and unit mode)
    if selling_price > 0 and variable_cost is not None and variable_cost > 0:
        contrib = selling_price - variable_cost
        if contrib <= 0:
            loss_pct = (abs(contrib) / selling_price) * 100.0
            warnings.append(ValidationWarning(
                field="variable_cost_per_unit",
                message=f"Negative unit contribution margin: Selling Price (₹{selling_price:,.2f}) − Variable Cost (₹{variable_cost:,.2f}) = -₹{abs(contrib):,.2f} per unit (-{loss_pct:.1f}% gross margin). Every unit sold creates an operating loss, resulting in negative Net Profit and negative Return on Project. Adjust variable cost per unit below selling price.",
                code="NEGATIVE_CONTRIBUTION"
            ))
            
    return warnings


def _build_and_compute(
    assumptions_record: ProjectFinancialAssumptions,
    category_id: str,
    db: DBSession
) -> tuple[Dict[str, Any], List[ValidationWarning]]:
    tmpl = get_business_template(category_id)
    
    # Determine revenue and units
    if assumptions_record.is_direct_revenue_mode:
        monthly_rev = assumptions_record.monthly_revenue
        # Preserve unit price or use template
        price = assumptions_record.selling_price if assumptions_record.selling_price > 0 else tmpl.typical_selling_price
        units_m = (monthly_rev / price) if price > 0 else 1.0
        var_cost = assumptions_record.variable_cost_per_unit if assumptions_record.variable_cost_per_unit > 0 else (price * (tmpl.typical_cogs_pct / 100.0))
    else:
        price = assumptions_record.selling_price
        units_m = assumptions_record.units_per_day * assumptions_record.operating_days
        var_cost = assumptions_record.variable_cost_per_unit
        monthly_rev = price * units_m

    fixed_costs = assumptions_record.monthly_expenses
    
    # Financing
    project_cost = assumptions_record.project_cost
    own_capital = assumptions_record.own_capital
    debt_amount = assumptions_record.loan_amount

    wc_cfg = WorkingCapitalConfig(
        inventory_days=tmpl.default_inventory_days,
        receivable_days=tmpl.default_receivable_days,
        payable_days=tmpl.default_payable_days,
    )

    fin_input = CanonicalFinancialInput(
        business_type=category_id,
        products=[ProductItem(
            name=tmpl.name,
            units_per_month=units_m,
            selling_price=price,
            variable_cost_per_unit=var_cost,
        )],
        opex=OpexBreakdown(other=fixed_costs),
        own_capital=own_capital,
        total_project_cost=project_cost,
        asset_cost=project_cost * tmpl.depreciable_asset_share if project_cost else None,
        useful_life_years=tmpl.asset_useful_life_years,
        derive_debt_from_scheme=False,
        debt_amount=debt_amount,
        interest_rate_annual_pct=assumptions_record.interest_rate_annual_pct,
        tenure_months=assumptions_record.loan_tenure_months,
        moratorium_months=assumptions_record.moratorium_months,
        tax_rate_pct=assumptions_record.tax_rate_pct,
        working_capital_cfg=wc_cfg,
    )

    res = compute_canonical_financials(fin_input)
    res_dict = res.to_dict()

    scheme = match_scheme(project_cost, own_contribution=own_capital)

    # Sync to DB tables for backwards compatibility
    loan = db.query(LoanProduct).filter(LoanProduct.session_id == assumptions_record.session_id).first()
    if loan:
        loan.project_cost = project_cost
        loan.loan_amount = debt_amount
        loan.beneficiary_contribution = own_capital
    else:
        loan = LoanProduct(
            session_id=assumptions_record.session_id,
            project_cost=project_cost,
            loan_amount=debt_amount,
            beneficiary_contribution=own_capital,
        )
        db.add(loan)

    proj = db.query(FinancialProjection).filter(FinancialProjection.session_id == assumptions_record.session_id).first()
    if proj:
        proj.monthly_revenue = res_dict["monthly_revenue"]
        proj.monthly_opex = res_dict["monthly_opex"]
        proj.net_profit = res_dict["monthly_pat"]
        proj.break_even_units = res_dict["break_even_units_monthly"] or 0.0
        proj.dscr = res_dict["dscr"]
        proj.roi = res_dict["roi_on_total_project_pct"]
        proj.monthly_emi = res_dict["monthly_emi"]
        proj.monthly_interest = res_dict["monthly_interest"]
        proj.financing_gap = res_dict["financing_gap"]
        proj.payback_months = res_dict["payback_months"]
    else:
        proj = FinancialProjection(
            session_id=assumptions_record.session_id,
            monthly_revenue=res_dict["monthly_revenue"],
            monthly_opex=res_dict["monthly_opex"],
            net_profit=res_dict["monthly_pat"],
            break_even_units=res_dict["break_even_units_monthly"] or 0.0,
            dscr=res_dict["dscr"],
            roi=res_dict["roi_on_total_project_pct"],
            monthly_emi=res_dict["monthly_emi"],
            monthly_interest=res_dict["monthly_interest"],
            financing_gap=res_dict["financing_gap"],
            payback_months=res_dict["payback_months"],
        )
        db.add(proj)

    warnings = _check_warnings(
        selling_price=price,
        variable_cost=var_cost,
        units_per_day=assumptions_record.units_per_day,
        operating_days=assumptions_record.operating_days,
        monthly_revenue=monthly_rev,
        is_direct_mode=assumptions_record.is_direct_revenue_mode
    )

    # Generate Seasonal Profile
    seasonal_data = compute_seasonal_revenue(res_dict["monthly_revenue"], category_id)

    # Generate Revenue Scenarios
    scenarios_data = compute_revenue_scenarios(
        monthly_revenue=res_dict["monthly_revenue"],
        monthly_variable_cost=res_dict["monthly_cogs"],
        monthly_fixed_cost=res_dict["monthly_opex"],
        emi=res_dict["monthly_emi"],
        total_investment=project_cost,
        monthly_interest=res_dict["monthly_interest"],
        monthly_depreciation=res_dict["monthly_depreciation"],
        effective_tax_rate_pct=assumptions_record.tax_rate_pct or 0.0,
    )

    # Format Cash Flow 12-Month Projection with seasonal curve
    cashflow_formatted = []
    cum_cash = 0.0
    for i, s_item in enumerate(seasonal_data):
        m_name = s_item["month"]
        s_idx = s_item["index"]
        rev_m = round(res_dict["monthly_revenue"] * s_idx, 2)
        cogs_m = round(res_dict["monthly_cogs"] * s_idx, 2)
        opex_m = round(res_dict["monthly_opex"], 2)
        exp_m = round(cogs_m + opex_m, 2)
        emi_m = res_dict["monthly_emi"] if (i + 1) > assumptions_record.moratorium_months else 0.0
        tax_m = round(max(0.0, (rev_m - exp_m - res_dict["monthly_depreciation"] - res_dict["monthly_interest"]) * ((assumptions_record.tax_rate_pct or 0.0) / 100.0)), 2)
        net_m = round(rev_m - exp_m - emi_m - tax_m, 2)
        cum_cash = round(cum_cash + net_m, 2)

        cashflow_formatted.append({
            "month": m_name,
            "month_num": i + 1,
            "seasonal_index": s_idx,
            "revenue": rev_m,
            "expenses": exp_m,
            "cogs": cogs_m,
            "opex": opex_m,
            "emi_payment": emi_m,
            "net_cash": net_m,
            "net_cash_flow": net_m,
            "cumulative": cum_cash,
            "cumulative_cash_flow": cum_cash,
        })

    financials_payload = {
        "project_cost": res_dict["total_project_cost"],
        "loan_amount": res_dict["debt_amount"],
        "beneficiary_contribution": res_dict["own_capital"],
        "user_capital": res_dict["own_capital"],
        "other_funding": res_dict["other_funding"],
        "eligible_subsidy": res_dict["eligible_subsidy"],
        "financing_gap": res_dict["financing_gap"],
        "financing_reconciled": res_dict["financing_reconciled"],
        "scheme": scheme.__dict__ if hasattr(scheme, "__dict__") else {"scheme_name": getattr(scheme, "scheme_name", "Standard Loan")},
        "interest_rate_pct": assumptions_record.interest_rate_annual_pct,
        "rate": assumptions_record.interest_rate_annual_pct,
        "tenure_months": assumptions_record.loan_tenure_months,
        "moratorium_months": assumptions_record.moratorium_months,
        "emi": res_dict["monthly_emi"],
        "monthly_emi": res_dict["monthly_emi"],
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
        "break_even_units": res_dict["break_even_units_monthly"],
        "break_even_revenue": res_dict["break_even_revenue_monthly"],
        "margin_of_safety_pct": res_dict["margin_of_safety_pct"],
        "economic_viability": res_dict["economic_viability"],
        "viability_reasons": res_dict["viability_reasons"],
        "assessability_unknowns": res_dict["assessability_unknowns"],
        "roi": res_dict["roi_on_total_project_pct"],
        "roi_pct": res_dict["roi_on_total_project_pct"],
        "roi_on_total_project_pct": res_dict["roi_on_total_project_pct"],
        "roi_on_owner_equity_pct": res_dict["roi_on_owner_equity_pct"],
        "gross_margin_pct": res_dict["gross_margin_pct"],
        "net_margin_pct": res_dict["net_margin_pct"],
        "operating_days_per_month": assumptions_record.operating_days,
        "total_repayment": res_dict["total_repayment"],
        "total_interest_paid": res_dict["total_interest_paid"],
        "loan_schedule": res_dict["loan_schedule"],
        "cashflow_projection": cashflow_formatted,
        "seasonal_revenue": seasonal_data,
        "revenue_scenarios": scenarios_data,
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
            "net_profit": res_dict["monthly_pat"],
            "net_margin_pct": res_dict["net_margin_pct"],
        },
        "working_capital": {
            "net_working_capital": res_dict["net_working_capital"],
            "monthly_working_capital": res_dict["net_working_capital"],
            "inventory_requirement": res_dict["inventory_requirement"],
            "receivables": res_dict["receivables_requirement"],
            "payables": res_dict["payables_requirement"],
            "cash_conversion_cycle_days": res_dict["cash_conversion_cycle_days"],
            "daily_cash_needed": round((res_dict["monthly_opex"] + res_dict["monthly_cogs"]) / assumptions_record.operating_days, 2) if assumptions_record.operating_days > 0 else 0.0,
            "weekly_cash_needed": round(((res_dict["monthly_opex"] + res_dict["monthly_cogs"]) / assumptions_record.operating_days) * 7, 2) if assumptions_record.operating_days > 0 else 0.0,
            "recommended_buffer": round(res_dict["net_working_capital"] * 0.20, 2),
            "inventory_days": wc_cfg.inventory_days,
            "receivable_days": wc_cfg.receivable_days,
            "payable_days": wc_cfg.payable_days,
        },
        "payback_period": {
            "payback_months": res_dict["payback_months"],
            "payback_achieved": res_dict["payback_achieved"],
            "note": res_dict["payback_undetermined_reason"] if not res_dict["payback_achieved"] else f"Recovered in {res_dict['payback_months']} months"
        },
        "assumptions_provenance": res_dict["assumptions_provenance"],
        "financial_status": res_dict["financial_status"],
        "decision_gates": res_dict["decision_gates"],
        "financial_confidence": res_dict["financial_confidence"],
        "monthly_forecast": res_dict["monthly_forecast"],
        "stress_scenarios": res_dict["stress_scenarios"],
        "validation_issues": res_dict["validation_issues"],
        "explainability": res_dict["explainability"],
    }

    return financials_payload, warnings


def _compute_scores_for_session(
    record: ProjectFinancialAssumptions,
    financials: Dict[str, Any],
    session: Session,
    category_id: str,
) -> Dict[str, Any]:
    tmpl = get_business_template(category_id)
    population = None
    comp_count = None
    
    if session.location_id:
        try:
            demo = data_layer.get_demographics(session.location_id)
            if demo and demo.get("value"):
                population = demo["value"].get("population")
            
            comps = data_layer.get_competitors(session.location_id, category_id)
            if comps and comps.get("count") is not None:
                comp_count = comps.get("count")
        except Exception as e:
            logger.warning("Could not fetch location market data for score computation: %s", e)

    price = record.selling_price if not record.is_direct_revenue_mode else tmpl.typical_selling_price

    units_m = (record.units_per_day * record.operating_days) if not record.is_direct_revenue_mode else (record.monthly_revenue / price if price > 0 else 1.0)
    
    cash_flow = financials.get("monthly_cash_flow")
    if cash_flow is None and "pnl_statement" in financials:
        cash_flow = financials["pnl_statement"].get("ebitda", 0.0) - financials.get("monthly_tax", 0.0)

    card = compute_all_dimensions(
        roi=financials.get("roi_pct"),
        dscr=financials.get("dscr"),
        net_margin=financials.get("net_margin_pct"),
        break_even_units=financials.get("break_even_units"),
        monthly_units=units_m,
        competitor_count=comp_count,
        population=population,
        overall_confidence="Medium" if population else "Low",
        threats_count=None,
        has_debt=bool(record.loan_amount and record.loan_amount > 0),
        project_cost=record.project_cost,
        own_capital=record.own_capital,
        loan_amount=record.loan_amount,
        monthly_revenue=financials.get("monthly_revenue"),
        monthly_expenses=financials.get("monthly_opex"),
        monthly_net_profit=financials.get("net_profit"),
        monthly_operating_cash_flow=cash_flow,
        monthly_emi=financials.get("monthly_emi"),
        break_even_revenue=financials.get("break_even_revenue"),
        annual_revenue=(financials.get("monthly_revenue") or 0.0) * 12.0,
        annual_net_profit=(financials.get("net_profit") or 0.0) * 12.0,
        annual_ebit=(financials["pnl_statement"]["ebit"]) * 12.0 if "pnl_statement" in financials and "ebit" in financials["pnl_statement"] else 0.0,
        category_id=category_id,
        unit_price=price,
    )
    return card.to_dict()


@router.get("/{project_id}", response_model=FinancialRecalculateResponse)
def get_financial_assumptions(project_id: str, db: DBSession = Depends(get_db)):
    """
    Get latest saved assumptions and computed canonical financial DTO.
    If no assumptions exist yet, initializes them from the session and business template.
    """
    session = db.query(Session).filter(Session.id == project_id).first()
    if not session:
        session = Session(
            id=project_id,
            margin_capital=50000.0,
            category_id="retail_kirana",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    category_id = session.category_id or "retail_kirana"
    tmpl = get_business_template(category_id)
    
    record = db.query(ProjectFinancialAssumptions).filter(ProjectFinancialAssumptions.session_id == project_id).first()
    
    if not record:
        # Initialize defaults based on capital and template
        margin = session.margin_capital or 50000.0
        promoter_pct = tmpl.promoter_contribution_pct or 25.0
        project_cost = margin / (promoter_pct / 100.0)
        loan_amount = max(0.0, project_cost - margin)
        
        selling_price = tmpl.typical_selling_price
        units_day = tmpl.typical_units_per_day
        op_days = tmpl.typical_operating_days
        var_cost = tmpl.typical_variable_cost_per_unit
        fixed_cost = tmpl.typical_monthly_fixed_cost
        rev = selling_price * units_day * op_days

        record = ProjectFinancialAssumptions(
            session_id=project_id,
            version=1,
            project_cost=round(project_cost, 2),
            own_capital=round(margin, 2),
            loan_amount=round(loan_amount, 2),
            is_direct_revenue_mode=False,
            monthly_revenue=round(rev, 2),
            selling_price=round(selling_price, 2),
            units_per_day=round(units_day, 2),
            operating_days=op_days,
            variable_cost_per_unit=round(var_cost, 2),
            monthly_expenses=round(fixed_cost, 2),
            interest_rate_annual_pct=9.0,
            loan_tenure_months=60,
            moratorium_months=0,
            tax_rate_pct=None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    financials, warnings = _build_and_compute(record, category_id, db)
    db.commit()

    score_dict = _compute_scores_for_session(record, financials, session, category_id)


    assumptions_dto = FinancialAssumptionsDTO(
        session_id=record.session_id,
        version=record.version,
        project_cost=record.project_cost,
        own_capital=record.own_capital,
        loan_amount=record.loan_amount,
        is_direct_revenue_mode=record.is_direct_revenue_mode,
        monthly_revenue=record.monthly_revenue,
        selling_price=record.selling_price,
        units_per_day=record.units_per_day,
        operating_days=record.operating_days,
        variable_cost_per_unit=record.variable_cost_per_unit,
        monthly_expenses=record.monthly_expenses,
        interest_rate_annual_pct=record.interest_rate_annual_pct,
        loan_tenure_months=record.loan_tenure_months,
        moratorium_months=record.moratorium_months,
        tax_rate_pct=record.tax_rate_pct,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
        last_updated_ist=_to_ist_str(record.updated_at),
        validation_warnings=warnings,
    )

    return FinancialRecalculateResponse(
        status="success" if not warnings else "warning",
        assumptions_version=record.version,
        last_updated_ist=_to_ist_str(record.updated_at),
        validation_warnings=warnings,
        assumptions=assumptions_dto,
        financials=financials,
        scores=score_dict,
    )



@router.post("/recalculate", response_model=FinancialRecalculateResponse)
def recalculate_financial_assumptions(req: FinancialRecalculateRequest, db: DBSession = Depends(get_db)):
    """
    Validate assumptions, check optimistic concurrency, persist to DB with audit log,
    compute canonical financial model, and return updated DTO.
    """
    session = db.query(Session).filter(Session.id == req.session_id).first()
    if not session:
        cat_id = req.category_id or "retail_kirana"
        session = Session(
            id=req.session_id,
            margin_capital=float(req.assumptions.own_capital or 50000.0),
            category_id=cat_id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    category_id = req.category_id or session.category_id or "retail_kirana"
    tmpl = get_business_template(category_id)
    
    inp = req.assumptions
    record = db.query(ProjectFinancialAssumptions).filter(ProjectFinancialAssumptions.session_id == req.session_id).first()
    
    old_dict = {}
    current_version = 0
    if record:
        current_version = record.version
        if inp.version is not None and inp.version != record.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflict: Assumptions have been modified (current version {record.version}, submitted version {inp.version}). Please refresh."
            )
        old_dict = {
            "project_cost": record.project_cost,
            "own_capital": record.own_capital,
            "loan_amount": record.loan_amount,
            "monthly_revenue": record.monthly_revenue,
            "selling_price": record.selling_price,
            "units_per_day": record.units_per_day,
            "operating_days": record.operating_days,
            "variable_cost_per_unit": record.variable_cost_per_unit,
            "monthly_expenses": record.monthly_expenses,
            "interest_rate_annual_pct": record.interest_rate_annual_pct,
            "loan_tenure_months": record.loan_tenure_months,
            "is_direct_revenue_mode": record.is_direct_revenue_mode,
        }

    # Derive fields if omitted
    project_cost = float(inp.project_cost)
    own_capital = float(inp.own_capital)
    loan_amount = float(inp.loan_amount if inp.loan_amount is not None else max(0.0, project_cost - own_capital))
    
    is_direct = bool(inp.is_direct_revenue_mode)
    op_days = int(inp.operating_days or 30)
    
    if is_direct:
        if inp.monthly_revenue is None or inp.monthly_revenue < 0:
            raise HTTPException(status_code=422, detail="Direct Monthly Revenue is required when direct revenue mode is active.")
        monthly_rev = float(inp.monthly_revenue)
        price = float(inp.selling_price or tmpl.typical_selling_price)
        units_day = float(inp.units_per_day or (monthly_rev / price / op_days if price > 0 and op_days > 0 else 1.0))
        var_cost = float(inp.variable_cost_per_unit if inp.variable_cost_per_unit is not None else (price * (tmpl.typical_cogs_pct / 100.0)))
    else:
        price = float(inp.selling_price if inp.selling_price is not None else tmpl.typical_selling_price)
        units_day = float(inp.units_per_day if inp.units_per_day is not None else tmpl.typical_units_per_day)
        var_cost = float(inp.variable_cost_per_unit if inp.variable_cost_per_unit is not None else (price * (tmpl.typical_cogs_pct / 100.0)))
        monthly_rev = price * units_day * op_days

    fixed_cost = float(inp.monthly_expenses if inp.monthly_expenses is not None else tmpl.typical_monthly_fixed_cost)
    interest_rate = float(inp.interest_rate_annual_pct if inp.interest_rate_annual_pct is not None else 9.0)
    tenure = int(inp.loan_tenure_months if inp.loan_tenure_months is not None else 60)
    moratorium = int(inp.moratorium_months or 0)
    tax_rate = float(inp.tax_rate_pct) if inp.tax_rate_pct is not None else None

    new_version = current_version + 1

    if not record:
        record = ProjectFinancialAssumptions(
            session_id=req.session_id,
            version=new_version,
            project_cost=project_cost,
            own_capital=own_capital,
            loan_amount=loan_amount,
            is_direct_revenue_mode=is_direct,
            monthly_revenue=monthly_rev,
            selling_price=price,
            units_per_day=units_day,
            operating_days=op_days,
            variable_cost_per_unit=var_cost,
            monthly_expenses=fixed_cost,
            interest_rate_annual_pct=interest_rate,
            loan_tenure_months=tenure,
            moratorium_months=moratorium,
            tax_rate_pct=tax_rate,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(record)
    else:
        record.version = new_version
        record.project_cost = project_cost
        record.own_capital = own_capital
        record.loan_amount = loan_amount
        record.is_direct_revenue_mode = is_direct
        record.monthly_revenue = monthly_rev
        record.selling_price = price
        record.units_per_day = units_day
        record.operating_days = op_days
        record.variable_cost_per_unit = var_cost
        record.monthly_expenses = fixed_cost
        record.interest_rate_annual_pct = interest_rate
        record.loan_tenure_months = tenure
        record.moratorium_months = moratorium
        record.tax_rate_pct = tax_rate
        record.updated_at = datetime.now(timezone.utc)

    # Record Audit Trail
    audit_entry = FinancialAssumptionsAudit(
        session_id=req.session_id,
        version_from=current_version,
        version_to=new_version,
        changed_by=req.changed_by or "user",
        old_assumptions=old_dict,
        new_assumptions={
            "project_cost": project_cost,
            "own_capital": own_capital,
            "loan_amount": loan_amount,
            "monthly_revenue": monthly_rev,
            "selling_price": price,
            "units_per_day": units_day,
            "operating_days": op_days,
            "variable_cost_per_unit": var_cost,
            "monthly_expenses": fixed_cost,
            "interest_rate_annual_pct": interest_rate,
            "loan_tenure_months": tenure,
            "is_direct_revenue_mode": is_direct,
        }
    )
    db.add(audit_entry)

    financials, warnings = _build_and_compute(record, category_id, db)
    db.commit()
    db.refresh(record)

    score_dict = _compute_scores_for_session(record, financials, session, category_id)

    assumptions_dto = FinancialAssumptionsDTO(
        session_id=record.session_id,
        version=record.version,
        project_cost=record.project_cost,
        own_capital=record.own_capital,
        loan_amount=record.loan_amount,
        is_direct_revenue_mode=record.is_direct_revenue_mode,
        monthly_revenue=record.monthly_revenue,
        selling_price=record.selling_price,
        units_per_day=record.units_per_day,
        operating_days=record.operating_days,
        variable_cost_per_unit=record.variable_cost_per_unit,
        monthly_expenses=record.monthly_expenses,
        interest_rate_annual_pct=record.interest_rate_annual_pct,
        loan_tenure_months=record.loan_tenure_months,
        moratorium_months=record.moratorium_months,
        tax_rate_pct=record.tax_rate_pct,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
        last_updated_ist=_to_ist_str(record.updated_at),
        validation_warnings=warnings,
    )

    return FinancialRecalculateResponse(
        status="success" if not warnings else "warning",
        assumptions_version=record.version,
        last_updated_ist=_to_ist_str(record.updated_at),
        validation_warnings=warnings,
        assumptions=assumptions_dto,
        financials=financials,
        scores=score_dict,
    )

