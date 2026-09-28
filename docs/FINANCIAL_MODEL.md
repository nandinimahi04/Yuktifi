# The financial model

There is exactly one place in this codebase that decides what a business earns.
It is `backend/app/financial/`. Every screen that shows a number — the analysis
dashboard, the What-If simulator, the stress matrix, the dynamic simulator, the
report, the ranking list, the AI narration — is a *reader* of that model.

This document describes what the model computes, what it refuses to compute, and
the rules that keep the readers honest. It is derived from the code, not from
intent; if the two disagree, the code is right and this file is stale.

---

## 1. The rule that everything else follows from

**A number is only published if it was declared.**

The engine never fills a gap with a plausible figure. A founder who did not
mention a loan has no EMI, no DSCR and no interest. A business with no project
cost has no ROI and no payback. These are reported as `null` alongside a status
string that says *why*, and every surface is required to render that difference
rather than collapsing it to zero.

This is not a stylistic preference. The failure mode it prevents is specific:
a null that is displayed as `0` is not obviously wrong, and a founder checking
the screen has no reason to suspect the number underneath it. Worse, a
*total* can be right while its *composition* is fiction — see §8.

The three states are kept distinct everywhere:

| State | Meaning | Example |
| --- | --- | --- |
| `null` | not declared, or not applicable | DSCR with no debt |
| `0` | declared, and genuinely zero | opex for a business with no fixed cost |
| status string | which of the above applies, and why | `dscr_status = NOT_APPLICABLE_NO_DEBT` |

`null` and `0` are never interchanged. Where a boolean-like answer has three
states, the third is a separate flag rather than a magic value — see §7.

---

## 2. Where the numbers come from

`CanonicalFinancialInput` (`app/financial/canonical_engine.py`) is the only
accepted input. It carries three things together:

- **the figures** — products, opex lines, capital, loan terms;
- **the provenance** of each figure, via `FieldSource` — declared, observed,
  derived, defaulted;
- **the unknowns** — `assessability_unknowns` naming what is still missing.

The provenance travels into the result (`input_provenance`,
`assumptions_provenance`) and is what the UI uses to distinguish "this is what
you told us" from "this is what we worked out from what you told us". Validation
issues are returned, not raised: `validation_errors`,
`validation_warnings`, `validation_issues`.

Validation **refuses** rather than repairs. A negative price, a negative
interest rate or a zero tenure against a non-zero debt is an error, and the
engine does not clamp it to something runnable and continue — a clamped input
produces a confident wrong answer, which is worse than a refusal.

---

## 3. The profit waterfall

Monthly, then annualised. The order matters and is not rearranged by any screen.

```
revenue                 Σ (units × price)  per product
− variable costs        Σ (units × variable cost per unit)
= gross profit
− opex                  Σ of the declared opex lines
= EBITDA
− depreciation          from declared asset base and useful life
= EBIT
− interest              from the real amortisation schedule
= PBT
− tax                   only if a tax rate was declared
= PAT                   profit after tax
```

Two details that were wrong before and are now pinned by tests:

**Interest comes from the schedule, not a formula.** `build_loan_schedule`
produces a month-by-month row, and `monthly_interest` is `year1_interest / 12`.
A closed-form `principal × rate / 12` is wrong twice: it ignores a declining
balance, and during a moratorium it understates what is actually payable. The
projected cash flow adds back `annual_interest` and subtracts only the principal
portion, because `PAT` has *already* had interest charged — deducting the full
payment from a post-interest figure charges the same interest twice.

**Contribution per unit is withheld when it would be fiction.** If a plan has
aggregate revenue but no per-unit price and cost, then `contribution_per_unit`
and `break_even_units` are `null` and `break_even_revenue` is published
instead. Deriving a unit price from a margin assumption and calling it a unit
economics is a fabrication, and a downstream "you need 2,187 units a month"
figure built that way is unfalsifiable.

**Depreciation follows the declared asset base.** Useful life and asset cost
come from the input. Where a dataset implies a different asset base from the one
the founder declared, the declared one wins and the discrepancy is recorded.

---

## 4. Tax

`tax_status` is one of:

- `MODELLED` — a tax rate was declared; `monthly_tax` and `annual_tax` are real.
- `NOT_MODELED` — no rate was declared. PAT here is **before** tax, and is
  labelled as such.

A default tax rate would be a silent policy decision presented as the founder's
own. The status string exists so that a screen cannot accidentally compare a
post-tax figure from one run with a pre-tax figure from another — the exact
mistake that appeared when a What-If run applied a tax rate the base plan never
had. The What-If response carries both `tax_status` and `base_tax_status` for
this reason.

---

## 5. Working capital

Published as a block, and derived from the declared cycle:

```
inventory_requirement      inventory days of variable cost
receivables_requirement    receivable days of revenue
payables_requirement       payable days of variable cost
net_working_capital        Σ requirements
cash_conversion_cycle_days inventory + receivable − payable
```

Two conventions that were previously mis-stated:

- **`daily_cash_needed` is operating cash flow per trading day**
  (`monthly_operating_cash_flow / operating_days_per_month`), and the weekly
  figure is that × 7. It is *not* net working capital divided by a month, and
  *not* opex divided by 30. Those are three different numbers and the old code
  reported whichever was convenient at the call site.
- **`operating_days_per_month` is a declared input**, not a constant 30. A
  business trading 26 days a month is modelled on 26 days.

`working_capital_days_scale` in the What-If set multiplies the declared cycle,
so "what if my supplier gave me 60 days" is answerable.

---

## 6. Decision gates and status

Five gates, evaluated in order, each with a status and a reason:

`FINANCING_GATE` · `UNIT_ECONOMICS_GATE` · `BREAK_EVEN_GATE` ·
`CASH_FLOW_GATE` · `DEBT_SERVICE_GATE`

Default benchmarks (`DEFAULT_GATE_BENCHMARK`): DSCR ≥ 1.25, contribution margin
≥ 20%, EBITDA margin ≥ 5%, ROI on project ≥ 0%, payback ≤ 60 months, cash buffer
≥ 1 month, financing must reconcile.

A gate resolves to one of four states, and the fourth matters:

| State | Meaning |
| --- | --- |
| pass | met on declared data |
| fail | not met on declared data |
| unknown | the input was never declared, so the gate is unanswered |
| not applicable | the question does not arise — e.g. debt service with no debt |

`UNKNOWN` is not `FAIL`, and `NOT_APPLICABLE` is not `UNKNOWN`. A debtless
business has an *inapplicable* debt-service gate with the reason recorded; a
business that never declared a project cost has an *unknown* financing gate. The
result keeps them in separate lists (`gates_passed`, `failed_gates`,
`unknown_gates`, `not_applicable_gates`) precisely so the two cannot be
conflated on the way to a verdict.

`financial_status` is a structured verdict, not a bare string — `value` plus
`reasons`, `conditions`, and the four gate lists:

```
GO              all applicable gates pass
CONDITIONAL     some pass, some fail, none unknown
NO_GO           a gate fails on declared data
INSUFFICIENT_EVIDENCE   a gate is unknown — the plan was never fully declared
```

`financial_confidence` is separate and answers a different question: how much of
the model was observed versus declared (`band` HIGH/MEDIUM/LOW with a `score`
and a stated `basis`). It is deliberately independent of performance — a
well-evidenced business that loses money is high confidence, and a profitable
projection built on assumptions is low confidence.

---

## 7. Tri-state answers

Any yes/no question with a "not applicable" case is returned as three states,
never as a boolean that silently answers a question nobody asked.

**`survives_stress`** — can the scenario still cover its own debt service?

| Value | Meaning |
| --- | --- |
| `true` | DSCR ≥ 1.0 |
| `false` | DSCR < 1.0, **or** CFADS is negative |
| `null` | no debt service exists to cover |

The original expression was `dscr is not None and dscr >= 1.0`, which reported
**every debtless business as failing a stress test**. A borrower with no loan
cannot fail to service a loan. `survives_stress_applicable` is published
alongside so a caller that needs a real boolean can branch explicitly.

**`payback_achieved`** — same treatment, with
`payback_status` / `payback_undetermined_reason` for the unknown case.

---

## 8. Composition is not optional

A total that is right does not make its parts right. The clearest instance in
this codebase:

A founder entered one figure, `fixed_cost_monthly = 17,500`, documented as "rent,
salary, insurance". The opex block split it 50/30/20 into rent 8,750, salaries
5,250 and electricity 1,750. The total was correct. The composition was
invented — and the cost breakdown, the AI explanation and the PDF report all
repeated those three numbers as though the founder had stated them.

The founder's check is the total, so the total matched, and the fiction passed
review. It is now carried wholly on `opex.other`, with the cost profile left
accurate about what it actually records: one aggregate, not three readings.

The general rule: **a line item must have a source.** If it has no source it
does not go in the block; if the block would then be empty, the total carries it
and the screen says the composition is undeclared.

---

## 9. Stress scenarios

`STRESS_SCENARIOS` in `app/financial/projection.py` is the only matrix. It is a
tuple of seven, and `apply_shock` is the only thing that applies one.

| key | severity | demand | price | cost | rate |
| --- | --- | --- | --- | --- | --- |
| `demand_minus_10` | moderate | −10% | | | |
| `demand_minus_20` | severe | −20% | | | |
| `price_minus_10` | moderate | | −10% | | |
| `cost_plus_10` | moderate | | | +10% | |
| `cost_plus_15` | severe | | | +15% | |
| `interest_plus_2` | severe | | | | +2 pts |
| `combined_severe` | combined | −20% | −10% | +15% | +2 pts |

A **volume** shock and a **price** shock are different events and are kept
distinct on purpose. A volume fall takes variable cost down with it; a price cut
does not. `combined_severe` therefore compounds the four moves properly — the
earlier version omitted the price cut and overstated worst-case EBITDA by about
₹1,600 a month on the Vada Pav fixture.

The stress adapter, the What-If simulator and the dynamic simulator all call
`apply_shock` / `apply_what_if`. They cannot disagree about what a given shock
does, and a test asserts that they do not.

---

## 10. The What-If levers

`WhatIfAdjustments` has thirteen levers, and **all thirteen are reachable over
HTTP** — this was the gap. The endpoint used to accept two shocks and a tenor;
the other eleven existed only in Python, so a founder could not ask "what if I
put in more of my own money" or "what if my supplier gave me 60 days" without
the product being able to phrase the question.

| Lever | Unit |
| --- | --- |
| `units_multiplier` | factor (1.10 = 110% of current volume) |
| `price_delta_pct` | percentage points |
| `variable_cost_delta_pct` | percentage points |
| `fixed_cost_delta_pct` | percentage points |
| `interest_rate_annual_pct` | percentage points, absolute |
| `tenure_months` | months |
| `own_capital` | currency, absolute |
| `debt_amount` | currency, absolute |
| `other_funding` | currency, absolute |
| `tax_rate_pct` | percentage points |
| `operating_days_per_month` | days |
| `annual_price_growth_pct` | percentage points |
| `working_capital_days_scale` | factor on the declared cycle |

The original `revenue_delta_pct` / `cost_delta_pct` / `tenure_override_years`
are retained and **translated into levers**, so both forms run through one path
and cannot answer differently. `revenue_delta_pct` remains a *volume* shock
(`units_multiplier = 1 + pct/100`); reinterpreting it as a price move would
change every existing client's answer in the flattering direction.

Responses carry `applied_adjustments` — each lever with its previous value,
applied value and change — so a caller can confirm its request was honoured
rather than silently ignored.

One result worth stating plainly, because it looks like a bug and is not:
**a longer tenure lowers the EMI and lowers profit.** Extending 60 months to 120
cuts the payment by ~39% and more than doubles lifetime interest, and year-one
interest rises slightly because the balance declines more slowly. Presenting only
the lower EMI would be the misleading half of the answer.

---

## 11. What each surface is allowed to do

| Surface | Role |
| --- | --- |
| `app/financial/` | the only place a figure is computed |
| `app/engines/financial_engine.py` | presentation adapter; adds no arithmetic |
| `app/engines/stress_engine.py` | iterates the canonical matrix |
| `app/engines/simulation_engine.py` | applies canonical levers to the session's own model |
| `app/engines/simulator/simulator_engine.py` | canonical path, with an explicitly labelled scalar fallback |
| `app/services/session_service.py` | builds `CanonicalFinancialInput`; does not compute results |
| `frontend/app/[locale]/financials/page.tsx` | renders canonical fields; derives nothing |
| AI narration | explains figures it is given; is never asked for a number |

The test that keeps this honest is cross-surface consistency: the same input
through two surfaces must produce the same number, and a surface that re-derives
a value from a *summary* of the model rather than the model itself fails,
because a summary drops cost lines.

---

## 12. Verifying any of this

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

391 tests. The ones that matter most for this document:

| File | Pins |
| --- | --- |
| `test_canonical_financial_contract.py` | the engine's own contract |
| `test_financial_consistency.py` | one input, many surfaces, one answer |
| `test_stress_matrix.py` | the matrix, and that the adapter agrees with it |
| `test_financial_truth.py` | What-If levers, tri-state, legacy-field meaning |
| `test_whatif_api_truth.py` | every engine lever is reachable over HTTP |
| `test_capital_sizing.py` | declared costs are not re-invented |
| `test_ranking_truth.py` | unmeasured is not the same as failed |
