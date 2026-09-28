"""
Comprehensive Unit & Integration Test Suite for YuktiFi Canonical Financial Architecture.
Tests deterministic math, waterfall consistency, business templates, stress engine, location resolver, and dossier generator.
"""
import unittest
import sys
from pathlib import Path

# Ensure backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.financial.canonical_engine import (
    CanonicalFinancialInput,
    ProductItem,
    OpexBreakdown,
    WorkingCapitalConfig,
    compute_canonical_financials,
    compute_emi
)
from app.templates.business_templates import get_business_template, TEMPLATES
from app.location.resolver import LocationResolver
from app.engines.stress_engine import run_stress_test_suite
from app.engines.feasibility_engine import compute_yukti_score, compute_why_not_analysis
from app.reports.dossier_generator import generate_auditable_dossier
from app.evidence.schema import EvidenceRecord


class TestCanonicalFinancialEngine(unittest.TestCase):

    def test_canonical_financial_waterfall(self):
        """Verify exact financial waterfall calculations."""
        inp = CanonicalFinancialInput(
            business_type="retail_kirana",
            products=[ProductItem(name="Grocery Pack", units_per_month=500, selling_price=500.0, variable_cost_per_unit=300.0)],
            opex=OpexBreakdown(rent=10000.0, salaries=15000.0, electricity=5000.0),
            own_capital=50000.0,
            total_project_cost=500000.0,
            debt_amount=450000.0,
            asset_cost=500000.0,
            useful_life_years=10.0,
            interest_rate_annual_pct=10.0,
            tenure_months=60
        )

        res = compute_canonical_financials(inp)

        # 1. Revenue = 500 * 500 = 250,000
        self.assertEqual(res.monthly_revenue, 250000.0)
        # 2. Variable Cost / COGS = 500 * 300 = 150,000
        self.assertEqual(res.monthly_cogs, 150000.0)
        # 3. Gross Profit = 250,000 - 150,000 = 100,000
        self.assertEqual(res.monthly_gross_profit, 100000.0)
        self.assertEqual(res.gross_margin_pct, 40.0)
        # 4. OPEX = 10,000 + 15,000 + 5,000 = 30,000
        self.assertEqual(res.monthly_opex, 30000.0)
        # 5. EBITDA = 100,000 - 30,000 = 70,000
        self.assertEqual(res.monthly_ebitda, 70000.0)
        # 6. Depreciation = 500,000 / 10 / 12 = 4166.67
        self.assertEqual(res.monthly_depreciation, round(500000.0 / 120.0, 2))
        # 7. EBIT = 70,000 - 4166.67 = 65833.33
        self.assertEqual(res.monthly_ebit, round(70000.0 - (500000.0 / 120.0), 2))
        # 8. Declared debt = 450,000
        self.assertEqual(res.approved_loan_amount, 450000.0)
        # 9. Financing reconciles exactly
        self.assertEqual(res.financing_gap, 0.0)
        self.assertTrue(res.financing_reconciled)
        # 10. EMI check
        expected_emi = compute_emi(450000.0, 10.0, 60)
        self.assertEqual(res.monthly_emi, expected_emi)
        # 11. DSCR check
        self.assertGreater(res.dscr, 1.0)

    def test_business_templates_catchment(self):
        """Verify sector business templates and catchment parameters."""
        kirana = get_business_template("retail_kirana")
        self.assertEqual(kirana.catchment_radius_min_km, 1.0)
        self.assertEqual(kirana.catchment_radius_max_km, 3.0)

        agri = get_business_template("agri_machinery")
        self.assertEqual(agri.catchment_radius_min_km, 10.0)
        self.assertEqual(agri.catchment_radius_max_km, 30.0)

    def test_location_resolver_insufficient_evidence(self):
        """Verify unresolved locations explicitly return INSUFFICIENT_LOCATION_EVIDENCE."""
        resolver = LocationResolver([])
        result = resolver.resolve(query="Invalid Nonexistent Place 12345")
        self.assertEqual(result["status"], "INSUFFICIENT_LOCATION_EVIDENCE")

    def test_stress_test_suite(self):
        """Verify deterministic stress testing scenarios update DSCR and cashflow."""
        inp = CanonicalFinancialInput(
            business_type="retail_kirana",
            products=[ProductItem(name="Item A", units_per_month=200, selling_price=100.0, variable_cost_per_unit=50.0)],
            opex=OpexBreakdown(rent=2000.0),
            own_capital=20000.0,
            asset_cost=100000.0
        )
        stress_output = run_stress_test_suite(inp)
        self.assertIn("demand_minus_20", stress_output["scenarios"])
        res_base = stress_output["scenarios"]["base_case"]["result"]
        res_stressed = stress_output["scenarios"]["demand_minus_20"]["result"]
        self.assertLess(res_stressed["monthly_revenue"], res_base["monthly_revenue"])

    def test_feasibility_and_why_not(self):
        """Verify YUKTI Score and Why Not comparison engine."""
        inp = CanonicalFinancialInput(
            business_type="retail_kirana",
            products=[ProductItem(name="Item A", units_per_month=200, selling_price=100.0, variable_cost_per_unit=50.0)],
            opex=OpexBreakdown(rent=2000.0),
            own_capital=20000.0,
            asset_cost=100000.0
        )
        res = compute_canonical_financials(inp)
        yukti = compute_yukti_score(res, mapped_competitors_count=2)
        self.assertTrue(0 <= yukti["yukti_score"] <= 100)
        self.assertIn("overall_confidence", yukti)

        why_not = compute_why_not_analysis(20000.0, "retail_kirana", list(TEMPLATES.keys()))
        self.assertGreater(len(why_not), 0)

    def test_auditable_dossier_generation(self):
        """Verify 24-section dossier generation."""
        inp = CanonicalFinancialInput(
            business_type="retail_kirana",
            products=[ProductItem(name="Item A", units_per_month=200, selling_price=100.0, variable_cost_per_unit=50.0)],
            opex=OpexBreakdown(rent=2000.0),
            own_capital=20000.0,
            asset_cost=100000.0
        )
        res = compute_canonical_financials(inp)
        stress = run_stress_test_suite(inp)
        feas = compute_yukti_score(res, mapped_competitors_count=2)
        why_not = compute_why_not_analysis(20000.0, "retail_kirana", ["dairy", "agri_machinery"])

        dossier = generate_auditable_dossier(
            profile={"own_capital": 20000.0},
            location={"district": "Solapur"},
            business_template={"name": "Retail Kirana"},
            financial_result=res.to_dict(),
            stress_result=stress,
            feasibility_result=feas,
            why_not_result=why_not,
            schemes=[]
        )

        self.assertIn("sections", dossier)
        self.assertIn("24_legal_disclaimer_attribution", dossier["sections"])


if __name__ == "__main__":
    unittest.main()
