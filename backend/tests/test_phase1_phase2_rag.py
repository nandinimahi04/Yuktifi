from app.phase1.service import run_decision
from app.phase2.service import upsert_evidence, list_evidence
from app.rag.store import add_document, search

def test_canonical_decision():
    out=run_decision({
        'business_id':'dairy','business_name':'Dairy','location':'Solapur',
        'financial':{'margin_capital':100000,'monthly_revenue':180000,'monthly_opex':100000,
                    'annual_interest_rate_pct':12,'tenure_months':60,'moratorium_months':0,
                    'total_project_cost':1000000,'debt_amount':900000},
        'market':{'population':5000,'mapped_competitors':3,'local_evidence_count':4,'evidence_count':6},'risk_score':70
    })
    assert out['financial']['project_cost']==1000000
    assert out['financial']['loan_amount']==900000
    assert out['financial']['financing_gap']==0
    assert out['financial']['financing_reconciled'] is True
    assert out['decision'] in {'GO','CONDITIONAL','NO-GO'}


def test_canonical_decision_does_not_invent_debt():
    """Margin capital alone must never imply a loan or an inflated project cost."""
    out=run_decision({
        'business_id':'dairy','business_name':'Dairy','location':'Solapur',
        'financial':{'margin_capital':100000,'monthly_revenue':180000,'monthly_opex':100000,
                    'annual_interest_rate_pct':12,'tenure_months':60,'moratorium_months':0},
        'market':{'population':5000,'mapped_competitors':3,'local_evidence_count':4,'evidence_count':6},'risk_score':70
    })
    assert out['financial']['project_cost']==100000
    assert out['financial']['loan_amount']==0
    assert out['financial']['dscr'] is None
    assert out['financial']['dscr_status']=='NOT_APPLICABLE_NO_DEBT'
    assert out['financial']['financing_gap']==0

def test_evidence_roundtrip():
    rec=upsert_evidence({'id':'test_ev_1','metric':'population','value':'5000','unit':'persons','source':'test','geography':'TestVillage','confidence':'High','is_estimate':False})
    assert rec['id']=='test_ev_1'
    assert any(x['id']=='test_ev_1' for x in list_evidence('TestVillage','population'))

def test_rag_retrieval():
    add_document('Test scheme guideline','Eligibility requires a rural micro enterprise and the official guideline defines the application conditions.','Test','https://example.invalid')
    hits=search('rural micro enterprise eligibility',3)
    assert hits and hits[0]['title']=='Test scheme guideline'


def test_dairy_end_to_end_demo():
    from app.phase1.dairy_demo import build_dairy_demo
    out = build_dairy_demo()
    assert out['scenario']['business'] == 'dairy'
    assert out['financial']['project_cost'] == 1000000.0
    assert out['decision']['evidence_ids']
    assert len(out['risk']['scenarios']) == 5
    assert out['limitations']


def test_livestock_source_normalization_and_summary(tmp_path):
    from app.data_ingestion.livestock import read_source, validate_rows, summarize_location
    p = tmp_path / 'livestock.csv'
    p.write_text(
        'district_as_per_source,town_or_block_name,village_or_ward_name,livestock_name,gender,value\n'
        'Solapur,Akkalkot,DemoVillage,Cattle,Male,10\n'
        'Solapur,Akkalkot,DemoVillage,Cattle,Female,20\n'
        'Solapur,Akkalkot,DemoVillage,Buffalo,Female,5\n',
        encoding='utf-8'
    )
    rows = read_source(p)
    meta = validate_rows(rows)
    summary = summarize_location(rows, 'Solapur', 'Akkalkot', 'DemoVillage')
    assert meta['numeric_rows'] == 3
    assert summary['matched_rows'] == 3
    assert summary['livestock_totals'] == {'Buffalo': 5, 'Cattle': 30}


def test_livestock_ingest_creates_provenance(tmp_path):
    from app.data_ingestion.livestock import ingest_to_evidence
    p = tmp_path / 'livestock.csv'
    p.write_text(
        'district,block,village,livestock_name,gender,value\n'
        'Solapur,Akkalkot,DemoVillage,Cattle,Female,20\n',
        encoding='utf-8'
    )
    out = ingest_to_evidence(p, 'Solapur', 'Akkalkot', 'DemoVillage')
    assert out['summary']['livestock_totals']['Cattle'] == 20
    assert out['evidence']['dataset'] == 'Maharashtra 20th Livestock Census 2019 Village wise'
    assert out['evidence']['is_estimate'] is False


def test_dairy_demo_can_attach_official_livestock_context(tmp_path):
    from app.phase1.dairy_demo import build_dairy_demo
    p = tmp_path / 'livestock.csv'
    p.write_text(
        'district,block,village,livestock_name,gender,value\n'
        'Solapur,Akkalkot,DemoVillage,Cattle,Female,20\n',
        encoding='utf-8'
    )
    out = build_dairy_demo(livestock_source=str(p))
    assert out['livestock_context']['summary']['livestock_totals']['Cattle'] == 20
    # Official livestock context must not change the canonical finance path.
    assert out['financial']['project_cost'] == 1000000.0
