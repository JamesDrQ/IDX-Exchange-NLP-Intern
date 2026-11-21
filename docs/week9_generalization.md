# Week 9 generalization revision: version 1.2

This is the current report. Version 1.1's 42-example holdout is now **diagnostic
and development data**, not independent validation. Its original labels, report
and freeze are preserved. No automated screening result establishes full legal
compliance. Legal sources and the API/workflow description remain in
[the Week 9 documentation](week9_compliance.md).

## Analysis of every prior error

The IDs below refer to `data/evaluation/week9_holdout.json`. All eight false
negatives were predicted `none`; the false positive was predicted `error`.

| ID suffix | Original text | Expected | Root cause and generalized response |
| --- | --- | --- | --- |
| 011 | If you have a baby, your application will be declined. | error | **Conditional/second-person paraphrase.** Existing grammar required an applicant noun followed by a dependent relationship and rejection. Compose an if-clause describing a household with an application denial or resident rejection. |
| 012 | This rental is reserved for people without dependents under eighteen. | error | **Inverse eligibility and missing child paraphrase.** A positive reservation can express exclusion through an absence condition. Combine housing availability/exclusivity with household qualification; recognize age-qualified dependents. |
| 016 | A letter from your pastor is necessary to qualify for this apartment. | error | **Context-dependent eligibility evidence.** Religious affiliation is expressed through a required reference rather than a named religious group. Require the conjunction of religious evidence, obligation and housing qualification, rather than flagging clergy references alone. |
| 017 | The lease is available only to practicing members of our faith. | error | **Indirect religious preference.** Faith membership is a qualification even without a denomination. Share an exclusive-housing frame with category-specific membership and household slots. |
| 018 | Applicants who use mobility aids will be rejected. | error | **Relative-clause paraphrase and category coverage gap.** Disability wording describes an aid rather than a group label. Bind resident, aid use/need and exclusion; aid mentions without exclusion remain legitimate. |
| 019 | Applicants born outside the country will be turned away. | error | **Birthplace paraphrase.** National-origin vocabulary previously relied on selected demonyms. Reuse the exclusion frame with birthplace conditions. |
| 030 | The former rule that tenants must attend church has been abolished; no religious participation is required. | none | **Historical reference and assertion scope.** A restriction embedded in an expressly abolished rule was treated as current. Require a local policy frame plus an affirmative rescission immediately after the restriction; do not suppress based on “former” alone. |
| 041 | Best suited to people who have finished raising their children. | warning | **Implicit life-stage preference.** Household audience preference is implied rather than phrased as “no children.” Combine audience language with an explicit completed-childraising condition; review rather than declare exclusion. |
| 042 | Residents should be capable of independent living. | warning | **Context-dependent ability expectation and modality.** The phrase may imply an ability condition but does not state categorical exclusion. Separate soft expectation from mandatory ability requirements. |

All nine now receive their unchanged expected severity. This is a regression
result after development on these failures, not evidence of independent accuracy.

## Architecture and severity

The checker still uses configurable `ComplianceRule` records. Version 1.2 adds:

- Shared resident, household, housing, exclusivity, denial and obligation frames
  in `scripts/compliance_context_patterns.py`, combined with category-specific
  dependent-child, religious membership/evidence, mobility and birthplace slots.
  No rule contains a complete diagnostic sentence as a hardcoded string.
- A separate assertion-scope helper in `scripts/compliance_context.py`. It requires
  an adjacent rule/policy/requirement frame and an affirmative rescission in the
  same local sentence/semicolon segment. “Has not been abolished,” an old policy
  still in force, or revocation of an unrelated parking policy cannot suppress an
  active restriction. Findings in later clauses are checked independently.
- Exact evidence offsets, local negation, existing exception review and the
  error-first submission gate remain intact. The context helper is included in
  the frozen source hash list.

Severity is an application policy, not a legal verdict:

| Severity | Criterion | Examples |
| --- | --- | --- |
| error | Explicit exclusion, exclusive housing eligibility or mandatory protected-characteristic condition | Resident rejection for using aids; required religious reference for tenancy; mandatory independent-living ability |
| warning | Suggestive audience preference, softer expectation or a claimed exception requiring verification | Completed-childraising audience; “should” or “expected to” live independently; unverified senior housing |
| info | Nonblocking factual guidance, not a protected-class restriction | Accurate accessibility feature description |
| none | No supported actionable pattern or a narrowly recognized denial/rescission | Optional religious reference; ordinary architecture; explicitly revoked rule |

Errors block publication, warnings require review, info/none can proceed under
this screening gate. A permitted submission is not a legal certification.
Mandatory ability conditions may still need factual/program-specific review;
this conservative gate blocks apparent conditions rather than deciding exemptions.
Human review remains necessary for context outside the recognized grammar.

36 new development examples cover these frames, optional evidence, property
features, local negation, active restrictions after rescission, and severity
modality. The old 42-case holdout also became regression fixtures. No prior test
assertions were relaxed and no existing labels or examples were changed.

## Evaluation design and provenance

Data stages are kept separate:

1. Original 62-case corpus and earlier 39-case development corpus: development.
2. Previously scored 42-case holdout: now diagnostic/development.
3. New 36-case development corpus: development.
4. Fresh 53-case corpus: created **after** the v1.2 checker/evaluator freeze and
   sealed before either model scored it. Seven direct errors, 18 indirect errors,
   eight warnings and 20 compliant none/info examples. No exact-text overlap with
   earlier datasets. No model or label changes followed evaluation.

All corpora are AI-authored synthetic data. The same agent authored the fresh set
and the rules, so this is temporal separation, **not independent authorship or
human-verified legal ground truth**. Some examples recombine known grammatical
structures; no exact overlap does not establish semantic independence. The fresh
set is now observed and cannot remain an untouched test for future tuning.

`week9_v12_rule_freeze.json` hashes all executable modules. The fresh manifest
hashes the data and freeze. The saved v1.1 source snapshot was verified against its
original freeze before it was used to score the same fresh examples. Earlier
reports are retained; revised reports use new `week9_v12_*` filenames.

Binary positive means warning/error; negative means none/info. Recall includes
review cases. Direct/indirect recall uses examples explicitly labeled with those
kinds. Severity accuracy measures exact maximum severity, including none. Reports
retain TP/FP/TN/FN, all predictions, severity mismatches and FP/FN IDs. Counts with
zero denominators are null. These are listing-level screening metrics, not legal
verdict, category or exact-span accuracy metrics.

## Measured comparison

| Dataset and model | TP | FP | TN | FN | Overall recall | Precision | Severity accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original 62, v1.2 development | 41 | 0 | 21 | 0 | 100% | 100% | 100% |
| Earlier 39, v1.2 development | 18 | 0 | 21 | 0 | 100% | 100% | 100% |
| Old 42, v1.1 historical holdout | 18 | 1 | 15 | 8 | 69.23% | 94.74% | 78.57% |
| Old 42, v1.2 diagnostic | 26 | 0 | 16 | 0 | 100% | 100% | 100% |
| New 36, v1.2 development | 21 | 0 | 15 | 0 | 100% | 100% | 100% |
| **Fresh 53, v1.1 baseline** | **12** | **2** | **18** | **21** | **36.36%** | **85.71%** | **56.60%** |
| **Fresh 53, v1.2 revised** | **26** | **0** | **20** | **7** | **78.79%** | **100%** | **86.79%** |

The two fresh-set rows are the controlled same-dataset comparison. Comparing the
old 69.23% recall with the new 78.79% mixes different data and is not a controlled
measurement of improvement. Do not pool development and fresh-set scores.

| Recall on fresh 53 | v1.1 baseline | v1.2 revised |
| --- | ---: | ---: |
| Direct violations | 7/7 = 100% | 7/7 = 100% |
| Indirect violations | 2/18 = 11.11% | 13/18 = 72.22% |
| All error-labeled cases | 9/25 = 36% | 20/25 = 80% |
| Review/warning cases | 3/8 = 37.5% | 6/8 = 75% |

All detected direct and indirect error-labeled cases received error severity.
The revised checker fixes all 14 additional fresh positives without creating a
new false positive. This measured gain is limited to this synthetic sample.

## Remaining fresh-set failures

No false positives were observed for v1.2. Seven false negatives remain:

| Fresh ID suffix | Expected | Missed language and remaining gap |
| --- | --- | --- |
| 012 | error | “Applications from anyone bringing a child will not be considered.” Application-as-subject and negative consideration are not covered. |
| 013 | error | “You must promise not to have children during the lease.” A future reproductive condition requires promise/temporal semantics. |
| 018 | error | “Only applicants who share the landlord’s beliefs will be approved.” Implicit shared-belief qualification and approval inversion are not covered. |
| 022 | error | “Anyone needing a live-in aide is ineligible for the apartment.” Caregiver need and ineligibility vocabulary are outside the aid-use grammar. |
| 025 | error | “Only people born in the United States qualify.” Domestic-birth eligibility is not captured by the foreign-birth rejection grammar. |
| 052 | warning | “A welcoming retreat for empty nesters seeking neighbors like themselves.” Coded audience preference is not recognized. |
| 053 | warning | “Residents are expected to share our spiritual values.” Implicit religious conformity is not recognized. |

Rules remain frozen despite these misses. Broader historical paraphrases,
quotations, hypotheticals, clause nesting, unrecognized groups, multilingual
language, obfuscation and advertisement images remain limitations. Short local
patterns can still overflag text outside this sample; zero observed FP is not a
guarantee. State/local law, eligibility exceptions, facts and actual treatment
are not adjudicated. Further work should promote these errors to development and
use a new independently reviewed test set.

## Reproduction and checks

From the repository root, using Python in the existing `idx-nlp` environment:

```bash
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_compliance.json \
  --output docs/week9_v12_original_evaluation.json
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_development.json \
  --output docs/week9_v12_previous_development_evaluation.json
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_holdout.json \
  --output docs/week9_v12_diagnostic_evaluation.json
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_v12_development.json \
  --output docs/week9_v12_development_evaluation.json
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_v12_fresh_holdout.json \
  --freeze docs/week9_v12_rule_freeze.json --output docs/week9_v12_fresh_evaluation.json
```

To reproduce the old model on the same fresh corpus, run this from
`data/evaluation/week9_v11_snapshot` (the snapshot has the original evaluator):

```bash
python -m scripts.evaluate_week9 --dataset ../week9_v12_fresh_holdout.json \
  --freeze ../../../docs/week9_rule_freeze.json \
  --output ../../../docs/week9_v11_fresh_evaluation.json
```

Final QA (November 21, 2026): **208 Week 9 tests; 632 offline tests passed,
0 failed, 0 skipped, 2 database tests deselected**, with the same pre-existing
pytest warning about `test_manifest_path` returning a value. The earlier 630-test
run excluded entire database-related files; final QA also runs the two offline
setup checks. See [the final QA report](week9_final_qa.md).

```bash
python -m pytest tests/test_week9_compliance.py -q
RUN_MYSQL_INTEGRATION=0 python -m pytest -q \
  -k 'not test_mysql_connection and not test_query_parser_to_read_only_mysql_select'
```

Database integration files were excluded. No dependencies added, production
access, commits, pushes or merges. Week 1–8 files and prior labels were checked
for unchanged hashes. The old freeze intentionally fails against v1.2 code; use
its verified source snapshot, not a rewritten old freeze.
