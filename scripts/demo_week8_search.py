"""Reproducible OFFLINE demonstration: SQLite fixtures, not live MySQL.

Loads original fields from the 70 development listings only and adds two clearly
synthetic records to exercise complete bed/bath searches. Never uses references.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from scripts.week8_search_pipeline import Week8SearchPipeline

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/annotations/week8'
OUTPUT = ROOT / 'data/processed/week8_search_demo'
COLUMNS = ['L_ListingID', 'L_City', 'L_SystemPrice', 'L_Keyword2', 'LM_Dec_3',
           'L_Remarks', 'PoolPrivateYN', 'PoolFeatures', 'GarageYN', 'FireplaceYN']
QUERIES = [
    'Find 3-bedroom homes in San Diego under $800k',
    'Under $500k in Irvine',
    'Find homes in Sonora under $1m',
    'Show prices and bathrooms for homes in Sonora',
    'Find homes in Irvine under $1',
    'Find homes with school ratings above 9',
    'Find homes between $900k and $500k',
    'Find properties without a pool',
    "What's the weather tomorrow?",
    'Find homes in Irvine near the beach',
    'Find homes with a garage',
    'How many homes are in Irvine?',
    'Find homes in Irvine with a private pool',
    "Find homes in Irvine' OR 1=1 --",
    'Find homes in Irvine',  # Forced executor failure for this example only.
]


class SQLiteFixtureExecutor:
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.calls = 0
        self.provenance = {}
        self.connection.execute('CREATE TABLE rets_property (id INTEGER PRIMARY KEY, '
                                'L_ListingID TEXT, L_City TEXT, L_SystemPrice REAL, '
                                'L_Keyword2 INTEGER, LM_Dec_3 REAL, L_Remarks TEXT, '
                                'PoolPrivateYN TEXT, PoolFeatures TEXT, GarageYN INTEGER, FireplaceYN TEXT)')
        self.insert_sql = 'INSERT INTO rets_property (' + ','.join(COLUMNS) + ') VALUES (' + ','.join('?' for _ in COLUMNS) + ')'
        for line in (INPUT / 'dev_listings.jsonl').read_text().splitlines():
            row = json.loads(line)
            original = dict(row['source_fields'], L_ListingID=row['listing_id'], L_Remarks=row['remarks'])
            self.add(original, 'original_development_export_fields')
        self.add({'L_ListingID': 'SYNTHETIC-SD-001', 'L_City': 'San Diego',
                  'L_SystemPrice': 750000, 'L_Keyword2': 3, 'LM_Dec_3': 2,
                  'L_Remarks': 'This home has 3 bedrooms and 2 bathrooms. A covered patio and renovated kitchen are included.',
                  'PoolPrivateYN': '0'}, 'synthetic_test_fixture_not_a_real_listing')
        self.add({'L_ListingID': 'SYNTHETIC-IRV-001', 'L_City': 'Irvine',
                  'L_SystemPrice': 450000, 'L_Keyword2': 2, 'LM_Dec_3': 2,
                  'L_Remarks': 'This home has 2 bedrooms and 2 bathrooms. Enjoy a private pool and covered patio.',
                  'PoolPrivateYN': '1', 'PoolFeatures': 'Private'}, 'synthetic_test_fixture_not_a_real_listing')

    def add(self, row, provenance):
        self.connection.execute(self.insert_sql, [row.get(key) for key in COLUMNS])
        self.provenance[row['L_ListingID']] = provenance

    def __call__(self, sql, params):
        self.calls += 1
        return [dict(row) for row in self.connection.execute(sql.replace('%s', '?'), params).fetchall()]

    def close(self):
        self.connection.close()


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in INPUT.iterdir() if p.is_file()}


def run_demo(output=OUTPUT):
    output = Path(output)
    annotation_root = (ROOT / 'data/annotations').resolve()
    if output.resolve() == annotation_root or annotation_root in output.resolve().parents:
        raise ValueError('Demo output must be outside the Week 8 annotations')
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite {output}')
    before = hashes()
    fixture = SQLiteFixtureExecutor()
    pipeline = Week8SearchPipeline(executor=fixture, result_limit=3)
    examples = []
    try:
        for index, query in enumerate(QUERIES):
            calls_before = fixture.calls
            if index == len(QUERIES)-1:
                def fail(sql, params):
                    raise RuntimeError('Simulated database outage')
                pipeline.executor = fail
            response = pipeline.search(query)
            examples.append({'example': index+1, 'execution_mode': 'OFFLINE_SQLITE_FIXTURE',
                             'simulated_database_failure': index == len(QUERIES)-1,
                             'fixture_sql_calls': fixture.calls-calls_before,
                             'result_provenance': {r['listing_id']: fixture.provenance[r['listing_id']] for r in response['results']},
                             'response': response})
    finally:
        fixture.close()
    assert hashes() == before, 'Input artifacts changed'
    output.mkdir(parents=True)
    (output/'examples.json').write_text(json.dumps(examples, indent=2, ensure_ascii=False)+'\n')
    report = ['# Week 8 Step 3 offline demonstration', '',
              '**Not live MySQL verification.** SQL ran against an in-memory SQLite fixture using bound parameters. '
              'The fixture contains 70 original development exports and two labeled synthetic listings. '
              'No extracted bedroom/bathroom guesses were inserted into missing source fields. '
              'Example 15 forces an executor failure. Test listings and human references were not used.', '']
    for example in examples:
        r = example['response']
        report += [f"## {example['example']}. {r['query']}", '',
                   '**Parsed filters:** `' + json.dumps(r['filters']) + '`', '',
                   '**Pre-query:** ' + r['pre_query']['reason_code'] + ' — ' + r['pre_query']['explanation'], '',
                   '**Post-query:** ' + (r['post_query']['reason_code'] + ' — ' + r['post_query']['explanation'] if r['post_query'] else 'Not run.'), '',
                   '**Final:** ' + r['reason_code'] + ' — ' + r['explanation'], '']
        for listing in r['results']:
            report += [f"- {listing['listing_id']} ({example['result_provenance'][listing['listing_id']]}): {listing['summary']}"]
        report += ['']
    (output/'examples.md').write_text('\n'.join(report))
    metadata = {'execution_mode': 'offline_sqlite_fixture_not_live_mysql', 'examples': len(examples),
                'input_hashes': before, 'code_hashes': {name: hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()
                    for name in ('answerability_checker.py', 'week8_search_pipeline.py', 'demo_week8_search.py')},
                'human_references': 'untouched', 'rouge': 'not_calculated'}
    (output/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    for example in run_demo(args.output):
        print(example['example'], example['response']['reason_code'], example['response']['query'])


if __name__ == '__main__':
    main()
