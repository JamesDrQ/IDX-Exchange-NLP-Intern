import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import interactive_annotator as annotator


class DevelopmentAnnotatorTests(unittest.TestCase):
    def test_development_selects_separate_file(self):
        self.assertEqual(
            annotator.data_path("development"),
            Path("data/labeled/week3_dev_annotations.jsonl"),
        )

    def test_accept_requires_explicit_full_listing_confirmation(self):
        text = "2-bedroom home with a pool"
        record = {
            "listing_id": "dev-1",
            "text": text,
            "entities": [],
            "human_verified": False,
        }
        records = [record]
        pool_start = text.index("pool")
        suggestions = [[0, 10, "BEDROOM"], [pool_start, pool_start + 4, "AMENITY"]]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dev.jsonl"
            inputs = iter(["a", "", "YES"])
            with patch.object(annotator, "generate_candidates", return_value=suggestions):
                completed = annotator.review_record(
                    record, records, path,
                    input_fn=lambda _prompt: next(inputs),
                    output_fn=lambda _message: None,
                )

            self.assertTrue(completed)
            self.assertTrue(record["human_verified"])
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(saved["human_verified"])
            self.assertEqual(saved["entities"], suggestions)

    def test_saving_edits_without_confirmation_keeps_record_unverified(self):
        text = "2-bedroom home with a pool"
        current = [[0, 10, "BEDROOM"]]
        record = {
            "listing_id": "dev-2",
            "text": text,
            "entities": current.copy(),
            "human_verified": False,
        }
        records = [record]
        pool_start = text.index("pool")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dev.jsonl"
            inputs = iter(["", "", "no"])
            with patch.object(
                annotator,
                "generate_candidates",
                return_value=[[pool_start, pool_start + 4, "AMENITY"]],
            ):
                annotator.review_record(
                    record, records, path,
                    input_fn=lambda _prompt: next(inputs),
                    output_fn=lambda _message: None,
                )

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(saved["human_verified"])
            self.assertEqual(saved["entities"], current)

    def test_add_entity_by_text_and_label(self):
        text = "A home with a pool"
        record = {
            "listing_id": "dev-5",
            "text": text,
            "entities": [],
            "human_verified": False,
        }
        records = [record]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dev.jsonl"
            inputs = iter(["", "pool,AMENITY", "", "no"])
            with patch.object(annotator, "generate_candidates", return_value=[]):
                annotator.review_record(
                    record, records, path,
                    input_fn=lambda _prompt: next(inputs),
                    output_fn=lambda _message: None,
                )

            saved = json.loads(path.read_text(encoding="utf-8"))
            start = text.index("pool")
            self.assertEqual(saved["entities"], [[start, start + 4, "AMENITY"]])
            self.assertFalse(saved["human_verified"])

    def test_remove_selected_suggestion_preserves_current_entity(self):
        text = "2-bedroom home with a pool"
        current = [[0, 10, "BEDROOM"]]
        record = {
            "listing_id": "dev-6",
            "text": text,
            "entities": current.copy(),
            "human_verified": False,
        }
        records = [record]
        pool_start = text.index("pool")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dev.jsonl"
            inputs = iter(["2", "", "YES"])
            with patch.object(
                annotator,
                "generate_candidates",
                return_value=[current[0], [pool_start, pool_start + 4, "AMENITY"]],
            ):
                annotator.review_record(
                    record, records, path,
                    input_fn=lambda _prompt: next(inputs),
                    output_fn=lambda _message: None,
                )

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["entities"], current)
            self.assertTrue(saved["human_verified"])

    def test_quit_preserves_existing_entities_and_verified_record_is_untouched(self):
        record = {
            "listing_id": "dev-3",
            "text": "2-bedroom home",
            "entities": [[0, 10, "BEDROOM"]],
            "human_verified": True,
        }
        records = [record]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dev.jsonl"
            before = json.dumps(record)
            result = annotator.review_record(
                record, records, path,
                input_fn=lambda _prompt: self.fail("verified record must be skipped"),
                output_fn=lambda _message: None,
            )
            self.assertTrue(result)
            self.assertEqual(json.dumps(record), before)
            self.assertFalse(path.exists())

    def test_invalid_entity_offsets_and_labels_are_rejected(self):
        with self.assertRaises(ValueError):
            annotator.validate_entities([[0, 99, "BEDROOM"]], "short")
        with self.assertRaises(ValueError):
            annotator.validate_entities([[0, 2, "UNKNOWN"]], "text")

    def test_development_run_does_not_modify_primary_annotation_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dev_path = root / "week3_dev_annotations.jsonl"
            primary_path = root / "week3_annotations.jsonl"
            dev_path.write_text(
                json.dumps({
                    "listing_id": "dev-4", "text": "already done",
                    "entities": [], "human_verified": True,
                }) + "\n",
                encoding="utf-8",
            )
            primary_path.write_text("test split data sentinel\n", encoding="utf-8")
            primary_before = primary_path.read_bytes()

            with patch.object(annotator, "DATA_DIR", root):
                annotator.main(["--split", "development"])

            self.assertEqual(primary_path.read_bytes(), primary_before)


if __name__ == "__main__":
    unittest.main()
