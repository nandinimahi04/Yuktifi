from __future__ import annotations

def stress_test(base: dict) -> dict:
    scenarios = [
        ("base",1.00,1.00,1.00),
        ("revenue_-10pct",0.90,1.00,1.00),
        ("revenue_-20pct",0.80,1.00,1.00),
        ("variable_cost_+10pct",1.00,1.10,1.00),
        ("interest_+2pct",1.00,1.00,base["annual_rate_pct"]+2),
        ("combined",0.80,1.10,base["annual_rate_pct"]+2),
    ]
    rows=[]
    from .finance import calculate
    for name, rf, cf, rate in scenarios:
        m=calculate(promoter_margin=base["promoter_margin"], monthly_units=base["monthly_units"],
                    price_per_unit=base["price_per_unit"]*rf, variable_cost_per_unit=base["variable_cost_per_unit"]*cf,
                    fixed_cost_monthly=base["fixed_cost_monthly"], annual_rate_pct=rate,
                    tenure_months=base["tenure_months"], financing_pct=base["financing_pct"])
        rows.append({"scenario":name,"operating_profit":m.operating_profit,"emi":m.monthly_emi,"dscr":m.dscr,
                     "repayment_ok": (m.dscr is not None and m.dscr >= 1.25)})
    measured=[r["dscr"] for r in rows if r["dscr"] is not None]
    min_dscr=min(measured) if measured else None
    score=max(0,min(100,round(min_dscr/1.25*100,1))) if min_dscr is not None else None
    return {"benchmark_dscr":1.25,"scenarios":rows,"worst_case_dscr":min_dscr,"stress_score":score}
