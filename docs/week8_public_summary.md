# Week 8 public submission summary

The implementation provides lead-2, entity-aware extractive, and factual Hybrid listing summaries. The search integration reuses existing parsing, schema validation, intent classification and parameterized SQL, and rejects unsupported or partially understood constraints before database execution. Post-query checks distinguish absent results, insufficient evidence and execution failures.

The original 100-listing split remains 70 development / 30 held-out test. Evaluation uses 30 reviewed references from each split. Development references were confirmed human-authored after earlier AI-assisted drafting; test references were AI-assisted source-only drafts subsequently reviewed by the user. Test references are not an independently human-authored benchmark.

| Method | Development ROUGE-L F1 | Held-out ROUGE-L F1 |
|---|---:|---:|
| Lead-2 | 0.2027 | 0.2340 |
| Extractive | 0.2478 | 0.2400 |
| Hybrid | 0.4190 | 0.3689 |

**Hybrid performs best but does not satisfy the required held-out score greater than 0.4.** No optimization followed test evaluation. The frozen model and saved predictions remain unchanged.

Normalization is Unicode NFKC plus casefold, Unicode alphanumeric tokens excluding underscores, no stemming, document-level longest common subsequence, and macro-averaged F1. ROUGE measures lexical overlap, not factual correctness. Remaining limitations include small samples, scope ambiguity, conservative omissions, imperfect feature selection and reference-writing bias.

The 20 quality ratings were produced by Codex and accepted by the user as a substitute; **they are not authentic teammate or human ratings**. Their means are accuracy 4.40, completeness 3.35, readability 3.85, conciseness 4.75, overall 4.0875. The original human teammate evaluation requirement remains unmet.

## Reproduction and privacy

`docs/week8_submission_files.txt` is a public **candidate** allowlist, not permission to publish the entire existing repository or its history. `docs/week8_release_checks.json` contains content-free hashes and saved aggregate results. Full listing records, annotations, predictions, detailed reports and original freeze artifacts are retained locally and excluded from this public package pending distribution-rights review. Exact data-backed reproduction requires authorized access to that private bundle. Hashes alone cannot reproduce evaluation.

Use Python 3.11 and `pip install -r requirements.txt`. Existing notebook/chart dependencies are retained; optional Week 5 semantic-search dependencies are documented separately in `requirements-week5.txt`. NLTK English Punkt is also required; exact frozen reproduction needs the tokenizer version/hash recorded with the private candidate. The working environment passes `pip check`; a clean isolated install could not obtain the pinned NumPy package from the package index, so fresh-install validation is outstanding.

Run relevant tests with:

```sh
python -m pytest -q tests/test_database_config.py tests/test_setup.py tests/test_week3*.py tests/test_query_parser.py tests/test_schema_validator.py tests/test_sql_generator.py tests/test_week4_integration.py tests/test_week5.py tests/test_week6*.py tests/test_week7*.py tests/test_week8*.py -k 'not generation_is_reproducible_and_preserves_annotations' -rs
python scripts/verify_week8_release.py
```

The latter command requires the private bundle and only validates saved hashes/results; it never regenerates predictions or reruns ROUGE. Some repository tests also require private source fixtures, prior-week models and tokenizer data. The public allowlist is an addition to the existing project, not a standalone source archive with all data-dependent tests runnable.

Cleanup verification: **374 passed, 2 skipped, 1 deselected**. Both skips are live MySQL checks; the deselected test would regenerate both development and held-out predictions. These are offline test results, not live-database verification.

Before any public push, rotate the previously committed database credential and address its historical exposure. Previously tracked listing datasets also require a separate rights/privacy decision. See `docs/week8_security_cleanup.md`.
