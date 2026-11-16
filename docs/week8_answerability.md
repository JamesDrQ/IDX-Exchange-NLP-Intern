# Week 8 Step 3: answerability and integrated search

> Submission status: see `week8_final_report.md` and `week8_submission_audit.md` for current results and files. Held-out evaluation is complete (Hybrid 0.368893, below 0.4). The current reviewed references and accepted AI replacement ratings are in `data/annotations/week8_review/`. Earlier preparation commands, pending-work statements and test counts below describe their original project stage; do not recreate the freeze or regenerate test predictions.

Implemented a deterministic answerability checker and a wrapper around the
existing Week 7 analysis pipeline. The wrapper uses Week 4 parsing, schema
validation and SQL generation, the existing MySQL connector/configuration
pattern, and the unchanged Week 8 Step 2 summarizer.

## Files

- `scripts/answerability_checker.py`: pre-query constraint coverage and post-query
  evidence validation.
- `scripts/week8_search_pipeline.py`: integrated search and lazy MySQL executor.
- `scripts/demo_week8_search.py`: 15 reproducible offline demonstrations.
- `tests/test_week8_answerability.py`: domain, capability, coverage, filter and
  returned-data checks.
- `tests/test_week8_search_pipeline.py`: pipeline, binding, cleanup, rejection,
  error handling and summary integration tests.
- `data/processed/week8_search_demo/`: `examples.md`, full `examples.json`, and
  provenance/code/input hashes in `manifest.json`.

No Weeks 3–7 module or Step 2 summarization module was changed. The 70/30 split,
listing artifacts, reference CSVs, and previously generated Step 2 outputs remain
unchanged. No references or ROUGE scores were generated.

## Architecture

```text
Original query
  -> normalize numeric bedroom/bathroom hyphens (3-bedroom -> 3 bedroom)
  -> Week7SearchPipeline.analyze (Week 4 parser + actual Week 7 intent model)
  -> AnswerabilityChecker.check_pre_query
  -> SQLGenerator.generate (bound values)
  -> strict price operators, stable ordering, bounded result page
  -> lazy MySQL dictionary-cursor execution
  -> AnswerabilityChecker.check_post_query
  -> ListingSummarizer.hybrid_summary (default)
  -> structured response with reasons, summaries and supporting evidence
```

Intent and confidence are returned as context; a classifier label is not treated
as proof of supported operations. In particular, the actual model labels
“Under $500k in Irvine” as low-confidence research, but its supported listing
constraints pass validation.

The wrapper defaults to 20 results (configurable from 1–100), requests one extra
row to set `has_more`, and uses `ORDER BY L_ListingID, id`. This is a result page,
not a total-count answer. Narrowing the search is supported; pagination cursors
are not implemented.

Values and the SQL limit are bound parameters. Under/below/less-than and
over/above produce strict `<` and `>` price operators in the wrapper; Week 4's
existing inclusive SQL generator remains unchanged. Between ranges remain
inclusive. Decimal MySQL fields are converted to ordinary numeric Python values
only at the unchanged summarizer's input boundary.

## Pre-query logic

`check_pre_query(query, filters=None)` returns a dictionary containing `stage`,
`answerable`, `status`, `reason_code`, `explanation`, parsed `filters`,
`required_fields`, `unparsed_fragments`, `normalized_query` and
`strict_price_bounds` where applicable. It never opens a database connection.

The checker recognizes supported listing-search framing, known cities, numeric
price/bedroom/bathroom constraints, private-pool predicates, and explicit field
requests such as “Show prices and bathrooms for homes in Irvine.” It also uses
known unavailable attributes and unsupported-operation checks. It does not
require a property keyword when valid filters establish the search context.

A second coverage pass identifies complete supported constraint spans, parses
those spans with the actual Week 4 parser, combines their requirements, and
compares them with the whole-query parse. Only harmless framing words and
punctuation can remain. Unknown phrases, unconsumed numbers, exclusions, unknown
locations and SQL-like tails are rejected rather than silently discarded.
Repeated conflicting constraints are invalid; repeated constraints that the
parser fails to preserve are partially understood. Unfinished constraints and
fractional-dollar limits that the parser would round are rejected.

The schema validator's real API is `validate(filters) -> list[str]`. SQL
capability is also checked using the real generator. Negative pool searches are
rejected because NULL/blank flags are not evidence of absence. Generic positive
pool requests retain Week 4's private-pool convention, explicitly disclosed in
pre-query and successful final explanations. Community-only filters are rejected.

A curated capability catalog distinguishes absent data (for example school
ratings) from fields present in the dataset but unsupported by the current
parser/SQL mappings (for example garage, year built and floor area). Unknown
attributes outside that catalog fall back to an explicit partial-understanding
response rather than an unverified claim that the database lacks them.

## Post-query logic

`check_post_query(query, results, pre_result=None)` accepts lists of dictionary
records or a pandas DataFrame. It checks:

1. Empty results separately from malformed results.
2. Listing identity and meaningful listing information.
3. Every field requested for display or needed to substantiate a filter.
4. Null, blank, sentinel, nonfinite, negative or invalid numeric/boolean values.
5. Whether each returned row actually satisfies the city, numeric and private-pool
   predicates, including strict price boundaries.

Only fields needed by this query are mandatory; an unrequested missing bathroom
count does not invalidate a price/location search. A page with some incomplete
rows is explicitly reported as missing data, not silently reduced to complete
rows. Requested answers use original returned fields; unverified Week 6 guesses
cannot fill missing required columns. Pool flags inconsistent with an explicit
`PoolFeatures=None` sentinel are not accepted as supporting evidence.

## Reason codes

| Code | Meaning |
| --- | --- |
| `QUERY_SUPPORTED` | Pre-query validation passed. |
| `INVALID_QUERY` | Empty, wrong-type or oversized input. |
| `OUT_OF_DOMAIN` | Request is outside property listing search. |
| `UNSUPPORTED_ATTRIBUTE` | Requested data is not provided by the known schema. |
| `UNSUPPORTED_FILTER` | Existing search cannot enforce the requested attribute/filter. |
| `UNSUPPORTED_NEGATIVE_POOL` | Source flags cannot prove absence of a pool. |
| `UNSUPPORTED_OPERATION` | Aggregation, ranking, multi-city search, comparison, prediction or contact/booking action is unsupported. |
| `PARTIALLY_UNDERSTOOD` | Important language or constraints were not fully represented. |
| `INVALID_FILTERS` | Invalid values or contradictory constraints. |
| `NO_MATCHING_LISTINGS` | Supported search returned no rows. |
| `MISSING_REQUIRED_DATA` | Returned rows lack usable requested/constraint fields. |
| `RESULT_CONSTRAINT_MISMATCH` | Returned evidence does not support requested filters. |
| `INVALID_RESULT_FORMAT` | Executor returned an unexpected record structure. |
| `PRE_QUERY_REJECTED` | A post-check was attempted for a rejected query. |
| `DATABASE_UNAVAILABLE` | MySQL credentials/configuration are unavailable. |
| `DATABASE_EXECUTION_FAILED` | Connection/query execution failed. |
| `SUMMARIZATION_FAILED` | Records passed validation, but summary generation failed. |
| `RESULTS_SUPPORTED` | Returned listings support the requested search. |

Database driver exception text is not returned to users because it may contain
connection details. Database and summarization failures remain separate from
query rejection and missing data. `execution_attempted` means the executor was
called, not that a connection or SQL execution necessarily succeeded.

## Usage and database configuration

```python
from scripts.week8_search_pipeline import Week8SearchPipeline

pipeline = Week8SearchPipeline()
response = pipeline.search("Find 3-bedroom homes in San Diego under $800k")
```

For baseline/extractive comparisons, pass `summary_method="lead2"` or
`summary_method="extractive"`. Hybrid is the default.

The lazy `MySQLExecutor` uses the existing Week 6 `connection_settings` helper
and `mysql.connector` dictionary-cursor interface. Environment aliases are
`IDX_MYSQL_*`, `MYSQL_*`, and `DB_*` for user/password/host/port. The Week 6
configuration selects database `real_estate`. The wrapper does not import the
legacy `data_loading.py`, which opens a database connection at import time.

No interactive credential prompt occurs inside a search request. Applications
can inject `MySQLExecutor(settings=...)` to supply an explicit connector settings
mapping, including another database or an intentionally blank password, or
inject a callable `executor(sql, params)` for fixtures. The wrapper does not
automatically load `.env` or expose credentials in its response.

## Test and demonstration results

Executed in the existing `idx-nlp` environment:

```bash
conda run -n idx-nlp python -m pytest -q tests/test_week3*.py tests/test_query_parser.py tests/test_schema_validator.py tests/test_sql_generator.py tests/test_week4_integration.py tests/test_week5.py tests/test_week6*.py tests/test_week7*.py tests/test_week8*.py
```

**310 passed, 1 skipped**: 81 new answerability/integration cases plus 229 existing
cases passed. The existing live Week 4 MySQL integration test skipped because
its expected credentials were not exported in the process environment.

A separate read-only connection probe using the local `.env` settings failed
with MySQL connection error 2003. No successful live MySQL query is claimed.
The fixture suite tests parameter binding and resource cleanup using mock MySQL
connections; the demonstration executes generated SQL against local SQLite.
These are not substitutes for live MySQL verification.

To reproduce the 15-example demonstration:

```bash
conda run -n idx-nlp python -m scripts.demo_week8_search --output /tmp/week8-search-new-demo
```

Use a fresh output directory; existing directories and annotation-directory
outputs are refused. Examples include:

- Complete San Diego bed/price search and shorthand Irvine price search, using
  explicitly labeled synthetic fixtures with authoritative-looking test fields.
- A Sonora search using original development export fields and real source text.
- A Sonora bathroom-field request rejected after execution because the original
  export has no structured bathroom count.
- No matching results, unavailable school ratings, reversed price ranges,
  unsupported negative pools, weather, unparsed beach proximity, unsupported
  garage filtering, aggregate requests, supported private pools, injection-like
  tails, and a deliberately simulated database outage.

`examples.md` shows all 15 queries, parsed filters, pre-query outcomes,
post-query outcomes if reached, and final summaries/explanations. `examples.json`
also contains intent, source provenance, evidence, missing-field details, and
fixture SQL call counts. Rejected queries have zero executor calls.

## Limits and remaining Week 8 work

- This is a conservative controlled-language layer, not a general semantic
  parser. Some legitimate paraphrases will need rephrasing; rejection is safer
  than dropping unrecognized constraints. Broader syntax should be added with
  regression cases and an explicit SQL capability mapping.
- The supported search fields are city, price, beds, baths and positive private
  pools. Source attributes beyond these, geospatial proximity, disjunctions,
  aggregation, sorting requests, status filtering, and booking are not supported.
  “Homes” retains the existing table-search meaning; it does not secretly add an
  unimplemented property-type or active-status filter.
- Capability definitions reflect the inspected local schema and parser, not
  dynamic database introspection. Schema changes require catalog maintenance.
- Source consistency checks cannot prove listing truth or detect every conflict
  in narrative remarks. The unchanged summarizer's documented limitations remain.
- A missing required field in any returned row rejects that page. Partial-answer
  delivery and pagination are future work.
- Live MySQL verification remains pending working database access. Human-written
  references and teammate ratings of 20 summaries are still required. Final
  held-out ROUGE evaluation should wait for verified references and a frozen
  summarization method.

No fine-tuning, paid model calls, commits, pushes, split changes or human-reference
changes were performed.
