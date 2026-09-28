from fastapi.testclient import TestClient
from app.main import app


def test_v3_requires_explicit_economics():
    c=TestClient(app)
    r=c.post('/api/v3/advisory', json={'business_id':'dairy','location':{'query':'Akkalkot, Solapur, Maharashtra'},'promoter_margin':100000})
    assert r.status_code==422
    assert 'Missing business inputs' in str(r.json())


def test_v3_advisory_persists_run():
    c=TestClient(app)
    payload={'business_id':'dairy','location':{'query':'Akkalkot, Solapur, Maharashtra','population':5000,'households':1000},'promoter_margin':100000,'monthly_units':727,'price_per_unit':55,'variable_cost_per_unit':20,'fixed_cost_monthly':15000,'annual_rate_pct':12,'tenure_months':60,'use_demo_assumptions':False}
    r=c.post('/api/v3/advisory', json=payload)
    assert r.status_code==200, r.text
    run_id=r.json()['run_id']
    r2=c.get('/api/v3/advisory/'+run_id)
    assert r2.status_code==200
    assert r2.json()['run_id']==run_id
