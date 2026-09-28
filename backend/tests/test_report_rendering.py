"""
Report rendering regression tests.

The report template previously referenced `location.population_density` and
`projection.monthly_emi`, neither of which existed on the models, so report
generation raised for every session. These tests render the report for the
cases that used to crash.
"""
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP_DIR = tempfile.gettempdir()


def _fresh_db(request):
    # A unique file per test, and released on teardown, because a SQLite file
    # cannot be removed while an engine still holds it open on Windows.
    path = os.path.join(_TMP_DIR, f"yukti_report_{request.node.name}.db")
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.db import Base
    import app.models  # noqa: F401 — register all models
    from app.models import (
        Location, Session as SessionModel, BusinessCategory,
        LoanProduct, FinancialProjection,
    )
    from app.models.core import AdminLevel

    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    loc = Location(
        id="loc_rpt", village="Aurangabadwadi", block="Barshi",
        district="Solapur", state="Maharashtra", lat=17.6, lng=75.9,
        admin_level=AdminLevel.village, data_richness="rich",
    )
    cat = BusinessCategory(id="kirana", name="Kirana Store")
    sess = SessionModel(
        id="sess_rpt", user_id=None, location_id=loc.id,
        margin_capital=100_000.0, category_id=cat.id,
    )
    db.add_all([loc, cat, sess])
    db.commit()

    def _teardown():
        db.close()
        engine.dispose()

    request.addfinalizer(_teardown)
    return db, loc, cat, sess


def _add_loan(db, sess, project_cost, contribution, loan_amount):
    from app.models import LoanProduct
    db.add(LoanProduct(
        id="lp_rpt", session_id=sess.id, project_cost=project_cost,
        loan_amount=loan_amount, beneficiary_contribution=contribution,
        matched_scheme_id=None,
    ))
    db.commit()


def _add_projection(db, sess, dscr):
    from app.models import FinancialProjection
    db.add(FinancialProjection(
        id="fp_rpt", session_id=sess.id, monthly_revenue=100_000.0,
        monthly_opex=40_000.0, net_profit=30_000.0, break_even_units=0.0,
        dscr=dscr, roi=30.0, monthly_emi=0.0, monthly_interest=0.0,
        financing_gap=0.0, payback_months=24.0,
    ))
    db.commit()


def test_report_renders_for_a_debt_free_business(request):
    """dscr=None previously crashed the DSCR cell's format call."""
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    _add_loan(db, sess, project_cost=100_000.0, contribution=100_000.0, loan_amount=0.0)
    _add_projection(db, sess, dscr=None)

    html = generate_html_report(db, sess.id)

    assert "Session not found" not in html
    assert "N/A (no debt)" in html
    assert "No debt is assumed" in html
    assert ">None<" not in html


def test_report_renders_for_a_leveraged_business(request):
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    _add_loan(db, sess, project_cost=500_000.0, contribution=200_000.0, loan_amount=300_000.0)
    _add_projection(db, sess, dscr=1.85)

    html = generate_html_report(db, sess.id)

    assert "1.85" in html
    assert "N/A (no debt)" not in html


def test_report_never_asserts_an_unsourced_consumer_base(request):
    """
    The old template multiplied a non-existent density column by five. A real
    figure may only appear when it comes with its origin and confidence.
    """
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    _add_loan(db, sess, project_cost=100_000.0, contribution=100_000.0, loan_amount=0.0)
    _add_projection(db, sess, dscr=None)

    html = generate_html_report(db, sess.id)

    assert "Target Consumer Base" in html
    assert "within 5km radius" not in html

    cell = html.split("Target Consumer Base</strong></td>")[1].split("</td>")[0]
    if "no population figure is asserted" in cell:
        return
    # A number is shown, so it must be attributed and qualified.
    assert "confidence" in cell
    assert re.search(r"\d", cell), "a shown figure must not be blank"


def test_report_does_not_use_pune_coordinates_for_an_arbitrary_location(request):
    """_parse_location used to default to Pune, reporting the wrong city."""
    from app.data_layer.retrieval import DataRetrieval

    payload = DataRetrieval().get_demographics("loc_rpt")
    assert payload["value"] is None
    assert "No coordinates available" in payload["note"]


def test_report_does_not_invent_a_government_subsidy(request):
    """The template used to print project_cost * 0.25 as an estimated subsidy."""
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    _add_loan(db, sess, project_cost=1_000_000.0, contribution=250_000.0, loan_amount=750_000.0)
    _add_projection(db, sess, dscr=1.85)

    html = generate_html_report(db, sess.id)

    assert "Government Subsidy" not in html
    assert "Unfunded Gap" in html


def test_report_shows_the_financing_gap_when_the_structure_does_not_close(request):
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    # 1L of own money cannot fund a 5L project with only 1L of debt.
    _add_loan(db, sess, project_cost=500_000.0, contribution=100_000.0, loan_amount=100_000.0)
    _add_projection(db, sess, dscr=1.2)

    html = generate_html_report(db, sess.id)

    assert "does not fully cover the project cost" in html
    assert "300,000" in html


def test_report_renders_without_a_loan_or_projection_row(request):
    """A session that has not been calculated yet must still render."""
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    html = generate_html_report(db, sess.id)

    assert "Session not found" not in html
    assert "Kirana Store" in html


def test_missing_session_is_reported_not_rendered(request):
    from app.reports.report_builder import generate_html_report

    db, loc, cat, sess = _fresh_db(request)
    assert generate_html_report(db, "does_not_exist") == "<p>Session not found.</p>"
