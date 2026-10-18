import unittest

from scripts.annotation_helper import generate_candidates
from scripts.entity_extractor import EntityExtractor


class Week3EntityExtractorTests(unittest.TestCase):
    def entities(self, text):
        return [(text[start:end], label) for start, end, label in generate_candidates(text)]

    def test_explicit_numeric_and_spelled_out_quantities(self):
        text = "5-bedroom, four-and-a-half-bath home with two additional bedrooms."
        self.assertEqual(
            self.entities(text),
            [
                ("5-bedroom", "BEDROOM"),
                ("four-and-a-half-bath", "BATHROOM"),
                ("two additional bedrooms", "BEDROOM"),
            ],
        )

    def test_mixed_fraction_bathroom_and_area_measurements(self):
        text = "2 1/2 bath home with 2,115 square feet and 900 sqft."
        self.assertEqual(
            self.entities(text),
            [
                ("2 1/2 bath", "BATHROOM"),
                ("2,115 square feet", "SQFT"),
                ("900 sqft", "SQFT"),
            ],
        )

    def test_price_context_and_explicit_range(self):
        text = "Grant of $100,000; listing price $1,200,000. Offered from 9000000 to 10000000."
        self.assertEqual(
            self.entities(text),
            [
                ("$1,200,000", "PRICE"),
                ("9000000", "PRICE"),
                ("10000000", "PRICE"),
            ],
        )

    def test_financing_and_reduction_amounts_are_not_prices(self):
        text = "Seller financing of $500,000, annual income $120,000, reduced $100,000."
        self.assertNotIn("PRICE", [label for _, label in self.entities(text)])

    def test_taxonomy_views_and_distinct_occurrences(self):
        text = "Mountain views, private patio, fire pit, and private patio."
        self.assertEqual(
            self.entities(text),
            [
                ("Mountain views", "AMENITY"),
                ("private patio", "AMENITY"),
                ("fire pit", "AMENITY"),
                ("private patio", "AMENITY"),
            ],
        )

    def test_compound_pool_and_spa_keeps_features_separate(self):
        text = "The backyard has a pool and spa."
        self.assertEqual(
            self.entities(text),
            [("backyard", "AMENITY"), ("pool", "AMENITY"), ("spa", "AMENITY")],
        )

    def test_vague_marketing_and_nearby_public_features_are_excluded(self):
        text = "Living space, open floor plan, and walking distance to a golf course."
        self.assertEqual(self.entities(text), [])

        community_text = "The residential community includes a golf course."
        self.assertEqual(
            self.entities(community_text),
            [("golf course", "AMENITY")],
        )

    def test_offsets_are_exact_and_labels_stay_within_week3_schema(self):
        text = "Three-bedroom home with a California Room and hillside views."
        spans = generate_candidates(text)
        self.assertTrue(all(text[start:end] for start, end, _ in spans))
        self.assertTrue(
            all(label in EntityExtractor.labels for _, _, label in spans)
        )
        self.assertEqual(
            [(text[start:end], label) for start, end, label in spans],
            [
                ("Three-bedroom", "BEDROOM"),
                ("California Room", "AMENITY"),
                ("hillside views", "AMENITY"),
            ],
        )

    def test_value_api_keeps_numeric_types(self):
        result = EntityExtractor().extract_all(
            "3-bedroom, 2 1/2 bath home with 1,200 square feet offered at $450k and a pool."
        )
        self.assertEqual(result["bedrooms"], 3)
        self.assertEqual(result["bathrooms"], 2.5)
        self.assertEqual(result["sqft"], 1200)
        self.assertEqual(result["price"], 450000)
        self.assertIn("pool", [value.casefold() for value in result["amenities"]])


if __name__ == "__main__":
    unittest.main()
