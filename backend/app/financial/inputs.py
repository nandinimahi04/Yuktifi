"""
Input typing, provenance and validation for the YuktiFi canonical engine.

This module is PART OF the canonical engine (app.financial.*), not a second
engine. It owns three responsibilities and contains no arithmetic:

    1. What kind of number is this?          -> InputSource
    2. Where did it come from, and when?      -> ProvenanceEntry
    3. Is it usable at all?                   -> ValidationIssue

The distinction that matters throughout: a WARNING means the engine can
still compute, but the result rests on a gap, and that gap is carried into
the confidence assessment and the financial status. An ERROR means the
number is not interpretable (a negative selling price, an interest rate
below zero, 40 operating days in a month) and must be reported rather than
silently corrected. Nothing in this module adjusts a value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.financial.canonical_engine import CanonicalFinancialInput


SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"

#: Days a month can legitimately have. 26 is not a bound: an establishment
#: working 30 or 31 days a month is unusual but real, and is not an error.
MIN_OPERATING_DAYS = 1
MAX_OPERATING_DAYS = 31


class InputSource(str, Enum):
    """
    Where a number came from. Every financial input carries one of these.

    USER_PROVIDED    the entrepreneur entered it, or it came from an onboarding
                     form they filled in.
    SOURCE_DERIVED   computed from a cited dataset (census, cost profile,
                     scheme rule). Traceable to a source id.
    TEMPLATE_DEFAULT supplied by the business template for this category.
    MODEL_ASSUMPTION chosen by the financial model itself because the field is
                     required for the model to run and no evidence exists.
    ESTIMATE         an informed guess. Never presented as measured.
    DEMO_DATA        illustrative only. Must be labelled as such downstream.
    """
    USER_PROVIDED = "USER_PROVIDED"
    SOURCE_DERIVED = "SOURCE_DERIVED"
    TEMPLATE_DEFAULT = "TEMPLATE_DEFAULT"
    MODEL_ASSUMPTION = "MODEL_ASSUMPTION"
    ESTIMATE = "ESTIMATE"
    DEMO_DATA = "DEMO_DATA"

    def __str__(self) -> str:  # keeps JSON serialisation as the bare value
        return self.value


VALID_INPUT_SOURCES = frozenset(s.value for s in InputSource)

#: Sources that mean "we do not have observed data for this". They are not
#: errors, but they cap how confident any figure derived from them can be.
UNVERIFIED_SOURCES = frozenset({
    InputSource.MODEL_ASSUMPTION.value,
    InputSource.ESTIMATE.value,
    InputSource.DEMO_DATA.value,
})

#: Weight each source contributes to the confidence score. A user-typed number
#: is not automatically true, but it is observed; a model assumption is not.
SOURCE_CONFIDENCE_WEIGHT: Dict[str, float] = {
    InputSource.USER_PROVIDED.value: 1.00,
    InputSource.SOURCE_DERIVED.value: 0.85,
    InputSource.TEMPLATE_DEFAULT.value: 0.60,
    InputSource.ESTIMATE.value: 0.40,
    InputSource.MODEL_ASSUMPTION.value: 0.30,
    InputSource.DEMO_DATA.value: 0.20,
}

#: Beyond this age, even a cited figure is treated as stale for confidence.
FRESHNESS_HALFLIFE_DAYS = 365.0

#: Multiplier applied to the confidence score when at least one recorded input
#: is older than a year. Deliberately a penalty rather than a hard zero: a
#: three-year-old population figure may still be the best available, but it
#: should not be worth as much as this month's.
STALE_CONFIDENCE_MULTIPLIER = 0.80


@dataclass
class ProvenanceEntry:
    """
    One field, where it came from, when it was true, and what it is worth.

    `as_of` is a date string (ISO). `note` is the human explanation shown in
    the evidence drawer, e.g. the dataset name or the template id.
    """
    field: str
    value: Any
    source: str
    as_of: Optional[str] = None
    note: Optional[str] = None
    freshness_days: Optional[int] = None

    def __post_init__(self) -> None:
        if self.source not in VALID_INPUT_SOURCES:
            raise ValueError(
                f"Invalid input source {self.source!r} for {self.field!r}. "
                f"Allowed: {sorted(VALID_INPUT_SOURCES)}"
            )

    @property
    def verified(self) -> bool:
        return self.source in (InputSource.USER_PROVIDED.value, InputSource.SOURCE_DERIVED.value)

    @property
    def weight(self) -> float:
        return SOURCE_CONFIDENCE_WEIGHT.get(self.source, 0.30)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source": self.source,
            "as_of": self.as_of,
            "note": self.note,
            "freshness_days": self.freshness_days,
            "verified": self.verified,
        }


def provenance_summary(entries: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise whatever shape the caller passed into ProvenanceEntry objects.

    Accepts `{"field": InputSource.USER_PROVIDED}` (source only) or
    `{"field": {"source": ..., "as_of": ..., "note": ...}}`. An unrecognised
    source is preserved as an ESTIMATE rather than dropped, so a caller cannot
    launder an undeclared number into looking verified.
    """
    out: Dict[str, ProvenanceEntry] = {}
    for name, raw in (entries or {}).items():
        if isinstance(raw, ProvenanceEntry):
            out[name] = raw
            continue
        if isinstance(raw, str):
            source = raw if raw in VALID_INPUT_SOURCES else InputSource.ESTIMATE.value
            out[name] = ProvenanceEntry(field=name, value=None, source=source)
            continue
        if isinstance(raw, dict):
            source = str(raw.get("source") or "")
            if source not in VALID_INPUT_SOURCES:
                source = InputSource.ESTIMATE.value
            out[name] = ProvenanceEntry(
                field=name,
                value=raw.get("value"),
                source=source,
                as_of=raw.get("as_of"),
                note=raw.get("note"),
                freshness_days=raw.get("freshness_days"),
            )
            continue
        out[name] = ProvenanceEntry(
            field=name, value=None, source=InputSource.ESTIMATE.value,
            note=f"Unrecognised provenance entry of type {type(raw).__name__}.",
        )
    return out


@dataclass
class ValidationIssue:
    field: str
    code: str
    message: str
    severity: str = SEVERITY_ERROR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


class FinancialValidationError(ValueError):
    """
    Raised when an input cannot be interpreted at all.

    The engine does not repair the value and carry on. A negative interest
    rate, a 40-day month or a negative own capital are not inputs to be
    guessed at; they are errors the caller has to see and fix.
    """

    def __init__(self, issues: List[ValidationIssue]) -> None:
        self.issues = list(issues)
        detail = "; ".join(f"{i.field}: {i.message}" for i in self.issues)
        super().__init__(detail)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "FINANCIAL_INPUT_INVALID",
            "message": "The financial inputs could not be used as supplied.",
            "issues": [i.to_dict() for i in self.issues],
        }


def _err(field_name: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(field_name, code, message, SEVERITY_ERROR)


def _warn(field_name: str, code: str, message: str) -> ValidationIssue:
    return ValidationIssue(field_name, code, message, SEVERITY_WARNING)


def _check_number(
    issues: List[ValidationIssue],
    inp: "CanonicalFinancialInput",
    attr: str,
    *,
    label: str,
    minimum: Optional[float] = None,
    zero_is_warning: bool = False,
    zero_message: Optional[str] = None,
    maximum: Optional[float] = None,
) -> None:
    """Shared numeric check. Never modifies the value."""
    value = getattr(inp, attr, None)
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        issues.append(_err(attr, "NOT_A_NUMBER", f"{label} must be a number, got {value!r}."))
        return
    if minimum is not None and value < minimum:
        issues.append(_err(
            attr, "BELOW_MINIMUM",
            f"{label} is {value}, which is below the minimum of {minimum}.",
        ))
        return
    if maximum is not None and value > maximum:
        issues.append(_err(
            attr, "ABOVE_MAXIMUM",
            f"{label} is {value}, which is above the maximum of {maximum}.",
        ))
        return
    if zero_is_warning and value == 0:
        issues.append(_warn(attr, "NOT_MODELLED", zero_message or f"{label} is zero, so it is not modelled."))


def validate_financial_input(inp: "CanonicalFinancialInput") -> List[ValidationIssue]:
    """
    Validate a canonical input.

    Returns every issue found. ERROR means the figure is not interpretable.
    WARNING means the engine can proceed but the result is resting on a gap,
    and that gap must travel with the result into confidence and status.

    This function never changes a value. Correction is the caller's decision,
    not the model's.
    """
    issues: List[ValidationIssue] = []

    if not (inp.business_type or "").strip():
        issues.append(_err("business_type", "MISSING", "A business type is required to model a business."))

    if not inp.products:
        issues.append(_err(
            "products", "NO_PRODUCTS",
            "At least one product or service line is required. Without one there is no revenue, "
            "and every downstream figure would be an artefact of a zero.",
        ))

    for idx, p in enumerate(inp.products):
        prefix = f"products[{idx}].{p.name or idx}"
        if not (p.name or "").strip():
            issues.append(_warn(f"{prefix}.name", "MISSING", "This product line has no name."))
        for attr, label, zero_message in (
            ("units_per_month", "Monthly units",
             f"{prefix} has no monthly volume, so its revenue is not modelled."),
            ("selling_price", "Selling price",
             f"{prefix} has a selling price of zero, so its revenue is not modelled."),
            ("variable_cost_per_unit", "Variable cost per unit",
             f"{prefix} has no variable cost declared, so its contribution is overstated by the "
             f"whole of its own cost."),
        ):
            value = getattr(p, attr, None)
            if value is None:
                issues.append(_warn(f"{prefix}.{attr}", "MISSING", f"{prefix}: {label} is missing."))
                continue
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                issues.append(_err(
                    f"{prefix}.{attr}", "NOT_A_NUMBER", f"{prefix}: {label} must be a number."))
                continue
            if value < 0:
                issues.append(_err(
                    f"{prefix}.{attr}", "NEGATIVE",
                    f"{prefix}: {label} is {value}. A negative value is not interpretable and has "
                    f"not been corrected.",
                ))
            elif value == 0:
                issues.append(_warn(f"{prefix}.{attr}", "NOT_MODELLED", zero_message))

    for attr in ("rent", "salaries", "electricity", "transport", "maintenance",
                 "marketing", "insurance", "admin", "other"):
        value = getattr(inp.opex, attr, 0.0)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            issues.append(_err(f"opex.{attr}", "NOT_A_NUMBER", f"Operating cost {attr} must be a number."))
        elif value < 0:
            issues.append(_err(
                f"opex.{attr}", "NEGATIVE",
                f"Operating cost {attr} is {value}. A cost cannot be negative.",
            ))

    _check_number(issues, inp, "own_capital", label="Own capital", minimum=0.0,
                  zero_is_warning=True,
                  zero_message="No own capital was declared, so return on the entrepreneur's own "
                               "money cannot be assessed.")
    _check_number(issues, inp, "total_project_cost", label="Total project cost", minimum=0.0)
    _check_number(issues, inp, "debt_amount", label="Loan amount", minimum=0.0)
    _check_number(issues, inp, "other_funding", label="Other funding", minimum=0.0)
    _check_number(issues, inp, "eligible_subsidy", label="Eligible subsidy", minimum=0.0)
    _check_number(issues, inp, "asset_cost", label="Asset cost", minimum=0.0)
    _check_number(issues, inp, "salvage_value", label="Salvage value", minimum=0.0)
    _check_number(issues, inp, "interest_rate_annual_pct", label="Interest rate", minimum=0.0)
    _check_number(issues, inp, "annual_price_growth_pct", label="Annual price growth", minimum=-100.0)
    _check_number(issues, inp, "annual_volume_growth_pct", label="Annual volume growth", minimum=-100.0)
    _check_number(issues, inp, "discount_rate_pct", label="Discount rate", minimum=0.0)

    tax = getattr(inp, "tax_rate_pct", None)
    if tax is not None:
        if not isinstance(tax, (int, float)) or isinstance(tax, bool):
            issues.append(_err("tax_rate_pct", "NOT_A_NUMBER", "Tax rate must be a number."))
        elif tax < 0:
            issues.append(_err("tax_rate_pct", "NEGATIVE", f"Tax rate is {tax}. A tax rate cannot be negative."))
        elif tax > 100:
            issues.append(_err(
                "tax_rate_pct", "ABOVE_MAXIMUM",
                f"Tax rate is {tax}%, which exceeds 100%. No tax rate above 100% exists.",
            ))
    else:
        issues.append(_warn(
            "tax_rate_pct", "NOT_MODELLED",
            "No tax rate was declared, so tax is not modelled. Post-tax figures are pre-tax.",
        ))

    tenure = getattr(inp, "tenure_months", 0)
    if not isinstance(tenure, int) or isinstance(tenure, bool):
        issues.append(_err("tenure_months", "NOT_A_NUMBER", "Tenure must be a whole number of months."))
    elif tenure < 0:
        issues.append(_err("tenure_months", "NEGATIVE", f"Tenure is {tenure} months."))

    mor = getattr(inp, "moratorium_months", 0)
    if not isinstance(mor, int) or isinstance(mor, bool):
        issues.append(_err("moratorium_months", "NOT_A_NUMBER", "Moratorium must be a whole number of months."))
    elif mor < 0:
        issues.append(_err("moratorium_months", "NEGATIVE", f"Moratorium is {mor} months."))
    elif isinstance(tenure, int) and tenure > 0 and mor >= tenure:
        issues.append(_err(
            "moratorium_months", "EXCEEDS_TENURE",
            f"A {mor}-month moratorium leaves no repayment period inside a {tenure}-month tenure.",
        ))

    if (inp.debt_amount or 0) > 0:
        if tenure == 0:
            issues.append(_err(
                "tenure_months", "ZERO_TENURE_WITH_DEBT",
                "A loan is declared but its tenure is zero, so the repayment cannot be scheduled.",
            ))
        if mor >= tenure and tenure > 0:
            issues.append(_err(
                "moratorium_months", "NO_REPAYMENT_PERIOD",
                "The moratorium is as long as the tenure, so no principal is ever repaid.",
            ))

    life = getattr(inp, "useful_life_years", 0.0)
    if not isinstance(life, (int, float)) or isinstance(life, bool):
        issues.append(_err("useful_life_years", "NOT_A_NUMBER", "Useful life must be a number of years."))
    elif life <= 0:
        issues.append(_err(
            "useful_life_years", "NOT_POSITIVE",
            f"Useful life is {life} years. An asset with a life of zero years cannot be depreciated; "
            f"depreciation has not been assumed.",
        ))

    days = getattr(inp, "operating_days_per_month", None)
    if days is not None:
        if not isinstance(days, int) or isinstance(days, bool):
            issues.append(_err("operating_days_per_month", "NOT_A_NUMBER", "Operating days must be a whole number."))
        elif not (MIN_OPERATING_DAYS <= days <= MAX_OPERATING_DAYS):
            issues.append(_err(
                "operating_days_per_month", "OUT_OF_RANGE",
                f"Operating days per month is {days}. A month has between {MIN_OPERATING_DAYS} "
                f"and {MAX_OPERATING_DAYS} days, so this value has not been adjusted to fit.",
            ))

    seasonality = getattr(inp, "seasonality_index", None)
    if seasonality is not None:
        if not isinstance(seasonality, (list, tuple)) or len(seasonality) != 12:
            issues.append(_err(
                "seasonality_index", "WRONG_LENGTH",
                f"A seasonality profile needs exactly 12 monthly factors, got "
                f"{len(seasonality) if hasattr(seasonality, '__len__') else type(seasonality).__name__}.",
            ))
        else:
            for m, factor in enumerate(seasonality, start=1):
                if not isinstance(factor, (int, float)) or isinstance(factor, bool):
                    issues.append(_err(f"seasonality_index[{m}]", "NOT_A_NUMBER", f"Month {m} factor is not a number."))
                elif factor <= 0:
                    issues.append(_err(
                        f"seasonality_index[{m}]", "NON_POSITIVE",
                        f"Month {m} seasonality factor is {factor}. A month with zero or negative "
                        f"demand cannot be modelled.",
                    ))

    wc = getattr(inp, "working_capital_cfg", None)
    if wc is not None:
        for attr, label in (("inventory_days", "Inventory days"),
                            ("receivable_days", "Receivable days"),
                            ("payable_days", "Payable days")):
            value = getattr(wc, attr, 0)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                issues.append(_err(f"working_capital_cfg.{attr}", "NOT_A_NUMBER", f"{label} must be a number."))
            elif value < 0:
                issues.append(_err(
                    f"working_capital_cfg.{attr}", "NEGATIVE", f"{label} is {value}."))

    horizon = getattr(inp, "npv_horizon_years", 0)
    if not isinstance(horizon, int) or isinstance(horizon, bool):
        issues.append(_err("npv_horizon_years", "NOT_A_NUMBER", "NPV horizon must be a whole number of years."))
    elif horizon < 1:
        issues.append(_err("npv_horizon_years", "BELOW_MINIMUM", f"NPV horizon is {horizon} years."))

    declared = provenance_summary(getattr(inp, "field_provenance", {}) or {})
    if not declared:
        issues.append(_warn(
            "field_provenance", "NO_PROVENANCE",
            "No input provenance was recorded, so it is not possible to say which figures are "
            "observed and which are assumed. Confidence is capped accordingly.",
        ))

    return issues


def split_issues(issues: List[ValidationIssue]) -> Dict[str, List[ValidationIssue]]:
    return {
        "errors": [i for i in issues if i.severity == SEVERITY_ERROR],
        "warnings": [i for i in issues if i.severity == SEVERITY_WARNING],
    }


def raise_on_errors(issues: List[ValidationIssue]) -> None:
    errors = [i for i in issues if i.severity == SEVERITY_ERROR]
    if errors:
        raise FinancialValidationError(errors)
