"""Week 6 focused tests; run from project root with pytest."""
import json

from scripts.signal_extractor import SignalExtractor


class StubEntityExtractor:
    def extract_all(self, text):
        return {
            "bedrooms": 3 if "3 bed" in text else None,
            "bathrooms": 2 if "2 bath" in text else None,
            "sqft": None,
            "price": None,
            "amenities": ["private pool"] if "private pool" in text.lower() else [],
        }


def extractor(tmp_path):
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps({"terms": [
        {"term": "renovated", "category": "condition"},
        {"term": "seller financing", "category": "financial"},
        {"term": "near downtown", "category": "location"},
        {"term": "ocean view", "category": "view"},
    ]}), encoding="utf-8")
    return SignalExtractor(taxonomy_path=path, entity_extractor=StubEntityExtractor())


def test_structured_fields_and_financing(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_ListingID": "A001",
        "L_Remarks": "3 bed 2 bath. Private pool. Recently renovated. Seller may finance. Near downtown.",
        "L_SystemPrice": 850000,
        "L_City": "Irvine",
        "PoolPrivateYN": "1",
        "GarageYN": 0,
        "FireplaceYN": "N",
        "ViewYN": "Y",
    })
    assert result["entities"] == {
        "bedrooms": 3, "bathrooms": 2, "sqft": None, "price": 850000, "city": "Irvine"
    }
    assert result["flags"]["pool"] is True
    assert result["flags"]["private_pool"] is True
    assert result["flags"]["garage"] is False
    assert result["flags"]["fireplace"] is False
    assert result["flags"]["view"] is True
    assert "seller_financing_possible" in result["keywords"]["financial"]
    assert "near downtown" in result["keywords"]["location"]


def test_missing_private_pool_does_not_mean_no_pool(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_ListingID": "A002", "L_Remarks": "A quiet home.",
        "PoolPrivateYN": "0", "PoolFeatures": None,
    })
    assert result["flags"]["private_pool"] is False
    assert result["flags"]["pool"] is None


def test_negated_pool_not_positive(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_ListingID": "A003", "L_Remarks": "No pool or fireplace.",
    })
    assert result["flags"]["pool"] is False
    assert result["flags"]["fireplace"] is False


def test_null_remarks_and_half_baths_not_total(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_ListingID": "A004", "L_Remarks": None,
        "MainLevelBedrooms": 2, "BathroomsHalf": 1,
    })
    assert result["entities"]["bedrooms"] is None
    assert result["entities"]["bathrooms"] is None


def test_no_private_pool_but_community_pool(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_ListingID": "A005",
        "L_Remarks": "No private pool, but a community pool is available.",
    })
    assert result["flags"]["private_pool"] is False
    assert result["flags"]["pool"] is True


def test_financing_unavailable_is_not_positive(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_ListingID": "A006", "L_Remarks": "Seller financing is not available.",
    })
    assert "seller financing" not in result["keywords"]["financial"]


def test_pool_flags_from_private_and_community_feature_tokens(tmp_path):
    signal_extractor = extractor(tmp_path)
    cases = [
        ({"PoolPrivateYN": "1", "PoolFeatures": "InGround,Private"}, (True, True, False)),
        ({"PoolPrivateYN": "0", "PoolFeatures": "Community,Association"}, (True, False, True)),
        ({"PoolPrivateYN": "1", "PoolFeatures": "Private,Association"}, (True, True, True)),
    ]
    for fields, expected in cases:
        result = signal_extractor.extract_signals({"L_Remarks": "", **fields})
        assert tuple(result["flags"][k] for k in ("pool", "private_pool", "community_pool")) == expected


def test_pool_none_sentinel_is_negative_but_blank_fields_stay_unknown(tmp_path):
    signal_extractor = extractor(tmp_path)
    no_pool = signal_extractor.extract_signals({"L_Remarks": "", "PoolFeatures": "None"})
    missing = signal_extractor.extract_signals({"L_Remarks": "", "PoolFeatures": None, "PoolPrivateYN": ""})
    assert tuple(no_pool["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (False, False, False)
    assert tuple(missing["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (None, None, None)


def test_explicit_no_pool_sets_all_pool_flags_false(tmp_path):
    result = extractor(tmp_path).extract_signals({"L_Remarks": "This property has no pool."})
    assert tuple(result["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (False, False, False)


def test_structured_no_private_pool_does_not_override_community_evidence(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_Remarks": "Residents enjoy a shared pool.", "PoolPrivateYN": "0", "PoolFeatures": None,
    })
    assert result["flags"]["pool"] is True
    assert result["flags"]["private_pool"] is False
    assert result["flags"]["community_pool"] is True


def test_condition_normalizes_hyphenation_and_ignores_feature_or_hoa_context():
    result = SignalExtractor(entity_extractor=StubEntityExtractor()).extract_signals({
        "L_Remarks": (
            "This move-in-ready home has fresh interior paint and custom cabinetry. "
            "The HOA recently renovated all balconies."
        )
    })
    assert "move in ready" in result["keywords"]["condition"]
    assert "freshly painted" in result["keywords"]["condition"]
    assert "custom" not in result["keywords"]["condition"]
    assert "renovated" not in result["keywords"]["condition"]


def test_location_requires_context_for_bare_destination_terms():
    result = SignalExtractor(entity_extractor=StubEntityExtractor()).extract_signals({
        "L_Remarks": (
            "The patio has direct access to the covered carport. "
            "Excellent schools and parks are nearby. A beach-inspired palette completes the home."
        )
    })
    location = result["keywords"]["location"]
    assert "direct access" not in location
    assert "schools" in location
    assert "parks" in location
    assert "beach" not in location


def test_property_type_ignores_room_and_possible_secondary_use_mentions():
    result = SignalExtractor(entity_extractor=StubEntityExtractor()).extract_signals({
        "L_Remarks": (
            "A cozy cabin has a loft-style bedroom. The shed offers workshop, studio, "
            "hobby, or storage space."
        )
    })
    assert "loft" not in result["keywords"]["property_type"]
    assert "studio" not in result["keywords"]["property_type"]


def test_amenity_hyphen_variants_emit_canonical_labels():
    result = SignalExtractor().extract_signals({
        "L_Remarks": "The primary bedroom has a walk-in closet and walk-in shower."
    })
    assert "walk in closet" in result["amenities"]
    assert "walk in shower" in result["amenities"]
    assert "walk-in closet" not in result["amenities"]


def test_negated_condition_phrase_is_not_emitted():
    result = SignalExtractor(entity_extractor=StubEntityExtractor()).extract_signals({
        "L_Remarks": "The home is not move-in ready and needs repairs."
    })
    assert "move in ready" not in result["keywords"]["condition"]
    assert "needs_repairs" in result["keywords"]["condition"]


def test_contradictory_private_pool_database_and_text_is_unknown_for_private(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_Remarks": "This home has a private swimming pool.", "PoolPrivateYN": "0", "PoolFeatures": None,
    })
    assert result["flags"]["pool"] is True
    assert result["flags"]["private_pool"] is None
    assert result["flags"]["community_pool"] is None


def test_proposed_pool_is_not_existing_pool_evidence(tmp_path):
    signal_extractor = extractor(tmp_path)
    proposed = signal_extractor.extract_signals({
        "L_Remarks": "Imagine an infinity-edge pool here; this lot has room to add one.",
        "PoolFeatures": "None",
    })
    no_structured_data = signal_extractor.extract_signals({
        "L_Remarks": "Potential to build a pool in the backyard.",
        "PoolFeatures": None,
    })
    assert proposed["flags"]["pool"] is False
    assert no_structured_data["flags"]["pool"] is None


def test_optional_separately_paid_community_pool_is_not_property_amenity(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_Remarks": (
            'For a separate fee, join the Lake and Lodge Membership to take advantage of the pool.'
        ),
        "PoolFeatures": "None",
    })
    assert tuple(result["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (False, False, False)


def test_community_pool_remarks_override_none_feature_sentinel(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_Remarks": "The community offers a pool and spa for residents.",
        "PoolFeatures": "None",
    })
    assert tuple(result["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (True, False, True)


def test_resident_amenity_list_identifies_community_pool(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_Remarks": (
            "Residents enjoy resort-style amenities including clubhouse, pool and spa."
        ),
        "PoolFeatures": None,
    })
    assert tuple(result["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (True, False, True)


def test_generic_pool_feature_does_not_identify_ownership_type(tmp_path):
    result = extractor(tmp_path).extract_signals({"L_Remarks": "", "PoolFeatures": "InGround,Heated"})
    assert result["flags"]["pool"] is True
    assert result["flags"]["private_pool"] is None
    assert result["flags"]["community_pool"] is None


def test_private_and_community_pool_text_can_both_be_true(tmp_path):
    result = extractor(tmp_path).extract_signals({
        "L_Remarks": "The home has a private pool and residents enjoy a community pool.",
        "PoolPrivateYN": "",
        "PoolFeatures": "Community,Association",
    })
    assert tuple(result["flags"][k] for k in ("pool", "private_pool", "community_pool")) == (True, True, True)
