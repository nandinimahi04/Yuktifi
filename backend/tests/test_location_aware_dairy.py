from app.location.service import load_resolver
from app.phase1.dairy_demo import build_dairy_demo
from app.location.context import build_location_context


def test_canonical_location_context():
    from app.location.resolver import LocationResolver
    rows = [{
        'state': 'Maharashtra', 'district': 'Solapur', 'subdistrict': 'Akkalkot',
        'block': 'Akkalkot', 'village': 'Chincholi (Najik)', 'village_code': '562788'
    }]
    result = LocationResolver(rows).resolve_text('Chincholi Najik, Akkalkot, Solapur, Maharashtra')
    ctx = build_location_context(result)
    assert ctx['canonical_label'] == 'Chincholi (Najik), Akkalkot, Solapur, Maharashtra'
    assert ctx['codes']['village_code'] == '562788'


def test_dairy_accepts_canonical_location():
    ctx = {
        'status': 'resolved',
        'canonical_label': 'Chincholi (Najik), Akkalkot, Solapur, Maharashtra',
        'state': 'Maharashtra', 'district': 'Solapur', 'subdistrict': 'Akkalkot',
        'block': 'Akkalkot', 'village': 'Chincholi (Najik)',
        'codes': {'village_code': '562788'},
        'coordinates': {'lat': None, 'lng': None},
        'resolution_method': 'master_match', 'match_score': 1.0,
    }
    result = build_dairy_demo(canonical_location=ctx)
    assert result['location_context']['canonical_label'].startswith('Chincholi')
    assert result['scenario']['location'].startswith('Chincholi')


def test_dairy_population_pipeline_can_be_attached(tmp_path):
    import csv
    p = tmp_path / "pca.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["State", "District", "Sub-District", "Village", "Village Code", "Residence", "Number of Households", "Total Population"])
        w.writerow(["Maharashtra", "Solapur", "Akkalkot", "Chincholi (Najik)", "562788", "Total", 321, 1456])
    ctx = {
        'status': 'resolved', 'canonical_label': 'Chincholi (Najik), Akkalkot, Solapur, Maharashtra',
        'state': 'Maharashtra', 'district': 'Solapur', 'subdistrict': 'Akkalkot', 'block': 'Akkalkot',
        'village': 'Chincholi (Najik)', 'codes': {'village_code': '562788'},
        'coordinates': {'lat': None, 'lng': None}, 'resolution_method': 'master_match', 'match_score': 1.0,
    }
    result = build_dairy_demo(canonical_location=ctx, census_source=str(p))
    assert result['population_context']['summary']['metrics']['population']['value'] == 1456
    assert result['decision']['market']['population'] == 1456
