import json

from scripts.evaluate_week6_gold import (
    _metric_summary,
    canonical_tag,
    evaluate,
    normalized_tag_set,
    tag_counts,
)
from scripts.prepare_week6_gold import fieldnames


def test_guideline_aliases_are_canonicalized_by_category():
    assert canonical_tag("condition", "FRESH PAINT") == "freshly painted"
    assert canonical_tag("condition", "freshly painted") == "freshly painted"
    assert canonical_tag("location", "just minutes") == "minutes from"
    assert canonical_tag("location", "just minutes from") == "minutes from"
    assert canonical_tag("property_type", "townhouse") == "townhome"
    assert canonical_tag("property_type", "condominium") == "condo"
    assert canonical_tag("property_type", "single family residence") == "single family home"
    assert canonical_tag("amenities", "walk-in closets") == "walk in closet"
    assert canonical_tag("amenities", "walk-in shower") == "walk in shower"
    assert canonical_tag("amenities", "walk-in pantry") == "walk in pantry"


def test_hyphen_spacing_and_case_are_normalized_symmetrically():
    gold = normalized_tag_set('["Move in ready"]', category="condition", normalization="canonical")
    pred = normalized_tag_set('["move-in-ready"]', category="condition", normalization="canonical")
    assert gold == pred == {"move in ready"}


def test_undocumented_or_meaningful_distinctions_are_not_collapsed():
    assert canonical_tag("condition", "beautifully updated") == "beautifully updated"
    assert canonical_tag("amenities", "private balcony") != canonical_tag("amenities", "balcony")
    assert canonical_tag("view", "ocean view") != canonical_tag("view", "ocean views")
    assert normalized_tag_set('["townhouse"]', category="property_type") == {"townhouse"}


def test_tag_instance_precision_recall_f1_counts():
    counts = tag_counts({"a", "b"}, {"b", "c"})
    assert counts == (1, 1, 1)
    assert _metric_summary(counts) == {
        "tp": 1,
        "fp": 1,
        "fn": 1,
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
    }


def test_evaluator_reports_strict_and_canonical_metrics_symmetrically(tmp_path, capsys):
    row = {name: "" for name in fieldnames()}
    row.update({
        "listing_id": "EVAL-1",
        "remarks": "",
        "source_fields_json": "{}",
        "review_status": "done",
        "pred_keyword_condition": json.dumps(["fresh paint"]),
        "gold_keyword_condition": json.dumps(["freshly painted"]),
        "pred_keyword_location": json.dumps(["just minutes"]),
        "gold_keyword_location": json.dumps(["minutes from"]),
        "pred_keyword_property_type": json.dumps(["townhouse"]),
        "gold_keyword_property_type": json.dumps(["townhome"]),
        "pred_amenities": json.dumps(["walk-in closets"]),
        "gold_amenities": json.dumps(["walk in closet"]),
    })
    input_path = tmp_path / "review.csv"
    import csv
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames())
        writer.writeheader()
        writer.writerow(row)

    result = evaluate(input_path, normalization="both")
    output = capsys.readouterr().out

    strict = result["text_metrics"]["strict"]["all"]
    canonical = result["text_metrics"]["canonical"]["all"]
    assert (strict["tp"], strict["fp"], strict["fn"], strict["f1"]) == (0, 4, 4, 0.0)
    assert (canonical["tp"], canonical["fp"], canonical["fn"], canonical["f1"]) == (4, 0, 0, 1.0)
    assert result["normalization_resolved"]["all"] == {"fp": 4, "fn": 4}
    assert "Free-text exact-label (strict)" in output
    assert "Free-text canonical-label" in output
