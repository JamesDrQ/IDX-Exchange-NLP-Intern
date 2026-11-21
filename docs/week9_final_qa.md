# Week 9 v1.2 final QA — November 21, 2026

**Ready to commit as the documented offline screening implementation and
submission example.** This is not approval for unattended production publication
or a claim of full legal compliance. No code, rules, labels, dependencies or
freezes changed during final QA. Two documentation details were corrected: a stale
library version and the more complete offline test command/count.

## Checklist

- [x] Reproduced v1.1 and v1.2 on the identical frozen 53-example dataset.
- [x] Parsed reproduced JSON reports exactly equal the checked-in reports.
- [x] Independently recounted TP, FP, TN, FN and severity agreement from predictions.
- [x] Verified dataset/manifest hashes and both model freezes; v1.1 used its snapshot.
- [x] Original direct known-violation target verified: 30/30 detected as errors.
- [x] Original corpus precision exceeds 80%: 41/41 = 100%, zero false positives.
- [x] All seven remaining fresh-set misses documented with unchanged labels.
- [x] Error, warning, info, mixed severity and invalid-input gate checks pass.
- [x] Full offline suite passed; both live database tests explicitly deselected.
- [x] Synthetic provenance, diagnostic reuse and fresh-set limitations documented.
- [x] Explicit commit manifest prepared, excluding unrelated Week 8 files.
- [x] Proposed files scanned for common credential/token/private-key patterns.
- [x] No Week 1–8 file changes; prior capture hashes and Git scope checked.

## Verified counts and denominators

“Positive” means an expected **error or warning**. A warning is a review signal,
not an adjudicated violation. None and info are negative. Overall recall measures
screening coverage; it must not be described as recall solely over legal violations.

The fresh 53 examples contain 7 direct error cases (`known_violation`), 18 indirect
error cases (`indirect`), 8 review/warning cases (`borderline`), and 20 compliant
none/info cases. Thus the overall positive denominator is **7+18+8 = 33**, not 25
or 53. The 25-error subset is also reported separately.

| Metric | v1.1 | v1.2 |
| --- | ---: | ---: |
| TP / FP / TN / FN | 12 / 2 / 18 / 21 | 26 / 0 / 20 / 7 |
| Overall screening recall, TP/(TP+FN) | 12/33 = 36.36% | 26/33 = 78.79% |
| Direct error recall | 7/7 = 100% | 7/7 = 100% |
| Indirect error recall | 2/18 = 11.11% | 13/18 = 72.22% |
| Other positive category: review warnings | 3/8 = 37.50% | 6/8 = 75.00% |
| All error-labeled recall | 9/25 = 36.00% | 20/25 = 80.00% |
| Precision, TP/(TP+FP) | 12/14 = 85.71% | 26/26 = 100% |
| Exact maximum-severity accuracy | 30/53 = 56.60% | 46/53 = 86.79% |

Severity accuracy compares **error/warning/info/none exactly** across all 53
examples. It is not conditional on a detection and is not per-category or
per-finding accuracy. For these runs the severity mismatches coincide with binary
FP/FN, but that need not hold generally; a warning predicted as error would count
as a binary TP and a severity error. Automated metric tests cover that distinction.
All detected direct/indirect error cases in this comparison received error severity.

Original 62-case v1.2 evaluation: TP=41, FP=0, TN=21, FN=0, overall recall
41/41=100%, precision 41/41=100%, severity accuracy 62/62=100%. Its positive groups
are 30 direct known violations, two original indirect challenges, and nine review
cases. The direct-only test has TP=30, FN=0 and recall 100%; precision within that
positive-only subset is 30/30=100% but cannot establish false-positive performance.
The mixed 62-case corpus supplies 21 negative cases and the more meaningful
precision check. All original labels remain unchanged.

The older 42-case holdout's v1.1 result (69.23% recall, 94.74% precision) is
historical. After v1.2 development it is diagnostic data scoring 100%; it is **not**
independent final validation. The two fresh-set rows above provide the same-data
model comparison. Neither the same-author synthetic labels nor zero observed
false positives establish general real-world accuracy. The 53-case set is now
observed and must not be treated as untouched validation after further tuning.

## Seven remaining false negatives

All are predicted none and retained in `week9_v12_fresh_evaluation.json`.
The full descriptions are in the unchanged fresh corpus and generalization report.

| Fresh ID | Expected | Failure category |
| --- | --- | --- |
| w9-fresh-012 | error | Application-as-subject; child accompaniment; “not considered” rejection paraphrase. |
| w9-fresh-013 | error | Promised future childlessness; temporal/reproductive eligibility condition. |
| w9-fresh-018 | error | Implicit shared-belief qualification and approval inversion. |
| w9-fresh-022 | error | Caregiver/live-in aide need and ineligibility paraphrase. |
| w9-fresh-025 | error | Positive domestic-birth eligibility rather than foreign-birth exclusion. |
| w9-fresh-052 | warning | Coded life-stage audience and affinity preference. |
| w9-fresh-053 | warning | Implicit spiritual conformity expectation. |

These are five missed error cases and two missed review cases. They are documented
limitations, not relabeled negatives or unreported test exclusions.

## Workflow and test verification

The pure example gate returns blocked for any error, review_required for warning
without error, and ready for info/none. Mixed error/warning/info remains blocked.
`requires_review` records the presence of warnings even when an error blocks.
Invalid/blank input raises an exception; there is no publication side effect or
client approval override. Senior claims can route familial restrictions to review
but cannot authorize publication. Real review approvals, authentication, audit
storage and publication are outside this demonstration.

Final command, in the existing `idx-nlp` environment:

```bash
RUN_MYSQL_INTEGRATION=0 python -m pytest -q \
  -k 'not test_mysql_connection and not test_query_parser_to_read_only_mysql_select'
```

Result: **632 passed, 0 failed, 0 skipped, 2 deselected**. Includes 208 Week 9 tests
and 424 other collected passing checks. The two deselections are live MySQL tests,
not skipped failures. The existing `scripts/evaluate_week3_test.py::test_manifest_path`
emits `PytestReturnNotNoneWarning`; this is unrelated to Week 9 and was not changed.
The earlier 630-passing run omitted the entire setup file and therefore two offline
setup checks. No database integration functionality was exercised or certified.

## Reproduction audit

Both model commands in `week9_generalization.md` were executed with output sent to
`/tmp`, avoiding overwriting historical evidence. Each parsed report exactly
matched its committed candidate JSON. Fresh dataset and freeze SHA-256 values
matched `week9_v12_fresh_manifest.json`; prior holdout/manifest hashes also matched.
Current v1.2 files and the v1.1 snapshot matched their respective code freezes.
The current evaluator's `--freeze` verifies code, not dataset hashes: this QA
separately checked the dataset manifest. For arbitrary custom evaluations, callers
must validate their labels and dataset identity; the supplied evaluator is not a
cryptographic attestation system.

## Git, data and secret hygiene

The sole modified tracked file is README.md, with an additive Week 9 section.
Week 9 implementation and evidence files are untracked until explicitly staged.
No staged files, commits, pushes or merges were made. The exact proposed scope is
[week9_commit_files.txt](week9_commit_files.txt), one repository-relative path per
line. Stage only that allowlist; do not use `git add .`.

Intentional generated artifacts: small deterministic evaluation reports, dataset
hash manifests, code freezes and the verified five-file v1.1 source snapshot.
They preserve prior claims and enable the same-data baseline comparison. The five
synthetic datasets serve distinct original/development/diagnostic/fresh roles;
none contains a production listing extract. Retain them for reproducibility.
No unnecessary model binaries, raw SQL, production datasets, caches, logs or
temporary outputs are proposed. Existing caches remain ignored; QA outputs remain
in `/tmp`. Existing `.env` is ignored and was not opened. The tracked environment
example is unchanged and outside the proposed commit.

Common secret signatures (private keys, AWS/service tokens, credential assignments
and credential-bearing URLs) produced **zero matches in the proposed files**.
This is a scoped pattern-based review, not a guarantee that all possible secrets
can be detected. No secret values were printed. Paths and synthetic prose were
reviewed as part of the allowlist audit.

These unrelated untracked documents must remain outside the Week 9 commit:

- docs/week8_ai_ratings_report.md
- docs/week8_development_evaluation.md
- docs/week8_final_report.md
- docs/week8_hybrid_optimization.md
- docs/week8_model_freeze.md
- docs/week8_private_artifacts.txt
- docs/week8_submission_audit.md
- docs/week8_summarization.md

Week 1–8 source/data/doc hashes match the captured pre-v1.2 state, and Git shows
no tracked code changes there. Passing regression tests support unchanged offline
functionality; live database behavior was intentionally not tested.

## Readiness and outstanding limitations

Ready for a scoped commit of the Week 9 implementation, tests and documented
research/evaluation evidence. No release-blocking implementation or reproduction
issue was found in this QA. Remaining limitations are seven fresh-set false
negatives, same-author synthetic validation, restricted English grammar, complex
context and exception handling, and an example-only submission workflow. They
preclude claiming exhaustive detection or unattended production readiness.
The pre-existing pytest warning remains. No detection changes were made in QA.
