"""Regression tests from five manually reviewed real listing examples (no raw remarks)."""
import json

from scripts.signal_extractor import SignalExtractor


class StubEntityExtractor:
    def extract_all(self, text):
        return {
            "bedrooms": None,
            "bathrooms": None,
            "sqft": None,
            "price": None,
            "amenities": ["courtyard", "kitchen", "courtyard", "KITCHEN"],
        }


def test_lucerne_condition_and_lake_proximity(tmp_path):
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(json.dumps({"terms": []}), encoding="utf-8")
    result = SignalExtractor(taxonomy_path, StubEntityExtractor()).extract_signals({
        "L_ListingID": "regression-1",
        "L_Remarks": (
            "Located just a short walk from the lake. "
            "This home needs repairs. Buy a bargain and fix it up."
        ),
        "PropertyCondition": "Fixer",
    })
    assert "needs_repairs" in result["keywords"]["condition"]
    assert "fixer_upper" in result["keywords"]["condition"]
    assert "near_lake" in result["keywords"]["location"]
    assert result["property_condition"] == "Fixer"
    assert result["amenities"] == ["courtyard", "kitchen"]


def test_structured_community_pool_does_not_imply_private_pool(tmp_path):
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(json.dumps({"terms": []}), encoding="utf-8")
    result = SignalExtractor(taxonomy_path, StubEntityExtractor()).extract_signals({
        "L_ListingID": "regression-2",
        "L_Remarks": "A home in a quiet neighborhood.",
        "PoolFeatures": "Community,Fenced,Filtered,Gunite,InGround,Association",
        "PoolPrivateYN": "",
    })
    assert result["flags"]["pool"] is True
    assert result["flags"]["community_pool"] is True
    assert result["flags"]["private_pool"] is False


def test_no_pool_reference_is_not_an_amenity_claim(tmp_path):
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(json.dumps({"terms": []}), encoding="utf-8")
    result = SignalExtractor(taxonomy_path, StubEntityExtractor()).extract_signals({
        "L_ListingID": "regression-3",
        "L_Remarks": "No pool or fireplace.",
    })
    assert result["flags"]["pool"] is False
    assert result["flags"]["fireplace"] is False
    assert result["flags"]["community_pool"] is False


def test_square_foot_singular_week3_regex():
    from scripts.entity_extractor import EntityExtractor
    extracted = EntityExtractor().extract_all("Approx 1,100 square foot 2 bedroom + 2 bath residence.")
    assert extracted["sqft"] == 1100
