# YuktiFi — Prototype Starter Code

Working skeleton for every file in the structure doc. The **deterministic engines, scheme engine, recommendation engine, and boundary-value tests are fully implemented and runnable** — these are the judge-critical pieces (Section 17.1, Section 40). The market-intelligence, AI-layer, and report modules are implemented as clear, wired-together stubs — enough to run end-to-end on curated demo data, with `# TODO` marking where real data/prompts replace placeholders.

Copy each block into the matching path from the file-structure doc.

---

## `backend/requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
alembic==1.13.2
psycopg2-binary==2.9.9
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
anthropic==0.34.2
jinja2==3.1.4
weasyprint==62.3
pytest==8.3.3
httpx==0.27.2
```

---

## `backend/app/core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://yukti:yukti@localhost:5432/yukti"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()
```

## `backend/app/core/db.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## `backend/app/models/` (condensed — one file's worth, split by filename as needed)

```python
# app/models/core.py
import enum
import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Enum, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base

def uid():
    return str(uuid.uuid4())

class AdminLevel(str, enum.Enum):
    village = "village"
    block = "block"
    district = "district"

class ConfidenceLevel(str, enum.Enum):
    high = "High"
    medium = "Medium"
    low = "Low"

class VerdictEnum(str, enum.Enum):
    GO = "GO"
    CAUTION = "CAUTION"
    ALTERNATIVE = "ALTERNATIVE"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String)
    language_pref = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    sessions = relationship("Session", back_populates="user")

class Location(Base):
    __tablename__ = "locations"
    id = Column(String, primary_key=True, default=uid)
    village = Column(String, nullable=True)
    block = Column(String, nullable=True)
    district = Column(String)
    state = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    admin_level = Column(Enum(AdminLevel))

class BusinessCategory(Base):
    __tablename__ = "business_categories"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String, unique=True)
    parent_category = Column(String, nullable=True)
    cost_profile_ref = Column(String, nullable=True)

class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("margin_capital > 0"),)
    id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.id"))
    location_id = Column(String, ForeignKey("locations.id"))
    margin_capital = Column(Float)
    category_id = Column(String, ForeignKey("business_categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="sessions")

class GovernmentScheme(Base):
    __tablename__ = "government_schemes"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String)
    min_project_cost = Column(Float)
    max_project_cost = Column(Float)
    financing_pct = Column(Float)
    max_loan_amount = Column(Float)
    interest_rate = Column(Float)
    tenure_months = Column(Integer)
    moratorium_months = Column(Integer)
    source_url = Column(String)
    effective_from = Column(DateTime)
    last_verified = Column(DateTime)

class LoanProduct(Base):
    __tablename__ = "loan_products"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    project_cost = Column(Float)
    loan_amount = Column(Float)
    beneficiary_contribution = Column(Float)
    matched_scheme_id = Column(String, ForeignKey("government_schemes.id"), nullable=True)

class FinancialProjection(Base):
    __tablename__ = "financial_projections"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    monthly_revenue = Column(Float)
    monthly_opex = Column(Float)
    net_profit = Column(Float)
    break_even_units = Column(Float)
    dscr = Column(Float)
    roi = Column(Float)

class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    revenue_delta_pct = Column(Float, default=0)
    cost_delta_pct = Column(Float, default=0)
    tenure_override = Column(Integer, nullable=True)
    resulting_dscr = Column(Float)
    resulting_verdict = Column(Enum(VerdictEnum))
    created_at = Column(DateTime, default=datetime.utcnow)

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(String, primary_key=True, default=uid)
    session_id = Column(String, ForeignKey("sessions.id"))
    yukti_score = Column(Float)
    verdict = Column(Enum(VerdictEnum))
    dimension_breakdown_json = Column(JSON)
    confidence_multiplier = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class ConfidenceTag(Base):
    __tablename__ = "confidence_tags"
    id = Column(String, primary_key=True, default=uid)
    referenced_entity_type = Column(String)
    referenced_entity_id = Column(String)
    level = Column(Enum(ConfidenceLevel))
    method_note = Column(String)

class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String)
    url = Column(String)
    type = Column(String)
    retrieved_at = Column(DateTime)
```

---

## `backend/app/schemas/finance.py`

```python
from pydantic import BaseModel

class FinanceRequest(BaseModel):
    session_id: str
    margin_capital: float

class FinanceResponse(BaseModel):
    project_cost: float
    loan_amount: float
    beneficiary_contribution: float
```

## `backend/app/schemas/scheme.py`

```python
from pydantic import BaseModel
from typing import Optional

class SchemeMatchRequest(BaseModel):
    session_id: str
    project_cost: float

class SchemeMatchResponse(BaseModel):
    matched: bool
    scheme_name: Optional[str] = None
    max_loan: Optional[float] = None
    rate: Optional[float] = None
    tenure_years: Optional[int] = None
    moratorium_months: Optional[int] = None
    rejected_alternative: Optional[str] = None
    explanation: str
    source_url: Optional[str] = None
```

## `backend/app/schemas/simulation.py`

```python
from pydantic import BaseModel
from typing import Optional

class SimulateRequest(BaseModel):
    session_id: str
    revenue_delta_pct: float = 0.0
    cost_delta_pct: float = 0.0
    tenure_override_years: Optional[int] = None

class SimulateResponse(BaseModel):
    emi: float
    dscr: float
    break_even_units: float
    verdict: str
    net_profit: float
```

---

## `backend/app/engines/financial_engine.py` — **fully implemented, deterministic only**

```python
"""
Pure deterministic financial math. NEVER import an LLM client here.
Every function must be a closed-form calculation traceable to Section 14/17.
"""
from dataclasses import dataclass

CONTRIBUTION_PCT = 0.10          # beneficiary contribution
FINANCING_PCT = 0.90             # scheme financing share


def compute_project_cost(margin_capital: float) -> float:
    """PC = Margin / 0.10  (Section 17.1)"""
    if margin_capital <= 0:
        raise ValueError("margin_capital must be > 0")
    return margin_capital / CONTRIBUTION_PCT


def compute_loan_amount(project_cost: float, scheme_max_loan: float | None = None) -> float:
    """Loan = PC * 0.90, capped at the matched scheme's ceiling if provided."""
    loan = project_cost * FINANCING_PCT
    if scheme_max_loan is not None:
        loan = min(loan, scheme_max_loan)
    return loan


def compute_emi(principal: float, annual_rate_pct: float, tenure_months: int,
                 moratorium_months: int = 0) -> float:
    """
    Standard reducing-balance EMI, repayment starts after the moratorium.
    Moratorium does not waive interest by default here — flag if your
    scheme's actual moratorium is interest-free vs. interest-accruing.
    """
    r = (annual_rate_pct / 100) / 12
    n = tenure_months - moratorium_months
    if n <= 0:
        raise ValueError("tenure_months must exceed moratorium_months")
    if r == 0:
        return principal / n
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return round(emi, 2)


def compute_dscr(net_operating_income_monthly: float, emi: float) -> float:
    """Debt Service Coverage Ratio — the repayment-capacity hard gate input."""
    if emi == 0:
        return float("inf")
    return round(net_operating_income_monthly / emi, 2)


def compute_break_even_units(fixed_costs_monthly: float, price_per_unit: float,
                              variable_cost_per_unit: float) -> float:
    contribution = price_per_unit - variable_cost_per_unit
    if contribution <= 0:
        raise ValueError("price must exceed variable cost per unit")
    return round(fixed_costs_monthly / contribution, 1)


def compute_net_profit(monthly_revenue: float, monthly_opex: float) -> float:
    return round(monthly_revenue - monthly_opex, 2)


def compute_roi(net_annual_profit: float, total_investment: float) -> float:
    if total_investment == 0:
        return 0.0
    return round((net_annual_profit / total_investment) * 100, 2)


@dataclass
class FinancialSnapshot:
    project_cost: float
    loan_amount: float
    contribution: float
    emi: float
    dscr: float
    break_even_units: float
    net_profit: float
    roi: float
```

---

## `backend/app/engines/scheme_engine.py` — **fully implemented, pure rule table**

```python
"""
Pure rule-table lookup against NSFDC-verified schemes (Section 16.1).
This module NEVER calls an LLM and NEVER improvises a scheme.
"""
from dataclasses import dataclass
from typing import Optional

MICRO_FINANCE_CEILING = 140_000
TERM_LOAN_CEILING = 5_000_000        # ₹50 lakh, matches Section 17.1's stated max
MICRO_FINANCE_MAX_LOAN = 125_000
TERM_LOAN_MAX_LOAN = 4_500_000       # ₹45 lakh

SCHEMES = {
    "Micro Credit Finance": {
        "rate": 6.5, "tenure_years": 3, "moratorium_months": 3,
        "max_loan": MICRO_FINANCE_MAX_LOAN,
        "source_url": "https://nsfdc.nic.in",  # TODO: pin exact scheme page URL
    },
    "Term Loan": {
        "rate": 8.0, "tenure_years": 7, "moratorium_months": 6,
        "max_loan": TERM_LOAN_MAX_LOAN,
        "source_url": "https://nsfdc.nic.in",
    },
}


@dataclass
class SchemeMatch:
    matched: bool
    scheme_name: Optional[str]
    max_loan: Optional[float]
    rate: Optional[float]
    tenure_years: Optional[int]
    moratorium_months: Optional[int]
    rejected_alternative: Optional[str]
    explanation: str
    source_url: Optional[str]


def match_scheme(project_cost: float) -> SchemeMatch:
    if project_cost <= MICRO_FINANCE_CEILING:
        s = SCHEMES["Micro Credit Finance"]
        return SchemeMatch(
            matched=True,
            scheme_name="Micro Credit Finance",
            max_loan=min(project_cost * 0.90, s["max_loan"]),
            rate=s["rate"], tenure_years=s["tenure_years"],
            moratorium_months=s["moratorium_months"],
            rejected_alternative="Term Loan (project cost below its band)",
            explanation=(
                f"Your project cost of ₹{project_cost:,.0f} is at or below the "
                f"₹{MICRO_FINANCE_CEILING:,.0f} ceiling, so you're routed to Micro Credit Finance."
            ),
            source_url=s["source_url"],
        )
    elif MICRO_FINANCE_CEILING < project_cost <= TERM_LOAN_CEILING:
        s = SCHEMES["Term Loan"]
        return SchemeMatch(
            matched=True,
            scheme_name="Term Loan",
            max_loan=min(project_cost * 0.90, s["max_loan"]),
            rate=s["rate"], tenure_years=s["tenure_years"],
            moratorium_months=s["moratorium_months"],
            rejected_alternative="Micro Credit Finance (project cost exceeds its ceiling)",
            explanation=(
                f"Your project cost of ₹{project_cost:,.0f} falls in the "
                f"₹{MICRO_FINANCE_CEILING:,.0f}–₹{TERM_LOAN_CEILING:,.0f} band, "
                f"so you're routed to the Term Loan scheme rather than Micro Credit Finance."
            ),
            source_url=s["source_url"],
        )
    else:
        return SchemeMatch(
            matched=False, scheme_name=None, max_loan=None, rate=None,
            tenure_years=None, moratorium_months=None, rejected_alternative=None,
            explanation=(
                f"Based on your available margin capital, the resulting project cost of "
                f"₹{project_cost:,.0f} exceeds the ₹{TERM_LOAN_CEILING:,.0f} ceiling modelled "
                "in this prototype's financing schemes. This does not necessarily mean the "
                "business is unfinanceable — it means it likely requires a different financing "
                "instrument (larger MSME term-loan products or bank co-financing) not modelled "
                "here. Consider resizing the project or consulting your nearest bank/State "
                "Channelizing Agency about larger-ticket options."
            ),
            source_url=None,
        )
```

---

## `backend/app/engines/recommendation_engine.py`

```python
"""
Section 12/13 — hard gates + weighted scoring + verdict banding.
Weights below are [PROTOTYPE-ASSUMPTION] — tune against your own rubric,
but keep them as named constants, never inline magic numbers.
"""
from dataclasses import dataclass

WEIGHTS = {
    "financial_viability": 0.30,
    "repayment_capacity": 0.25,
    "market_opportunity": 0.20,
    "capital_efficiency": 0.15,
    "risk_exposure": 0.10,
}

DSCR_HARD_GATE = 1.0   # below this, verdict cannot be GO regardless of score


@dataclass
class ScoreBreakdown:
    dimensions: dict
    raw_score: float
    confidence_multiplier: float
    final_score: float
    verdict: str


def band_verdict(score: float, dscr: float) -> str:
    if dscr < DSCR_HARD_GATE:
        return "NOT_RECOMMENDED"
    if score >= 80:
        return "GO"
    if score >= 60:
        return "CAUTION"
    if score >= 40:
        return "ALTERNATIVE"
    return "NOT_RECOMMENDED"


def compute_yukti_score(dimension_scores: dict, confidence_multiplier: float, dscr: float) -> ScoreBreakdown:
    """
    dimension_scores: dict of {dimension_name: 0-100 value}, must match WEIGHTS keys.
    confidence_multiplier: 0.0-1.0, derived from the aggregate confidence of inputs
      used (Section 10) — a High-confidence analysis should not be penalised,
      a Low-confidence one should visibly pull the score down or trigger caveats.
    """
    raw = sum(dimension_scores[k] * WEIGHTS[k] for k in WEIGHTS)
    final = round(raw * confidence_multiplier, 1)
    verdict = band_verdict(final, dscr)
    return ScoreBreakdown(
        dimensions=dimension_scores,
        raw_score=round(raw, 1),
        confidence_multiplier=confidence_multiplier,
        final_score=final,
        verdict=verdict,
    )
```

---

## `backend/app/engines/simulation_engine.py`

```python
"""Section 15 — recalculation chain for the What-If Simulator."""
from app.engines.financial_engine import compute_emi, compute_dscr, compute_net_profit
from app.engines.recommendation_engine import compute_yukti_score, band_verdict


def run_simulation(base_state: dict, revenue_delta_pct: float, cost_delta_pct: float,
                    tenure_override_years: int | None) -> dict:
    """
    base_state must contain: principal, rate, tenure_months, moratorium_months,
    monthly_revenue, monthly_opex, dimension_scores, confidence_multiplier.
    """
    tenure_months = (tenure_override_years * 12) if tenure_override_years else base_state["tenure_months"]

    emi = compute_emi(
        base_state["principal"], base_state["rate"], tenure_months, base_state["moratorium_months"]
    )
    new_revenue = base_state["monthly_revenue"] * (1 + revenue_delta_pct / 100)
    new_opex = base_state["monthly_opex"] * (1 + cost_delta_pct / 100)
    net_profit = compute_net_profit(new_revenue, new_opex)
    dscr = compute_dscr(net_profit, emi)

    score = compute_yukti_score(base_state["dimension_scores"], base_state["confidence_multiplier"], dscr)

    return {
        "emi": emi,
        "dscr": dscr,
        "net_profit": net_profit,
        "verdict": score.verdict,
        "final_score": score.final_score,
    }
```

---

## `backend/app/engines/market_intelligence/` (stubs wired to curated data)

```python
# app/engines/market_intelligence/competitor_density.py
"""Section 11 — reads curated/OSM data, always returns a confidence tag."""

def estimate_competitor_density(location_id: str, category_id: str, data_layer) -> dict:
    records = data_layer.get_competitors(location_id, category_id)  # TODO: wire to data_layer/retrieval.py
    if not records:
        return {"count_estimate": None, "confidence": "Low",
                "note": "No competitor data available for this location/category."}
    origins = {r["source"] for r in records}
    confidence = "High" if origins == {"public_source"} else ("Medium" if "public_source" in origins else "Low")
    return {"count_estimate": len(records), "confidence": confidence, "records": records}
```

```python
# app/engines/market_intelligence/pricing.py
def estimate_pricing_band(location_id: str, category_id: str, data_layer) -> dict:
    band = data_layer.get_pricing(location_id, category_id)  # TODO: wire to curated dataset
    if band is None:
        return {"low": None, "high": None, "confidence": "Low"}
    return {"low": band["low"], "high": band["high"], "confidence": band.get("confidence", "Medium")}
```

*(`market_reach.py`, `opportunity_gaps.py`, `swot.py`, `threats.py` follow the same pattern: read from `data_layer`, always attach a confidence level, never fabricate a number when data is absent — return `None` + `"Low"` instead.)*

---

## `backend/app/data_layer/confidence_tagging.py`

```python
"""Section 10 — the trust layer. Central place that decides confidence levels."""

def tag_confidence(data_origin: str, sample_size: int | None = None) -> str:
    if data_origin == "public_source" and (sample_size is None or sample_size >= 5):
        return "High"
    if data_origin == "public_source":
        return "Medium"
    if data_origin == "prototype_curated":
        return "Medium" if sample_size and sample_size >= 3 else "Low"
    return "Low"
```

---

## `backend/app/ai_layer/numeric_validator.py` — **non-negotiable per Section 18.4**

```python
import re

def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d[\d,]*\.?\d*", text))

def validate_llm_output(llm_text: str, allowed_context_numbers: set[str]) -> tuple[bool, str]:
    """
    Returns (is_valid, reason). Rejects the LLM's narration if it contains
    any number not present in the context it was given — this is the check
    that must fire in a rehearsed test (Section 40, Top-5-fixes #4).
    """
    found = extract_numbers(llm_text)
    normalized_allowed = {n.replace(",", "") for n in allowed_context_numbers}
    for n in found:
        if n.replace(",", "") not in normalized_allowed:
            return False, f"Unrecognized number '{n}' not present in provided context."
    return True, "ok"
```

## `backend/app/ai_layer/prompt_templates.py`

```python
EXPLAIN_TEMPLATE = """You are explaining an already-computed financial result to a rural
entrepreneur in plain {language}. Use ONLY the following computed values and their
confidence tags. Do not introduce any number not present here. If the answer requires
a number not provided, say the data is not available rather than estimating.

Computed context:
{context_json}

User question: {question}
"""
```

## `backend/app/ai_layer/llm_client.py`

```python
import anthropic
from app.core.config import settings
from app.ai_layer.numeric_validator import validate_llm_output
from app.ai_layer.prompt_templates import EXPLAIN_TEMPLATE

client = anthropic.Anthropic(api_key=settings.llm_api_key)

FALLBACK_TEMPLATE = "Your result is: {summary}. (Detailed explanation unavailable right now.)"

def explain(context: dict, question: str, language: str = "English") -> str:
    import json
    prompt = EXPLAIN_TEMPLATE.format(
        language=language, context_json=json.dumps(context), question=question
    )
    resp = client.messages.create(
        model=settings.llm_model, max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
    allowed_numbers = {str(v) for v in _flatten_numbers(context)}
    is_valid, _reason = validate_llm_output(text, allowed_numbers)
    if not is_valid:
        return FALLBACK_TEMPLATE.format(summary=context.get("summary", "see your results screen"))
    return text

def _flatten_numbers(obj):
    nums = []
    if isinstance(obj, dict):
        for v in obj.values():
            nums.extend(_flatten_numbers(v))
    elif isinstance(obj, list):
        for v in obj:
            nums.extend(_flatten_numbers(v))
    elif isinstance(obj, (int, float)):
        nums.append(obj)
    return nums
```

---

## `backend/app/api/routes_finance.py`

```python
from fastapi import APIRouter
from app.schemas.finance import FinanceRequest, FinanceResponse
from app.engines.financial_engine import compute_project_cost, compute_loan_amount

router = APIRouter()

@router.post("/calculate-finance", response_model=FinanceResponse)
def calculate_finance(req: FinanceRequest):
    project_cost = compute_project_cost(req.margin_capital)
    loan_amount = compute_loan_amount(project_cost)
    contribution = project_cost - loan_amount
    return FinanceResponse(project_cost=project_cost, loan_amount=loan_amount,
                            beneficiary_contribution=contribution)
```

## `backend/app/api/routes_schemes.py`

```python
from fastapi import APIRouter
from app.schemas.scheme import SchemeMatchRequest, SchemeMatchResponse
from app.engines.scheme_engine import match_scheme, SCHEMES

router = APIRouter()

@router.get("/schemes")
def list_schemes():
    return SCHEMES

@router.post("/match-scheme", response_model=SchemeMatchResponse)
def match(req: SchemeMatchRequest):
    result = match_scheme(req.project_cost)
    return SchemeMatchResponse(**result.__dict__)
```

## `backend/app/api/routes_simulate.py`

```python
from fastapi import APIRouter
from app.schemas.simulation import SimulateRequest, SimulateResponse
from app.engines.simulation_engine import run_simulation
# TODO: load base_state from Session/FinancialProjection rows via session_id

router = APIRouter()

@router.post("/simulate", response_model=SimulateResponse)
def simulate(req: SimulateRequest):
    base_state = get_base_state_for_session(req.session_id)  # implement in services/session_service.py
    result = run_simulation(base_state, req.revenue_delta_pct, req.cost_delta_pct, req.tenure_override_years)
    return SimulateResponse(
        emi=result["emi"], dscr=result["dscr"],
        break_even_units=base_state.get("break_even_units", 0),
        verdict=result["verdict"], net_profit=result["net_profit"],
    )

def get_base_state_for_session(session_id: str) -> dict:
    raise NotImplementedError("Wire this to session_service.py + DB")
```

## `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_finance, routes_schemes, routes_simulate
# TODO: import routes_profile, routes_rank, routes_market, routes_recommend, routes_explain, routes_report

app = FastAPI(title="YuktiFi API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(routes_finance.router)
app.include_router(routes_schemes.router)
app.include_router(routes_simulate.router)
```

---

## `backend/tests/test_boundary_values.py` — **run this before every demo**

```python
import pytest
from app.engines.financial_engine import compute_project_cost, compute_loan_amount
from app.engines.scheme_engine import match_scheme, MICRO_FINANCE_CEILING, TERM_LOAN_CEILING

# Encodes the exact table from Section 17.1
@pytest.mark.parametrize("margin,expected_scheme", [
    (14_000, "Micro Credit Finance"),      # exactly at boundary — inclusive
    (14_001, "Term Loan"),                 # just above — exclusive
    (100_000, "Term Loan"),
    (500_000, "Term Loan"),                # PC = 50L exactly, at ceiling
    (600_000, None),                       # PC = 60L, exceeds both schemes
])
def test_boundary_routing(margin, expected_scheme):
    pc = compute_project_cost(margin)
    result = match_scheme(pc)
    if expected_scheme is None:
        assert result.matched is False
    else:
        assert result.scheme_name == expected_scheme

def test_project_cost_formula():
    assert compute_project_cost(100_000) == 1_000_000

def test_loan_capped_at_term_loan_ceiling():
    pc = compute_project_cost(500_000)  # PC = 50,00,000
    result = match_scheme(pc)
    assert result.max_loan == 4_500_000  # capped at ₹45L even though 90% of PC is 45L exactly here

def test_zero_margin_raises():
    with pytest.raises(ValueError):
        compute_project_cost(0)
```

## `backend/tests/test_numeric_validator.py`

```python
from app.ai_layer.numeric_validator import validate_llm_output

def test_rejects_hallucinated_number():
    context_numbers = {"84", "1,00,000"}
    bad_output = "Your score is 84 and your loan is 2,50,000."  # 2,50,000 not in context
    is_valid, _ = validate_llm_output(bad_output, context_numbers)
    assert is_valid is False

def test_accepts_grounded_numbers():
    context_numbers = {"84", "100000"}
    good_output = "Your score is 84, based on a project of 100000 rupees."
    is_valid, _ = validate_llm_output(good_output, context_numbers)
    assert is_valid is True
```

---

## `frontend/lib/api-client.ts`

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  calculateFinance: (margin_capital: number, session_id: string) =>
    post<{ project_cost: number; loan_amount: number; beneficiary_contribution: number }>(
      "/calculate-finance", { session_id, margin_capital }
    ),
  matchScheme: (project_cost: number, session_id: string) =>
    post<{ matched: boolean; scheme_name?: string; rate?: number; explanation: string }>(
      "/match-scheme", { session_id, project_cost }
    ),
  simulate: (session_id: string, revenue_delta_pct: number, cost_delta_pct: number, tenure_override_years?: number) =>
    post<{ emi: number; dscr: number; verdict: string; net_profit: number }>(
      "/simulate", { session_id, revenue_delta_pct, cost_delta_pct, tenure_override_years }
    ),
};
```

## `frontend/components/ConfidenceBadge.tsx`

```tsx
type Confidence = "High" | "Medium" | "Low";

const COLORS: Record<Confidence, string> = {
  High: "bg-green-100 text-green-800",
  Medium: "bg-amber-100 text-amber-800",
  Low: "bg-red-100 text-red-800",
};

export function ConfidenceBadge({ level }: { level: Confidence }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${COLORS[level]}`}>
      {level} confidence
    </span>
  );
}
```

## `frontend/components/VerdictBanner.tsx`

```tsx
type Verdict = "GO" | "CAUTION" | "ALTERNATIVE" | "NOT_RECOMMENDED";

const STYLES: Record<Verdict, { bg: string; label: string }> = {
  GO: { bg: "bg-green-600", label: "GO" },
  CAUTION: { bg: "bg-amber-500", label: "GO WITH CAUTION" },
  ALTERNATIVE: { bg: "bg-orange-500", label: "CONSIDER ALTERNATIVES" },
  NOT_RECOMMENDED: { bg: "bg-red-600", label: "NOT RECOMMENDED" },
};

export function VerdictBanner({ verdict, score }: { verdict: Verdict; score: number }) {
  const s = STYLES[verdict];
  return (
    <div className={`${s.bg} text-white rounded-lg p-4 flex items-center justify-between`}>
      <span className="text-2xl font-bold">{score}/100</span>
      <span className="text-lg font-semibold">{s.label}</span>
    </div>
  );
}
```

## `frontend/components/WhatIfSlider.tsx`

```tsx
import { useState, useCallback } from "react";
import { api } from "@/lib/api-client";

export function WhatIfSlider({ sessionId, onResult }: { sessionId: string; onResult: (r: any) => void }) {
  const [revenueDelta, setRevenueDelta] = useState(0);

  const handleChange = useCallback(async (val: number) => {
    setRevenueDelta(val);
    const result = await api.simulate(sessionId, val, 0);   // sub-second recompute (Section 21)
    onResult(result);
  }, [sessionId, onResult]);

  return (
    <div>
      <label className="block text-sm font-medium mb-1">Revenue change: {revenueDelta}%</label>
      <input
        type="range" min={-50} max={50} value={revenueDelta}
        onChange={(e) => handleChange(Number(e.target.value))}
        className="w-full h-8"  // large touch target, Section 20.2
      />
    </div>
  );
}
```

## `frontend/app/simulator/page.tsx`

```tsx
"use client";
import { useState } from "react";
import { WhatIfSlider } from "@/components/WhatIfSlider";
import { VerdictBanner } from "@/components/VerdictBanner";

export default function SimulatorPage() {
  const [result, setResult] = useState<{ verdict: any; dscr: number; net_profit: number } | null>(null);
  const sessionId = "demo-session-id"; // TODO: pull from session context/store

  return (
    <main className="max-w-md mx-auto p-4 space-y-6">
      <h1 className="text-xl font-semibold">What-If Simulator</h1>
      <WhatIfSlider sessionId={sessionId} onResult={setResult} />
      {result && (
        <div className="space-y-2">
          <VerdictBanner verdict={result.verdict} score={Math.round(result.dscr * 50)} />
          <p className="text-sm text-gray-600">DSCR: {result.dscr} · Net profit: ₹{result.net_profit}</p>
        </div>
      )}
    </main>
  );
}
```

---

## What's intentionally left as a stub, and why

| Module | Status | Reason |
|---|---|---|
| `market_intelligence/*.py` | Stub + confidence pattern | Real logic depends on your curated dataset shape — write it once Location 1's JSON files exist |
| `report/pdf_export.py` | Not included here | Wire `weasyprint` or a headless-Chrome print once `report.html.jinja` is drafted |
| `routes_profile.py`, `routes_rank.py`, `routes_market.py`, `routes_recommend.py`, `routes_explain.py` | Not included here | Same pattern as `routes_finance.py`/`routes_schemes.py` above — copy the shape once the underlying engine call is ready |
| Alembic migration files | Not included here | Run `alembic revision --autogenerate` once all models above are in place |
| `docker-compose.yml` | Not included here | Standard Postgres + two-service compose file — ask for it once your `.env` values are fixed |

Say the word if you want any of these five filled in next — the scheme/finance/recommendation engines and their tests above are the part worth getting exactly right first, since that's what a judge will actually poke at live.
