"""
YuktiFi Printable HTML Report Generator.
Renders the 24-section Auditable Decision Dossier into a clean, professional HTML document with print CSS styling.
"""
from typing import Dict, Any

def _fmt_money(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        return f"&#8377;{float(val):,.2f}"
    except (ValueError, TypeError):
        return str(val)

def _fmt_num(val: Any, suffix: str = "") -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):,.2f}{suffix}"
    except (ValueError, TypeError):
        return f"{val}{suffix}"

def render_dossier_to_html(dossier: Dict[str, Any]) -> str:
    title = dossier.get("title", "YUKTIFI AUDITABLE DECISION DOSSIER")
    sec = dossier.get("sections", {})

    profile = sec.get("1_entrepreneur_profile", {})
    location = sec.get("2_location_resolution", {})
    tmpl = sec.get("3_business_template", {})
    market = sec.get("4_market_evidence", {})
    proj = sec.get("6_project_cost", {})
    rev = sec.get("7_revenue_model", {})
    cost = sec.get("8_cost_waterfall", {})
    profit = sec.get("9_profit_waterfall", {})
    wc = sec.get("10_working_capital", {})
    fin = sec.get("11_financing_structure", {})
    emi = sec.get("12_emi_schedule", {})
    dscr = sec.get("13_dscr_analysis", {})
    be = sec.get("14_break_even_analysis", {})
    roi = sec.get("15_roi_metrics", {})
    pb = sec.get("16_payback_analysis", {})
    schemes = sec.get("17_scheme_router", [])
    stress = sec.get("18_stress_tests", {})
    conf = sec.get("20_confidence_propagation", {})
    why_this = sec.get("22_why_this_business", [])
    why_not = sec.get("23_why_not_alternatives", [])
    disclaimer = sec.get("24_legal_disclaimer_attribution", "")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            color: #1e293b;
            background-color: #f8fafc;
            line-height: 1.5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            color: #1e3a8a;
            font-size: 26px;
        }}
        .header p {{
            margin: 5px 0 0 0;
            color: #64748b;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 25px;
        }}
        .card {{
            background: #f1f5f9;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #2563eb;
        }}
        .card h3 {{
            margin-top: 0;
            font-size: 15px;
            color: #334155;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 5px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            padding: 3px 0;
        }}
        .metric-label {{ color: #475569; }}
        .metric-value {{ font-weight: 600; color: #0f172a; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 13px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #f1f5f9;
            color: #334155;
            font-weight: 600;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-green {{ background: #dcfce7; color: #166534; }}
        .badge-blue {{ background: #dbeafe; color: #1e40af; }}
        .badge-amber {{ background: #fef3c7; color: #92400e; }}
        .disclaimer {{
            margin-top: 40px;
            padding: 15px;
            background: #fffbeb;
            border: 1px solid #fde68a;
            border-radius: 6px;
            font-size: 12px;
            color: #78350f;
        }}
        @media print {{
            body {{ background: #ffffff; padding: 0; }}
            .container {{ box-shadow: none; padding: 0; max-width: 100%; }}
            .no-print {{ display: none; }}
            .card {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Generated by YuktiFi Canonical Decision Engine &bull; Official Feasibility Dossier</p>
        </div>

        <div class="grid">
            <div class="card">
                <h3>1. Enterprise & Entrepreneur Profile</h3>
                <div class="metric"><span class="metric-label">Business Template</span><span class="metric-value">{tmpl.get('name', 'N/A')}</span></div>
                <div class="metric"><span class="metric-label">Sector</span><span class="metric-value">{tmpl.get('sector', 'N/A')}</span></div>
                <div class="metric"><span class="metric-label">Catchment Radius</span><span class="metric-value">{tmpl.get('catchment_radius', 'N/A')}</span></div>
                <div class="metric"><span class="metric-label">Applicant Capital</span><span class="metric-value">{_fmt_money(profile.get('applicant_capital'))}</span></div>
            </div>
            <div class="card">
                <h3>2. Location & Data Confidence</h3>
                <div class="metric"><span class="metric-label">State / District</span><span class="metric-value">{location.get('state', 'N/A')}, {location.get('district', 'N/A')}</span></div>
                <div class="metric"><span class="metric-label">Village / Sub-district</span><span class="metric-value">{location.get('village', 'N/A')}, {location.get('subdistrict', 'N/A')}</span></div>
                <div class="metric"><span class="metric-label">Evidence Coverage</span><span class="metric-value">{_fmt_num(conf.get('evidence_coverage_pct'), '%')}</span></div>
                <div class="metric"><span class="metric-label">Overall Confidence</span><span class="metric-value"><span class="badge badge-green">{conf.get('overall_confidence', 'MEDIUM')}</span></span></div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 25px;">
            <h3>3. Canonical Financial Waterfall (Monthly)</h3>
            <div class="grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 0;">
                <div>
                    <div class="metric"><span class="metric-label">Monthly Revenue</span><span class="metric-value">{_fmt_money(rev.get('monthly_revenue'))}</span></div>
                    <div class="metric"><span class="metric-label">Less: COGS / Variable</span><span class="metric-value">{_fmt_money(cost.get('cogs_monthly'))}</span></div>
                    <div class="metric"><span class="metric-label">Gross Profit</span><span class="metric-value">{_fmt_money(profit.get('gross_profit_monthly'))}</span></div>
                </div>
                <div>
                    <div class="metric"><span class="metric-label">Less: OPEX</span><span class="metric-value">{_fmt_money(cost.get('opex_monthly'))}</span></div>
                    <div class="metric"><span class="metric-label">EBITDA</span><span class="metric-value">{_fmt_money(profit.get('ebitda_monthly'))}</span></div>
                    <div class="metric"><span class="metric-label">Less: Depreciation</span><span class="metric-value">{_fmt_money(cost.get('depreciation_monthly'))}</span></div>
                </div>
                <div>
                    <div class="metric"><span class="metric-label">EBIT</span><span class="metric-value">{_fmt_money(profit.get('ebit_monthly'))}</span></div>
                    <div class="metric"><span class="metric-label">Tax Status</span><span class="metric-value">{profit.get('tax_status', 'NOT_MODELED')}</span></div>
                    <div class="metric"><span class="metric-label">Net Profit (PAT)</span><span class="metric-value">{_fmt_money(profit.get('pat_monthly'))}</span></div>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>4. Financing, EMI & Debt Service</h3>
                <div class="metric"><span class="metric-label">Total Project Cost</span><span class="metric-value">{_fmt_money(proj.get('total_project_cost'))}</span></div>
                <div class="metric"><span class="metric-label">Approved Loan</span><span class="metric-value">{_fmt_money(fin.get('approved_loan_amount'))}</span></div>
                <div class="metric"><span class="metric-label">Monthly EMI</span><span class="metric-value">{_fmt_money(emi.get('monthly_emi'))}</span></div>
                <div class="metric"><span class="metric-label">DSCR</span><span class="metric-value"><span class="badge badge-blue">{_fmt_num(dscr.get('dscr'))}</span></span></div>
            </div>
            <div class="card">
                <h3>5. Break-even, ROI & Payback</h3>
                <div class="metric"><span class="metric-label">BE Monthly Revenue</span><span class="metric-value">{_fmt_money(be.get('break_even_revenue_monthly'))}</span></div>
                <div class="metric"><span class="metric-label">Margin of Safety</span><span class="metric-value">{_fmt_num(be.get('margin_of_safety_pct'), '%')}</span></div>
                <div class="metric"><span class="metric-label">Owner Equity ROI</span><span class="metric-value">{_fmt_num(roi.get('roi_owner_equity_pct'), '%')}</span></div>
                <div class="metric"><span class="metric-label">Payback Period</span><span class="metric-value">{_fmt_num(pb.get('payback_months'), ' Months')}</span></div>
            </div>
        </div>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px;">6. Deterministic Stress Scenarios</h3>
        <table>
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Description</th>
                    <th>DSCR Impact</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""
    for sc_key, sc_val in stress.items():
        if isinstance(sc_val, dict):
            sc_name = sc_val.get('scenario_name', str(sc_key).replace('_', ' ').title())
            sc_desc = sc_val.get('description', '')
            res_item = sc_val.get("result", {})
            dscr_val = res_item.get('dscr') if isinstance(res_item, dict) else res_item
            breached = bool(sc_val.get('dscr_breached', False))
        else:
            sc_name = str(sc_key).replace('_', ' ').title()
            sc_desc = "Stressed operational parameters"
            dscr_val = sc_val
            breached = float(sc_val or 0) < 1.1 if isinstance(sc_val, (int, float)) else False

        html_content += f"""
                <tr>
                    <td><strong>{sc_name}</strong></td>
                    <td>{sc_desc}</td>
                    <td>{_fmt_num(dscr_val)}</td>
                    <td><span class="badge {'badge-green' if not breached else 'badge-amber'}">{'SAFE' if not breached else 'BREACHED'}</span></td>
                </tr>
"""

    html_content += f"""
            </tbody>
        </table>

        <h3 style="color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; margin-top: 30px;">7. Why NOT the Alternatives?</h3>
        <table>
            <thead>
                <tr>
                    <th>Alternative Category</th>
                    <th>Capital Fit</th>
                    <th>Reason for Non-Recommendation</th>
                </tr>
            </thead>
            <tbody>
"""
    for wn in why_not:
        html_content += f"""
                <tr>
                    <td><strong>{str(wn.get('business_category', '')).replace('_', ' ').title()}</strong></td>
                    <td>{wn.get('capital_fit', 'N/A')}</td>
                    <td>{wn.get('why_not_reason', 'N/A')}</td>
                </tr>
"""
    formatted_disclaimer = disclaimer.replace('\n', '<br>')
    html_content += f"""
            </tbody>
        </table>

        <div class="disclaimer">
            <strong>LEGAL NOTICE & DATA ATTRIBUTION:</strong><br>
            {formatted_disclaimer}
        </div>
    </div>
</body>
</html>
"""
    return html_content
