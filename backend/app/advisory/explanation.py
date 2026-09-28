from __future__ import annotations

def build_explanation(result: dict) -> dict:
    d=result["decision"]
    f=result["financial"]
    m=result["market"]
    r=result["risk"]
    bullets=[
      f"Decision: {d['decision']}",
      f"Base monthly revenue is ₹{f['monthly_revenue']:,.0f}; operating profit is ₹{f['operating_profit']:,.0f}.",
      f"Base DSCR is {f['dscr']}; worst modeled stress DSCR is {r['worst_case_dscr']}.",
    ]
    if m["estimated_units_monthly"] is not None: bullets.append(f"Modeled local demand is {m['estimated_units_monthly']:,.0f} {result['business']['sales_unit']}/month; this is an estimate, not observed sales.")
    bullets += d["why"]
    return {"grounded":True,"explanation":bullets,"evidence":result["evidence"],"llm_allowed":"explain_only"}
