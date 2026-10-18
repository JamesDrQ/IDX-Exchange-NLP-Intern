import unittest

from scripts.prepare_week3_dev import build_dev_records


class PrepareWeek3DevTests(unittest.TestCase):
    def test_regex_labels_are_not_marked_human_verified(self):
        split = {"development": [0, 1]}
        auto_records = [
            {"listing_id": "a", "text": "auto text", "entities": [[0, 4, "AMENITY"]]},
            {"listing_id": "b", "text": "second text", "entities": []},
        ]
        manual_records = [
            # Legacy progress flag alone is not proof of human review.
            {"listing_id": "a", "entities": [[0, 4, "AMENITY"]], "annotated": True},
            # Explicit confirmation is required for human verification.
            {"listing_id": "b", "entities": [[0, 6, "BEDROOM"]], "human_verified": True},
        ]

        result = build_dev_records(split, auto_records, manual_records)

        self.assertFalse(result[0]["human_verified"])
        self.assertEqual(result[0]["entities"], auto_records[0]["entities"])
        self.assertTrue(result[1]["human_verified"])
        self.assertEqual(result[1]["entities"], manual_records[1]["entities"])


if __name__ == "__main__":
    unittest.main()
