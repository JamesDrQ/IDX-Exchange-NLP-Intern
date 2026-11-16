"""Pre/post checks exercise actual Week 4 interfaces, without database access."""
from decimal import Decimal

import pandas as pd
import pytest

from scripts.answerability_checker import AnswerabilityChecker
from scripts.query_parser import PropertyFilters


@pytest.fixture
def checker():
    return AnswerabilityChecker(valid_cities=['Irvine', 'San Diego', 'Sonora'])


@pytest.mark.parametrize('query', [
    'Find 3-bedroom homes in San Diego under $800k', 'Under $500k in Irvine',
    'Find homes between $500k and $900k', 'Find homes with at least 3 bedrooms',
    'Find homes with 2.5 bathrooms', 'Find homes in Irvine with a private pool',
    'Show prices and bathrooms for homes in Irvine', 'Find homes',
])
def test_valid_queries(checker, query):
    check = checker.check_pre_query(query)
    assert check['answerable'], check


@pytest.mark.parametrize(('query', 'reason'), [
    (None, 'INVALID_QUERY'), (' ', 'INVALID_QUERY'), ([], 'INVALID_QUERY'),
    ("What's the weather tomorrow?", 'OUT_OF_DOMAIN'),
    ('Weather in Irvine', 'OUT_OF_DOMAIN'),
    ('Find homes with school ratings above 9', 'UNSUPPORTED_ATTRIBUTE'),
    ('Find homes with low crime', 'UNSUPPORTED_ATTRIBUTE'),
    ('Find homes between $900k and $500k', 'INVALID_FILTERS'),
    ('Find homes with at least 4 bedrooms and up to 2 bedrooms', 'INVALID_FILTERS'),
    ('Find homes with 3 bedrooms and 4 bedrooms', 'INVALID_FILTERS'),
    ('Find homes over $500k under $500k', 'INVALID_FILTERS'),
    ('Find properties without a pool', 'UNSUPPORTED_NEGATIVE_POOL'),
    ('Find homes in Irvine near the beach', 'PARTIALLY_UNDERSTOOD'),
    ('Find homes in Atlantis', 'PARTIALLY_UNDERSTOOD'),
    ('Find homes under $900k and under $500k', 'PARTIALLY_UNDERSTOOD'),
    ('Find homes in Irvine or San Diego', 'UNSUPPORTED_OPERATION'),
    ('Find homes with a garage', 'UNSUPPORTED_FILTER'),
    ('Find homes with a community pool', 'UNSUPPORTED_FILTER'),
    ('Find homes with 2000 sqft', 'UNSUPPORTED_FILTER'),
    ('How many homes are in Irvine?', 'UNSUPPORTED_OPERATION'),
    ('Schedule a tour of homes in Irvine', 'UNSUPPORTED_OPERATION'),
    ('Find homes in Irvine not San Diego', 'UNSUPPORTED_OPERATION'),
    ('Find homes in Irvine excluding pools', 'PARTIALLY_UNDERSTOOD'),
    ("Find homes in Irvine' OR 1=1 --", 'PARTIALLY_UNDERSTOOD'),
    ('Find homes with 3 bedrooms under 500000', 'PARTIALLY_UNDERSTOOD'),
    ('Find homes with', 'PARTIALLY_UNDERSTOOD'),
    ('Find homes in', 'PARTIALLY_UNDERSTOOD'),
    ('Find homes under $500000.99', 'PARTIALLY_UNDERSTOOD'),
])
def test_rejected_queries(checker, query, reason):
    check = checker.check_pre_query(query)
    assert check['answerable'] is False
    assert check['reason_code'] == reason
    assert check['explanation']


def test_supplied_filters_cannot_bypass_coverage(checker):
    check = checker.check_pre_query('Find 3 bedroom homes', PropertyFilters())
    assert check['reason_code'] == 'PARTIALLY_UNDERSTOOD'
    check = checker.check_pre_query('Find homes', PropertyFilters(price_min=-1))
    assert check['reason_code'] == 'INVALID_FILTERS'


def test_empty_results(checker):
    assert checker.check_post_query('Find homes', [])['reason_code'] == 'NO_MATCHING_LISTINGS'
    assert checker.check_post_query('Find homes', pd.DataFrame())['reason_code'] == 'NO_MATCHING_LISTINGS'


@pytest.mark.parametrize('value', [None, '', float('nan'), Decimal('NaN'), 'unknown', -1])
def test_missing_requested_fields(checker, value):
    row = {'L_ListingID': '1', 'L_City': 'Irvine', 'L_SystemPrice': 400000, 'LM_Dec_3': value}
    check = checker.check_post_query('Show bathrooms for homes in Irvine', [row])
    assert check['reason_code'] == 'MISSING_REQUIRED_DATA'
    assert 'LM_Dec_3' in check['incomplete_records'][0]['fields']


def test_nonrequested_missing_fields_are_allowed(checker):
    rows = [{'L_ListingID': '1', 'L_City': 'Irvine', 'L_SystemPrice': 400000}]
    assert checker.check_post_query('Under $500k in Irvine', rows)['answerable']
    assert checker.check_post_query('Under $500k in Irvine', pd.DataFrame(rows))['answerable']
    assert checker.check_post_query('Find homes', [{'L_ListingID': '1'}])['reason_code'] == 'MISSING_REQUIRED_DATA'


def test_mixed_complete_and_incomplete_is_not_silent_partial_success(checker):
    rows = [{'L_ListingID': '1', 'L_SystemPrice': 1}, {'L_ListingID': '2', 'L_Remarks': 'Patio.'}]
    check = checker.check_post_query('Show prices for homes', rows)
    assert not check['answerable']
    assert check['incomplete_records'][0]['listing_id'] == '2'


@pytest.mark.parametrize('row', [
    {'L_ListingID': '1', 'L_City': 'San Diego', 'L_SystemPrice': 400000},
    {'L_ListingID': '1', 'L_City': 'Irvine', 'L_SystemPrice': 500000},
    {'L_ListingID': '1', 'L_City': 'Irvine', 'L_SystemPrice': 600000},
])
def test_returned_evidence_must_match_filters(checker, row):
    assert checker.check_post_query('Under $500k in Irvine', [row])['reason_code'] == 'RESULT_CONSTRAINT_MISMATCH'


def test_pool_evidence_and_missing_flags(checker):
    query = 'Find homes with a private pool'
    for value, code in [(None, 'MISSING_REQUIRED_DATA'), ('', 'MISSING_REQUIRED_DATA'),
                        ('0', 'RESULT_CONSTRAINT_MISMATCH'), ('1', 'RESULTS_SUPPORTED')]:
        row = {'L_ListingID': '1', 'L_City': 'Irvine', 'PoolPrivateYN': value}
        assert checker.check_post_query(query, [row])['reason_code'] == code
    row['PoolFeatures'] = 'None'
    assert checker.check_post_query(query, [row])['reason_code'] == 'RESULT_CONSTRAINT_MISMATCH'


def test_bad_result_format_and_rejected_precheck(checker):
    assert checker.check_post_query('Find homes', None)['reason_code'] == 'INVALID_RESULT_FORMAT'
    assert checker.check_post_query('Find homes', [1])['reason_code'] == 'INVALID_RESULT_FORMAT'
    assert checker.check_post_query('Find homes without a pool', [])['reason_code'] == 'PRE_QUERY_REJECTED'
