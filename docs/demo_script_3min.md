# 3-Minute Demo Script

Three minutes, one narrative: **a decision support tool that refuses to make up
numbers.**

## Before you start

- Backend and frontend running (`start_yukti.bat`).
- Pick a location with coordinates so live providers have something to work
  with. If you have no network, say so out loud and switch to the
  "labelled demo" variant below. Do not pretend a fallback is live.
- Know your three gate outcomes: `GO`, `CONDITIONAL`, `NO_GO`, plus
  `INSUFFICIENT_EVIDENCE` when inputs are missing.

## 0:00 — The one-line thesis

> "Most MSME tools will confidently tell you a kirana store needs ₹4.2 lakh and
> returns in 14 months. Ours shows you the arithmetic, tells you which parts are
> measured and which are assumed, and refuses to answer when it doesn't know."

Say this before touching the screen.

## 0:20 — Dashboard, then the Evidence & Gaps tab

Load the financials page. Revenue, variable cost, EBITDA, break-even, DSCR.

Immediately switch to **Evidence & Gaps**. This is the differentiator, so do it
fast and say what you see:

- Every figure has a source: user-typed, dataset-derived, template default,
  estimate, or model assumption.
- Missing inputs are listed as **missing**, with the reason. They are not
  silently zero.
- The confidence band and its **basis** — why it is not higher.

**Say this:** "Everything on the previous tab is traceable to one of these. The
ones marked as assumptions are the ones I would not defend in a bank meeting."

## 0:50 — The gate refuses to be confident

Point at the verdict chip.

**Say this:** "A `CONDITIONAL` here is not a weaker GO. It means a named
condition is unmet. A `NO_GO` on template defaults is not the same as a `NO_GO`
on my own numbers — the confidence band tells you which."

If the verdict is `INSUFFICIENT_EVIDENCE`, that is a *good* demo moment. Say so:
> "This is the case most tools hide. I have not entered a loan amount, so there
> is no debt service to cover, so there is no DSCR. The tool reports that
> instead of assuming zero debt and reporting a comfortable ratio."

## 1:15 — What-If, all thirteen levers

Move **units sold** down 20%. Revenue falls 20%. Then say the thing that
surprises people:

> "Profit falls more than 20%. Fixed costs don't scale with volume — rent,
> salary, insurance — so the drop in profit is steeper than the drop in
> revenue. That is the actual operating leverage in a small retail business."

Now move **tenure** up. Point out that EMI falls and interest rises.

**Say this:** "Longer tenure is a smaller monthly payment and a larger lifetime
cost. Both numbers are on the same tab, so the trade is visible."

Name that all thirteen levers from the canonical model are exposed over the API,
not a hand-picked subset. `test_whatif_api_truth.py` fails if the engine grows a
lever the HTTP schema does not expose.

## 1:50 — The stress matrix, and the honest stress

Show the seven scenarios, then point at **`combined_severe`**: demand −20%,
price −10%, variable cost +15%, rate +2 points.

**Say this:** "Each scenario moves one lever, so I can attribute the damage.
`combined_severe` moves all of them together, because that is the case that
actually ends a business."

Point at the `survives_stress` column. If a business has no debt, it reads
"not applicable", not "yes, it survived" — a debt-free business cannot fail a
debt service test.

## 2:20 — RAG, and saying "I don't have that"

Ask the assistant a scheme question it can answer, and one it cannot.

- Answered: it cites `[SOURCE n]`. The citation index refers to a source that
  was actually retrieved.
- Unanswered: it says the indexed evidence is insufficient, and
  **`grounded` is `false`**.

**Say this:** "If the language model is unavailable, you get `grounded: false`
and the sources, with the answer field empty. You never get source text dressed
up as an answer. And an answer that cites nothing is reported as unverified."

## 2:45 — Close

> "The product is the evidence trail and the refusals. The projections are
> ordinary arithmetic. What is unusual is that it tells you which parts of the
> arithmetic you should believe."

## If you have no network: the labelled-demo variant

Say this explicitly at the top, not at the end:

> "I have no network here, so every figure is from a bundled fixture. The app
> labels this itself — you'll see a demo banner, and every response carries an
> `X-YuktiFi-Data-Mode: demo` header."

Then make the same point, differently: the interesting property under demo mode
is that **the app knows** it is demo. It does not quietly serve stale cached
data and hope you don't notice.

## Questions to expect, with honest answers

**"Where does the population number come from?"**
The areal estimate: circle area times a national mean density from Census 2011.
It uses no information about your specific location. It is labelled
`INFERRED`, capped at medium confidence, and says
`COARSE AREAL ESTIMATE, NOT A GRID-BASED COUNT`. There is no gridded source
configured in this build.

**"How many competitors are there?"**
Mapped businesses within 5 km from OpenStreetMap — a lower bound only. If the
query fails, the count is `null` and it says the survey could not be run. It
never reports zero for a failed query.

**"What about the Census data?"**
Not implemented. The client is a stub and returns nothing. Population comes from
the areal path. This is documented rather than hidden.

**"Is the DSCR real?"**
Only if you entered a loan. No loan means no DSCR, and the field says
`NOT_APPLICABLE_NO_DEBT`.

**"Can it hallucinate a scheme detail?"**
The RAG prompt restricts answers to retrieved excerpts, and the citation
indices are checked against the retrieval set. An answer with no valid citation
is returned with `grounded: false` and an unverified note. This is grounded
retrieval, not verification against the scheme's own text — a misread excerpt
could still produce a wrong answer. Say that.
