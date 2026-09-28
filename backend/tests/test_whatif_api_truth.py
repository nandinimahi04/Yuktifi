"""
The What-If endpoint could only ask two questions, and the third screen answered
a third one.

`SimulateRequest` had three fields: `revenue_delta_pct`, `cost_delta_pct` and
`tenure_override_years`. The canonical engine behind it had thirteen levers in
`WhatIfAdjustments` - own capital, debt, interest rate, tax rate, supplier
terms, operating days, price growth. Eleven of them were reachable only by
importing Python.

The consequence was not that the product was slow to answer. It was that it
asked the wrong question without saying so. A founder who wanted to know "what
if I put in more of my own money" could only express it as a revenue cut, and
the screen would confidently report a smaller profit, which is a real number for
a scenario nobody was considering. The engine could answer; the product could
not ask.

These tests pin the request surface to the engine's own lever set, and pin the
old three fields to the meaning they always had.
"""
import pytest

from app.financial.canonical_engine import CanonicalFinancialInput
from app.financial.projection import WhatIfAdjustments
from app.schemas.simulation import SimulateRequest

ENGINE_LEVERS = {f.name for f in WhatIfAdjustments.__dataclass_fields__.values()}


# ── The request surface must not be a subset of the engine ───────────────────

def test_every_engine_lever_is_reachable_over_http():
    """
    Any lever the engine can apply, a client must be able to name. This is the
    test that would have caught the gap: it fails the moment a lever is added to
    the engine and not to the schema.
    """
    # The declared fields, not a populated request - an unset request correctly
    # reports no levers at all, which is the next test's subject.
    declared = set(SimulateRequest.model_fields)
    declared -= {"session_id", "revenue_delta_pct", "cost_delta_pct", "tenure_override_years"}
    # A lever the client may not set is a lever the client cannot ask about.
    assert declared == ENGINE_LEVERS, (
        f"engine levers with no request field: {sorted(ENGINE_LEVERS - declared)}; "
        f"request fields the engine does not have: {sorted(declared - ENGINE_LEVERS)}"
    )

    # And the translation must actually emit a lever when the client sets one,
    # rather than declaring the field and then dropping it on the floor.
    for lever in sorted(ENGINE_LEVERS):
        emitted = SimulateRequest(session_id="s", **{lever: 1.0}).to_adjustments()
        assert set(emitted) == {lever}


def test_an_unset_lever_is_absent_rather_than_zero():
    """
    `to_adjustments` must omit unset levers. Including them as 0 would read as
    "set this to nothing" - a zero interest rate, a zero price, a zero tax rate
    - which is a different and much more flattering plan than the one the caller
    asked about.
    """
    assert SimulateRequest(session_id="s").to_adjustments() == {}

    # Explicitly zero IS meaningful and must survive.
    zeroes = SimulateRequest(
        session_id="s", interest_rate_annual_pct=0.0, units_multiplier=1.0
    ).to_adjustments()
    assert zeroes == {"interest_rate_annual_pct": 0.0, "units_multiplier": 1.0}


def test_the_shorthand_fields_still_default_to_a_no_op():
    """
    An old client that sends only `session_id` must get the plan back unchanged,
    not a plan with a 0% revenue shock applied twice.
    """
    # The shorthand fields are not levers; they are translated into levers by
    # `_legacy_levers`, so they must not be counted as a second, competing set.
    req = SimulateRequest(session_id="s")
    assert req.revenue_delta_pct == 0.0
    assert req.cost_delta_pct == 0.0
    assert req.tenure_override_years is None
