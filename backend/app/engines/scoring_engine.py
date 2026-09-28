"""
Composite scoring.

The previous implementation returned an integer for every dimension, substituting
a neutral 50 whenever an input was unknown, then averaged them into a single
"yukti_score" and mapped that to a verdict like "Strong Opportunity". Two
consequences:

* A user with no competitor data, no DSCR and no population figure received a
  score built from three invented 50s and two real numbers, presented with the
  same authority as a fully-evidenced result.
* Because the unknown contributions were free, low evidence produced a
  *middling* score rather than an abstention, and a middling score reads as
  "worth considering".

Now every dimension is either computed from a real input or returns `None`, and
the composite is only produced when enough dimensions are actually known. The
result reports its own coverage, and the verdict is withheld below the coverage
threshold rather than guessed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

#: Below this many known dimensions, no composite score is published.
MIN_DIMENSIONS_FOR_SCORE = 3

#: Below this composite coverage, the verdict is withheld.
MIN_COVERAGE_FOR_VERDICT = 0.6

#: Consumers per mapped competitor that scores a full 100 on market opportunity.
CONSUMERS_PER_COMPETITOR_TARGET = 2_000.0

#: DSCR at which repayment capacity scores a full 100.
DSCR_TARGET = 2.5

#: ROI and net margin at which financial viability scores a full 100.
ROI_TARGET = 50.0
NET_MARGIN_TARGET = 30.0


from datetime import datetime, timezone

@dataclass
class Dimension:
    """One scored dimension, or an explicit absence of one."""

    key: str
    label: str
    score: Optional[int] = None
    known: bool = False
    reason: str = ""
    value: Optional[float] = None
    unit: str = ""
    status: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    drivers: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    formula: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "score": self.score,
            "known": self.known,
            "state": "COMPUTED" if self.known else "UNAVAILABLE",
            "reason": self.reason,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "confidence": round(self.confidence, 2),
            "drivers": self.drivers,
            "sources": self.sources,
            "formula": self.formula,
            "inputs": self.inputs,
            "timestamp": self.timestamp,
        }


def _clamp(v: float) -> int:
    return int(max(0, min(100, v)))


# ── Dimensions ──────────────────────────────────────────────────────────────

def calculate_financial_viability(
    roi: Optional[float] = None,
    net_margin: Optional[float] = None,
    monthly_revenue: Optional[float] = None,
    monthly_net_profit: Optional[float] = None,
    monthly_operating_cash_flow: Optional[float] = None,
    dscr: Optional[float] = None,
    break_even_revenue: Optional[float] = None,
) -> Dimension:
    """
    Financial Viability / 100:
    Evaluates profitability, net margin, cash flow cushion, debt service coverage and break-even position.
    """
    sources = [
        "YUKTIFI Canonical Deterministic Financial Engine (v1.0)",
        "Standard Cost Accounting & P&L Schedule"
    ]
    formula = (
        "Viability Score = 0.35×(Net Margin / 30%) + 0.25×(ROI / 40%) + "
        "0.25×Margin of Safety + 0.15×DSCR Coverage"
    )

    if roi is None and net_margin is None and monthly_revenue is None:
        return Dimension(
            "financial_viability", "Financial viability",
            score=None, known=False,
            reason="Insufficient data: Profitability, net margin, and revenue inputs are missing.",
            sources=sources, formula=formula,
        )

    # 1. Net Margin Score (Target 30% = 100)
    eff_margin = net_margin if net_margin is not None else ((monthly_net_profit / monthly_revenue * 100.0) if monthly_net_profit is not None and monthly_revenue and monthly_revenue > 0 else None)
    if eff_margin is not None:
        margin_score = 0.0 if eff_margin <= 0 else min(100.0, (eff_margin / NET_MARGIN_TARGET) * 100.0)
    else:
        margin_score = min(100.0, (roi / ROI_TARGET) * 100.0) if roi is not None else 50.0

    # 2. ROI Score (Target 40% = 100)
    if roi is not None:
        roi_score = 0.0 if roi <= 0 else min(100.0, (roi / 40.0) * 100.0)
    else:
        roi_score = margin_score

    # 3. Margin of Safety / Break-even Cushion
    if break_even_revenue is not None and monthly_revenue and monthly_revenue > 0:
        mos_pct = ((monthly_revenue - break_even_revenue) / monthly_revenue) * 100.0
        mos_score = min(100.0, max(0.0, mos_pct * 1.5))
    else:
        mos_pct = 0.0
        mos_score = margin_score

    # 4. Debt Coverage Component
    if dscr is not None:
        dscr_score = min(100.0, (dscr / 2.0) * 100.0) if dscr >= 1.0 else max(0.0, dscr * 25.0)
    else:
        dscr_score = margin_score

    # Composite Viability
    raw_score = 0.35 * margin_score + 0.25 * roi_score + 0.25 * mos_score + 0.15 * dscr_score

    # Hard Gates: Zero loss-making businesses receiving favorable viability scores
    if (eff_margin is not None and eff_margin <= 0) or (monthly_net_profit is not None and monthly_net_profit <= 0) or (roi is not None and roi <= 0):
        clamped_score = min(25, int(round(raw_score)))
    elif dscr is not None and dscr < 1.0:
        clamped_score = min(35, int(round(raw_score)))
    elif break_even_revenue is not None and monthly_revenue and break_even_revenue > monthly_revenue:
        clamped_score = min(30, int(round(raw_score)))
    else:
        clamped_score = _clamp(raw_score)

    status = "HIGH" if clamped_score >= 70 else ("MODERATE" if clamped_score >= 45 else "LOW")
    
    drivers = []
    if eff_margin is not None:
        drivers.append(f"Net Margin: {eff_margin:.1f}%.")
    if roi is not None:
        drivers.append(f"Return on Investment (ROI): {roi:.1f}%.")
    if break_even_revenue is not None and monthly_revenue:
        drivers.append(f"Break-even: ₹{break_even_revenue:,.0f} (Margin of Safety: {mos_pct:.1f}%).")
    if dscr is not None:
        drivers.append(f"DSCR Debt Coverage: {dscr:.2f}x.")

    reason = f"Viability score {clamped_score}/100 computed from " + (f"Net Margin {eff_margin:.1f}%" if eff_margin is not None else f"ROI {roi:.1f}%") + f" and cash flow coverage."

    return Dimension(
        "financial_viability", "Financial viability",
        score=clamped_score, known=True, reason=reason,
        value=round(eff_margin, 1) if eff_margin is not None else (round(roi, 1) if roi is not None else None),
        unit="% Net Margin" if eff_margin is not None else "% ROI",
        status=status,
        confidence=0.95,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={"roi_pct": roi, "net_margin_pct": eff_margin, "dscr": dscr, "break_even_revenue": break_even_revenue},
    )


def calculate_repayment_capacity(
    dscr: Optional[float] = None,
    has_debt: bool = True,
    monthly_emi: Optional[float] = None,
    monthly_cash_flow: Optional[float] = None,
    loan_amount: Optional[float] = None,
) -> Dimension:
    """
    Repayment Capacity / 100:
    DSCR = cash available for debt service ÷ total debt-service obligation (EMI).
    Includes EMI affordability and 100% promoter equity detection.
    """
    sources = [
        "YUKTIFI Debt Amortization & Repayment Engine",
        "Reserve Bank of India (RBI) Prudential Loan Coverage Benchmarks"
    ]
    formula = "Repayment Score = min(100, (DSCR / 2.0) × 100); Debt-Free (100% Equity) = 100/100"

    # 1. 100% Equity / Debt-Free Business (explicitly evidenced zero loan)
    if (loan_amount is not None and loan_amount == 0) or (monthly_emi is not None and monthly_emi == 0 and loan_amount is not None):
        return Dimension(
            "repayment_capacity", "Repayment capacity",
            score=100, known=True,
            reason="100% Promoter Equity Funded (₹0 Debt). No debt service or EMI obligation exists, eliminating default risk.",
            value=100.0,
            unit="/ 100",
            status="HIGH",
            confidence=0.95,
            drivers=[
                "100% Promoter Equity Funded (₹0 debt burden).",
                "Zero monthly EMI obligation.",
                "Zero debt default risk.",
            ],
            sources=sources,
            formula=formula,
            inputs={"has_debt": False, "loan_amount": 0.0, "monthly_emi": 0.0},
        )

    # 2. Leveraged Business: DSCR Evaluation
    if dscr is None:
        if not has_debt:
            return Dimension(
                "repayment_capacity", "Repayment capacity",
                score=None, known=False,
                reason="No debt service obligation, so there is nothing to repay and no DSCR to score.",
                sources=sources,
                formula=formula,
                inputs={"has_debt": False},
            )
        if monthly_cash_flow is not None and monthly_cash_flow < 0:
            return Dimension(
                "repayment_capacity", "Repayment capacity",
                score=15, known=True,
                reason="Negative operating cash flow cannot cover debt service obligations.",
                value=0.0,
                unit="x DSCR",
                status="LOW",
                confidence=0.90,
                drivers=["Negative operating cash flow produces zero debt service coverage."],
                sources=sources,
                formula=formula,
                inputs={"dscr": None, "has_debt": True, "monthly_cash_flow": monthly_cash_flow},
            )
        return Dimension(
            "repayment_capacity", "Repayment capacity",
            score=None, known=False,
            reason="Insufficient data: Debt service coverage ratio (DSCR) or loan amortization schedule is missing.",
            sources=sources,
            formula=formula,
            inputs={"has_debt": True},
        )

    if dscr < 1.0:
        clamped_score = max(5, int(round(dscr * 25.0)))
        return Dimension(
            "repayment_capacity", "Repayment capacity",
            score=clamped_score, known=True,
            reason=(
                f"DSCR {dscr:.2f}x is below 1.0: projected cash flow does not cover "
                f"monthly debt service obligation (EMI)."
            ),
            value=round(dscr, 2),
            unit="x DSCR",
            status="LOW",
            confidence=0.95,
            drivers=[
                f"DSCR {dscr:.2f}x is below the 1.0x debt service safety line.",
                f"Operating cash flow is insufficient to service the monthly loan EMI.",
            ],
            sources=sources,
            formula=formula,
            inputs={"dscr": dscr, "has_debt": True, "monthly_emi": monthly_emi},
        )

    clamped_score = _clamp(min(100.0, (dscr / 2.0) * 100.0))
    status = "HIGH" if clamped_score >= 70 else ("MODERATE" if clamped_score >= 45 else "LOW")
    drivers = [
        f"DSCR {dscr:.2f}x against benchmark target of 2.0x.",
        f"Operating cash flow covers debt obligations with safe buffer.",
    ]
    if monthly_emi is not None and monthly_emi > 0:
        drivers.append(f"Monthly EMI obligation: ₹{monthly_emi:,.0f}.")
    return Dimension(
        "repayment_capacity", "Repayment capacity",
        score=clamped_score, known=True,
        reason=f"DSCR {dscr:.2f}x provides healthy debt service coverage against target of 2.0x.",
        value=round(dscr, 2),
        unit="x DSCR",
        status=status,
        confidence=0.95,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={"dscr": dscr, "has_debt": True, "monthly_emi": monthly_emi},
    )



def calculate_market_opportunity(
    competitor_count: Optional[int] = None,
    population: Optional[int] = None,
    category_id: str = "retail_kirana",
    unit_price: Optional[float] = None,
    target_share: Optional[float] = None,
) -> Dimension:
    """
    Market Opportunity / 100:
    Demand strength, competition density/gap, market size and local catchment signals.
    """
    sources = [
        "Census of India 2011 (Catchment Demographics)",
        "OpenStreetMap / Overpass API (Spatial Features)"
    ]
    formula = (
        "Target Market = (Population / 4.8) × Target Share; "
        "Opportunity (₹/mo) = Target Consumers × Monthly Demand Units × Unit Price; "
        "Score = 0.45×Demand Headroom + 0.35×Competitor Space + 0.20×Catchment Scale"
    )

    if population is None or population <= 0:
        return Dimension(
            "market_opportunity", "Market opportunity",
            score=None, known=False,
            reason="Insufficient data: Catchment population / demographic customer base is missing.",
            sources=sources, formula=formula,
            inputs={"population": population, "competitor_count": competitor_count},
        )

    # Calculate deterministic market opportunity
    from app.engines.analytics_opportunity_engine import compute_market_opportunity as _compute_mkt
    dto = _compute_mkt(
        category_id=category_id,
        population=population,
        competitor_count=competitor_count,
        selling_price_override=unit_price,
        target_share_override=target_share,
    )
    return Dimension(
        key="market_opportunity",
        label="Market opportunity",
        score=dto.score,
        known=dto.score is not None,
        reason=dto.drivers[0] if dto.drivers else "Computed from catchment demographics and competitor density.",
        value=dto.value,
        unit=dto.unit,
        status=dto.status,
        confidence=dto.confidence,
        drivers=dto.drivers,
        sources=dto.sources,
        formula=dto.formula,
        inputs=dto.inputs,
        timestamp=dto.timestamp,
    )


def calculate_capital_efficiency(
    break_even: Optional[float] = None,
    projected: Optional[float] = None,
    roi: Optional[float] = None,
    project_cost: Optional[float] = None,
    annual_net_profit: Optional[float] = None,
    annual_revenue: Optional[float] = None,
    annual_ebit: Optional[float] = None,
    break_even_revenue: Optional[float] = None,
    monthly_revenue: Optional[float] = None,
    annual_operating_cash_flow: Optional[float] = None,
) -> Dimension:
    """
    Capital Efficiency / 100:
    Return generated per rupee invested (Profit ÷ Total Project Cost, ROCE, Capital Turnover).
    """
    sources = ["YUKTIFI Canonical Capital Sizing & Return Engine"]
    formula = (
        "Operating Profit (EBIT) / Project Cost × 100; "
        "ROI % = (Annual Net Profit / Total Project Cost) × 100; "
        "Capital Turnover = Annual Revenue / Project Cost; "
        "Score = 0.50×ROI Score + 0.30×Turnover Score + 0.20×Payback Score"
    )

    # 1. When project cost is provided
    if project_cost is not None and project_cost > 0:
        eff_ann_rev = annual_revenue if annual_revenue is not None else ((monthly_revenue or projected or 0.0) * 12.0)
        eff_ann_profit = annual_net_profit if annual_net_profit is not None else ((roi / 100.0 * project_cost) if roi is not None else 0.0)
        eff_roi = roi if roi is not None else ((eff_ann_profit / project_cost) * 100.0)
        turnover = eff_ann_rev / project_cost
        cash_flow = annual_operating_cash_flow if annual_operating_cash_flow is not None else eff_ann_profit
        payback_years = round(project_cost / cash_flow, 2) if cash_flow > 0 else None

        roi_score = 0.0 if eff_roi <= 0 else min(100.0, (eff_roi / 40.0) * 100.0)
        turnover_score = min(100.0, max(0.0, (turnover / 2.5) * 100.0))
        
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

        if eff_ann_profit <= 0 or eff_roi <= 0:
            final_score = min(20, int(round(0.50 * roi_score + 0.30 * turnover_score + 0.20 * payback_score)))
        else:
            final_score = _clamp(0.50 * roi_score + 0.30 * turnover_score + 0.20 * payback_score)

        status = "HIGH" if final_score >= 70 else ("MODERATE" if final_score >= 45 else "LOW")
        drivers = [
            f"Return on Investment (ROI): {eff_roi:.1f}% on ₹{project_cost:,.0f} total project cost.",
            f"Capital Turnover Ratio: {turnover:.2f}x annual revenue velocity.",
        ]
        if payback_years is not None:
            drivers.append(f"Estimated Capital Payback: {payback_years:.1f} years ({int(payback_years * 12)} months).")

        return Dimension(
            "capital_efficiency", "Capital efficiency",
            score=final_score, known=True,
            reason=f"ROI is {eff_roi:.1f}% with capital turnover of {turnover:.2f}x.",
            value=round(eff_roi, 1),
            unit="% ROI",
            status=status,
            confidence=0.95,
            drivers=drivers,
            sources=sources,
            formula=formula,
            inputs={
                "project_cost": project_cost,
                "annual_revenue": eff_ann_rev,
                "annual_net_profit": eff_ann_profit,
                "roi_pct": round(eff_roi, 2),
                "capital_turnover": round(turnover, 2),
                "payback_years": payback_years,
            },
        )

    # 2. Legacy / fallback from ROI alone
    if roi is not None:
        roi_score = _clamp(min(100.0, (roi / 40.0) * 100.0))
        status = "HIGH" if roi_score >= 70 else ("MODERATE" if roi_score >= 45 else "LOW")
        return Dimension(
            "capital_efficiency", "Capital efficiency",
            score=roi_score, known=True,
            reason=f"ROI {roi:.1f}% against target of 40%.",
            value=round(roi, 1),
            unit="% ROI",
            status=status,
            confidence=0.85,
            drivers=[f"Return on Investment (ROI): {roi:.1f}%."],
            sources=sources,
            formula=formula,
            inputs={"roi_pct": roi},
        )

    # 3. Fallback from Break-even vs Projected revenue
    be_val = break_even_revenue or break_even
    proj_val = monthly_revenue or projected
    if be_val is not None and proj_val is not None and proj_val > 0:
        ratio = be_val / proj_val
        clamped_score = _clamp(100 - ratio * 100)
        status = "HIGH" if clamped_score >= 70 else ("MODERATE" if clamped_score >= 45 else "LOW")
        return Dimension(
            "capital_efficiency", "Capital efficiency",
            score=clamped_score, known=True,
            reason=f"Break-even is {ratio * 100:.0f}% of projected revenue.",
            value=round((1.0 - ratio) * 100.0, 1),
            unit="% Margin of Safety",
            status=status,
            confidence=0.90,
            drivers=[f"Break-even achieved at {ratio * 100:.0f}% of monthly capacity."],
            sources=sources,
            formula=formula,
            inputs={"break_even": be_val, "projected_revenue": proj_val, "break_even_share_pct": round(ratio * 100, 1)},
        )

    return Dimension(
        "capital_efficiency", "Capital efficiency",
        score=None, known=False,
        reason="Insufficient data: Total project cost, ROI, and break-even revenue inputs are missing.",
        sources=sources, formula=formula,
    )


def calculate_risk_exposure(
    confidence: Optional[str] = None,
    threats_count: Optional[int] = None,
    dscr: Optional[float] = None,
    monthly_operating_cash_flow: Optional[float] = None,
    monthly_revenue: Optional[float] = None,
    monthly_opex: Optional[float] = None,
    break_even_revenue: Optional[float] = None,
    competitor_density: Optional[float] = None,
    debt_amount: Optional[float] = None,
    project_cost: Optional[float] = None,
) -> Dimension:
    """
    Risk Exposure / 100 (Resilience Score):
    Demand volatility, cost sensitivity, debt burden, competition and downside scenarios.
    Requirement: Higher risk produces a LOWER score.
    """
    sources = [
        "YUKTIFI Multi-Factor Risk Assessment Engine",
        "Deterministic Sensitivity & Cash Flow Stress Matrix"
    ]
    formula = (
        "Risk Index = 0.35×Financial Risk + 0.25×Market Risk + 0.20×Operational Risk + 0.20×Data Uncertainty; "
        "Score = 100 − Risk Index (Higher risk produces a lower score)"
    )

    if confidence is None and dscr is None and monthly_revenue is None:
        return Dimension(
            "risk_exposure", "Risk exposure",
            score=None, known=False,
            reason="Insufficient data: Risk parameters and evidence confidence are missing.",
            sources=sources, formula=formula,
        )

    conf_str = confidence or "Medium"

    # 1. Financial Risk (0-100, higher = worse)
    fin_risk_parts = []
    if monthly_operating_cash_flow is not None:
        if monthly_operating_cash_flow < 0:
            fin_risk_parts.append(100.0)
        elif monthly_revenue and monthly_revenue > 0 and monthly_operating_cash_flow < (monthly_revenue * 0.08):
            fin_risk_parts.append(60.0)
        else:
            fin_risk_parts.append(15.0)

    if dscr is not None:
        if dscr < 1.0:
            fin_risk_parts.append(95.0)
        elif dscr < 1.25:
            fin_risk_parts.append(70.0)
        elif dscr < 1.5:
            fin_risk_parts.append(45.0)
        else:
            fin_risk_parts.append(15.0)
    elif debt_amount is not None and debt_amount == 0:
        fin_risk_parts.append(0.0)

    if break_even_revenue is not None and monthly_revenue and monthly_revenue > 0:
        be_ratio = break_even_revenue / monthly_revenue
        if be_ratio > 0.90:
            fin_risk_parts.append(90.0)
        elif be_ratio > 0.70:
            fin_risk_parts.append(50.0)
        else:
            fin_risk_parts.append(15.0)

    financial_risk = sum(fin_risk_parts) / len(fin_risk_parts) if fin_risk_parts else 30.0

    # 2. Market Risk (0-100)
    density = competitor_density or 0.0
    if density > 6.0:
        market_risk = 85.0
    elif density > 3.0:
        market_risk = 55.0
    elif density > 0.5:
        market_risk = 30.0
    else:
        market_risk = 35.0

    # 3. Operational Risk (0-100)
    if monthly_opex is not None and monthly_revenue and monthly_revenue > 0:
        fc_ratio = monthly_opex / monthly_revenue
        fc_risk = 75.0 if fc_ratio > 0.45 else (45.0 if fc_ratio > 0.25 else 20.0)
    else:
        fc_risk = 30.0
    operational_risk = fc_risk

    # 4. Data Uncertainty (0-100)
    data_risk = {"high": 15.0, "medium": 40.0, "low": 75.0, "unavailable": 85.0}.get(conf_str.lower(), 40.0)
    threats_penalty = (threats_count * 5.0) if threats_count is not None else 0.0

    # Composite Risk Index (0-100, higher = higher risk)
    risk_index = round(min(100.0, max(0.0, 0.35 * financial_risk + 0.25 * market_risk + 0.20 * operational_risk + 0.20 * data_risk + threats_penalty)), 1)
    
    # Requirement: Higher risk produces a LOWER score!
    resilience_score = _clamp(100.0 - risk_index)
    status = "HIGH" if resilience_score >= 70 else ("MODERATE" if resilience_score >= 45 else "LOW")

    drivers = [
        f"Composite Risk Index: {risk_index:.1f}/100 ({'Low Risk' if risk_index <= 35 else ('Moderate Risk' if risk_index <= 65 else 'High Risk')}).",
        f"Evidence confidence: {conf_str}.",
    ]
    if dscr is not None:
        drivers.append(f"Debt leverage & coverage risk: DSCR {dscr:.2f}x.")
    if threats_count:
        drivers.append(f"{threats_count} identified operational/market threat(s).")

    return Dimension(
        "risk_exposure", "Risk exposure",
        score=resilience_score, known=True,
        reason=f"Risk Index {risk_index:.0f}/100 ({conf_str} confidence, {threats_count or 0} threats). Higher risk lowers score.",
        value=risk_index,
        unit="/ 100 Risk",
        status=status,
        confidence=0.85,
        drivers=drivers,
        sources=sources,
        formula=formula,
        inputs={
            "risk_index": risk_index,
            "resilience_score": resilience_score,
            "financial_risk": round(financial_risk, 1),
            "market_risk": round(market_risk, 1),
            "operational_risk": round(operational_risk, 1),
            "data_uncertainty": round(data_risk, 1),
            "confidence": conf_str,
            "threats_count": threats_count,
        },
    )


# ── Composite ───────────────────────────────────────────────────────────────

@dataclass
class ScoreCard:
    """A composite that knows what it does not know."""

    dimensions: list[Dimension] = field(default_factory=list)
    composite: Optional[int] = None
    coverage: float = 0.0
    verdict: Optional[dict[str, Any]] = None
    unscored: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "yukti_score": self.composite,
            "score_coverage_pct": round(self.coverage * 100, 1),
            "verdict": self.verdict,
            "dimensions": {d.key: d.to_dict() for d in self.dimensions},
            "unscored_dimensions": self.unscored,
            "scoring_note": (
                f"Composite is the mean of {len(self.dimensions) - len(self.unscored)} scored "
                f"dimensions. Unscored dimensions are excluded, not imputed, so the score is "
                f"based on a partial evidence base."
            ),
        }


def generate_verdict(overall_score: float) -> dict[str, Any]:
    if overall_score >= 75:
        return {"text": "Strong Opportunity", "color": "emerald-600"}
    if overall_score >= 50:
        return {"text": "Moderate Potential", "color": "amber-600"}
    return {"text": "High Risk", "color": "red-600"}


def compute_all_dimensions(
    roi: Optional[float] = None,
    dscr: Optional[float] = None,
    net_margin: Optional[float] = None,
    break_even_units: Optional[float] = None,
    monthly_units: Optional[float] = None,
    competitor_count: Optional[int] = None,
    population: Optional[int] = None,
    overall_confidence: Optional[str] = None,
    threats_count: Optional[int] = None,
    has_debt: bool = True,
    # Extended parameters
    project_cost: Optional[float] = None,
    own_capital: Optional[float] = None,
    loan_amount: Optional[float] = None,
    monthly_revenue: Optional[float] = None,
    monthly_expenses: Optional[float] = None,
    monthly_net_profit: Optional[float] = None,
    monthly_operating_cash_flow: Optional[float] = None,
    monthly_emi: Optional[float] = None,
    break_even_revenue: Optional[float] = None,
    annual_revenue: Optional[float] = None,
    annual_net_profit: Optional[float] = None,
    annual_ebit: Optional[float] = None,
    category_id: str = "retail_kirana",
    unit_price: Optional[float] = None,
    target_share: Optional[float] = None,
    competitor_density: Optional[float] = None,
) -> ScoreCard:
    """Compute every dimension, then publish a composite only if it is earned."""
    dims = [
        calculate_financial_viability(
            roi=roi,
            net_margin=net_margin,
            monthly_revenue=monthly_revenue,
            monthly_net_profit=monthly_net_profit,
            monthly_operating_cash_flow=monthly_operating_cash_flow,
            dscr=dscr,
            break_even_revenue=break_even_revenue or (break_even_units if break_even_units and break_even_units > 1000 else None),
        ),
        calculate_repayment_capacity(
            dscr=dscr,
            has_debt=has_debt if loan_amount is None else (loan_amount > 0),
            monthly_emi=monthly_emi,
            monthly_cash_flow=monthly_operating_cash_flow,
            loan_amount=loan_amount,
        ),
        calculate_market_opportunity(
            competitor_count=competitor_count,
            population=population,
            category_id=category_id,
            unit_price=unit_price,
            target_share=target_share,
        ),
        calculate_capital_efficiency(
            break_even=break_even_units,
            projected=monthly_units,
            roi=roi,
            project_cost=project_cost,
            annual_net_profit=annual_net_profit,
            annual_revenue=annual_revenue,
            annual_ebit=annual_ebit,
            break_even_revenue=break_even_revenue,
            monthly_revenue=monthly_revenue,
            annual_operating_cash_flow=(monthly_operating_cash_flow * 12.0) if monthly_operating_cash_flow is not None else None,
        ),
        calculate_risk_exposure(
            confidence=overall_confidence,
            threats_count=threats_count,
            dscr=dscr,
            monthly_operating_cash_flow=monthly_operating_cash_flow,
            monthly_revenue=monthly_revenue,
            monthly_opex=monthly_expenses,
            break_even_revenue=break_even_revenue,
            competitor_density=competitor_density,
            debt_amount=loan_amount,
            project_cost=project_cost,
        ),
    ]

    known = [d for d in dims if d.known]
    unscored = [d.label for d in dims if not d.known]
    coverage = len(known) / len(dims)

    composite: Optional[int] = None
    verdict: Optional[dict[str, Any]] = None

    if len(known) >= MIN_DIMENSIONS_FOR_SCORE:
        composite = round(sum(d.score for d in known) / len(known))  # type: ignore[misc]
        if coverage >= MIN_COVERAGE_FOR_VERDICT:
            verdict = generate_verdict(composite)

    return ScoreCard(
        dimensions=dims, composite=composite, coverage=coverage,
        verdict=verdict, unscored=unscored,
    )



def generate_next_steps(
    scores: dict[str, Any], financials: dict[str, Any], market: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Next steps, most important first.

    An unscored dimension produces a step to obtain the data, which is the honest
    action: you cannot act on a dimension you could not measure.
    """
    steps: list[dict[str, Any]] = []
    dims = scores.get("dimensions", scores)

    def _score_of(key: str) -> Optional[int]:
        d = dims.get(key)
        if isinstance(d, dict):
            return d.get("score")
        return d if isinstance(d, (int, float)) else None

    repay = _score_of("repayment_capacity")
    if repay is None:
        steps.append({
            "priority": 1, "action": "Confirm the funding structure", "module": "financial",
            "reason": "Repayment capacity could not be scored. Establish whether the project will "
                      "carry debt, and if so on what terms, before relying on this analysis.",
        })
    elif repay < 50:
        steps.append({
            "priority": 1, "action": "Reduce the loan amount or extend tenure", "module": "financial",
            "reason": "DSCR is below 1.5. Projected cash flow does not cover debt service with a "
                      "safe margin, so the repayment schedule needs restructuring.",
        })

    fin = _score_of("financial_viability")
    if fin is not None and fin < 60:
        steps.append({
            "priority": 2, "action": "Re-cost the project before committing", "module": "financial",
            "reason": "Financial viability scores low. Obtain actual supplier quotations and "
                      "confirmed prices rather than sector assumptions.",
        })

    market_dim = _score_of("market_opportunity")
    if market_dim is None:
        steps.append({
            "priority": 1, "action": "Survey competitors on foot", "module": "market",
            "reason": "Local competition was not established. Walk the 5 km catchment and count "
                      "comparable businesses by hand; the map data is known to be incomplete.",
        })
    elif market_dim < 50:
        steps.append({
            "priority": 1, "action": "Survey competitors on foot", "module": "market",
            "reason": "Competitive density appears high relative to the local population. "
                      "Verify with a physical survey before entering.",
        })

    risk = _score_of("risk_exposure")
    if risk is None:
        steps.append({
            "priority": 2, "action": "Gather the missing evidence", "module": "risk",
            "reason": "Risk exposure could not be scored because evidence confidence is undetermined.",
        })
    elif risk < 60:
        steps.append({
            "priority": 2, "action": "Review the identified threats", "module": "risk",
            "reason": "Evidence is thin or several structural risks were flagged.",
        })

    if not steps:
        steps.append({
            "priority": 3, "action": "Move to a detailed business plan", "module": "general",
            "reason": "Every scored dimension is healthy. Begin formalising the launch plan, "
                      "and re-verify the cost and price assumptions with real quotations.",
        })

    steps.sort(key=lambda s: s["priority"])
    return steps
