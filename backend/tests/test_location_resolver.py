from app.location.resolver import LocationResolver


def sample_rows():
    return [
        {"state": "Maharashtra", "district": "Solapur", "subdistrict": "Akkalkot", "block": "Akkalkot", "village": "Akkalkot (Rural)", "village_code": "562839"},
        {"state": "Maharashtra", "district": "Solapur", "subdistrict": "Akkalkot", "block": "Akkalkot", "village": "Chincholi (Najik)", "village_code": "562788"},
    ]


def test_text_resolves_hierarchy():
    r = LocationResolver(sample_rows()).resolve_text("Chincholi Najik, Akkalkot, Solapur, Maharashtra")
    assert r["status"] == "resolved"
    assert r["village"] == "Chincholi (Najik)"
    assert r["district"] == "Solapur"
    assert r["codes"]["village_code"] == "562788"


def test_unknown_does_not_invent():
    """An unrecognised place must not be coerced into a nearby known one."""
    r = LocationResolver(sample_rows()).resolve_text("Imaginary Village, Solapur")
    assert r["status"] == "INSUFFICIENT_LOCATION_EVIDENCE"
    # Nothing is asserted about a place the master data does not contain.
    assert "village" not in r
    assert "village_code" not in r


def test_coordinate_without_coordinate_master_is_explicit():
    """A coordinate that cannot be mapped must say why, not guess a district."""
    r = LocationResolver(sample_rows()).resolve_coordinates(17.1, 75.9)
    assert r["status"] == "INSUFFICIENT_LOCATION_EVIDENCE"
    assert r["reason"] == "needs_reverse_geocode"
    assert "district" not in r
