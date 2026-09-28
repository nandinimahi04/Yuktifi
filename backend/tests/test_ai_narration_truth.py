"""
Regressions for the remaining AI narration paths.

Two failures are covered here, both of which produced confident wrong text:

* `/chat` and `/explain` returned whatever Gemini said. The reply is free text, so
  an invented "your DSCR will be 1.8" passed schema validation untouched - the
  numeric guard already used by `llm_client.generate_explanation` was simply not
  applied on the one path users quote to a bank officer.
* `parse_onboarding_text` returned whatever capital the model produced. That
  number is the denominator of every ROI, DSCR and equity figure downstream and
  is presented to a lender as the applicant's own declaration.

`asyncio.run` is used directly because the project has no pytest-asyncio plugin.
"""
import asyncio

import pytest

from app.ai_layer.onboarding_parser import parse_onboarding_text
from app.api import routes_copilot as copilot


class _Model:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    async def generate_json_async(self, prompt, schema=None, **kwargs):
        self.calls += 1
        return self.response


def _install(monkeypatch, response):
    # The client is instantiated at import time, so the instance is what needs
    # replacing, not the class.
    model = _Model(response)
    monkeypatch.setattr(copilot, "gemini", model)
    return model


SCORE = {"overall": 73.2, "dimension_scores": {"market": 66.0}}
FIN = {"monthly_revenue": 108000, "dscr": 1.42}


def test_copilot_chat_passes_a_grounded_reply(monkeypatch):
    _install(monkeypatch, {"reply": "Your overall score of 73.2 reflects steady demand."})
    out = asyncio.run(
        copilot.copilot_chat(
            copilot.ChatRequest(
                message="Why is my score what it is?",
                location_id="solapur",
                category_id="dairy",
                score_data=dict(SCORE),
                financial_data=dict(FIN),
            )
        )
    )
    assert out["blocked"] is False
    assert "73.2" in out["reply"]


def test_copilot_chat_blocks_an_invented_ratio(monkeypatch):
    """
    "Your DSCR will be 1.8" is not in the context, so it must not be returned.

    The real DSCR on file is 1.42. A confident adjacent-sounding number is the
    hardest kind of fabrication to catch by eye.
    """
    _install(monkeypatch, {"reply": "With steady sales your DSCR will be 1.8, so you are safe."})
    out = asyncio.run(
        copilot.copilot_chat(
            copilot.ChatRequest(
                message="Am I safe?",
                location_id="solapur",
                category_id="dairy",
                score_data=dict(SCORE),
                financial_data=dict(FIN),
            )
        )
    )
    assert out["blocked"] is True
    assert "1.8" not in out["reply"]
    assert "1.42" in out["blocked_reason"] or "1.8" in out["blocked_reason"]


def test_copilot_explain_blocks_an_invented_figure(monkeypatch):
    _install(monkeypatch, {"explanation": "You will earn 240,000 per month in year one."})
    out = asyncio.run(
        copilot.copilot_explain(
            copilot.ExplainRequest(
                question="What will I earn?",
                location_id="solapur",
                category_id="dairy",
                financial_data=dict(FIN),
            )
        )
    )
    assert out["blocked"] is True
    assert "240,000" not in out["explanation"]


def test_copilot_explain_passes_grounded_numbers(monkeypatch):
    _install(monkeypatch, {"explanation": "Revenue on record is 108,000 per month."})
    out = asyncio.run(
        copilot.copilot_explain(
            copilot.ExplainRequest(
                question="What is my revenue?",
                location_id="solapur",
                category_id="dairy",
                financial_data=dict(FIN),
            )
        )
    )
    assert out["blocked"] is False
    assert "108,000" in out["explanation"]


def test_copilot_empty_reply_is_reported_not_faked(monkeypatch):
    _install(monkeypatch, {"reply": "   "})
    out = asyncio.run(
        copilot.copilot_chat(
            copilot.ChatRequest(
                message="hi", location_id="solapur", category_id="dairy"
            )
        )
    )
    assert out["reply"]
    assert "unable" in out["reply"].lower()


# ── onboarding parser ──────────────────────────────────────────────────────


def _parse(monkeypatch, response):
    from app.ai_layer import onboarding_parser as op

    model = _Model(response)
    monkeypatch.setattr(op, "gemini", model)
    return asyncio.run(op.parse_onboarding_text("I want to open a dairy with 2 lakh."))


def test_onboarding_keeps_a_capital_the_user_stated(monkeypatch):
    out = _parse(
        monkeypatch,
        {
            "business_category": "dairy",
            "location": "Solapur",
            "capital_in_inr": 200000,
            "experience_level": None,
        },
    )
    assert out["capital_in_inr"] == 200000
    assert out["business_category"] == "dairy"


def test_onboarding_drops_a_capital_the_user_never_stated(monkeypatch):
    """
    The model produced 850000 for a user who wrote "2 lakh".

    850,000 becomes the denominator of every ratio in the product and is shown
    to a bank as a declaration the applicant never made.
    """
    out = _parse(
        monkeypatch,
        {
            "business_category": "dairy",
            "location": "Solapur",
            "capital_in_inr": 850000,
            "experience_level": None,
        },
    )
    assert out["capital_in_inr"] is None
    assert out["business_category"] == "dairy"


def test_onboarding_treats_zero_capital_as_unstated(monkeypatch):
    """0 must never be read as "no money" - it is an unverified claim."""
    out = _parse(
        monkeypatch,
        {
            "business_category": "dairy",
            "location": "Solapur",
            "capital_in_inr": 0,
            "experience_level": None,
        },
    )
    assert out["capital_in_inr"] is None


def test_onboarding_accepts_decimal_lakh_and_50k(monkeypatch):
    from app.ai_layer import onboarding_parser as op

    model = _Model(
        {
            "business_category": "dairy",
            "location": None,
            "capital_in_inr": 150000,
            "experience_level": None,
        }
    )
    monkeypatch.setattr(op, "gemini", model)
    out = asyncio.run(op.parse_onboarding_text("I have 1.5 lakh saved."))
    assert out["capital_in_inr"] == 150000

    model.response = dict(model.response, capital_in_inr=50000)
    out = asyncio.run(op.parse_onboarding_text("budget is 50k"))
    assert out["capital_in_inr"] == 50000


def test_onboarding_ignores_empty_text_without_calling_the_model(monkeypatch):
    from app.ai_layer import onboarding_parser as op

    model = _Model({"capital_in_inr": 999999})
    monkeypatch.setattr(op, "gemini", model)
    out = asyncio.run(op.parse_onboarding_text("   "))
    assert out["capital_in_inr"] is None
    assert model.calls == 0
