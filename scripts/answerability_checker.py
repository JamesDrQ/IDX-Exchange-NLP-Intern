"""Conservative, auditable coverage checks for the Week 4 search language.

A parser result is not proof of coverage: every non-filler phrase must map to a
supported constraint or field request. Unknown language is rejected, not dropped.
"""
from collections.abc import Mapping
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from scripts.query_parser import QueryParser, PropertyFilters, load_valid_cities, _PRICE, _PRICE_SECOND
from scripts.schema_validator import SchemaValidator
from scripts.sql_generator import SQLGenerator, UnsupportedFilterError
from scripts.signal_extractor import _boolean

ROOT = Path(__file__).resolve().parents[1]
COLUMN = {'city': 'L_City', 'price': 'L_SystemPrice', 'bedrooms': 'L_Keyword2',
          'bathrooms': 'LM_Dec_3', 'pool': 'PoolPrivateYN'}
UNAVAILABLE = {
    'school ratings': r'\bschool (?:ratings?|scores?)\b',
    'crime statistics': r'\bcrime\b', 'walk scores': r'\bwalk ?scores?\b',
    'internet speeds': r'\b(?:internet|broadband) speeds?\b',
}
UNSUPPORTED_FILTERS = {
    'garage': r'\bgarages?\b', 'fireplace': r'\bfireplaces?\b',
    'floor area': r'\b(?:sqft|sq\.?\s*ft|square feet|square footage)\b',
    'year built': r'\b(?:built|construction|year built)\b',
    'property type': r'\b(?:condos?|condominiums?|townhomes?|townhouses?|apartments?|duplex|land|lots?)\b',
    'HOA fees': r'\bhoa\b', 'lot size': r'\b(?:acres?|acreage)\b',
    'listing status': r'\b(?:sold|pending|active|for sale|rentals?|for rent)\b',
    'community pool': r'\b(?:community|shared|association) pools?\b',
}
OPERATIONS = re.compile(r'\b(?:average|median|count|how many (?:homes|houses|properties|listings)|'
                        r'compare|cheapest|most expensive|sort|rank|top\s+\d+|'
                        r'schedule|book|tour|contact|email|call|predict|forecast|mortgage|taxes)\b', re.I)
OUTSIDE = re.compile(r'\b(?:weather|recipe|football|basketball|write code|translate|stock market)\b', re.I)
PROPERTY = re.compile(r'\b(?:real estate|homes?|houses?|properties|property|listings?|bedrooms?|bathrooms?|pool)\b', re.I)


def result(stage, status, code, explanation, **details):
    return {'stage': stage, 'answerable': status == 'answerable', 'status': status,
            'reason_code': code, 'explanation': explanation, **details}


def normalize_query(query):
    if not isinstance(query, str):
        return query
    return re.sub(r'(\d+(?:\.\d+)?)\s*[-\u2010-\u2015]\s*(bedrooms?|beds?|bathrooms?|baths?)\b',
                  r'\1 \2', query, flags=re.I)


def numeric(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value).strip())
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().casefold() not in {'', 'null', 'none', 'nan', 'n/a', 'unknown', 'other'}
    if isinstance(value, (float, Decimal)):
        return numeric(value) is not None
    return True


class AnswerabilityChecker:
    def __init__(self, parser=None, schema_validator=None, sql_generator=None, valid_cities=None):
        self.cities = list(valid_cities) if valid_cities is not None else load_valid_cities(ROOT / 'data/processed/valid_cities.txt')
        self.parser = parser or QueryParser(valid_cities=self.cities)
        self.validator = schema_validator or SchemaValidator(valid_cities=self.cities)
        self.generator = sql_generator or SQLGenerator(valid_cities=self.cities)

    def check_pre_query(self, query, filters=None):
        base = {'filters': {}, 'required_fields': [], 'unparsed_fragments': [], 'strict_price_bounds': []}
        def reject(status, code, explanation, **extra):
            return result('pre_query', status, code, explanation, **(base | extra))
        if not isinstance(query, str) or not query.strip():
            return reject('invalid', 'INVALID_QUERY', 'Enter a non-empty property search.')
        text = normalize_query(query).strip()
        base['normalized_query'] = text
        if len(text) > 2000:
            return reject('invalid', 'INVALID_QUERY', 'Please shorten the search to 2,000 characters or fewer.')
        parsed = filters if filters is not None else self.parser.parse(text)
        if not isinstance(parsed, PropertyFilters):
            return reject('invalid', 'INVALID_FILTERS', 'The query parser did not produce valid property filters.')
        base['filters'] = asdict(parsed)
        if OUTSIDE.search(text):
            return reject('unsupported', 'OUT_OF_DOMAIN', 'This search supports property listings, not that topic.')
        if not PROPERTY.search(text) and not any(v is not None for v in asdict(parsed).values()):
            return reject('unsupported', 'OUT_OF_DOMAIN', 'Please ask for property listings using a city, price, bedrooms, or bathrooms.')
        for label, pattern in UNAVAILABLE.items():
            if re.search(pattern, text, re.I):
                return reject('unsupported', 'UNSUPPORTED_ATTRIBUTE', f'The dataset does not provide {label}. That requirement cannot be checked.')
        if OPERATIONS.search(text):
            return reject('unsupported', 'UNSUPPORTED_OPERATION', 'This pipeline retrieves listings; it does not perform comparisons, aggregates, rankings, predictions, or contact/booking actions.')
        errors = self.validator.validate(parsed)
        if errors:
            return reject('invalid', 'INVALID_FILTERS', 'Invalid search filters: ' + '; '.join(errors), validation_errors=errors)
        for label, pattern in UNSUPPORTED_FILTERS.items():
            if re.search(pattern, text, re.I):
                return reject('unsupported', 'UNSUPPORTED_FILTER', f'The current parser and SQL search cannot enforce the requested {label} constraint. It will not be ignored.')
        if parsed.pool is False:
            return reject('unsupported', 'UNSUPPORTED_NEGATIVE_POOL', 'The dataset cannot reliably prove that a property has no pool: blank or NULL pool values mean unknown, not no pool.')
        if re.search(r'\b(?:in|with|without|between|under|over|and|or)\s*[?.!]*$', text, re.I):
            return reject('unsupported', 'PARTIALLY_UNDERSTOOD', 'The search ends with an unfinished constraint. Please supply its value.')

        remaining = list(text)
        constraints = []
        def consume(start, end):
            remaining[start:end] = ' ' * (end-start)
        # Explicit field requests are separate from filtering constraints.
        requested = set()
        projection = re.match(r'\s*(?:show|list|what are|tell me)\s+(?:the\s+)?'
                              r'(?P<fields>(?:prices?|bedrooms?|bathrooms?|cities|locations?)'
                              r'(?:\s*(?:,|and)\s*(?:prices?|bedrooms?|bathrooms?|cities|locations?))*)'
                              r'\s+(?:of|for)\s+', text, re.I)
        if projection:
            for token in re.findall(r'prices?|bedrooms?|bathrooms?|cities|locations?', projection['fields'], re.I):
                token = token.lower()
                requested.add('price' if token.startswith('price') else 'bedrooms' if token.startswith('bedroom') else 'bathrooms' if token.startswith('bathroom') else 'city')
            consume(*projection.span())
        # Longest city first; never consume a shorter name inside a longer one.
        cities_found = []
        for city in sorted(self.cities, key=len, reverse=True):
            pattern = r'(?<!\w)' + r'\s+'.join(re.escape(x) for x in city.split()) + r'(?!\w)'
            for match in re.finditer(pattern, ''.join(remaining), re.I):
                cities_found.append(city); consume(*match.span())
        if len({c.casefold() for c in cities_found}) > 1:
            return reject('unsupported', 'UNSUPPORTED_OPERATION', 'Only one city per search is supported; multiple cities will not be silently dropped.')
        if cities_found:
            constraints.append(PropertyFilters(city=cities_found[0]))

        # Match the existing parser's supported numeric constructions, then
        # independently parse each consumed span to verify the whole-query result.
        patterns = []
        for term, amount in ((r'(?:bedrooms?|beds?)', r'\d+'), (r'(?:bathrooms?|baths?)', r'\d+(?:\.\d+)?')):
            patterns += [rf'\bbetween\s+{amount}\s+and\s+{amount}\s+{term}\b',
                         rf'\b(?:at\s+least|minimum(?:\s+of)?|up\s+to|no\s+more\s+than)\s+{amount}\s+{term}\b',
                         rf'\b{amount}(?:\s*\+)?\s+{term}\b']
        patterns += [rf'\bbetween\s+{_PRICE}\s+and\s+{_PRICE_SECOND}',
                     rf'\b(?:under|below|less\s+than|over|above)\s+{_PRICE}',
                     r'\b(?:with|has)\s+(?:a\s+)?(?:(?:private|swimming)\s+)?pools?\b',
                     r'\bpool\s+required\b']
        for pattern in patterns:
            for match in re.finditer(pattern, ''.join(remaining), re.I):
                fragment = text[match.start():match.end()]
                part = self.parser.parse(fragment)
                if not any(v is not None for v in asdict(part).values()):
                    continue
                # Week 4 converts prices to integers. Do not silently round a
                # fractional-dollar boundary during that conversion.
                groups = match.groupdict()
                for suffix in ('', '2'):
                    amount = groups.get('amount' + suffix)
                    if amount is not None:
                        unit = (groups.get('unit' + suffix) or '').casefold()
                        multiplier = {'k': 1000, 'thousand': 1000, 'm': 1000000, 'million': 1000000}.get(unit, 1)
                        exact = Decimal(amount.replace(',', '')) * multiplier
                        if exact != exact.to_integral_value():
                            return reject('unsupported', 'PARTIALLY_UNDERSTOOD', 'The current price parser supports whole-dollar boundaries only; fractional-dollar limits will not be rounded silently.')
                constraints.append(part); consume(*match.span())
                if part.price_max is not None and re.match(r'(?:under|below|less\s+than)\b', fragment, re.I):
                    base['strict_price_bounds'].append('price_max')
                if part.price_min is not None and re.match(r'(?:over|above)\b', fragment, re.I):
                    base['strict_price_bounds'].append('price_min')
        merged = PropertyFilters()
        for part in constraints:
            for name, value in asdict(part).items():
                if value is None:
                    continue
                old = getattr(merged, name)
                if name.endswith('_min'):
                    value = max(old, value) if old is not None else value
                elif name.endswith('_max'):
                    value = min(old, value) if old is not None else value
                setattr(merged, name, value)
        errors = self.validator.validate(merged)
        if errors:
            return reject('invalid', 'INVALID_FILTERS', 'The requested constraints conflict: ' + '; '.join(errors), validation_errors=errors)
        if (merged.price_min is not None and merged.price_min == merged.price_max and base['strict_price_bounds']):
            return reject('invalid', 'INVALID_FILTERS', 'The strict price bounds leave no possible price.')
        if asdict(merged) != asdict(parsed):
            return reject('unsupported', 'PARTIALLY_UNDERSTOOD', 'The parser did not preserve every requested constraint. Please use one range per field.', coverage_filters=asdict(merged))
        residue = ''.join(remaining)
        # Only harmless search framing is ignorable; not/except/or/near/only,
        # numbers, quoted strings and unknown adjectives are deliberately kept.
        residue = re.sub(r'\b(?:please|find|show|me|list|search|for|homes?|houses?|properties|property|listings?|real estate|in|and|with|a|an|the|all)\b', ' ', residue, flags=re.I)
        residue = re.sub(r'[,?.!\s]+', ' ', residue).strip()
        if residue:
            return reject('unsupported', 'PARTIALLY_UNDERSTOOD', f'I could not reliably interpret this part of the search: {residue}. Please rephrase it using supported filters.', unparsed_fragments=[residue])
        try:
            self.generator.generate(parsed)
        except UnsupportedFilterError:
            return reject('unsupported', 'UNSUPPORTED_FILTER', 'The requested filters cannot be represented by the current SQL search.')
        required = {'L_ListingID'} | {COLUMN[name] for name in requested}
        for name, value in asdict(parsed).items():
            if value is not None:
                required.add(COLUMN[name.removesuffix('_min').removesuffix('_max')])
        base['required_fields'] = sorted(required)
        explanation = 'The requested listing search is supported.'
        if parsed.pool:
            explanation += ' Pool searches use explicitly recorded private pools; community-only pool searches are not supported.'
        base['strict_price_bounds'] = sorted(set(base['strict_price_bounds']))
        return result('pre_query', 'answerable', 'QUERY_SUPPORTED', explanation, **base)

    def check_post_query(self, query, results, pre_result=None):
        pre = pre_result if pre_result is not None else self.check_pre_query(query)
        if not pre['answerable']:
            return result('post_query', 'unsupported', 'PRE_QUERY_REJECTED', 'The query did not pass pre-query validation.')
        if hasattr(results, 'to_dict') and not isinstance(results, Mapping):
            results = results.to_dict(orient='records')
        if not isinstance(results, (list, tuple)) or any(not isinstance(row, Mapping) for row in results):
            return result('post_query', 'error', 'INVALID_RESULT_FORMAT', 'The search returned records in an unexpected format.')
        if not results:
            return result('post_query', 'no_results', 'NO_MATCHING_LISTINGS', 'No listings match your criteria.', result_count=0)
        missing, unsupported = [], []
        filters = pre['filters']
        for index, row in enumerate(results):
            absent = []
            for column in pre['required_fields']:
                value = row.get(column)
                if not present(value):
                    absent.append(column)
                elif column in ('L_SystemPrice', 'L_Keyword2', 'LM_Dec_3'):
                    n = numeric(value)
                    if n is None or n < 0 or (column == 'L_SystemPrice' and n == 0) or (column == 'L_Keyword2' and n != n.to_integral_value()):
                        absent.append(column)
                elif column == 'PoolPrivateYN' and _boolean(value) is None:
                    absent.append(column)
            if not any(present(row.get(c)) for c in ('L_Remarks', 'L_City', 'L_SystemPrice', 'L_Keyword2', 'LM_Dec_3')):
                absent.append('meaningful_listing_data')
            if absent:
                missing.append({'row_index': index, 'listing_id': row.get('L_ListingID'), 'fields': sorted(set(absent))})
                continue
            failed = []
            for name, value in filters.items():
                if value is None:
                    continue
                column = COLUMN[name.removesuffix('_min').removesuffix('_max')]
                observed = row[column]
                if name == 'city':
                    matches = isinstance(observed, str) and observed.strip().casefold() == value.strip().casefold()
                elif name == 'pool':
                    matches = _boolean(observed) is True and str(row.get('PoolFeatures', '')).strip().casefold() != 'none'
                else:
                    observed, target = numeric(observed), numeric(value)
                    strict = name in pre['strict_price_bounds']
                    matches = (observed > target if strict else observed >= target) if name.endswith('_min') else (observed < target if strict else observed <= target)
                if not matches:
                    failed.append(name)
            if failed:
                unsupported.append({'row_index': index, 'listing_id': row.get('L_ListingID'), 'constraints': failed})
        if missing:
            return result('post_query', 'missing_data', 'MISSING_REQUIRED_DATA', 'Matching records were returned, but required fields are missing or unusable. A complete answer cannot be supported.', incomplete_records=missing, result_count=len(results))
        if unsupported:
            return result('post_query', 'insufficient_evidence', 'RESULT_CONSTRAINT_MISMATCH', 'Returned records do not consistently support the requested filters. Please retry or check the source data.', inconsistent_records=unsupported, result_count=len(results))
        return result('post_query', 'answerable', 'RESULTS_SUPPORTED', 'Matching listings contain the information required for this search.', result_count=len(results))
