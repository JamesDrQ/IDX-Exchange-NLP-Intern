"""Week 7 analysis -> checked Week 4 SQL -> Week 8 summaries.

Database connections are lazy: rejected queries never open one. Callers may
inject a callable executor(sql, parameters) for fixture-backed integration.
"""
from decimal import Decimal
import os
from types import SimpleNamespace

from scripts.answerability_checker import AnswerabilityChecker, normalize_query, result
from scripts.query_parser import PropertyFilters
from scripts.sql_generator import SQLGenerator, UnsupportedFilterError
from scripts.week7_search_pipeline import Week7SearchPipeline
from scripts.listing_summarizer import ListingSummarizer


class DatabaseUnavailable(RuntimeError):
    pass


class MySQLExecutor:
    """Existing mysql.connector dictionary cursor and Week 6 configuration."""
    def __init__(self, settings=None, connect=None):
        self.settings = settings
        self.connect = connect

    def __call__(self, sql, parameters):
        import mysql.connector
        from scripts.sample_week6_signals import connection_settings
        settings = self.settings
        if settings is None:
            # Avoid interactive credential prompts inside a search request.
            user = next((os.getenv(k) for k in ('IDX_MYSQL_USER', 'MYSQL_USER', 'DB_USER') if os.getenv(k)), None)
            password = next((os.getenv(k) for k in ('IDX_MYSQL_PASSWORD', 'MYSQL_PASSWORD', 'DB_PASSWORD') if os.getenv(k)), None)
            if user is None or password is None:
                raise DatabaseUnavailable('Database settings unavailable')
            settings = connection_settings(SimpleNamespace(host=None, port=None))
        connection = (self.connect or mysql.connector.connect)(**settings)
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, parameters)
            return cursor.fetchall()
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                connection.close()


class Week8SearchPipeline:
    def __init__(self, analyzer=None, checker=None, sql_generator=None, executor=None,
                 summarizer=None, result_limit=20):
        if isinstance(result_limit, bool) or not isinstance(result_limit, int) or not 1 <= result_limit <= 100:
            raise ValueError('result_limit must be an integer from 1 to 100')
        self.analyzer = analyzer or Week7SearchPipeline()
        self.checker = checker or AnswerabilityChecker(parser=self.analyzer.parser)
        self.generator = sql_generator or self.checker.generator
        self.executor = executor if executor is not None else MySQLExecutor()
        self.summarizer = summarizer or ListingSummarizer()
        self.result_limit = result_limit

    def search(self, query, summary_method='hybrid'):
        if summary_method not in ('hybrid', 'extractive', 'lead2'):
            raise ValueError('summary_method must be hybrid, extractive, or lead2')
        response = {'query': query, 'normalized_query': normalize_query(query), 'filters': {},
                    'intent': None, 'pre_query': None, 'post_query': None,
                    'execution_attempted': False, 'results': [], 'summary_method': summary_method,
                    'result_limit': self.result_limit, 'has_more': False}
        def finish(check):
            response.update({k: check[k] for k in ('answerable', 'status', 'reason_code', 'explanation')})
            return response
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            response['pre_query'] = self.checker.check_pre_query(query)
            return finish(response['pre_query'])
        try:
            analysis = self.analyzer.analyze(normalize_query(query))
            filters = PropertyFilters(**analysis['filters'])
        except (ValueError, TypeError, OverflowError):
            response['pre_query'] = result('pre_query', 'unsupported', 'PARTIALLY_UNDERSTOOD', 'The search could not be reliably parsed. Please rephrase it using supported filters.')
            return finish(response['pre_query'])
        response['filters'] = analysis['filters']
        response['intent'] = {k: analysis[k] for k in ('intent', 'confidence', 'low_confidence', 'probabilities')}
        pre = self.checker.check_pre_query(query, filters)
        response['pre_query'] = pre
        if not pre['answerable']:
            return finish(pre)
        try:
            sql, params = self.generator.generate(filters)
        except UnsupportedFilterError:
            return finish(result('sql_generation', 'unsupported', 'UNSUPPORTED_FILTER', 'The SQL search cannot enforce these filters.'))
        except ValueError:
            return finish(result('sql_generation', 'invalid', 'INVALID_FILTERS', 'The SQL generator rejected the search filters.'))
        # Preserve strict 'under/over' semantics without changing Week 4's API.
        if 'price_min' in pre['strict_price_bounds']:
            sql = sql.replace('L_SystemPrice >= %s', 'L_SystemPrice > %s')
        if 'price_max' in pre['strict_price_bounds']:
            sql = sql.replace('L_SystemPrice <= %s', 'L_SystemPrice < %s')
        # A stable bounded page; the extra row reveals whether more results exist.
        sql += ' ORDER BY L_ListingID, id LIMIT %s'
        params = [*params, self.result_limit + 1]
        response['execution_attempted'] = True
        try:
            records = self.executor(sql, params)
        except DatabaseUnavailable:
            return finish(result('execution', 'database_error', 'DATABASE_UNAVAILABLE', 'Database access is not configured. No live search results are available.'))
        except Exception:
            # Driver messages can contain credentials or SQL details; never echo them.
            return finish(result('execution', 'database_error', 'DATABASE_EXECUTION_FAILED', 'The database search failed. Please retry once database access is restored.'))
        if hasattr(records, 'to_dict') and not isinstance(records, dict):
            records = records.to_dict(orient='records')
        if isinstance(records, (list, tuple)):
            response['has_more'] = len(records) > self.result_limit
            records = records[:self.result_limit]
        post = self.checker.check_post_query(query, records, pre)
        response['post_query'] = post
        if not post['answerable']:
            return finish(post)
        outputs = []
        try:
            for row in records:
                # MySQL DECIMAL values are original numeric fields; normalize only
                # their Python representation for the unchanged Step 2 interface.
                listing = dict(row)
                for key in ('L_SystemPrice', 'L_Keyword2', 'LM_Dec_3'):
                    if isinstance(listing.get(key), Decimal):
                        listing[key] = float(listing[key])
                remarks = listing.get('L_Remarks')
                if summary_method == 'hybrid':
                    summary = self.summarizer.hybrid_summary(remarks, listing)
                elif summary_method == 'extractive':
                    evidence = self.summarizer.supported_evidence(remarks, listing)
                    hints = {k: v['value'] for k, v in evidence['fields'].items()}
                    summary = self.summarizer.extractive_summary(remarks, hints)
                else:
                    summary = self.summarizer.lead2_summary(remarks)
                outputs.append({'listing_id': str(row['L_ListingID']), 'summary': summary,
                                'summary_available': bool(summary),
                                'requested_fields': {key: listing.get(key) for key in pre['required_fields']},
                                'supported_evidence': self.summarizer.supported_evidence(remarks, listing)})
        except Exception:
            return finish(result('summarization', 'error', 'SUMMARIZATION_FAILED', 'Listings were found, but their summaries could not be generated.'))
        response['results'] = outputs
        final = result('response', 'answerable', 'RESULTS_SUPPORTED',
                       f'Found {len(outputs)} supported listing(s) in this result page.' +
                       (' More listings are available; narrow the search to see a smaller set.' if response['has_more'] else ''))
        if filters.pool:
            final['explanation'] += ' Pool matches have an explicitly recorded private pool.'
        return finish(final)
