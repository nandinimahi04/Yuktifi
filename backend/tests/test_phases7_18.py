from app.advisory.national import run_advisory

def test_full_advisory_pipeline():
    r=run_advisory(
      business_id="dairy",
      location={"canonical_label":"Chincholi Najik, Akkalkot, Solapur, Maharashtra","population":2400,"households":520},
      promoter_margin=100000, monthly_units=727, price_per_unit=55, variable_cost_per_unit=20,
      fixed_cost_monthly=15000, mapped_competitors=[{"tag":"dairy"},{"tag":"sweet_shop"}],
      profile={"social_category":"OBC"}, spatial_population=2500)
    assert r["financial"]["project_cost"] == 1000000
    assert r["decision"]["decision"] in {"GO","CONDITIONAL","NO-GO"}
    assert r["market"]["estimated_units_monthly"] is not None
    assert r["risk"]["scenarios"]
    assert r["evidence"]
    assert all("source_url" in x for x in r["evidence"])

def test_unknown_scheme_is_not_fabricated():
    r=run_advisory(business_id="kirana", location={"canonical_label":"X"}, promoter_margin=100000,
      monthly_units=500, price_per_unit=100, variable_cost_per_unit=78, fixed_cost_monthly=18000)
    assert all(x["status"] == "UNKNOWN" for x in r["schemes"])
