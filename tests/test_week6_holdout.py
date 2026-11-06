import csv
import json
import sys
from types import SimpleNamespace

from scripts import evaluate_week6_gold
from scripts.prepare_week6_gold import fieldnames
from scripts.signal_extractor import SignalExtractor
from scripts.prepare_week6_holdout import (
    FINAL_HOLDOUT_SIZE,
    build_query,
    fetch_holdout_listings,
    load_excluded_ids,
    write_holdout_csv,
)


class StubExtractor:
    def extract_signals(self, listing):
        return {
            "listing_id": str(listing["L_ListingID"]),
            "entities": {"bedrooms": 2, "bathrooms": None, "sqft": None, "price": 250000, "city": "Test"},
            "amenities": [],
            "flags": {"pool": None, "private_pool": None, "community_pool": None, "garage": None, "fireplace": None, "view": None},
            "keywords": {"condition": [], "financial": [], "location": [], "property_type": [], "view": []},
        }


def test_excluded_ids_load_from_csv_and_jsonl(tmp_path):
    csv_path = tmp_path / "gold.csv"
    csv_path.write_text("listing_id\nA\n", encoding="utf-8")
    sample_path = tmp_path / "sample.jsonl"
    sample_path.write_text('{"listing_id":"B"}\n{"listing_id":"C"}\n', encoding="utf-8")
    assert load_excluded_ids((csv_path, sample_path)) == {"A", "B", "C"}


def test_default_exclusions_scan_all_processed_listing_csv_and_jsonl(tmp_path):
    data_root = tmp_path / "data"
    processed = data_root / "processed"
    processed.mkdir(parents=True)
    (processed / "week6_gold_review.csv").write_text(
        "listing_id\nDEV-1\n", encoding="utf-8"
    )
    (processed / "week6_review_sample.jsonl").write_text(
        '{"listing_id":"DEV-2"}\n', encoding="utf-8"
    )
    (processed / "week6_holdout_review.csv").write_text(
        "listing_id\nOLD-HOLDOUT\n", encoding="utf-8"
    )
    (processed / "extra_development.csv").write_text(
        "L_ListingID\nEXTRA-DEV\n", encoding="utf-8"
    )
    (processed / "unrelated.csv").write_text("query\ntext\n", encoding="utf-8")
    assert load_excluded_ids(data_root=data_root) == {
        "DEV-1", "DEV-2", "OLD-HOLDOUT", "EXTRA-DEV"
    }


def test_holdout_query_excludes_ids_and_uses_seeded_order():
    query = build_query(3)
    assert "CAST(L_ListingID AS CHAR) NOT IN (%s, %s, %s)" in query
    assert "CRC32(CONCAT(CAST(L_ListingID AS CHAR), %s))" in query
    assert "LIMIT %s" in query


def test_database_sampling_parameters_are_reproducible_for_a_fixed_seed(monkeypatch):
    import mysql.connector
    from scripts import sample_week6_signals

    captured = []

    class Cursor:
        def execute(self, query, params):
            captured.append((query, tuple(params)))
        def fetchall(self):
            return []
        def close(self):
            pass

    class Connection:
        def cursor(self, dictionary=False):
            assert dictionary is True
            return Cursor()
        def close(self):
            pass

    monkeypatch.setattr(mysql.connector, "connect", lambda **kwargs: Connection())
    monkeypatch.setattr(sample_week6_signals, "connection_settings", lambda args: {"host": args.host})
    args = SimpleNamespace(seed=8675309, limit=FINAL_HOLDOUT_SIZE, host="localhost", port=3306)
    excluded = {"Z", "A", "M"}
    fetch_holdout_listings(args, excluded)
    fetch_holdout_listings(args, excluded)
    assert captured[0] == captured[1]
    assert captured[0][1] == ("A", "M", "Z", "8675309", FINAL_HOLDOUT_SIZE)
    assert "ORDER BY CRC32(CONCAT(CAST(L_ListingID AS CHAR), %s))" in captured[0][0]


def test_holdout_csv_uses_review_schema_with_blank_gold_and_pending_status(tmp_path):
    listings = [
        {"L_ListingID": f"H{i:02}", "L_Remarks": f"Full remarks {i}", "L_SystemPrice": 250000,
         "L_City": "Test", "PoolFeatures": "None"}
        for i in range(FINAL_HOLDOUT_SIZE)
    ]
    output = tmp_path / "holdout.csv"
    assert write_holdout_csv(listings, output, StubExtractor(), {"DEV"}) == FINAL_HOLDOUT_SIZE
    with output.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == FINAL_HOLDOUT_SIZE
    assert len({row["listing_id"] for row in rows}) == FINAL_HOLDOUT_SIZE
    assert list(rows[0]) == fieldnames()
    assert all(not row[col] for row in rows for col in fieldnames() if col.startswith("gold_"))
    assert all(row["review_status"] == "pending" for row in rows)
    assert rows[0]["remarks"] == "Full remarks 0"
    assert json.loads(rows[0]["source_fields_json"])["PoolFeatures"] == "None"
    assert rows[0]["pred_entity_bedrooms"] == "2"


def test_holdout_csv_rejects_duplicate_and_development_ids(tmp_path):
    listing = {"L_ListingID": "DEV", "L_Remarks": "", "PoolFeatures": "None"}
    output = tmp_path / "holdout.csv"
    import pytest
    with pytest.raises(ValueError, match="Development listing"):
        write_holdout_csv([listing] * FINAL_HOLDOUT_SIZE, output, StubExtractor(), {"DEV"})
    listing["L_ListingID"] = "H"
    with pytest.raises(ValueError, match="duplicate"):
        write_holdout_csv([listing] * FINAL_HOLDOUT_SIZE, output, StubExtractor(), set())


def test_final_holdout_predictions_come_from_current_signal_extractor(tmp_path):
    listings = [
        {
            "L_ListingID": f"CURRENT-{i:03}",
            "L_Remarks": "A move-in-ready home near downtown.",
            "L_SystemPrice": 500000,
            "L_City": "Test City",
        }
        for i in range(FINAL_HOLDOUT_SIZE)
    ]
    output = tmp_path / "current_predictions.csv"
    write_holdout_csv(listings, output, SignalExtractor(), set())
    with output.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert all("move in ready" in json.loads(row["pred_keyword_condition"]) for row in rows)


def test_final_holdout_writer_refuses_to_overwrite(tmp_path):
    output = tmp_path / "existing.csv"
    output.write_text("keep me", encoding="utf-8")
    listings = [
        {"L_ListingID": f"H{i:02}", "L_Remarks": "", "L_SystemPrice": 200000}
        for i in range(FINAL_HOLDOUT_SIZE)
    ]
    import pytest
    with pytest.raises(FileExistsError):
        write_holdout_csv(listings, output, StubExtractor(), set())
    assert output.read_text(encoding="utf-8") == "keep me"


def test_evaluator_accepts_cli_input_path(monkeypatch, tmp_path):
    target = tmp_path / "review.csv"
    seen = []
    monkeypatch.setattr(
        evaluate_week6_gold, "evaluate", lambda path, **kwargs: seen.append((path, kwargs))
    )
    monkeypatch.setattr(sys, "argv", ["evaluate_week6_gold", "--input", str(target)])
    evaluate_week6_gold.main()
    assert seen == [(target, {"normalization": "strict"})]


def test_evaluator_cli_accepts_canonical_normalization(monkeypatch, tmp_path):
    target = tmp_path / "review.csv"
    seen = []
    monkeypatch.setattr(
        evaluate_week6_gold, "evaluate", lambda path, **kwargs: seen.append((path, kwargs))
    )
    monkeypatch.setattr(
        sys, "argv", ["evaluate_week6_gold", "--input", str(target), "--normalization", "both"]
    )
    evaluate_week6_gold.main()
    assert seen == [(target, {"normalization": "both"})]
