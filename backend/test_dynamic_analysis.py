from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("Running YuktiFi Dynamic Analysis Tests...")
    
    # Test 1: Unsupported Location (Pune)
    payload_pune = {
        "profile": {"name": "Test User"},
        "location": {"state": "Maharashtra", "district": "Pune"},
        "capital": {"investment_amount": 50000},
        "business": {"area_of_interest": "dairy"}
    }
    r = client.post("/api/analysis/generate", json=payload_pune)
    data = r.json()
    assert data["data_available"] == False, "Pune should not be available"
    print("Test 1 (Unsupported Location): PASS")

    # Test 2: Supported Location (Solapur)
    payload_solapur = {
        "profile": {"name": "Test User"},
        "location": {"state": "Maharashtra", "district": "Solapur"},
        "capital": {"investment_amount": 50000},
        "business": {"area_of_interest": "dairy"}
    }
    r = client.post("/api/analysis/generate", json=payload_solapur)
    data = r.json()
    assert data["data_available"] == True, "Solapur should be available"
    print("Test 2 (Supported Location): PASS")
    
    # Test 3: Location API
    r = client.get("/api/locations/states")
    states = r.json()
    assert len(states) > 0, "States API should return data"
    
    r = client.get("/api/locations/districts?state_id=MH")
    districts = r.json()
    assert len(districts) > 0, "Districts API should return data"
    print("Test 3 (Locations API): PASS")

    print("All tests passed.")

if __name__ == "__main__":
    run_tests()
