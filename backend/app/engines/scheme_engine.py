"""
Scheme routing. Pure rule-table lookup, no LLM, no improvisation.

What this module is allowed to say, and what it now says explicitly:

* It may only say a business is *potentially* eligible. Eligibility is decided by
  a bank against documents, a caste/income certificate, a project report and the
  scheme's current guidelines - none of which exist here. `matched` is retained
  for API compatibility but is documented as "routed to this scheme", not
  "approved".
* Every quoted rule carries its identity: rule id, version, effective date and
  verification state. The bands below are prototype constants transcribed by the
  authors, and nothing in this repository re-verifies them against a dated
  circular, so `VERIFICATION` is UNVERIFIED for all of them and
  `requires_confirmation` names the fields a user must confirm with the agency
  before relying on the number. Presenting an undated rate to a borrower as if it
  were a current offer is the same class of error as inventing one.
* `PMEGP` is listed for transparency but is not routed to, because this build
  has no rule for it. A scheme in a table that no code path can select is a
  promise the product cannot keep, so it is reported as not evaluated rather than
  left as a silent omission. The old `PMEGP_FINANCING_PCT = 0.25` "margin money
  subsidy" constant was referenced by nothing; it advertised a 25% subsidy that
  no calculation applied, and has been removed rather than left as a trap.
"""
from dataclasses import dataclass, field
from typing import Optional

MICRO_FINANCE_CEILING = 140_000
TERM_LOAN_CEILING = 5_000_000
MICRO_FINANCE_MAX_LOAN = 125_000
TERM_LOAN_MAX_LOAN = 4_500_000

#: The disclaimer attached to every match, without exception.
DISCLAIMER = (
    "This is a routing suggestion, not an eligibility decision. No document in this "
    "product has been checked against a bank or the State Channelizing Agency. "
    "Confirm the current terms with the agency before acting on any figure here."
)

#: Recorded once, honestly: these constants were never re-verified against a dated
#: circular in this repository.
RULE_VERIFICATION = {
    "status": "UNVERIFIED",
    "reviewed_on": None,
    "note": (
        "Prototype constants. No dated circular is stored in this repository, so no "
        "field below can be presented as a current official term."
    ),
}


SCHEMES = {
    "Micro Credit Finance": {
        "rule_id": "NSFDC-MCF",
        "rule_version": "prototype-2024-01",
        "effective_from": None,
        "rate": 6.5,
        "rate_verified": False,
        "tenure_years": 3,
        "tenure_verified": False,
        "moratorium_months": 3,
        "max_loan": MICRO_FINANCE_MAX_LOAN,
        "min_loan": None,
        "min_loan_verified": False,
        "source_url": "https://nsfdc.nic.in",
        "implemented": True,
    },
    "Term Loan": {
        "rule_id": "NSFDC-TL",
        "rule_version": "prototype-2024-01",
        "effective_from": None,
        "rate": 8.0,
        "rate_verified": False,
        "tenure_years": 7,
        "tenure_verified": False,
        "moratorium_months": 6,
        "max_loan": TERM_LOAN_MAX_LOAN,
        "min_loan": None,
        "min_loan_verified": False,
        "source_url": "https://nsfdc.nic.in",
        "implemented": True,
    },
    "PMEGP": {
        "rule_id": "PMEGP",
        "rule_version": "not-implemented",
        "effective_from": None,
        "rate": None,
        "rate_verified": False,
        "tenure_years": 7,
        "tenure_verified": False,
        "moratorium_months": 6,
        "max_loan": 1_250_000,
        "min_loan": None,
        "min_loan_verified": False,
        "source_url": "https://kviconline.gov.in/pmegpeportal",
        # No routing rule exists for PMEGP in this build. It is reported as not
        # evaluated instead of being silently unavailable.
        "implemented": False,
    },
}

#: Schemes present in the table but not selectable, with the reason.
NOT_EVALUATED = {
    name: (
        "Listed for transparency. This build has no eligibility or ceiling rule for "
        "this scheme, so it is not evaluated and no subsidy or loan amount is "
        "estimated for it."
    )
    for name, rule in SCHEMES.items()
    if not rule["implemented"]
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

    # Added: what may and may not be concluded from this result.
    potentially_eligible: bool = False
    eligibility_statement: str = ""
    rule_id: Optional[str] = None
    rule_version: Optional[str] = None
    rule_effective_from: Optional[str] = None
    rule_verification: Optional[dict] = None
    criteria_met: list = field(default_factory=list)
    criteria_unmet: list = field(default_factory=list)
    requires_confirmation: list = field(default_factory=list)
    not_evaluated_schemes: list = field(default_factory=list)
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def match_scheme(
    project_cost: Optional[float],
    own_contribution: Optional[float] = None,
) -> SchemeMatch:
    """
    Route a project to a scheme band and report the debt the scheme could
    support.

    The funded amount is the funding gap (project cost less the promoter's own
    money), capped by the scheme ceiling. It is never a fixed percentage of
    project cost, because no scheme lends a percentage of whatever number the
    application happens to declare. When the promoter's contribution is not
    supplied the gap is unknown and no funded amount is quoted.

    An unknown project cost is not a zero project cost: it routes to no band and
    says so, rather than defaulting into the micro-finance bracket.
    """
    if project_cost is None or project_cost <= 0:
        return SchemeMatch(
            matched=False, scheme_name=None, max_loan=None, rate=None,
            tenure_years=None, moratorium_months=None, rejected_alternative=None,
            explanation=(
                "No project cost is available, so no scheme band could be selected. "
                "Routing depends entirely on project size, and a zero cost would place "
                "this business in the smallest band by default - which is a "
                "conclusion, not a default."
            ),
            source_url=None,
            eligibility_statement=(
                "Cannot be assessed: the project cost is unknown."
            ),
            not_evaluated_schemes=list(NOT_EVALUATED),
        )

    if project_cost <= MICRO_FINANCE_CEILING:
        s = SCHEMES["Micro Credit Finance"]
        return _build_match(
            "Micro Credit Finance", s, project_cost, own_contribution,
            rejected_alternative="Term Loan (project cost below its band)",
            explanation=(
                f"Your project cost of Rs {project_cost:,.0f} is at or below the "
                f"Rs {MICRO_FINANCE_CEILING:,.0f} ceiling, so you're routed to Micro Credit Finance."
            ),
        )
    elif MICRO_FINANCE_CEILING < project_cost <= TERM_LOAN_CEILING:
        s = SCHEMES["Term Loan"]
        return _build_match(
            "Term Loan", s, project_cost, own_contribution,
            rejected_alternative="Micro Credit Finance (project cost exceeds its ceiling)",
            explanation=(
                f"Your project cost of Rs {project_cost:,.0f} falls in the "
                f"Rs {MICRO_FINANCE_CEILING:,.0f}-Rs {TERM_LOAN_CEILING:,.0f} band, "
                f"so you're routed to the Term Loan scheme rather than Micro Credit Finance."
            ),
        )
    else:
        return SchemeMatch(
            matched=False, scheme_name=None, max_loan=None, rate=None,
            tenure_years=None, moratorium_months=None, rejected_alternative=None,
            explanation=(
                f"Your project cost of Rs {project_cost:,.0f} exceeds the "
                f"Rs {TERM_LOAN_CEILING:,.0f} ceiling modelled in this prototype's "
                "financing schemes. This does not necessarily mean the business is "
                "unfinanceable - it means it likely requires a different financing "
                "instrument (larger MSME term-loan products or bank co-financing) "
                "not modelled here. Consider resizing the project or consulting your "
                "nearest bank/State Channelizing Agency about larger-ticket options."
            ),
            source_url=None,
            eligibility_statement=(
                f"No scheme in this build covers a project of Rs {project_cost:,.0f}. "
                f"This is a limit of the rules modelled here, not a refusal by any agency."
            ),
            criteria_unmet=[
                f"Project cost Rs {project_cost:,.0f} is above the highest ceiling "
                f"modelled in this build (Rs {TERM_LOAN_CEILING:,.0f})."
            ],
            not_evaluated_schemes=list(NOT_EVALUATED),
        )


def _build_match(
    name: str,
    scheme: dict,
    project_cost: float,
    own_contribution: Optional[float],
    rejected_alternative: str,
    explanation: str,
) -> SchemeMatch:
    requires_confirmation = [
        "Interest rate and tenure must be confirmed with the agency; the values shown "
        "are prototype constants, not a verified offer.",
        "Your eligibility category, income and documentation have not been assessed.",
    ]
    if scheme.get("effective_from") is None:
        requires_confirmation.append(
            f"No effective date is recorded for rule {scheme['rule_id']} "
            f"v{scheme['rule_version']}, so it is not known whether these terms are "
            f"still in force."
        )

    criteria_met = [
        f"Project cost Rs {project_cost:,.0f} falls within this scheme's modelled band.",
    ]
    if own_contribution is not None:
        criteria_met.append(
            f"Your own contribution of Rs {own_contribution:,.0f} is declared."
        )

    if own_contribution is None:
        max_loan = None
        funded_note = (
            "Funded amount not quoted because your own contribution is unknown; "
            "the scheme funds the gap between project cost and your contribution, "
            f"up to Rs {scheme['max_loan']:,.0f}."
        )
        criteria_unmet = [
            "Your own contribution is unknown, so the funding gap - and therefore any "
            "loan amount - cannot be calculated."
        ]
    else:
        funding_gap = max(0.0, project_cost - own_contribution)
        max_loan = min(funding_gap, scheme["max_loan"])
        funded_note = (
            f"Funding gap is Rs {funding_gap:,.0f} "
            f"(project cost Rs {project_cost:,.0f} less your contribution "
            f"Rs {own_contribution:,.0f}); this scheme can fund up to "
            f"Rs {max_loan:,.0f}."
        )
        criteria_unmet = []

    # Criteria this build cannot evaluate at all. They are listed as unmet rather
    # than omitted, because a match with only one criterion tested reads as though
    # the rest had been checked and passed. None of these can be established
    # without the applicant's documents.
    criteria_unmet.extend([
        "Your eligibility category (SC/ST/OBC/Minority/EWS) has not been assessed.",
        "Your income and existing indebtedness have not been assessed.",
        "Supporting documents (identity, address, caste/income certificate where "
        "applicable, project report) have not been reviewed.",
        f"{name}'s unit, turnover and sector restrictions are not encoded in this "
        f"build, so they were neither satisfied nor excluded.",
    ])

    return SchemeMatch(
        matched=True,
        scheme_name=name,
        max_loan=max_loan,
        rate=scheme["rate"],
        tenure_years=scheme["tenure_years"],
        moratorium_months=scheme["moratorium_months"],
        rejected_alternative=rejected_alternative,
        explanation=f"{explanation} {funded_note}",
        source_url=scheme["source_url"],
        potentially_eligible=True,
        eligibility_statement=(
            f"Potentially eligible for {name} on the single criterion this build can "
            f"test - project size. This is not an eligibility decision."
        ),
        rule_id=scheme["rule_id"],
        rule_version=scheme["rule_version"],
        rule_effective_from=scheme["effective_from"],
        rule_verification=RULE_VERIFICATION,
        criteria_met=criteria_met,
        criteria_unmet=criteria_unmet,
        requires_confirmation=requires_confirmation,
        not_evaluated_schemes=list(NOT_EVALUATED),
    )
