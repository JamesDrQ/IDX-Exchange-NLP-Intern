"""Actual parser/classifier/summarizer with mocked execution; no live MySQL."""
from decimal import Decimal
from unittest.mock import Mock

import pytest

from scripts.week7_search_pipeline import Week7SearchPipeline
from scripts.week8_search_pipeline import Week8SearchPipeline, MySQLExecutor, DatabaseUnavailable


@pytest.fixture(scope='module')
def analyzer():
    return Week7SearchPipeline()


@pytest.fixture
def row():
    return {'id': 1, 'L_ListingID': 'fixture-1', 'L_City': 'San Diego',
            'L_Keyword2': 3, 'LM_Dec_3': Decimal('2.5'), 'L_SystemPrice': Decimal('750000'),
            'PoolPrivateYN': '1', 'PoolFeatures': 'Private',
            'L_Remarks': 'This home has 3 bedrooms and 2.5 bathrooms. Enjoy a covered patio and renovated kitchen.'}


@pytest.mark.parametrize('query', [
    'Find homes with school ratings above 9', 'Find homes between $900k and $500k',
    'Find homes without a pool', "What's the weather tomorrow?",
    'Find homes in Irvine near the beach', 'Find homes with 3 bedrooms and 4 bedrooms',
    "Find homes in Irvine' OR 1=1 --", 'Find homes with a garage',
    'Schedule a tour in Irvine', 'Find homes under $900k and under $500k',
    'Find homes with', 'Find homes under $500000.99',
    '', None,
])
def test_rejections_never_execute_database(analyzer, query):
    executor = Mock(side_effect=AssertionError('Must not execute'))
    response = Week8SearchPipeline(analyzer=analyzer, executor=executor).search(query)
    assert response['answerable'] is False
    assert response['execution_attempted'] is False
    assert response['post_query'] is None
    executor.assert_not_called()


def test_success_with_hybrid_and_bound_sql(analyzer, row):
    executor = Mock(return_value=[row])
    response = Week8SearchPipeline(analyzer=analyzer, executor=executor).search('Find 3-bedroom homes in San Diego under $800k')
    assert response['answerable']
    assert response['pre_query']['answerable'] and response['post_query']['answerable']
    assert response['intent']['intent']
    summary = response['results'][0]['summary']
    for phrase in ('3 bedrooms', '2.5 bathrooms', '$750,000', 'San Diego', 'patio'):
        assert phrase in summary
    sql, params = executor.call_args.args
    assert 'San Diego' not in sql and '800000' not in sql
    assert 'L_SystemPrice < %s' in sql
    assert params == ['San Diego', 800000, 3, 3, 21]
    assert sql.endswith('ORDER BY L_ListingID, id LIMIT %s')


def test_low_confidence_intent_does_not_reject_supported_search(analyzer, row):
    row.update(L_City='Irvine', L_SystemPrice=450000)
    response = Week8SearchPipeline(analyzer=analyzer, executor=Mock(return_value=[row])).search('Under $500k in Irvine')
    assert response['answerable']
    assert response['filters']['price_max'] == 500000


@pytest.mark.parametrize('method', ['lead2', 'extractive', 'hybrid'])
def test_summary_methods(analyzer, row, method):
    response = Week8SearchPipeline(analyzer=analyzer, executor=Mock(return_value=[row])).search('Find homes in San Diego', method)
    assert response['answerable']
    assert response['results'][0]['summary']


@pytest.mark.parametrize(('returned', 'code'), [([], 'NO_MATCHING_LISTINGS'),
    ([{'L_ListingID': 'x', 'L_City': 'Irvine'}], 'MISSING_REQUIRED_DATA'),
    ([{'L_ListingID': 'x', 'L_City': 'Sonora', 'L_SystemPrice': 1}], 'RESULT_CONSTRAINT_MISMATCH'),
    (None, 'INVALID_RESULT_FORMAT')])
def test_distinct_post_failures(analyzer, returned, code):
    response = Week8SearchPipeline(analyzer=analyzer, executor=Mock(return_value=returned)).search('Under $500k in Irvine')
    assert response['execution_attempted']
    assert response['reason_code'] == code
    assert response['results'] == []


@pytest.mark.parametrize(('error', 'code'), [(RuntimeError('password=secret'), 'DATABASE_EXECUTION_FAILED'),
                                            (DatabaseUnavailable(), 'DATABASE_UNAVAILABLE')])
def test_database_failures_are_distinct_and_redacted(analyzer, error, code):
    response = Week8SearchPipeline(analyzer=analyzer, executor=Mock(side_effect=error)).search('Find homes')
    assert response['reason_code'] == code
    assert response['post_query'] is None
    assert 'secret' not in str(response)


def test_limit_and_more_results(analyzer, row):
    response = Week8SearchPipeline(analyzer=analyzer, executor=Mock(return_value=[row, row]), result_limit=1).search('Find homes')
    assert response['has_more']
    assert len(response['results']) == 1


def test_mysql_cursor_binding_and_cleanup(row):
    cursor = Mock(); cursor.fetchall.return_value = [row]
    connection = Mock(); connection.cursor.return_value = cursor
    connect = Mock(return_value=connection)
    executor = MySQLExecutor(settings={'database': 'real_estate'}, connect=connect)
    sql, params = 'SELECT * FROM rets_property WHERE L_City = %s', ["Irvine' OR '1'='1"]
    assert executor(sql, params) == [row]
    cursor.execute.assert_called_once_with(sql, params)
    connection.cursor.assert_called_once_with(dictionary=True)
    cursor.close.assert_called_once(); connection.close.assert_called_once()


def test_mysql_cleanup_after_execute_failure():
    cursor = Mock(); cursor.execute.side_effect = RuntimeError('failure')
    connection = Mock(); connection.cursor.return_value = cursor
    executor = MySQLExecutor(settings={}, connect=Mock(return_value=connection))
    with pytest.raises(RuntimeError):
        executor('SELECT 1', [])
    cursor.close.assert_called_once(); connection.close.assert_called_once()


def test_mysql_missing_config_does_not_connect_or_prompt(monkeypatch):
    for name in ['IDX_MYSQL_USER','MYSQL_USER','DB_USER','IDX_MYSQL_PASSWORD','MYSQL_PASSWORD','DB_PASSWORD']:
        monkeypatch.delenv(name, raising=False)
    connect = Mock()
    with pytest.raises(DatabaseUnavailable):
        MySQLExecutor(connect=connect)('SELECT 1', [])
    connect.assert_not_called()


def test_summarization_failure_is_not_database_failure(analyzer, row):
    summarizer = Mock(); summarizer.hybrid_summary.side_effect = RuntimeError('bad summary')
    response = Week8SearchPipeline(analyzer=analyzer, executor=Mock(return_value=[row]), summarizer=summarizer).search('Find homes')
    assert response['reason_code'] == 'SUMMARIZATION_FAILED'
    assert response['post_query']['answerable']
