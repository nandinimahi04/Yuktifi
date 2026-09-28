import requests
import json
import time

BASE_URL = "http://localhost:8000"

def run_test():
    print("Starting E2E Verification Test...\n")
    
    # 1. Profile Creation
    print("1. Creating Profile...")
    res = requests.post(f"{BASE_URL}/profile", json={
        "name": "Test User",
        "location_input": "Solapur",
        "language": "en"
    })
    res.raise_for_status()
    profile = res.json()
    session_id = profile["user_id"]
    location_id = profile["location_id"]
    print(f"Profile created: Session ID: {session_id}, Location: {location_id}\n")
    
    # 2. Ranking Opportunities
    print("2. Ranking Opportunities...")
    res = requests.post(f"{BASE_URL}/rank-opportunities", json={
        "session_id": session_id,
        "location_id": location_id,
        "margin_capital": 50000
    })
    res.raise_for_status()
    rankings = res.json()["rankings"]
    top_cat = rankings[0]["category_id"]
    print(f"Found {len(rankings)} opportunities. Top category: {top_cat}\n")
    
    # 3. Market Intelligence
    print(f"3. Fetching Market Intelligence for {top_cat}...")
    res = requests.post(f"{BASE_URL}/analyze-market", json={
        "session_id": session_id,
        "location_id": location_id,
        "category_id": top_cat
    })
    res.raise_for_status()
    market = res.json()
    print(f"Market data loaded. Competitors: {market['competitors']['value']['count']}\n")
    
    # 4. Recommendation / Score
    print(f"4. Generating Score/Recommendation for {top_cat}...")
    res = requests.post(f"{BASE_URL}/recommend", json={
        "session_id": session_id
    })
    res.raise_for_status()
    recommendation = res.json()
    print(f"Score generated. Verdict: {recommendation['verdict']}, Yukti Score: {recommendation['yukti_score']}\n")
    
    # 5. Financial Calculation
    print("5. Calculating Financials...")
    res = requests.post(f"{BASE_URL}/calculate-finance", json={
        "session_id": session_id
    })
    res.raise_for_status()
    finance = res.json()
    print(f"Financials generated. Principal: {finance['loan_amount']}\n")
    
    # 6. Scheme Matching
    print("6. Matching Schemes...")
    res = requests.get(f"{BASE_URL}/schemes")
    res.raise_for_status()
    schemes = res.json()
    print(f"Found {len(schemes)} eligible schemes.\n")
    
    # 7. Simulation
    print("7. Running What-If Simulation (-20% Demand, +10% Cost)...")
    res = requests.post(f"{BASE_URL}/simulate", json={
        "session_id": session_id,
        "revenue_delta_pct": -20.0,
        "cost_delta_pct": 10.0,
        "tenure_override_years": None
    })
    res.raise_for_status()
    sim = res.json()
    print(f"Simulation complete. Survives stress? {sim['survives_stress']}, Simulated ROI: {sim['simulated_roi']}%\n")
    
    print("All API E2E tests passed successfully!")

if __name__ == "__main__":
    run_test()
