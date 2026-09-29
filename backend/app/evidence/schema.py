"""
Evidence, provenance, abstention and data-coverage primitives.

This module is the contract that keeps "we don't know" from turning into a number.

Three ideas, all enforced by construction here:

1. EVIDENCE STATES. Every externally-derived value carries an explicit state
   (VERIFIED / ESTIMATED / INFERRED / MISSING / STALE / CONFLICTING / UNAVAILABLE).
   There is no state that means "just use zero".

2. PROVENANCE THAT SURVIVES TRANSFORMATION. An `EvidenceRecord` carries source id,
   name, url, dataset, geography, reference date, retrieval date, method,
   confidence, coverage, estimate flag and limitations. `transform()` produces a new
   record that keeps the lineage and adds the derivation that was applied, so a
   number that has been through three stages can still be traced to the document it
   came from.

3. COVERAGE. `compute_coverage` reports what fraction of the required evidence is
   actually usable, and names what is missing. Callers that need a figure must ask
   for it; `require()` raises rather than substituting a default.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Iterable, Optional


# ─── States ──────────────────────────────────────────────────────────────────

class EvidenceState(str, Enum):
    """How much we are entitled to trust a value."""

    VERIFIED = "VERIFIED"            # retrieved from a named official source, current enough to act on
    ESTIMATED = "ESTIMATED"          # computed from a verified input by a documented method
    INFERRED = "INFERRED"            # reasoned from a verified input with an assumption applied
    STALE = "STALE"                  # real, but the reference date is too old to act on confidently
    CONFLICTING = "CONFLICTING"      # two sources disagree; the value is withheld
    MISSING = "MISSING"              # the source should exist and was not obtained
    UNAVAILABLE = "UNAVAILABLE"      # the source does not exist for this geography/case

    @property
    def is_usable(self) -> bool:
        """Can this state support a numerical result shown to a user?"""
        return self in (
            EvidenceState.VERIFIED,
            EvidenceState.ESTIMATED,
            EvidenceState.INFERRED,
            EvidenceState.STALE,
        )

    @property
    def is_live(self) -> bool:
        return self is EvidenceState.VERIFIED

    @property
    def weight(self) -> float:
        """Coverage contribution of an item in this state (0.0 - 1.0)."""
        return {
            EvidenceState.VERIFIED: 1.0,
            EvidenceState.ESTIMATED: 0.7,
            EvidenceState.INFERRED: 0.5,
            EvidenceState.STALE: 0.3,
            EvidenceState.CONFLICTING: 0.2,
            EvidenceState.MISSING: 0.0,
            EvidenceState.UNAVAILABLE: 0.0,
        }[self]


#: Ordered worst-first so a pipeline can short-circuit on the weakest link.
STATE_SEVERITY: tuple[EvidenceState, ...] = (
    EvidenceState.UNAVAILABLE,
    EvidenceState.MISSING,
    EvidenceState.CONFLICTING,
    EvidenceState.STALE,
    EvidenceState.INFERRED,
    EvidenceState.ESTIMATED,
    EvidenceState.VERIFIED,
)


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNAVAILABLE = "UNAVAILABLE"

    @classmethod
    def from_state(cls, state: EvidenceState) -> "Confidence":
        return {
            EvidenceState.VERIFIED: cls.HIGH,
            EvidenceState.ESTIMATED: cls.MEDIUM,
            EvidenceState.INFERRED: cls.MEDIUM,
            EvidenceState.STALE: cls.LOW,
            EvidenceState.CONFLICTING: cls.LOW,
            EvidenceState.MISSING: cls.UNAVAILABLE,
            EvidenceState.UNAVAILABLE: cls.UNAVAILABLE,
        }[state]

    @classmethod
    def from_pct(cls, pct: float) -> "Confidence":
        if pct >= 0.75:
            return cls.HIGH
        if pct >= 0.45:
            return cls.MEDIUM
        if pct > 0.0:
            return cls.LOW
        return cls.UNAVAILABLE


# ─── Records ─────────────────────────────────────────────────────────────────


# ─── Source registry ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Source:
    """A named, citable origin. `method` says how the value was obtained."""

    source_id: str
    name: str
    url: str = ""
    dataset: str = ""
    geography_level: str = ""
    reference_date: str = ""
    method: str = ""
    coverage: str = ""
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Official sources referenced by the product. Every downstream record points at one
# of these by `source_id`, so a number can always be traced to a public document.
SOURCES: dict[str, Source] = {
    "census_pca_2011": Source(
        source_id="census_pca_2011",
        name="Census of India - Primary Census Abstract",
        url="https://censusindia.gov.in/census.website/en/data/population-finder",
        dataset="Census PCA",
        geography_level="village",
        reference_date="2011",
        method="Official census publication",
        coverage="Census-defined administrative units",
        limitations=(
            "Reference year 2011. It is not a current population figure and must not be "
            "presented as one. Village-level figures are suppressed for small populations."
        ),
    ),
    "census_catalog": Source(
        source_id="census_catalog",
        name="Census of India data catalogue (NADA)",
        url="https://www.censusindia.gov.in/nada/index.php/catalog/42559",
        dataset="Census NADA",
        geography_level="administrative",
        reference_date="2011",
        method="Official publication catalogue",
        coverage="National",
        limitations="Metadata catalogue; not a value source on its own.",
    ),
    "livestock_census": Source(
        source_id="livestock_census",
        name="20th Livestock Census - village-wise",
        url="https://kerala.data.gov.in/resource/maharashtra-20th-livestock-census-2019-village-wise",
        dataset="Livestock Census",
        geography_level="village",
        reference_date="2019",
        method="Official livestock census publication",
        coverage="Village-level, subject to suppression",
        limitations="2019 reference year. Dairy herd counts are not current herd sizes.",
    ),
    "osm_overpass": Source(
        source_id="osm_overpass",
        name="OpenStreetMap (Overpass API)",
        url="https://www.openstreetmap.org/",
        dataset="OSM",
        geography_level="point",
        reference_date="live-query",
        method="Radius query on mapped POIs",
        coverage="Volunteer-mapped businesses only",
        limitations=(
            "OSM coverage of Indian informal and micro businesses is very incomplete. "
            "A zero result means zero MAPPED features, not zero competitors. "
            "Unmapped or unregistered businesses are invisible to this source."
        ),
    ),
    "overture_places": Source(
        source_id="overture_places",
        name="Overture Maps Foundation - Places Theme",
        url="https://overturemaps.org/download/",
        dataset="Overture Places",
        geography_level="point",
        reference_date="2024-2026",
        method="Global open-data spatial point extraction with category filtering",
        coverage="Curated open business places and points of interest",
        limitations=(
            "Overture captures registered and mapped commercial POIs. Rural informal micro-units, "
            "mobile tea carts, and unlisted home shops are frequently omitted."
        ),
    ),
    "worldpop_grid": Source(
        source_id="worldpop_grid",
        name="WorldPop Open Spatial Demographics",
        url="https://www.worldpop.org/",
        dataset="WorldPop High-Resolution Population Grids (100m/1km)",
        geography_level="gridded_catchment",
        reference_date="2020-2026",
        method="High-resolution spatial demographic modeling and areal disaggregation",
        coverage="Global 100m/1km gridded population layers",
        limitations=(
            "Modeled spatial estimates based on satellite imagery, settlement footprints, and census disaggregation. "
            "These are statistical models, not direct headcounts."
        ),
    ),
    "agmarknet": Source(
        source_id="agmarknet",
        name="AGMARKNET / eNAM (Ministry of Agriculture)",
        url="https://www.enam.gov.in/web/dashboard/agmarknet",
        dataset="AGMARKNET Daily Mandi Prices",
        geography_level="state/district/market",
        reference_date="daily",
        method="Official modal price reporting from agricultural mandis",
        coverage="Reporting mandis only; wholesale agricultural arrivals, not retail",
        limitations=(
            "Wholesale mandi modal prices from nearest reporting APMC market, not guaranteed local "
            "procurement cost. Transport, trader margins, and quality differences apply."
        ),
    ),
    "consumer_affairs": Source(
        source_id="consumer_affairs",
        name="Department of Consumer Affairs - Price Monitoring Division",
        url="https://fcainfoweb.nic.in/Default.aspx",
        dataset="Price Monitoring System (PMS) Daily Retail Prices",
        geography_level="market_centre",
        reference_date="daily",
        method="Official daily retail and wholesale price monitoring across reporting centres",
        coverage="22 core essential commodities across 555 market centres",
        limitations=(
            "Monitored retail prices from official reporting centres. Centre-specific and state-average "
            "benchmarks; local village retail prices may vary with logistics and shop format."
        ),
    ),
    "hces_2023_24": Source(
        source_id="hces_2023_24",
        name="MoSPI Household Consumption Expenditure Survey 2023-24 (Report No. 592)",
        url="https://www.mospi.gov.in/sites/default/files/publication_reports/Final_Report_HCES_2023-24L.pdf",
        dataset="HCES 2023-24 State & Sector Consumption Tables",
        geography_level="state/sector",
        reference_date="2023-2024",
        method="Official representative household sample survey (August 2023 - July 2024)",
        coverage="State/UT level by rural and urban sectors",
        limitations=(
            "Survey period August 2023 - July 2024. State-level rural/urban consumption benchmark; "
            "does not measure village-level micro demand directly."
        ),
    ),
    "data_gov_in": Source(
        source_id="data_gov_in",
        name="data.gov.in (Government Open Data Platform)",
        url="https://www.data.gov.in/",
        dataset="OGD",
        geography_level="varies",
        reference_date="varies",
        method="Government open data API",
        coverage="Catalogued datasets only",
        limitations="Coverage and freshness depend on the publishing department.",
    ),
    "udyam": Source(
        source_id="udyam",
        name="Udyam Registration Portal (Ministry of MSME)",
        url="https://udyamregistration.gov.in/",
        dataset="Udyam",
        geography_level="national",
        reference_date="live",
        method="Official portal",
        coverage="National",
        limitations="Registration data; not an economic dataset.",
    ),
    "nsfdc": Source(
        source_id="nsfdc",
        name="National Scheduled Castes Finance & Development Corporation",
        url="https://nsfdc.nic.in/",
        dataset="NSFDC schemes",
        geography_level="national",
        reference_date="see rule_version",
        method="Published scheme terms",
        coverage="NSFDC channelised schemes",
        limitations="Terms change. Final eligibility is determined by the lending institution.",
    ),
    "pmegp": Source(
        source_id="pmegp",
        name="PMEGP portal (KVIC / DPIIT)",
        url="https://www.kviconline.gov.in/pmegpeportal/",
        dataset="PMEGP",
        geography_level="national",
        reference_date="see rule_version",
        method="Published scheme guidelines",
        coverage="National, implemented through KVIC/DIC",
        limitations="Ceilings vary by activity category and sector. Must be verified before use.",
    ),
    "mudra": Source(
        source_id="mudra",
        name="MUDRA / PMMY (Ministry of Finance)",
        url="https://www.mudra.org.in/",
        dataset="MUDRA",
        geography_level="national",
        reference_date="see rule_version",
        method="Published lending product terms",
        coverage="Through lending institutions and MUDRA lenders",
        limitations="Loan-product ceilings and conditions are set by lenders within RBI guidance.",
    ),
    "lgd_location_master": Source(
        source_id="lgd_location_master",
        name="Local Government Directory (LGD) / Census administrative master",
        url="https://lgdirectory.gov.in/",
        dataset="LGD",
        geography_level="village",
        reference_date="varies",
        method="Deterministic fuzzy match against the bundled location master",
        coverage="Bundled master only; not nationwide unless the master is loaded",
        limitations=(
            "The bundled sample master is partial. A location that does not match is "
            "reported as unresolved rather than snapped to a nearby district."
        ),
    ),
    "curated_district_dataset": Source(
        source_id="curated_district_dataset",
        name="YUKTIFI curated Solapur district dataset",
        url="",
        dataset="solapur_combined.json",
        geography_level="district",
        reference_date="2026",
        method="Curated compilation of official and field-collected district data",
        coverage="Solapur district, Maharashtra only",
        limitations=(
            "Curated for one district. It is not a national dataset and must not be "
            "presented as coverage for any other district."
        ),
    ),
    "business_template": Source(
        source_id="business_template",
        name="YUKTIFI business template (model assumption)",
        url="",
        dataset="business_templates.py",
        geography_level="sector",
        reference_date="2026",
        method="Sector cost norms declared as explicit model assumptions",
        coverage="Named sectors only",
        limitations=(
            "A MODEL ASSUMPTION, not an observation. Sector norms vary substantially "
            "by location, size and operator. Edit before relying on it."
        ),
    ),
    "demo_fixture": Source(
        source_id="demo_fixture",
        name="YUKTIFI bundled demo fixture (DEMO DATA - NOT LIVE)",
        url="",
        dataset="demo",
        geography_level="fictional/sample",
        reference_date="2026",
        method="Hand-authored sample for offline demonstration",
        coverage="Demo only",
        limitations="DEMO DATA. Not live, not verified, and must not be used for a real decision.",
    ),
}


def get_source(source_id: str) -> Source:
    src = SOURCES.get(source_id)
    if src is None:
        return Source(
            source_id=source_id,
            name=f"Unregistered source: {source_id}",
            method="unregistered",
            limitations="Source is not in the registry. Its provenance cannot be asserted.",
        )
    return src


# ─── Records ─────────────────────────────────────────────────────────────────

def _iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


@dataclass
class EvidenceRecord:
    """
    A single number, with everything needed to judge it.

    `state` is the authoritative trust level. `confidence` is derived from it and
    cannot be set independently, so a caller cannot label a guessed value HIGH.
    """

    metric: str
    value: Any = None
    unit: str = ""
    source_id: str = ""
    dataset: str = ""
    source_url: str = ""
    geography: str = ""
    geography_level: str = ""
    reference_date: str = ""
    retrieved_at: str = ""
    method: str = ""
    coverage: str = ""
    state: EvidenceState = EvidenceState.UNAVAILABLE
    is_estimate: bool = False
    is_demo: bool = False
    limitations: str = ""
    derivation: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        src = get_source(self.source_id) if self.source_id else None
        if src is not None:
            self.source_url = self.source_url or src.url
            self.dataset = self.dataset or src.dataset
            self.reference_date = self.reference_date or src.reference_date
            self.method = self.method or src.method
            self.coverage = self.coverage or src.coverage
            self.limitations = self.limitations or src.limitations
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        # `is_estimate` is a consequence of the state, not an independent claim.
        if self.state in (EvidenceState.ESTIMATED, EvidenceState.INFERRED):
            self.is_estimate = True
        elif self.state is EvidenceState.VERIFIED:
            self.is_estimate = False
        if self.is_demo:
            self.state = EvidenceState.INFERRED if self.state.is_usable else self.state

    @property
    def confidence(self) -> Confidence:
        return Confidence.from_state(self.state)

    @property
    def usable(self) -> bool:
        return self.state.is_usable and self.value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "state": self.state.value,
            "confidence": self.confidence.value,
            "is_estimate": self.is_estimate,
            "is_demo": self.is_demo,
            "source_id": self.source_id,
            "source_name": get_source(self.source_id).name if self.source_id else "",
            "source_url": self.source_url,
            "dataset": self.dataset,
            "geography": self.geography,
            "geography_level": self.geography_level,
            "reference_date": self.reference_date,
            "retrieved_at": self.retrieved_at,
            "method": self.method,
            "coverage": self.coverage,
            "limitations": self.limitations,
            "derivation": list(self.derivation),
        }

    # ── Transformations ─────────────────────────────────────────────────────
    def transform(
        self,
        *,
        operation: str,
        value: Any = None,
        state: EvidenceState | None = None,
        method: str = "",
        **overrides: Any,
    ) -> "EvidenceRecord":
        """
        Derive a new record while keeping lineage.

        A transformation can only ever *lower* trust, never raise it: a VERIFIED
        input passed through a model becomes ESTIMATED, never stays VERIFIED. This
        is what stops provenance from being laundered through a pipeline.
        """
        new_state = state or (
            self.state if self.state is EvidenceState.VERIFIED else EvidenceState.ESTIMATED
        )
        if new_state is EvidenceState.VERIFIED and operation != "identity":
            new_state = EvidenceState.ESTIMATED
        derivation = [*self.derivation, operation]
        return EvidenceRecord(
            metric=overrides.pop("metric", self.metric),
            value=value if value is not None else self.value,
            unit=overrides.pop("unit", self.unit),
            source_id=overrides.pop("source_id", self.source_id),
            dataset=overrides.pop("dataset", self.dataset),
            source_url=overrides.pop("source_url", self.source_url),
            geography=overrides.pop("geography", self.geography),
            geography_level=overrides.pop("geography_level", self.geography_level),
            reference_date=overrides.pop("reference_date", self.reference_date),
            retrieved_at=overrides.pop("retrieved_at", self.retrieved_at),
            method=method or operation,
            coverage=overrides.pop("coverage", self.coverage),
            state=new_state,
            is_estimate=overrides.pop("is_estimate", self.is_estimate),
            is_demo=overrides.pop("is_demo", self.is_demo),
            limitations=overrides.pop("limitations", self.limitations),
            derivation=derivation,
        )


# ─── Constructors ────────────────────────────────────────────────────────────

def verified(metric: str, value: Any, source_id: str, **kw: Any) -> EvidenceRecord:
    return EvidenceRecord(metric=metric, value=value, source_id=source_id, state=EvidenceState.VERIFIED, **kw)


def estimated(metric: str, value: Any, source_id: str, method: str, **kw: Any) -> EvidenceRecord:
    return EvidenceRecord(metric=metric, value=value, source_id=source_id,
                          state=EvidenceState.ESTIMATED, method=method, **kw)


def inferred(metric: str, value: Any, source_id: str, method: str, **kw: Any) -> EvidenceRecord:
    return EvidenceRecord(metric=metric, value=value, source_id=source_id,
                          state=EvidenceState.INFERRED, method=method, **kw)


def missing(metric: str, why: str, **kw: Any) -> EvidenceRecord:
    return EvidenceRecord(metric=metric, value=None, state=EvidenceState.MISSING,
                          method=why, limitations=why, **kw)


def unavailable(metric: str, why: str, **kw: Any) -> EvidenceRecord:
    return EvidenceRecord(metric=metric, value=None, state=EvidenceState.UNAVAILABLE,
                          method=why, limitations=why, **kw)


def stale(record: EvidenceRecord, why: str) -> EvidenceRecord:
    return record.transform(operation=f"stale_check: {why}", state=EvidenceState.STALE,
                            limitations=why)


def conflicting(metric: str, values: dict[str, Any], source_ids: dict[str, str], **kw: Any) -> EvidenceRecord:
    detail = "; ".join(f"{k}={v}" for k, v in values.items())
    return EvidenceRecord(
        metric=metric, value=None, source_id=next(iter(source_ids.values()), ""),
        state=EvidenceState.CONFLICTING,
        method=f"Sources disagree: {detail}",
        limitations=(
            f"Conflicting values for {metric}: {detail}. The value is withheld rather "
            f"than averaged, because averaging two unverifiable figures produces a third "
            f"unverifiable figure."
        ),
        **kw,
    )


def validated(
    metric: str,
    value: Any,
    source_id: str,
    *,
    unit: str = "",
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_min: float | None = None,
    integer: bool = False,
    state: EvidenceState = EvidenceState.VERIFIED,
    **kw: Any,
) -> EvidenceRecord:
    """
    The single numeric gate. Every number from any source passes through here.

    A value that is not a finite number within its declared physical bounds is
    refused and reported as `CONFLICTING` with the reason, rather than being
    coerced. Coercion is how NaN reaches a report and how a negative price turns
    into a windfall.

    Bounds are expected to be supplied from the source's own metadata (a rate
    cannot be negative; a headcount cannot be fractional; a share is 0..1). Where
    no bound is known, `None` is passed deliberately - unbounded is not the same
    as unvalidated.
    """
    f = finite(value)
    if f is None:
        return EvidenceRecord(
            metric=metric, value=None, source_id=source_id, state=EvidenceState.CONFLICTING,
            method="numeric validation",
            limitations=(
                f"Rejected value for {metric}: {value!r} is not a finite number. "
                f"It is not treated as zero."
            ),
            unit=unit, **kw,
        )

    problems: list[str] = []
    if exclusive_min is not None and f <= exclusive_min:
        problems.append(f"must be > {exclusive_min}, got {f}")
    if minimum is not None and f < minimum:
        problems.append(f"must be >= {minimum}, got {f}")
    if maximum is not None and f > maximum:
        problems.append(f"must be <= {maximum}, got {f}")
    if integer and not float(f).is_integer():
        problems.append(f"must be a whole number, got {f}")

    if problems:
        return EvidenceRecord(
            metric=metric, value=None, source_id=source_id, state=EvidenceState.CONFLICTING,
            method="numeric validation",
            limitations=f"Rejected value for {metric}: " + "; ".join(problems) + ". It is not clamped.",
            unit=unit, **kw,
        )

    out: Any = int(f) if integer else f
    return EvidenceRecord(metric=metric, value=out, source_id=source_id, state=state, unit=unit, **kw)


# ─── Requirement + coverage ──────────────────────────────────────────────────

@dataclass
class Requirement:
    """One thing the decision needs in order to be trustworthy."""

    key: str
    label: str
    required: bool = True
    weight: float = 1.0


DEFAULT_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("local_population", "Current local demand / population", True, 1.5),
    Requirement("competitor_evidence", "Verified local competitor count", True, 1.5),
    Requirement("commodity_price", "Current commodity price", True, 1.0),
    Requirement("cost_profile", "Business cost profile", True, 1.5),
    Requirement("location_resolution", "Resolved location hierarchy", True, 1.0),
    Requirement("scheme_terms", "Current scheme terms", False, 0.5),
    Requirement("historical_trend", "Demand trend / seasonality", False, 0.5),
)


@dataclass
class CoverageReport:
    coverage_pct: float
    confidence: Confidence
    satisfied: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)
    records: dict[str, dict[str, Any]] = field(default_factory=dict)
    required_missing: list[str] = field(default_factory=list)

    @property
    def sufficient(self) -> bool:
        """Coverage alone is not enough - a required input must also be absent."""
        return not self.required_missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_coverage_pct": round(self.coverage_pct * 100, 1),
            "confidence": self.confidence.value,
            "sufficient": self.sufficient,
            "satisfied": self.satisfied,
            "degraded": self.degraded,
            "missing_evidence": self.missing_evidence,
            "required_missing": self.required_missing,
            "records": self.records,
        }


def compute_coverage(
    records: Iterable[EvidenceRecord],
    requirements: tuple[Requirement, ...] = DEFAULT_REQUIREMENTS,
) -> CoverageReport:
    """
    Weighted fraction of the required evidence that is actually usable.

    A record in STALE or CONFLICTING state counts partially and is listed under
    `degraded` rather than `satisfied`, so a user can see the difference between
    "we looked and found nothing" and "we found something too old to use".
    """
    by_key = {r.metric: r for r in records}
    total_w = sum(r.weight for r in requirements) or 1.0
    earned = 0.0
    satisfied: list[str] = []
    degraded: list[str] = []
    missing_evidence: list[str] = []
    required_missing: list[str] = []
    out: dict[str, dict[str, Any]] = {}

    for req in requirements:
        rec = by_key.get(req.key)
        if rec is None or not rec.usable:
            missing_evidence.append(req.label)
            if req.required:
                required_missing.append(req.label)
            if rec is not None:
                out[req.key] = rec.to_dict()
            continue
        earned += req.weight * rec.state.weight
        if rec.state in (EvidenceState.STALE, EvidenceState.CONFLICTING):
            degraded.append(req.label)
        else:
            satisfied.append(req.label)
        out[req.key] = rec.to_dict()

    pct = earned / total_w
    return CoverageReport(
        coverage_pct=pct,
        confidence=Confidence.from_pct(pct),
        satisfied=satisfied,
        missing_evidence=missing_evidence,
        degraded=degraded,
        records=out,
        required_missing=required_missing,
    )


# ─── Safe access ─────────────────────────────────────────────────────────────

class MissingEvidenceError(ValueError):
    """Raised when a caller needs a value that was never obtained."""


def require(record: EvidenceRecord, *, context: str = "") -> Any:
    """
    Return the value or refuse.

    This is the function that makes "missing data becomes zero" impossible for
    anything routed through the evidence layer. Callers that genuinely want a
    default must pass one explicitly and label the result.
    """
    if record.usable:
        return record.value
    where = f" for {context}" if context else ""
    raise MissingEvidenceError(
        f"No usable value{where} for '{record.metric}': state={record.state.value}. "
        f"{record.limitations or 'The source did not return this metric.'}"
    )


def value_or_none(record: Optional[EvidenceRecord]) -> Any:
    return record.value if (record is not None and record.usable) else None


def finite(value: Any) -> Optional[float]:
    """Coerce to a finite float, or None. Rejects NaN and infinity outright."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None
