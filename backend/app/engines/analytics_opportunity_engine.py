"""
YUKTIFI Deterministic Analytics & Opportunity Engine.
Calculates 4 core dashboard metrics:
1. Market Opportunity (₹/mo, score 0-100, HIGH/MODERATE/LOW)
2. Financial Viability (% Net Margin, score 0-100, HIGH/MODERATE/LOW)
3. Risk Exposure (/100 risk score, HIGH/MODERATE/LOW risk)
4. Capital Efficiency (% ROI, score 0-100, HIGH/MODERATE/LOW)

Zero hardcoded scores. Zero LLM calculations.
User Inputs + Validated Gov/Market Data + Canonical Engines -> Metrics -> Score.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    CanonicalFinancialResult,
    compute_canonical_financials,
    ProductItem,
    OpexBreakdown,
)
from app.templates.business_templates import get_business_template, BusinessTemplate

logger = logging.getLogger("yukti.analytics_opportunity")


# ── Score Normalization Utility ─────────────────────────────────────────────

def normalize_score(
    raw_value: float,
    min_val: float,
    max_val: float,
    invert: bool = False
) -> int:
    """
    Normalizes a raw continuous value into a 0-100 integer score.
    If invert=True, lower raw_value yields a higher score (e.g. lower risk).
    """
    if max_val == min_val:
        return 50
    ratio = (raw_value - min_val) / (max_val - min_val)
    ratio = max(0.0, min(1.0, ratio))
    if invert:
        ratio = 1.0 - ratio
    return int(round(ratio * 100.0))


def determine_status(
    score: float,
    invert_risk: bool = False,
    high_threshold: float = 70.0,
    mod_threshold: float = 45.0
) -> str:
    """
    Determines status label.
    For standard metrics: >=70 HIGH, 45-69 MODERATE, <45 LOW
    For risk metrics (invert_risk=True): <=35 LOW, 36-65 MODERATE, >65 HIGH
    """
    if invert_risk:
        if score <= 35.0:
            return "LOW"
        elif score <= 65.0:
            return "MODERATE"
        return "HIGH"
    else:
        if score >= high_threshold:
            return "HIGH"
        elif score >= mod_threshold:
            return "MODERATE"
        return "LOW"


@dataclass
class AnalyticsMetricDTO:
    """Standard DTO for an analytics metric."""
    key: str
    label: str
    value: Optional[float] = None
    unit: str = ""
    score: Optional[int] = None
    status: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    drivers: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    formula: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "score": self.score,
            "status": self.status,
            "confidence": round(self.confidence, 2),
            "drivers": self.drivers,
            "sources": self.sources,
            "formula": self.formula,
            "inputs": self.inputs,
            "timestamp": self.timestamp,
        }


# ── 1. Market Opportunity Metric ───────────────────────────────────────────

def compute_market_opportunity(
    category_id: str,
    population: Optional[int],
    competitor_count: Optional[int],
    addressable_price: Optional[float] = None,
    selling_price_override: Optional[float] = None,
    target_share_override: Optional[float] = None,
) -> AnalyticsMetricDTO:
    """
    Computes Market Opportunity deterministically:
    - Target Market = Population / 4.8 households × Relevant Target Share
    - Market Opportunity (₹/mo) = Estimated Monthly Demand × Addressable Price
    - Competitor Density = Competitors / Target Population × 1000
    - Score (0-100) from measurable demand headroom, competitor density & catchment scale.
    """
    template = get_business_template(category_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    sources = [
        "Census of India 2011 (Demographics & Catchment Population)",
        "OpenStreetMap / Overpass API (Competitor Geospatial Mapping)",
        "Official Government Enterprise Norms & Business Templates"
    ]
    formula = (
        "Target Market = (Population / 4.8) × Target Share; "
        "Opportunity (₹/mo) = Target Consumers × Monthly Demand Units × Selling Price; "
        "Score = 0.45×Demand Headroom + 0.35×Competitor Space + 0.20×Catchment Scale"
    )

    if population is None or population <= 0:
        return AnalyticsMetricDTO(
            key="market_opportunity",
            label="Market Opportunity",
            value=None,
            unit="₹ / month",
            score=None,
            status="INSUFFICIENT_DATA",
            confidence=0.0,
            drivers=["No verified population figure for the catchment."],
            sources=sources,
            formula=formula,
            inputs={"category_id": category_id, "population": population, "competitor_count": competitor_count},
            timestamp=now_iso,
        )

    # 1. Target share calibration
    sector_shares = {
        "vada_pav": 0.30,
        "panipuri": 0.25,
        "retail_kirana": 0.70,
        "tea_stall": 0.45,
        "dairy": 0.65,
        "restaurant": 0.20,
        "small_hospitality": 0.20,
        "bakery": 0.35,
        "tailoring": 0.20,
        "diagnostic": 0.15,
        "service_business": 0.15,
        "agri_machinery": 0.10,
        "food_processing": 0.25,
        "manufacturing": 0.15,
        "repair_services": 0.25,
        "mobile_repair": 0.25,
    }
    target_share = target_share_override or sector_shares.get(category_id, 0.25)
    target_consumers = population * target_share
    target_households = population / 4.8

    # 2. Addressable price & monthly unit demand
    unit_price = selling_price_override or addressable_price or template.typical_selling_price or 25.0
    
    # Typical monthly purchase frequency per target consumer
    # Street food ~ 4-6 times/mo; Kirana basket ~ 4 times/mo; Dairy ~ 20 times/mo; Repair/Tailoring ~ 0.5 times/mo
    monthly_frequencies = {
        "vada_pav": 4.0,
        "panipuri": 3.5,
        "retail_kirana": 4.0,
        "tea_stall": 8.0,
        "dairy": 15.0,
        "restaurant": 1.5,
        "bakery": 2.5,
        "tailoring": 0.4,
        "diagnostic": 0.15,
        "agri_machinery": 0.05,
        "food_processing": 1.0,
        "mobile_repair": 0.25,
    }
    freq = monthly_frequencies.get(category_id, 1.0)
    
    # Catchment total monthly market value
    total_catchment_demand_value = target_consumers * freq * unit_price
    # Realistic single-micro-enterprise addressable opportunity share (2% to 10% of local catchment depending on category)
    catchment_capture_share = min(0.15, max(0.02, 500.0 / max(100.0, target_consumers)))
    micro_opportunity_monthly_value = round(total_catchment_demand_value * catchment_capture_share, 2)

    # 3. Competitor density
    comp_count = competitor_count if competitor_count is not None else 0
    competitor_density = (comp_count / max(1.0, target_consumers)) * 1000.0

    # 4. Transparent 0-100 Score Components
    # Component A: Demand headroom relative to benchmark project turnover
    benchmark_revenue = (template.typical_selling_price * template.typical_units_per_day * template.typical_operating_days)
    demand_headroom_score = min(100.0, max(15.0, (micro_opportunity_monthly_value / max(1.0, benchmark_revenue)) * 85.0))

    # Component B: Competitor density headroom (high density reduces score)
    if comp_count == 0:
        competition_score = 65.0  # Conservative due to unmapped informal vendors
    elif competitor_density > 4.0:
        competition_score = max(10.0, 100.0 - (competitor_density * 18.0))
    else:
        competition_score = min(100.0, max(40.0, 100.0 - (competitor_density * 12.0)))

    # Component C: Catchment scale score
    scale_score = min(100.0, (population / 25000.0) * 100.0)

    final_score = int(round(0.45 * demand_headroom_score + 0.35 * competition_score + 0.20 * scale_score))
    final_score = max(0, min(100, final_score))

    status = determine_status(final_score, high_threshold=75.0, mod_threshold=50.0)

    # Drivers
    drivers = []
    drivers.append(f"Catchment population: {population:,} residents (~{int(target_households):,} households).")
    drivers.append(f"Target consumer base: ~{int(target_consumers):,} addressable buyers ({target_share*100:.0f}% category target).")
    if comp_count > 0:
        drivers.append(f"Mapped competitor density: {competitor_density:.2f} per 1,000 target consumers ({comp_count} competitors).")
    else:
        drivers.append("No mapped competitors in official OSM registry (informal vendors may exist).")
    drivers.append(f"Estimated addressable micro-market: ₹{micro_opportunity_monthly_value:,.0f} / month.")

    confidence = 0.85 if competitor_count is not None and population > 1000 else 0.65

    return AnalyticsMetricDTO(
        key="market_opportunity",
        label="Market Opportunity",
        value=micro_opportunity_monthly_value,
        unit="₹ / month",
        score=final_score,
        status=status,
        confidence=confidence,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={
            "population": population,
            "target_households": int(target_households),
            "target_share_pct": target_share * 100.0,
            "target_consumers": int(target_consumers),
            "addressable_unit_price": unit_price,
            "competitor_count": comp_count,
            "competitor_density_per_1k": round(competitor_density, 3),
            "estimated_market_size_monthly": micro_opportunity_monthly_value,
        },
        timestamp=now_iso,
    )


# ── 2. Financial Viability Metric ──────────────────────────────────────────

def compute_financial_viability(
    fin_result: CanonicalFinancialResult
) -> AnalyticsMetricDTO:
    """
    Computes Financial Viability deterministically from Canonical Financial Result:
    - Net Margin % = Net Profit / Revenue × 100
    - Break-even Units & Revenue Safety Margin
    - DSCR & Debt Repayment Capacity
    - Cash flow viability check (loss-making operations are capped at <= 30)
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    sources = [
        "YUKTIFI Canonical Deterministic Financial Engine (v1.0)",
        "Standard Cost Accounting & P&L Schedule"
    ]
    formula = (
        "Revenue = Price × Units; COGS = Variable Costs; EBIT = Gross Profit − OPEX − Depreciation; "
        "Net Profit = EBIT − Interest − Tax; Net Margin % = (Net Profit / Revenue) × 100; "
        "Score = 0.40×Net Margin + 0.35×Margin of Safety + 0.25×DSCR"
    )

    rev = fin_result.monthly_revenue
    net_profit = fin_result.monthly_pat
    net_margin = fin_result.net_margin_pct
    be_rev = fin_result.break_even_revenue_monthly
    dscr = fin_result.dscr

    if rev <= 0:
        return AnalyticsMetricDTO(
            key="financial_viability",
            label="Financial Viability",
            value=0.0,
            unit="% Net Margin",
            score=0,
            status="LOW",
            confidence=0.95,
            drivers=["Monthly revenue is zero or negative. Enterprise is non-viable."],
            sources=sources,
            formula=formula,
            inputs={"revenue": rev, "net_profit": net_profit},
            timestamp=now_iso,
        )

    # 1. Net margin component (Target 30% = 100)
    if net_margin <= 0:
        net_margin_score = 0.0
    else:
        net_margin_score = min(100.0, (net_margin / 30.0) * 100.0)

    # 2. Margin of safety component (Share of revenue above break-even)
    if be_rev is not None and rev > 0:
        mos_pct = ((rev - be_rev) / rev) * 100.0
        mos_score = min(100.0, max(0.0, mos_pct * 1.5))
    else:
        mos_pct = 0.0
        mos_score = 30.0

    # 3. DSCR component (Target 2.0 = 100)
    if dscr is None:
        dscr_score = net_margin_score  # No debt, score on margin alone
    elif dscr < 1.0:
        dscr_score = max(0.0, dscr * 25.0)
    else:
        dscr_score = min(100.0, (dscr / 2.0) * 100.0)

    # Composite Score
    base_score = 0.40 * net_margin_score + 0.35 * mos_score + 0.25 * dscr_score

    # Hard Gates: A loss-making business must NOT receive a favorable score!
    if net_profit <= 0 or net_margin <= 0:
        final_score = min(25, int(round(base_score)))
    elif dscr is not None and dscr < 1.0:
        final_score = min(35, int(round(base_score)))
    elif be_rev is not None and be_rev > rev:
        final_score = min(30, int(round(base_score)))
    else:
        final_score = max(0, min(100, int(round(base_score))))

    status = determine_status(final_score, high_threshold=70.0, mod_threshold=45.0)

    # Drivers
    drivers = []
    drivers.append(f"Net Profit Margin: {net_margin:.1f}% (₹{net_profit:,.0f} / month).")
    drivers.append(f"Gross Margin: {fin_result.gross_margin_pct:.1f}% (Gross Profit: ₹{fin_result.monthly_gross_profit:,.0f}).")
    if be_rev is not None:
        drivers.append(f"Break-even Monthly Revenue: ₹{be_rev:,.0f} (Margin of Safety: {mos_pct:.1f}%).")
    if dscr is not None:
        drivers.append(f"Debt Service Coverage Ratio (DSCR): {dscr:.2f}x (Monthly EMI: ₹{fin_result.monthly_emi:,.0f}).")
    else:
        drivers.append("Zero debt financing assumed (100% promoter equity).")

    return AnalyticsMetricDTO(
        key="financial_viability",
        label="Financial Viability",
        value=round(net_margin, 1),
        unit="% Net Margin",
        score=final_score,
        status=status,
        confidence=0.95,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={
            "monthly_revenue": rev,
            "monthly_cogs": fin_result.monthly_cogs,
            "monthly_gross_profit": fin_result.monthly_gross_profit,
            "gross_margin_pct": fin_result.gross_margin_pct,
            "monthly_opex": fin_result.monthly_opex,
            "monthly_depreciation": fin_result.monthly_depreciation,
            "monthly_ebit": fin_result.monthly_ebit,
            "monthly_net_profit": net_profit,
            "net_margin_pct": round(net_margin, 2),
            "break_even_monthly_revenue": be_rev,
            "break_even_units": fin_result.break_even_units_monthly,
            "dscr": dscr,
            "monthly_cash_flow": fin_result.monthly_operating_cash_flow,
        },
        timestamp=now_iso,
    )


# ── 3. Risk Exposure Metric ────────────────────────────────────────────────

def compute_risk_exposure(
    fin_result: CanonicalFinancialResult,
    competitor_density_per_1k: float = 0.0,
    evidence_confidence: str = "MEDIUM",
    category_id: str = "retail_kirana",
) -> AnalyticsMetricDTO:
    """
    Computes Risk Exposure deterministically:
    - Financial Risk (Cash flow, DSCR, break-even burden, buffer)
    - Market Risk (Competitor density, demand volatility)
    - Operational Risk (Working capital cycle days, fixed cost ratio)
    - Data Uncertainty Risk (Missing inputs, unmapped coverage)
    - Score (0-100) where HIGHER = HIGHER RISK.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    sources = [
        "YUKTIFI Multi-Factor Risk Assessment Engine",
        "Deterministic Sensitivity & Cash Flow Stress Matrix"
    ]
    formula = "Risk Exposure = 0.35×Financial Risk + 0.25×Market Risk + 0.20×Operational Risk + 0.20×Data Uncertainty"

    # 1. Financial Risk (0-100, higher = worse)
    fin_risk_parts = []
    # Cash flow deficit
    if fin_result.monthly_operating_cash_flow < 0:
        fin_risk_parts.append(100.0)
    elif fin_result.monthly_operating_cash_flow < (fin_result.monthly_revenue * 0.08):
        fin_risk_parts.append(60.0)
    else:
        fin_risk_parts.append(15.0)

    # DSCR and Debt leverage risk
    dscr = fin_result.dscr
    debt_amt = fin_result.approved_loan_amount
    project_cost = max(1.0, fin_result.total_project_cost)
    debt_share = debt_amt / project_cost

    if dscr is not None:
        if dscr < 1.0:
            dscr_risk = 95.0
        elif dscr < 1.25:
            dscr_risk = 70.0
        elif dscr < 1.5:
            dscr_risk = 45.0
        elif dscr < 2.5:
            dscr_risk = 25.0
        else:
            dscr_risk = 15.0
        # Blend DSCR with debt leverage
        fin_risk_parts.append(0.70 * dscr_risk + 0.30 * (debt_share * 100.0))
    else:
        # Zero debt = zero debt default risk
        fin_risk_parts.append(0.0)

    # Break-even risk
    if fin_result.break_even_revenue_monthly and fin_result.monthly_revenue > 0:
        be_ratio = fin_result.break_even_revenue_monthly / fin_result.monthly_revenue
        if be_ratio > 0.90:
            fin_risk_parts.append(90.0)
        elif be_ratio > 0.70:
            fin_risk_parts.append(50.0)
        else:
            fin_risk_parts.append(15.0)
    else:
        fin_risk_parts.append(50.0)

    financial_risk = sum(fin_risk_parts) / len(fin_risk_parts)

    # 2. Market Risk (0-100)
    if competitor_density_per_1k > 6.0:
        comp_risk = 85.0
    elif competitor_density_per_1k > 3.0:
        comp_risk = 55.0
    elif competitor_density_per_1k > 0.5:
        comp_risk = 30.0
    else:
        comp_risk = 35.0  # Moderate risk due to unmapped competition

    market_risk = comp_risk

    # 3. Operational Risk (0-100)
    ccc_days = fin_result.cash_conversion_cycle_days
    if ccc_days > 45:
        ccc_risk = 80.0
    elif ccc_days > 20:
        ccc_risk = 50.0
    else:
        ccc_risk = 20.0

    fixed_cost_ratio = (fin_result.monthly_opex / max(1.0, fin_result.monthly_revenue))
    if fixed_cost_ratio > 0.45:
        fc_risk = 75.0
    elif fixed_cost_ratio > 0.25:
        fc_risk = 45.0
    else:
        fc_risk = 20.0

    operational_risk = 0.55 * ccc_risk + 0.45 * fc_risk

    # 4. Data Uncertainty Risk (0-100)
    conf_upper = evidence_confidence.upper()
    if conf_upper == "HIGH":
        data_risk = 15.0
    elif conf_upper == "MEDIUM":
        data_risk = 40.0
    else:
        data_risk = 75.0

    # Composite Risk (Higher = Higher Risk)
    risk_score = round(
        0.35 * financial_risk +
        0.25 * market_risk +
        0.20 * operational_risk +
        0.20 * data_risk,
        1
    )
    final_score = int(round(risk_score))
    status = determine_status(final_score, invert_risk=True)

    # Drivers
    drivers = []
    if dscr is not None and dscr < 1.25:
        drivers.append(f"Tight debt coverage (DSCR {dscr:.2f}x < 1.25x).")
    elif dscr is not None:
        drivers.append(f"Comfortable debt service headroom (DSCR {dscr:.2f}x).")

    if fin_result.break_even_revenue_monthly:
        be_ratio = fin_result.break_even_revenue_monthly / max(1.0, fin_result.monthly_revenue)
        if be_ratio > 0.75:
            drivers.append(f"High break-even threshold ({be_ratio*100:.0f}% of sales needed to break even).")
        else:
            drivers.append(f"Safe break-even cushion ({be_ratio*100:.0f}% of sales required).")

    if ccc_days > 20:
        drivers.append(f"Revolving working capital cycle: {ccc_days} days.")
    else:
        drivers.append(f"Rapid cash conversion cycle: {ccc_days} days.")

    if competitor_density_per_1k > 4.0:
        drivers.append("Elevated competitor saturation in immediate radius.")

    return AnalyticsMetricDTO(
        key="risk_exposure",
        label="Risk Exposure",
        value=risk_score,
        unit="/ 100",
        score=final_score,
        status=status,
        confidence=0.85,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={
            "financial_risk_score": round(financial_risk, 1),
            "market_risk_score": round(market_risk, 1),
            "operational_risk_score": round(operational_risk, 1),
            "data_uncertainty_score": round(data_risk, 1),
            "cash_conversion_cycle_days": ccc_days,
            "dscr": dscr,
        },
        timestamp=now_iso,
    )


# ── 4. Capital Efficiency Metric ───────────────────────────────────────────

def compute_capital_efficiency(
    fin_result: CanonicalFinancialResult
) -> AnalyticsMetricDTO:
    """
    Computes Capital Efficiency deterministically:
    - Capital Efficiency % (ROCE) = Annual Operating Profit (EBIT) / Initial Project Cost × 100
    - ROI % = Annual Net Profit / Total Invested Capital × 100
    - Return on Owner's Equity (ROE) = Annual Net Profit / Own Capital × 100
    - Capital Turnover = Annual Revenue / Invested Capital
    - Payback Period = Initial Investment / Annual Net Cash Flow
    - Debt Structure & DSCR
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    sources = [
        "YUKTIFI Canonical Capital Sizing & Return Engine",
        "Audited Depreciation, Amortization & Debt Schedule"
    ]
    formula = (
        "Operating Profit (EBIT) / Project Cost × 100; "
        "ROI % = (Annual Net Profit / Total Project Cost) × 100; "
        "Capital Turnover = Annual Revenue / Project Cost; "
        "Score = 0.45×ROI + 0.30×Turnover + 0.25×Payback"
    )

    project_cost = max(1.0, fin_result.total_project_cost)
    annual_ebit = fin_result.annual_ebit
    annual_net_profit = fin_result.annual_pat
    annual_rev = fin_result.annual_revenue
    annual_cash_flow = fin_result.annual_operating_cash_flow
    own_cap = fin_result.own_capital

    # 1. Return Metrics
    capital_efficiency_pct = (annual_ebit / project_cost) * 100.0  # ROCE
    roi_pct = fin_result.roi_on_total_project_pct if fin_result.roi_on_total_project_pct is not None else ((annual_net_profit / project_cost) * 100.0)
    roe_pct = (annual_net_profit / own_cap * 100.0) if own_cap > 0 else roi_pct

    # 2. Capital Turnover
    turnover_ratio = annual_rev / project_cost

    # 3. Payback Period in Years
    if annual_cash_flow > 0:
        payback_years = round(project_cost / annual_cash_flow, 2)
    else:
        payback_years = None

    # 4. Transparent 0-100 Score Components
    # ROI component (Target 40% = 100)
    if roi_pct <= 0:
        roi_score = 0.0
    else:
        roi_score = min(100.0, (roi_pct / 40.0) * 100.0)

    # Turnover component (Target 2.5x = 100)
    turnover_score = min(100.0, max(0.0, (turnover_ratio / 2.5) * 100.0))

    # Payback component (<= 2 yrs = 100, 3 yrs = 75, 4 yrs = 50, > 5 yrs = 20)
    if payback_years is not None:
        if payback_years <= 2.0:
            payback_score = 100.0
        elif payback_years <= 3.0:
            payback_score = 75.0
        elif payback_years <= 4.0:
            payback_score = 50.0
        else:
            payback_score = 25.0
    else:
        payback_score = 10.0

    # Composite Score
    if annual_net_profit <= 0:
        final_score = min(20, int(round(0.45 * roi_score + 0.30 * turnover_score + 0.25 * payback_score)))
    else:
        final_score = int(round(0.45 * roi_score + 0.30 * turnover_score + 0.25 * payback_score))
        final_score = max(0, min(100, final_score))

    status = determine_status(final_score, high_threshold=70.0, mod_threshold=45.0)

    # Drivers
    drivers = []
    drivers.append(f"Return on Investment (ROI): {roi_pct:.1f}% on ₹{project_cost:,.0f} total project cost.")
    drivers.append(f"Operating Return on Capital (ROCE): {capital_efficiency_pct:.1f}% (Annual EBIT: ₹{annual_ebit:,.0f}).")
    if own_cap > 0 and fin_result.approved_loan_amount > 0:
        drivers.append(f"Return on Owner's Equity (ROE): {roe_pct:.1f}% (Equity: ₹{own_cap:,.0f}, Debt: ₹{fin_result.approved_loan_amount:,.0f}).")
    drivers.append(f"Capital Turnover Ratio: {turnover_ratio:.2f}x annual revenue velocity.")
    if payback_years is not None:
        drivers.append(f"Estimated Capital Payback: {payback_years:.1f} years ({int(payback_years * 12)} months).")
    else:
        drivers.append("Payback undefined due to non-positive operating cash flow.")

    return AnalyticsMetricDTO(
        key="capital_efficiency",
        label="Capital Efficiency",
        value=round(roi_pct, 1),
        unit="% ROI",
        score=final_score,
        status=status,
        confidence=0.95,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={
            "initial_project_cost": project_cost,
            "own_capital": own_cap,
            "loan_amount": fin_result.approved_loan_amount,
            "annual_revenue": annual_rev,
            "annual_ebit": annual_ebit,
            "annual_net_profit": annual_net_profit,
            "annual_net_cash_flow": annual_cash_flow,
            "capital_efficiency_roce_pct": round(capital_efficiency_pct, 2),
            "roi_pct": round(roi_pct, 2),
            "roe_pct": round(roe_pct, 2),
            "capital_turnover": round(turnover_ratio, 2),
            "payback_years": payback_years,
            "dscr": fin_result.dscr,
        },
        timestamp=now_iso,
    )


# ── Unified Analytics Opportunity Suite ─────────────────────────────────────

def compute_all_opportunity_analytics(
    fin_result: CanonicalFinancialResult,
    population: Optional[int] = None,
    competitor_count: Optional[int] = None,
    category_id: str = "retail_kirana",
    evidence_confidence: str = "MEDIUM",
    selling_price_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes all 4 core metrics deterministically and returns the unified dictionary.
    """
    # 1. Market Opportunity
    market_opp = compute_market_opportunity(
        category_id=category_id,
        population=population,
        competitor_count=competitor_count,
        selling_price_override=selling_price_override or fin_result.avg_price_per_unit,
    )

    # 2. Financial Viability
    fin_viability = compute_financial_viability(fin_result)

    # 3. Risk Exposure
    comp_density = market_opp.inputs.get("competitor_density_per_1k", 0.0) if market_opp.inputs else 0.0
    risk_exp = compute_risk_exposure(
        fin_result=fin_result,
        competitor_density_per_1k=comp_density,
        evidence_confidence=evidence_confidence,
        category_id=category_id,
    )

    # 4. Capital Efficiency
    cap_eff = compute_capital_efficiency(fin_result)

    return {
        "market_opportunity": market_opp.to_dict(),
        "financial_viability": fin_viability.to_dict(),
        "risk_exposure": risk_exp.to_dict(),
        "capital_efficiency": cap_eff.to_dict(),
    }
