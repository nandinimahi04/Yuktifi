"""
Comprehensive End-to-End Practical Workflow Test Suite for YuktiFi.
Verifies complete E2E execution across all 9 micro-enterprise business templates,
location resolution, canonical financial waterfall, stress testing, why-not comparison,
and printable 24-section HTML dossier generation.
"""
import unittest
import sys
from pathlib import Path

# Ensure backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.advisory.national import run_advisory
from app.advisory.report import build_report, build_html_report
from app.advisory.templates.registry import list_templates, TEMPLATES

class TestPracticalE2EWorkflow(unittest.TestCase):

    def test_all_business_templates_exist(self):
        """Verify all 9 production micro-enterprise templates are loaded in registry."""
        templates = list_templates()
        self.assertGreaterEqual(len(templates), 9)

        expected_ids = {"dairy", "kirana", "vada_pav", "tailoring", "diagnostic", "agri_machinery", "food_processing", "repair_services", "small_hospitality"}
        loaded_ids = {t["id"] for t in templates}
        self.assertTrue(expected_ids.issubset(loaded_ids))

    def test_e2e_vada_pav_flow(self):
        """Verify E2E advisory run for Vada Pav / Fast Food stall."""
        payload = {
            "business_id": "vada_pav",
            "location": {"query": "Solapur, Maharashtra", "lat": 17.6599, "lng": 75.9064},
            "promoter_margin": 30000.0,
            "monthly_units": 1500.0,
            "price_per_unit": 20.0,
            "variable_cost_per_unit": 9.0,
            "fixed_cost_monthly": 8000.0,
            "use_demo_assumptions": True
        }
        res = run_advisory(**payload)

        self.assertEqual(res["business"]["id"], "vada_pav")
        self.assertIn("financial", res)
        self.assertIn("decision", res)
        self.assertIn("why_not", res["decision"])
        self.assertGreater(len(res["decision"]["why_not"]), 0)

        # Test 24-section JSON dossier report
        dossier = build_report(res)
        self.assertIn("sections", dossier)
        self.assertIn("24_legal_disclaimer_attribution", dossier["sections"])

        # Test printable HTML dossier
        html = build_html_report(res)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("YUKTIFI AUDITABLE DECISION DOSSIER", html)

    def test_e2e_agri_machinery_flow(self):
        """Verify E2E advisory run for Agri Machinery Equipment Hiring."""
        payload = {
            "business_id": "agri_machinery",
            "location": {"query": "Solapur, Maharashtra"},
            "promoter_margin": 150000.0,
            "use_demo_assumptions": True
        }
        res = run_advisory(**payload)
        self.assertEqual(res["business"]["id"], "agri_machinery")
        self.assertGreater(res["financial"]["project_cost"], 1000000.0)

    def test_e2e_diagnostic_centre_flow(self):
        """Verify E2E advisory run for Diagnostic Clinical Centre."""
        payload = {
            "business_id": "diagnostic",
            "location": {"query": "Solapur, Maharashtra"},
            "promoter_margin": 80000.0,
            "use_demo_assumptions": True
        }
        res = run_advisory(**payload)
        self.assertEqual(res["business"]["id"], "diagnostic")
        self.assertEqual(res["business"]["default_catchment_km"], 10.0)

    def test_e2e_all_nine_templates_run_cleanly(self):
        """Verify that every single one of the 9 templates executes E2E without errors."""
        for template_id in TEMPLATES.keys():
            payload = {
                "business_id": template_id,
                "location": {"query": "Solapur, Maharashtra"},
                "promoter_margin": 50000.0,
                "use_demo_assumptions": True
            }
            res = run_advisory(**payload)
            self.assertEqual(res["business"]["id"], template_id)
            dossier = build_report(res)
            self.assertIn("sections", dossier)


if __name__ == "__main__":
    unittest.main()
