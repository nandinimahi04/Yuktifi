"""
The financial engine never ran for any user-selected business.

`/api/analysis/generate` returned HTTP 200 with `financials: null` for every
option in the onboarding dropdown. The engines were never at fault.

`CATEGORY_MAP` translated the ten dropdown labels into category IDs drawn from
the *business template* registry - `dairy`, `kirana`, `tailoring`,
`small_hospitality` and so on. The only dataset carrying actual economics,
`data/processed/solapur_combined.json`, keys its categories differently:
`retail_shop`, `manufacturing`, `agri_business`, `services_tech`,
`food_beverage`. The two sets shared five IDs and not one of those was reachable
from the map.

So `get_category_data()` found nothing, fell through to the template branch,
returned `total_setup_cost: None`, and `run_financial_engine` correctly refused
to invent a project cost:

    [FINANCIAL] total_setup_cost missing from dataset
    financial_data_available=False  project_cost=None  emi=None

The result was that "Retail & Shop" was silently modelled with no capital, no
EMI, no DSCR and no ROI, while the UI reported a successful analysis. The
four dropdown options with no map entry at all (Handicrafts & Artisanal,
Logistics & Delivery, Education & Training, Fashion & Apparel) were worse: with
no API key the matcher abstained, the endpoint returned
`INSUFFICIENT_INFORMATION`, and the financial engine was never reached at all.

`ALLOWED_CATEGORIES` had the same defect from the other side. The model was
instructed to return IDs like `dairy` and `tailoring`, and every one of those
answers was then discarded as "not one of the supported categories".

These tests pin the mapping to the dataset rather than to a hand-maintained list,
so the two cannot drift apart again.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai_layer.business_matcher import ALLOWED_CATEGORIES, CATEGORY_MAP
from app.data_layer.retrieval import DataRetrieval
from app.engines.financial_engine import run_financial_engine
from app.main import app
from app.core.paths import PROCESSED_DIR

# The ten options StepBusiness.tsx offers, as the labels appear in the dataset.
DROPDOWN_OPTIONS = [
    "Retail & Shop",
    "Manufacturing",
    "Agri-Business",
    "Services & Tech",
    "Food & Beverage",
    "Handicrafts & Artisanal",
    "Logistics & Delivery",
    "Education & Training",
    "Healthcare & Wellness",
    "Fashion & Apparel",
]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def dataset_categories():
    path = PROCESSED_DIR / "solapur_combined.json"
    if not path.exists():
        pytest.skip("processed district dataset not present")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["categories"]


def test_every_dropdown_option_has_a_category_mapping():
    for option in DROPDOWN_OPTIONS:
        assert option in CATEGORY_MAP, f"{option!r} has no CATEGORY_MAP entry"


def test_every_mapped_category_exists_in_the_economics_dataset(dataset_categories):
    """
    The exact defect: the map pointed at IDs the dataset does not contain, so
    every lookup missed and no cost data was ever returned.
    """
    for option, category_id in CATEGORY_MAP.items():
        assert category_id in dataset_categories, (
            f"{option!r} maps to {category_id!r}, which is absent from the "
            f"economics dataset. Available: {sorted(dataset_categories)}"
        )


def test_every_mapped_category_carries_a_setup_cost(dataset_categories):
    """A present-but-empty category is the same failure as a missing one."""
    for option, category_id in CATEGORY_MAP.items():
        setup = dataset_categories[category_id].get("initial_setup_costs", {})
        assert setup.get("total_setup_cost"), (
            f"{category_id!r} has no total_setup_cost, so the financial engine "
            f"cannot produce a project cost for {option!r}"
        )


def test_allowed_categories_cover_the_dataset(dataset_categories):
    """
    The allowlist is used to validate the model's answer, so a stale entry would
    reject a correct match and a missing one would reject a supported business.
    """
    missing = set(dataset_categories) - set(ALLOWED_CATEGORIES)
    assert not missing, f"dataset categories absent from ALLOWED_CATEGORIES: {sorted(missing)}"


def test_allowed_categories_are_all_resolvable(dataset_categories):
    """
    Every id the model is invited to return must be one the product can actually
    cost. An id with no template and no dataset would reintroduce the null-financials
    failure through the model path instead of the deterministic one.
    """
    for category_id in ALLOWED_CATEGORIES:
        assert DataRetrieval().get_category_data("solapur", category_id), (
            f"{category_id!r} is offered to the model but yields no category data"
        )


@pytest.mark.parametrize("option", DROPDOWN_OPTIONS)
def test_each_dropdown_option_produces_financials(option, dataset_categories):
    """The regression itself: every option must yield a costed financial result."""
    category_id = CATEGORY_MAP[option]
    data = DataRetrieval().get_category_data("solapur", category_id)
    result = run_financial_engine(
        user_capital=150000,
        setup_costs=data.get("initial_setup_costs", {}),
        pricing_margins=data.get("pricing_margins", {}),
        monthly_costs=data.get("monthly_running_costs", {}),
        unit_economics=data.get("unit_economics", {}),
        category_id=category_id,
    )
    assert result.get("financial_data_available") is True, (
        f"{option!r} produced no financial data: {result}"
    )
    assert result.get("project_cost"), f"{option!r} has no project cost"
    assert result.get("emi") is not None, f"{option!r} has no EMI"


def test_the_endpoint_returns_financials_for_a_user_selected_business(client):
    """
    A full request in the shape the onboarding page sends. Previously 200 with
    `financials: null` and `data_available: false`.
    """
    r = client.post(
        "/api/analysis/generate",
        json={
            "profile": {"name": "Test", "age": 28, "gender": "male",
                        "social_category": "general"},
            "location": {"district": "Solapur", "state": "Maharashtra"},
            "capital": {"investment_amount": 150000},
            "business": {"area_of_interest": "Retail & Shop",
                         "suggested_idea": "", "prior_experience": "Beginner"},
            "language": "English",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") != "INSUFFICIENT_INFORMATION"
    assert body.get("data_available") is True
    financials = body.get("financials")
    assert financials, "endpoint returned a successful analysis with no financials"
    assert financials["project_cost"]
    assert financials["emi"] is not None


@pytest.mark.parametrize("option", DROPDOWN_OPTIONS)
def test_the_endpoint_never_returns_null_financials_for_an_option(client, option):
    """
    Every label in the dropdown is a path a real user can take, so every one of
    them has to survive the round trip. The four previously unmapped options are
    the important cases: they abstained without an API key.
    """
    r = client.post(
        "/api/analysis/generate",
        json={
            "profile": {"name": "Test", "age": 28, "gender": "male",
                        "social_category": "general"},
            "location": {"district": "Solapur", "state": "Maharashtra"},
            "capital": {"investment_amount": 150000},
            "business": {"area_of_interest": option,
                         "suggested_idea": "", "prior_experience": "Beginner"},
            "language": "English",
        },
    )
    body = r.json()
    assert body.get("data_available") is True, f"{option!r} -> {body.get('status')}"
    assert body.get("financials"), f"{option!r} returned no financials"
