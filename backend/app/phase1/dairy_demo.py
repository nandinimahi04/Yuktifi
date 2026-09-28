"""
Dairy demo scenario.

A worked example for a village dairy unit. Its purpose is to demonstrate the
shape of a complete answer, so every number in it is either declared as a
scenario parameter or carried with a source. Nothing here is presented as a
measurement.

The response is labelled demo output at the top level (`is_demo`,
`data_status`) as well as in the scenario block, and the capital figures are
returned under `assumed_inputs` rather than silently used. That is the whole
reason this module exists in this form: a demo that shows a ₹1 lakh margin and
a ₹10 lakh project cost without saying so is indistinguishable, in a response
body, from a real plan for someone who has that money.

Official context can be attached to the demo - a livestock census extract, a
Census PCA village file - and doing so never changes the financial block. The
financials are a scenario; attaching real evidence about a village does not make
the entrepreneur's capital requirement real.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.phase1.service import (
    DAIRY_SCENARIO_MARGIN_CAPITAL,
    DAIRY_SCENARIO_MONTHLY_OPEX,
    DAIRY_SCENARIO_MONTHLY_REVENUE,
    DAIRY_SCENARIO_PROJECT_COST,
    run_decision,
)

DEMO_DATA_STATUS = "DEMO DATA / NOT LIVE"

DEFAULT_LOCATION = "Akkalkot, Solapur, Maharashtra"


#: Five risk scenarios, stated as scenarios with their trigger and the action
#: they imply. Each is a plausible local outcome rather than a worst case
#: invented to look thorough.
RISK_SCENARIOS: tuple[Dict[str, Any], ...] = (
    {
        "id": "monsoon_failure",
        "title": "Monsoon failure cuts fodder supply",
        "trigger": "Two or more consecutive failed rains in the block.",
        "impact": (
            "Fodder is bought in at a premium or the herd is culled. Variable cost per litre "
            "rises and herd size falls, so revenue and margin fall together."
        ),
        "mitigation": (
            "Store fodder for a full season and hold a buffer herd. Both cost money before "
            "they are needed, which is why the model prices them into the fixed costs."
        ),
    },
    {
        "id": "price_collapse",
        "title": "Co-operative or private buyer cuts the milk price",
        "trigger": "A new buyer within the block, or a seasonal supply glut.",
        "impact": (
            "Selling price per litre falls while the cost of producing it does not. The margin "
            "per litre compresses and, below a point, the unit stops covering its own costs."
        ),
        "mitigation": (
            "Diversify into value-added products (ghee, paneer, curd) where the price is set by "
            "value added rather than by the raw-milk market."
        ),
    },
    {
        "id": "animal_disease",
        "title": "Disease outbreak in the herd",
        "trigger": "Reported cases within the block, or a state advisory.",
        "impact": (
            "Mortality, veterinary cost and a fall in milk yield. Cash outflow rises in the same "
            "months as income falls, which is when a dairy unit is least able to absorb it."
        ),
        "mitigation": "Insurance, routine vaccination, and never running the herd on a single animal's health.",
    },
    {
        "id": "power_failure",
        "title": "Power interruption during milking",
        "trigger": "Extended load-shedding, or a transformer fault.",
        "impact": (
            "Milking is missed or deferred, so yield drops and the milk that does arrive is of "
            "lower grade, which reduces the price as well as the volume."
        ),
        "mitigation": "A backup inverter sized for the milking window, which is a capital cost with a stated payback.",
    },
    {
        "id": "labour_turnover",
        "title": "Milking staff leave",
        "trigger": "A better-paid opening elsewhere in the block.",
        "impact": (
            "Milking quality and frequency fall. This shows up as revenue rather than as a cost "
            "line, which is why it is easy to misread as a demand problem."
        ),
        "mitigation": "Written terms, a second trained person, and pay linked to yield rather than to hours.",
    },
)


def build_dairy_demo(
    location: str = DEFAULT_LOCATION,
    margin_capital: float = DAIRY_SCENARIO_MARGIN_CAPITAL,
    annual_interest_rate_pct: float = 12.0,
    tenure_months: int = 60,
    livestock_source: Optional[str] = None,
    census_source: Optional[str] = None,
    canonical_location: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the demo response.

    `margin_capital` and the project cost are SCENARIO PARAMETERS. They are
    returned under `assumed_inputs` with a note saying so, and the scenario
    block carries `margin_capital_is_assumed`, because a figure that is invented
    has to be identifiable as invented by a machine and not only by a reader who
    happens to know the module.
    """
    if float(margin_capital) <= 0:
        raise ValueError("margin_capital must be greater than 0 for the dairy scenario.")

    label = (canonical_location or {}).get("canonical_label") or location
    _seed_demo_evidence(label, float(margin_capital))

    decision = run_decision({
        "business_id": "dairy",
        "business_name": "Dairy",
        "location": location,
        "financial": {
            "business_type": "dairy",
            "margin_capital": float(margin_capital),
            "total_project_cost": DAIRY_SCENARIO_PROJECT_COST,
            "monthly_revenue": DAIRY_SCENARIO_MONTHLY_REVENUE,
            "monthly_opex": DAIRY_SCENARIO_MONTHLY_OPEX,
            "annual_interest_rate_pct": float(annual_interest_rate_pct),
            "tenure_months": int(tenure_months),
            # No debt is declared, so none is derived. The engine is explicit
            # that a loan is either stated or opted into, and the demo does not
            # opt in: showing a ₹9 lakh EMI against an unstated loan would be
            # the single most misleading figure in the response.
            "debt_amount": 0.0,
        },
        # These are scenario values, not measurements of the location. The
        # canonical location context, when supplied, does not overwrite them,
        # because a real population figure for a village is not the same thing
        # as the demand assumption a demo needs to be illustrative.
        "market": {
            "population": 5000,
            "mapped_competitors": 3,
            "local_evidence_count": 4,
            "evidence_count": 6,
            "geography": label,
            "basis": "Demo scenario values. Not a survey of this location.",
        },
        "risk_score": 70,
    })

    out: Dict[str, Any] = {
        "is_demo": True,
        "data_status": DEMO_DATA_STATUS,
        "scenario": {
            "business": "dairy",
            "location": (canonical_location or {}).get("canonical_label") or location,
            "margin_capital": float(margin_capital),
            "margin_capital_is_assumed": True,
            "total_project_cost": DAIRY_SCENARIO_PROJECT_COST,
            "total_project_cost_is_assumed": True,
            "annual_interest_rate_pct": float(annual_interest_rate_pct),
            "tenure_months": int(tenure_months),
        },
        "assumed_inputs": {
            "margin_capital": float(margin_capital),
            "total_project_cost": DAIRY_SCENARIO_PROJECT_COST,
            "monthly_revenue": DAIRY_SCENARIO_MONTHLY_REVENUE,
            "monthly_opex": DAIRY_SCENARIO_MONTHLY_OPEX,
            "market_population": 5000,
            "note": (
                "ASSUMPTION, not measurement. These are scenario parameters chosen to make the "
                "example illustrative. They are not quotes and not evidence about this "
                "location. Every figure derived from them inherits that status."
            ),
        },
        "financial": decision["financial"],
        "decision": {
            "verdict": decision["decision"],
            "financial_status": decision["financial_status"],
            "reasons": decision["reasons"],
            "conditions": decision["conditions"],
            "unknowns": decision["unknowns"],
            "market": decision["market"],
            "evidence_ids": decision["evidence_ids"],
            "confidence": decision["confidence"],
        },
        "risk": {
            "scenarios": [dict(s) for s in RISK_SCENARIOS],
            "note": (
                "These are the five risks a village dairy unit most often runs into. They are "
                "stated with their triggers so they can be watched for, not so they can be "
                "scored as though they had been measured."
            ),
        },
        "limitations": [
            "This is a demo. It is not a plan for any actual business and must not be presented as one.",
            "Margin capital, project cost, revenue and operating cost are scenario parameters, not measurements.",
            "No loan is modelled, so EMI and DSCR are not applicable. They are absent rather than assumed.",
            "The market figures are illustrative and are not a survey of the named location.",
            "Census and livestock context, where attached, are official historical records and are not current figures.",
        ],
    }

    if canonical_location is not None:
        out["location_context"] = canonical_location

    if livestock_source:
        out["livestock_context"] = _attach_livestock(livestock_source, out)
    if census_source:
        out["population_context"] = _attach_census(census_source, out, canonical_location)

    return out


def _seed_demo_evidence(geography: str, margin_capital: float) -> List[str]:
    """
    Register the demo's own inputs in the evidence store.

    A decision that cites nothing is hard to trust even when it is a demo, and
    hard to debug. So the demo's scenario parameters are stored like any other
    input, under the `demo_fixture` source, and every record is flagged
    `is_demo`, which forces its state down to INFERRED. That downgrade is the
    point: a reader can see that nothing here reached a verified state, without
    having to read the disclaimer at the top of the response.

    Returns the ids that were registered.
    """
    from app.phase2.service import upsert_evidence

    rows: List[Dict[str, Any]] = [
        {
            "metric": "dairy_monthly_revenue",
            "value": DAIRY_SCENARIO_MONTHLY_REVENUE,
            "unit": "INR per month",
            "method": "Demo scenario parameter",
        },
        {
            "metric": "dairy_monthly_opex",
            "value": DAIRY_SCENARIO_MONTHLY_OPEX,
            "unit": "INR per month",
            "method": "Demo scenario parameter",
        },
        {
            "metric": "margin_capital",
            "value": margin_capital,
            "unit": "INR",
            "method": "Demo scenario parameter",
        },
        {
            "metric": "total_project_cost",
            "value": DAIRY_SCENARIO_PROJECT_COST,
            "unit": "INR",
            "method": "Demo scenario parameter",
        },
        {
            "metric": "market_population",
            "value": 5000,
            "unit": "persons",
            "method": "Demo scenario parameter, not a survey",
        },
    ]

    ids: List[str] = []
    for row in rows:
        record = upsert_evidence({
            "id": f"demo_fixture_{row['metric']}_{geography}",
            "metric": row["metric"],
            "value": row["value"],
            "unit": row["unit"],
            "source_id": "demo_fixture",
            "geography": geography,
            "geography_level": "fictional/sample",
            "method": row["method"],
            "confidence": "High",
            "is_estimate": True,
            "is_demo": True,
            "limitations": (
                "DEMO DATA. A hand-authored scenario parameter chosen for illustration, "
                "not a measurement of any real business or location."
            ),
        })
        ids.append(record["id"])
    return ids


def _attach_livestock(source: str, out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach official livestock context.

    Failure to read the source is reported in the response rather than raised:
    a demo that cannot find an optional context file should still demonstrate
    the financial model, and it should say the context is missing rather than
    silently omitting it.
    """
    try:
        from app.data_ingestion.livestock import ingest_to_evidence
        return ingest_to_evidence(
            source,
            district=out["scenario"]["location"].split(",")[-2].strip()
            if "," in out["scenario"]["location"] else "Solapur",
            block=out["scenario"]["location"].split(",")[0].strip()
            if "," in out["scenario"]["location"] else "Akkalkot",
            village=None,
        )
    except (ValueError, TypeError, FileNotFoundError, KeyError) as exc:
        return {
            "available": False,
            "reason": f"The livestock source could not be read: {exc}",
            "effect_on_financials": "None. Livestock context is supply-side context and does not change the financial block.",
        }


def _attach_census(
    source: str,
    out: Dict[str, Any],
    canonical_location: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Attach official Census PCA context and reflect its population in the decision.

    The population here IS a measured figure from an official file, so unlike the
    scenario's own 5,000 it is allowed to be the number the decision reads. It
    still does not touch the financial block: a real population figure does not
    make the entrepreneur's capital requirement real.

    The canonical context is passed through whole rather than reconstructed from
    the display label, because the census reader matches on the canonical
    hierarchy (and village code when one is present). A label split on commas
    gets the right words and can still fail to match, and a failed match that
    looks like a data problem is a misleading report of one.
    """
    context_arg = canonical_location or _location_parts(out["scenario"]["location"])
    try:
        from app.data_ingestion.census_population import ingest_to_evidence
        context = ingest_to_evidence(source, context_arg)
    except (ValueError, TypeError, FileNotFoundError, KeyError) as exc:
        return {
            "available": False,
            "reason": f"The census source could not be read: {exc}",
            "effect_on_financials": "None. Population context does not change the financial block.",
        }

    # A non-match is a legitimate answer from a real file: the caller asked for
    # this village and the file does not contain it. That is reported as missing
    # rather than replaced with the scenario's own population, because the
    # scenario figure is not what the caller asked for.
    if context.get("summary", {}).get("status") != "matched":
        return {
            "available": False,
            "reason": "The census source was read but contains no row for this location.",
            "validation": context.get("validation"),
            "effect_on_financials": "None. Population context does not change the financial block.",
        }

    metrics = (context.get("summary") or {}).get("metrics") or {}
    population = (metrics.get("population") or {}).get("value")
    if population is not None:
        out["decision"]["market"]["population"] = population
        out["decision"]["market"]["population_source"] = (
            "Census of India Primary Census Abstract, village-level extract supplied by the caller. "
            "Reference year 2011, not a current population estimate."
        )
    return context


def _location_parts(label: str) -> Dict[str, Any]:
    """
    Split a free-text location label into the hierarchy the census reader wants.

    Only used when the caller supplied no canonical context. A split label is a
    best guess at the hierarchy, and the census reader reports a non-match
    rather than approximating, so a wrong guess here costs a "no row found" and
    not a wrong number.
    """
    parts = [p.strip() for p in label.split(",") if p.strip()]
    return {
        "village": parts[0] if parts else None,
        "subdistrict": parts[0] if len(parts) > 1 else None,
        "block": parts[0] if len(parts) > 1 else None,
        "district": parts[-2] if len(parts) > 1 else (parts[0] if parts else None),
        "state": parts[-1] if parts else None,
        "canonical_label": label,
    }
