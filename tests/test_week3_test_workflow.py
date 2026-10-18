import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import interactive_annotator as annotator
from scripts.evaluate_week3_test import evaluate_test_records


class Week3HeldOutWorkflowTests(unittest.TestCase):
    def test_test_split_uses_separate_annotation_and_manifest_paths(self):
        self.assertEqual(
            annotator.data_path("test"),
            Path("data/labeled/week3_test_annotations.jsonl"),
        )
        self.assertEqual(
            annotator.test_manifest_path(),
            Path("data/labeled/week3_test_evaluation_manifest.json"),
        )

    def test_initialization_uses_frozen_predictions_as_unverified_suggestions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "week3_split.json").write_text(
                json.dumps({"development": [0], "test": list(range(1, 31))}),
                encoding="utf-8",
            )
            with (root / "week3_auto_labels.jsonl").open("w", encoding="utf-8") as f:
                for index in range(250):
                    f.write(json.dumps({
                        "listing_id": f"id-{index}",
                        "text": "Listing with pool",
                        "entities": [[13, 17, "AMENITY"]],
                    }) + "\n")

            with patch.object(annotator, "DATA_DIR", root), patch.object(
                annotator, "generate_candidates", return_value=[[13, 17, "AMENITY"]]
            ):
                records = annotator.initialize_test_annotations()
                self.assertEqual(len(records), 30)
                self.assertEqual(records[0]["source_index"], 1)
                self.assertEqual(records[-1]["source_index"], 30)
                self.assertEqual(records[0]["predicted_entities"], [[13, 17, "AMENITY"]])
                self.assertEqual(records[0]["entities"], [[13, 17, "AMENITY"]])
                self.assertFalse(records[0]["human_verified"])
                self.assertTrue(
                    json.loads((root / "week3_test_evaluation_manifest.json").read_text())[
                        "predictions_are_suggestions_not_ground_truth"
                    ]
                )

                # Existing annotation progress is read as-is, never regenerated.
                records[0]["entities"] = []
                records[0]["human_verified"] = False
                annotator.save_records(records, root / "week3_test_annotations.jsonl")
                again = annotator.initialize_test_annotations()
                self.assertEqual(again[0]["entities"], [])

    def test_manual_edit_can_change_exact_span_and_label(self):
        text = "2-bedroom home with a pool"
        pool_start = text.index("pool")
        record = {
            "source_index": 1,
            "listing_id": "edit-1",
            "text": text,
            "entities": [[0, 10, "BEDROOM"], [pool_start, pool_start + 4, "AMENITY"]],
            "predicted_entities": [[0, 10, "BEDROOM"], [pool_start, pool_start + 4, "AMENITY"]],
            "human_verified": False,
        }
        records = [record]
        inputs = iter(["e", "1", "0:15,AMENITY", "", "", "no"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.jsonl"
            annotator.review_record(
                record,
                records,
                path,
                input_fn=lambda _prompt: next(inputs),
                output_fn=lambda _message: None,
            )
        self.assertIn([0, 15, "AMENITY"], record["entities"])
        self.assertFalse(record["human_verified"])

    def test_quitting_during_edits_saves_unverified_progress(self):
        text = "2-bedroom home with a pool"
        pool_start = text.index("pool")
        record = {
            "source_index": 1,
            "listing_id": "edit-quit",
            "text": text,
            "entities": [[0, 10, "BEDROOM"], [pool_start, pool_start + 4, "AMENITY"]],
            "predicted_entities": [[0, 10, "BEDROOM"], [pool_start, pool_start + 4, "AMENITY"]],
            "human_verified": False,
        }
        records = [record]
        inputs = iter(["e", "1", "0:15,AMENITY", "q"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.jsonl"
            completed = annotator.review_record(
                record,
                records,
                path,
                input_fn=lambda _prompt: next(inputs),
                output_fn=lambda _message: None,
            )
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(completed)
        self.assertIn([0, 15, "AMENITY"], saved["entities"])
        self.assertFalse(saved["human_verified"])

    def test_evaluator_rejects_unverified_test_records(self):
        indices = list(range(30))
        records = [
            {"source_index": index, "listing_id": f"id-{index}", "human_verified": False}
            for index in indices
        ]
        manifest = {
            "record_count": 30,
            "test_source_indices": indices,
            "predictions_are_suggestions_not_ground_truth": True,
            "regex_version": "frozen",
        }
        with self.assertRaisesRegex(RuntimeError, "not human-verified"):
            evaluate_test_records(records, indices, manifest, "frozen")

    def test_evaluator_rejects_invalid_verified_offsets(self):
        indices = list(range(30))
        records = [
            {
                "source_index": index,
                "listing_id": f"id-{index}",
                "text": "listing text",
                "predicted_entities": [],
                "entities": [[0, 99, "AMENITY"]] if index == 0 else [],
                "human_verified": True,
                "regex_version": "frozen",
            }
            for index in indices
        ]
        manifest = {
            "record_count": 30,
            "test_source_indices": indices,
            "predictions_are_suggestions_not_ground_truth": True,
            "regex_version": "frozen",
        }
        with self.assertRaisesRegex(ValueError, "offsets out of range"):
            evaluate_test_records(records, indices, manifest, "frozen")

    def test_evaluator_rejects_changed_frozen_extractor(self):
        indices = list(range(30))
        records = [
            {
                "source_index": index,
                "listing_id": f"id-{index}",
                "text": "listing text",
                "predicted_entities": [],
                "entities": [],
                "human_verified": True,
                "regex_version": "old-version",
            }
            for index in indices
        ]
        manifest = {
            "record_count": 30,
            "test_source_indices": indices,
            "predictions_are_suggestions_not_ground_truth": True,
            "regex_version": "old-version",
        }
        with self.assertRaisesRegex(RuntimeError, "does not match the frozen"):
            evaluate_test_records(records, indices, manifest, "new-version")


if __name__ == "__main__":
    unittest.main()
