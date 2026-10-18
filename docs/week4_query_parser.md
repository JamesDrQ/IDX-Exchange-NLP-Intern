# Week 4 Query Parser → SQL

## Objectives and deliverables

Week 4 turns a supported subset of natural-language property searches into structured filters and safe SQL conditions. The completed project includes:

- `scripts/query_parser.py`: the `PropertyFilters` schema, regex-based `QueryParser`, and `load_valid_cities()` helper.
- `scripts/schema_validator.py`: validation of filter values, ranges, and optionally configured cities.
- `scripts/sql_generator.py`: construction of a parameterized `SELECT` for `rets_property`.
- `tests/test_query_parser.py`, `tests/test_schema_validator.py`, and `tests/test_sql_generator.py`: unit and regression coverage.
- `tests/test_week4_integration.py`: an optional read-only MySQL pipeline test.
- `scripts/evaluate_week4.py` and `data/week4/query_eval.json`: evaluation over 50 manually labeled queries.
- `data/processed/valid_cities.txt`: the newline-delimited city dictionary, containing 972 non-empty city names.

## Architecture

```text
Natural-language query
        ↓
QueryParser → PropertyFilters
        ↓
SchemaValidator
        ↓
SQLGenerator → SQL text and bound parameters
        ↓
MySQL (execution is outside SQLGenerator)
```

The parser only interprets filters. The validator reports invalid fields and ranges without modifying the values. The SQL generator validates again before building the query. It does not open a database connection or execute SQL. The integration test is the separate component that can execute the generated, parameterized `SELECT`.

## Supported filters

`PropertyFilters` has optional fields for `city`, `price_min`, `price_max`, `bedrooms_min`, `bedrooms_max`, `bathrooms_min`, `bathrooms_max`, and `pool`. Unspecified filters remain `None`.

| Filter | Supported examples | Parsed meaning |
|---|---|---|
| Price | `under $700k`, `below $1.2m`, `less than $800,000`, `above 1.2 million`, `between $500k and $900k` | Inclusive minimum/maximum fields as indicated by the phrase. Prices require a monetary marker such as `$`, `k`, `m`, `thousand`, `million`, `USD`, or `dollar(s)`; comma separators are normalized. |
| Bedrooms | `3 bedrooms`, `3 bed`, `3+ beds`, `at least 3 bedrooms`, `minimum 3 beds`, `up to 4 bedrooms`, `no more than 4 beds`, `between 2 and 4 bedrooms` | Exact counts set both bounds; plus/minimum forms set a minimum; upper-bound forms set a maximum; range forms set both. |
| Bathrooms | `2 bathrooms`, `2.5 baths`, `2+ bathrooms`, `at least 2 baths`, `minimum 1.5 bathrooms`, `up to 3 bathrooms`, `no more than 2.5 baths`, `between 2 and 3.5 bathrooms` | Same bound behavior as bedrooms, with decimal counts. Recognized terms include `bath`, `baths`, `bathroom`, and `bathrooms`. |
| City | `homes in Irvine`, `properties in San Diego`, `Irvine homes` | Only names in the configured city list are recognized. Matching ignores case and uses word boundaries, and the parser returns the configured spelling. |
| Pool | `with a pool`, `has a private pool`, `pool required`, `without a pool`, `no swimming pool`, `don't want a pool` | Positive preference is `True`; negative preference is `False`; absent preference is `None`. Negative matches take priority. |

Parsing uses case-insensitive regular expressions. Multiple supported filters can be extracted from one query, for example `3+ beds, 2+ baths under $700k`.

## City dictionary

`load_valid_cities(path)` reads a newline-delimited text file, strips surrounding whitespace, and skips blank lines. The parser does not access MySQL or load a file implicitly: callers load the dictionary and inject it with `QueryParser(valid_cities=...)`. Tests can inject a small list directly. The same optional city list can be passed to `SchemaValidator` or `SQLGenerator` so validation checks city names against the configured set.

The repository dictionary is `data/processed/valid_cities.txt`. Its 972 entries are the exported distinct, non-empty values from `rets_property.L_City`.

## SQL generation and parameter safety

`SQLGenerator.generate(filters)` returns `(sql, params)`. The table is fixed to `rets_property`; the generator uses only the following column and operator mappings:

| Filter | Database column | Condition |
|---|---|---|
| `city` | `L_City` | `=` |
| `price_min`, `price_max` | `L_SystemPrice` | `>=`, `<=` |
| `bedrooms_min`, `bedrooms_max` | `L_Keyword2` | `>=`, `<=` |
| `bathrooms_min`, `bathrooms_max` | `LM_Dec_3` | `>=`, `<=` |
| `pool=True` | `PoolPrivateYN` | `= '1'` via a bound parameter |

Values are appended to the returned parameter list and represented in SQL by MySQL `%s` placeholders. User-provided values are never formatted into the SQL text; table names, columns, and operators come from fixed code mappings. With no filters, generation returns `SELECT * FROM rets_property` and an empty parameter list. SQLGenerator does not add a row limit; the integration test appends a fixed `LIMIT 10` for its read-only query.

The SQL generator rejects invalid filters with a `ValueError`. It raises `UnsupportedFilterError` for `pool=False` rather than making an unsafe assumption about how missing database values represent pool absence.

## Pool negation and data limitation

`pool=False` means the user prefers a listing without a pool. It is not a claim that a property's `PoolPrivateYN` value is false. The available data contains `'1'`, empty strings, and `NULL` for `PoolPrivateYN`; empty or missing values do not establish that a property lacks a pool. Accordingly, SQL generation supports the positive `PoolPrivateYN = '1'` condition but explicitly rejects the negative preference until the data provides a reliable representation for it.

## Tests and MySQL integration

The parser, validator, and SQL generator have unit tests for supported forms, combined filters, invalid values, boundaries, negative pool preference, and SQL injection attempts. The SQL injection test confirms that a hostile city string remains a parameter and is absent from the generated SQL text.

The optional MySQL integration test exercises the query-to-SQL path for `Find 3+ bedroom homes in Irvine under $1.2m with a pool`. It loads the city dictionary, parses and validates the filters, generates SQL, adds `LIMIT 10`, and checks the returned rows against the requested city, price ceiling, bedroom minimum, and pool flag. It executes only a `SELECT` against `idx_exchange`; it does not modify records. The test skips with a reason if credentials are unavailable, `mysql-connector-python` is not installed, or it cannot connect.

The integration test reads settings from the process environment. It recognizes `MYSQL_HOST`/`DB_HOST` and `MYSQL_PORT`/`DB_PORT` (defaulting to `127.0.0.1:3306`), and `MYSQL_USER`/`DB_USER` plus `MYSQL_PASSWORD`/`DB_PASSWORD`. The test code does not load `.env` files itself; make the settings available in the environment before running it.

Run the Week 4 unit tests:

```bash
python -m pytest -q \
  tests/test_query_parser.py \
  tests/test_schema_validator.py \
  tests/test_sql_generator.py
```

Run the optional MySQL integration test separately:

```bash
python -m pytest -q tests/test_week4_integration.py
```

## Evaluation methodology and results

`scripts/evaluate_week4.py` loads the 50 records in `data/week4/query_eval.json` and the valid-city dictionary, then compares parser output against each record's expected filters. Omitted expected fields count as `None`. A query is an exact match only when city, both price bounds, both bedroom bounds, both bathroom bounds, and pool all match. The script also reports category-level accuracy for city, price, bedrooms, bathrooms, and pool, plus every mismatch.

The recorded evaluation result is **50/50 exact matches (100%)**. The five field categories were also each 50/50 in that run. This is a curated development evaluation set: its queries were used while debugging the parser. The 100% result therefore describes performance on those cases and must not be presented as independent generalization performance.

Run the evaluation from the repository root with:

```bash
python scripts/evaluate_week4.py
```

The evaluator reads the local JSON and city dictionary only. It does not connect to MySQL.

## Limitations and future improvements

- The parser is regex-based and only supports the expressions covered by its current rules and tests. Unrecognized wording may leave a filter unset or may need additional regression coverage.
- Property type (such as `condo`) and geographic-radius wording are outside the current filter schema and evaluation scope.
- Negative pool filtering remains unsupported until the database distinguishes “no pool” from empty or missing values.
- Evaluation should be repeated on a separately authored, held-out set before drawing conclusions about generalization.
- Future work could broaden phrase coverage with reviewed examples, add an independent holdout evaluation, and define a trustworthy database representation for negative amenity filters before adding corresponding SQL conditions.
