"""
Integration test suite for National Location Support & External Legal Sources Manifest.
Verifies that POST /api/analysis/generate supports any location in India without static Solapur blocking,
and populates official external legal source attributions across provenance records.
"""
import unittest
import sys
import asyncio
from pathlib import Path

# Ensure backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.routes_analysis import generate_analysis, AnalysisRequest
from app.data_layer.retrieval import DataRetrieval

class TestNationalLocationSupport(unittest.TestCase):

    def test_data_retrieval_national_locations(self):
        """Verify DataRetrieval returns valid category data for non-Solapur locations."""
        retrieval = DataRetrieval()
        
        # Test Pune location
        pune_data = retrieval.get_category_data("pune_district", "kirana")
        self.assertIn("unit_economics", pune_data)
        self.assertIn("initial_setup_costs", pune_data)

        # Test Jaipur location
        jaipur_data = retrieval.get_category_data("jaipur_district", "dairy")
        self.assertIn("unit_economics", jaipur_data)

    def test_analysis_endpoint_national_resolution(self):
        """Verify generate_analysis succeeds for Jaipur, Rajasthan with external legal provenance."""
        req = AnalysisRequest(
            profile={"name": "Rajesh Kumar", "experience": "Beginner"},
            location={"district": "Jaipur", "state": "Rajasthan"},
            capital={"investment_amount": 50000},
            business={"area_of_interest": "Retail & Shop", "suggested_idea": "Kirana Store"}
        )

        res = asyncio.run(generate_analysis(req))

        self.assertEqual(res["status"], "success")
        self.assertTrue(res["data_available"])
        self.assertEqual(res["location"]["data_scope"], "national_live_resolution")
        self.assertEqual(res["location"]["district"], "Jaipur")
        self.assertIn("financials", res)
        self.assertIn("provenance", res)

        # Verify external legal source attributions exist
        prov_sources = [p.get("source") for p in res["provenance"]]
        self.assertTrue(any("Census" in s or "OpenStreetMap" in s or "YuktiFi" in s for s in prov_sources if s))


if __name__ == "__main__":
    unittest.main()
