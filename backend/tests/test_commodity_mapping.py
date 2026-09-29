"""
Unit tests for Commodity Taxonomy and Mapping (Phase 2).
"""
import pytest
from app.data_layer.normalization.commodity_mapper import commodity_mapper

def test_commodity_resolution():
    # Consumer affairs resolution
    assert commodity_mapper.resolve_commodity("Rice", "consumer_affairs") == "rice"
    assert commodity_mapper.resolve_commodity("Atta (Wheat)", "consumer_affairs") == "atta"
    assert commodity_mapper.resolve_commodity("Tur/Arhar Dal", "consumer_affairs") == "tur_dal"
    assert commodity_mapper.resolve_commodity("Tea Loose", "consumer_affairs") == "tea"

    # AGMARKNET resolution
    assert commodity_mapper.resolve_commodity("Arhar (Tur/Red Gram)", "agmarknet") == "tur_dal"
    assert commodity_mapper.resolve_commodity("Gram (Chana)", "agmarknet") == "gram_dal"
    assert commodity_mapper.resolve_commodity("Jowar(Sorghum)", "agmarknet") == "jowar"

def test_business_input_profiles():
    kirana_inputs = commodity_mapper.get_business_input_profile("retail_kirana")
    assert len(kirana_inputs) > 0
    assert "rice" in kirana_inputs
    assert "wheat" in kirana_inputs
    assert "edible_oil" in kirana_inputs
    assert sum(kirana_inputs.values()) == pytest.approx(1.0, rel=1e-2)

    tea_inputs = commodity_mapper.get_business_input_profile("tea_snacks")
    assert len(tea_inputs) > 0
    assert "milk" in tea_inputs
    assert "tea" in tea_inputs
    assert "sugar" in tea_inputs
    assert sum(tea_inputs.values()) == pytest.approx(1.0, rel=1e-2)
