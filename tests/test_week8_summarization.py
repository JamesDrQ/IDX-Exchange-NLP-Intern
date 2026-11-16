"""Week 8 unit/regression tests; no database or model network access."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.listing_summarizer import ListingSummarizer
from scripts.generate_week8_summaries import generate, DEFAULT_INPUT


class SummarizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = ListingSummarizer()

    def test_complete_listing(self):
        text = 'Welcome home. This home has 3 bedrooms and 2 bathrooms. Enjoy a renovated kitchen and covered patio. Call today.'
        data = {'L_Keyword2': 3, 'LM_Dec_3': 2, 'L_SystemPrice': 525000, 'L_City': 'Austin'}
        ext = self.s.extractive_summary(text, {'bedrooms': 3, 'bathrooms': 2})
        self.assertEqual(ext, 'This home has 3 bedrooms and 2 bathrooms. Enjoy a renovated kitchen and covered patio.')
        hybrid = self.s.hybrid_summary(text, data)
        for expected in ('3 bedrooms', '2 bathrooms', '$525,000', 'Austin', 'renovated kitchen', 'covered patio'):
            self.assertIn(expected, hybrid)
        self.assertEqual(len(self.s.sentences(hybrid)), 2)
        self.assertEqual(hybrid.count('3 bedrooms'), 1)

    def test_empty_and_malformed(self):
        for text in (None, '', '  ', 99, [], {}):
            self.assertEqual(self.s.extractive_summary(text, {'bedrooms': ''}), '')
            self.assertEqual(self.s.lead2_summary(text), '')
            self.assertEqual(self.s.hybrid_summary(text, None), '')
        for entities in (None, '', [], {'bedrooms': []}, {'bathrooms': 'NaN'}, {'city': {}}):
            self.assertEqual(self.s.extractive_summary('Quiet setting.', entities), 'Quiet setting.')

    def test_short_and_partial(self):
        self.assertEqual(self.s.lead2_summary('Covered patio'), 'Covered patio')
        self.assertIn('Covered patio', self.s.hybrid_summary('Covered patio', {}))
        hybrid = self.s.hybrid_summary('', {'L_SystemPrice': 100000})
        self.assertEqual(hybrid, 'This property is listed at $100,000.')
        for field in ('L_Keyword2', 'LM_Dec_3', 'L_SystemPrice', 'L_City'):
            data = {'L_Keyword2': 3, 'LM_Dec_3': 2, 'L_SystemPrice': 100000, 'L_City': 'Austin'}
            del data[field]
            evidence = self.s.supported_evidence('', data)['fields']
            self.assertNotIn({'L_Keyword2':'bedrooms','LM_Dec_3':'bathrooms','L_SystemPrice':'price','L_City':'city'}[field], evidence)

    def test_tokenization_and_source_preservation(self):
        text = 'At 12 Oak St. this home has 2.5 baths. A covered patio awaits! Large windows brighten the kitchen.'
        sentences = self.s.sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertIn('2.5 baths.', sentences[0])
        for s in self.s.sentences(self.s.extractive_summary(text, {}, 3)):
            self.assertIn(s, text)
        self.assertEqual(len(self.s.sentences('PRICE ADJUSTMENT!!!! CALL TODAY!!!!')), 2)

    def test_contextual_numeric_and_empty_hints(self):
        text = 'Address 3 Main Street. Listed at $300,000. This home has 3 bedrooms. There is a covered patio.'
        result = self.s.extractive_summary(text, {'bedrooms': 3, 'bathrooms': '', 'city': ''})
        self.assertIn('3 bedrooms', result)
        self.assertNotIn('Address 3', result)
        self.assertEqual(self.s.extractive_summary(text, {}), self.s.extractive_summary(text, {'bedrooms': '', 'city': ''}))

    def test_duplicate_and_contradictory_sentences(self):
        text = 'A covered patio awaits. A covered patio awaits. The home has 3 bedrooms. The home has 4 bedrooms. A renovated kitchen is included.'
        result = self.s.extractive_summary(text, {}, 3)
        self.assertEqual(result.count('A covered patio awaits.'), 1)
        self.assertNotIn('bedrooms', result)
        self.assertNotIn('bedrooms', self.s.supported_evidence(text, {})['fields'])
        text = 'A private pool is included. There is no private pool. A covered patio awaits.'
        self.assertNotIn('pool', self.s.extractive_summary(text, {}))
        result = self.s.hybrid_summary(text, {'L_City': 'Austin'})
        self.assertNotIn('pool', result)

    def test_negated_and_hypothetical_features(self):
        for text in ('No pool or fireplace.', 'There is room for a pool.', 'A pool could be installed.',
                     'The fireplace is not available.', 'No renovated kitchen or covered patio.',
                     'A nearby community pool is available.'):
            evidence = self.s.supported_evidence(text, {})
            self.assertEqual(evidence['features'], [], text)
        evidence = self.s.supported_evidence('No private pool, but a community pool is available.', {})
        self.assertEqual([f['key'] for f in evidence['features']], ['community_pool'])

    def test_private_and_community_pool(self):
        for data, expected in (({'PoolPrivateYN': 1}, 'private pool'),
                               ({'PoolFeatures': 'Community,Association', 'PoolPrivateYN': 0}, 'community pool')):
            hybrid = self.s.hybrid_summary('', data)
            self.assertIn(expected, hybrid)
        evidence = self.s.supported_evidence('A private pool is included.', {'PoolPrivateYN': 0})
        self.assertEqual(evidence['features'], [])
        evidence = self.s.supported_evidence('A community pool is included.', {'PoolPrivateYN': 0})
        self.assertEqual(evidence['features'][0]['key'], 'community_pool')

    def test_unverified_signals_never_generate_facts(self):
        data = {'source_fields': {}, 'candidate_signals': {
            'entities': {'bedrooms': 9, 'bathrooms': 8, 'price': 9000000, 'city': 'Invented'},
            'amenities': ['private pool'], 'flags': {'private_pool': True}}}
        result = self.s.hybrid_summary('Covered patio.', data)
        self.assertEqual(result, 'Covered patio.')
        self.assertFalse(self.s.supported_evidence('Covered patio.', data)['human_verified'])

    def test_ambiguous_totals_and_financial_amounts(self):
        for text in ('Main home has 3 bedrooms. Guest unit has 1 bath.',
                     'Choose 3 or 4 bedrooms.', 'The home has 2 full baths and 1 half bath.',
                     'Each unit has 2 bedrooms.', 'There are 2 bedrooms upstairs.'):
            facts = self.s.supported_evidence(text, {})['fields']
            self.assertNotIn('bedrooms', facts)
            self.assertNotIn('bathrooms', facts)
        for text in ('HOA fees are $500.', 'Save $10,000 on closing costs.', 'Appliances worth $5,000.'):
            self.assertNotIn('price', self.s.supported_evidence(text, {})['fields'])

    def test_structured_precedence_and_invalid_fields(self):
        text = 'This home has 3 bedrooms. Covered patio.'
        data = {'L_Keyword2': 4, 'LM_Dec_3': 'NaN', 'L_SystemPrice': -1, 'L_City': 'Other'}
        result = self.s.hybrid_summary(text, data)
        self.assertIn('4 bedrooms', result)
        self.assertNotIn('3 bedrooms', result)
        self.assertNotIn('NaN', result)
        for value in (True, [], {}, 'Infinity', ''):
            self.assertNotIn('bedrooms', self.s.supported_evidence('', {'L_Keyword2': value})['fields'])

    def test_three_sentences_and_determinism(self):
        text = 'This home has 3 bedrooms and 2 bathrooms. A renovated kitchen awaits. A private balcony overlooks the yard.'
        for method in (self.s.extractive_summary, self.s.hybrid_summary):
            first = method(text, {}, 3)
            self.assertEqual(len(self.s.sentences(first)), 3)
            self.assertEqual(first, method(text, {}, 3))
        self.assertEqual(self.s.lead2_summary(text), 'This home has 3 bedrooms and 2 bathrooms. A renovated kitchen awaits.')

    def test_development_review_regressions(self):
        text = 'Spacious 1-, 2-, and 3-bedroom homes range from 898 to 1,917 sq ft.'
        self.assertNotIn('bedrooms', self.s.supported_evidence(text, {})['fields'])
        text = 'This 4-bedroom, 3.5-bathroom home features a covered patio. There is potential space for an ADU. Dual A/C units provide cooling.'
        evidence = self.s.supported_evidence(text, {})
        self.assertEqual(evidence['fields']['bedrooms']['value'], 4)
        self.assertEqual(evidence['fields']['bathrooms']['value'], 3.5)
        hybrid = self.s.hybrid_summary(text, {'L_City': 'Austin'})
        self.assertIn('covered patio', hybrid)
        self.assertEqual(hybrid.count('4'), 1)
        text = 'This single-level home is minutes from Apple Park and Main Street Cupertino.'
        self.assertEqual(len(self.s.sentences(self.s.hybrid_summary(text, {'L_City': 'Cupertino'}))), 2)


class GenerationTests(unittest.TestCase):
    def test_generation_is_reproducible_and_preserves_annotations(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DEFAULT_INPUT.iterdir() if p.is_file()}
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            metadata = generate(output_dir=a)
            self.assertEqual(metadata['counts'], {'dev': 70, 'test': 30})
            generate(output_dir=b)
            for path in a.iterdir():
                self.assertEqual(path.read_bytes(), (b/path.name).read_bytes())
            with self.assertRaises(FileExistsError):
                generate(output_dir=a)
            for split in ('dev', 'test'):
                rows = [json.loads(x) for x in (a/f'{split}_summaries.jsonl').read_text().splitlines()]
                self.assertTrue(all('reference_summary' not in row for row in rows))
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DEFAULT_INPUT.iterdir() if p.is_file()})

    def test_cannot_write_into_annotations(self):
        with self.assertRaises(ValueError):
            generate(output_dir=DEFAULT_INPUT/'predictions')

    def test_changed_frozen_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'inputs'; source.mkdir()
            for filename in ('manifest.json', 'dev_listings.jsonl', 'test_listings.jsonl'):
                (source/filename).write_bytes((DEFAULT_INPUT/filename).read_bytes())
            with (source/'dev_listings.jsonl').open('a') as handle:
                handle.write('\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                generate(input_dir=source, output_dir=Path(tmp)/'outputs')


if __name__ == '__main__':
    unittest.main()
