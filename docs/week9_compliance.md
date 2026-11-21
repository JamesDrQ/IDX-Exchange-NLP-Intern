# Week 9: Fair Housing compliance screening

**Current implementation: v1.2.** See [the generalization report](week9_generalization.md)
for current results and commands. Evaluation figures and v1.1 freeze instructions
below are historical; the old holdout is now diagnostic data. The old freeze
can only be reproduced with the preserved v1.1 source snapshot.

This offline module screens English listing descriptions for potential discriminatory
preferences and exclusions. A match is a review signal, not a finding of illegality.
A `ready` result means no blocking pattern was detected, not legal certification.
Week 1–8 modules, frozen models, datasets and behavior are unchanged.

## Legal basis and sources

Sources consulted November 20, 2026:

- [24 CFR 100.75, eCFR](https://www.ecfr.gov/current/title-24/subtitle-B/chapter-I/part-100/subpart-B/section-100.75),
  with [official 2025 text](https://www.govinfo.gov/content/pkg/CFR-2025-title24-vol1/xhtml/CFR-2025-title24-vol1-sec100-75.html).
  Housing advertisements and statements must not indicate protected-class
  preferences, limitations or discrimination. The provision extends beyond text
  to other communication forms, which this checker does not inspect.
- [HUD legal opinion GME-0008, February 20, 1992](https://www.hud.gov/sites/documents/gme-0008lops.pdf).
  HUD explains that advertising language must be assessed in context, and that
  individual words do not resolve legality. Its discussion of older-person housing
  illustrates an exception, but predates HOPA amendments; do not use its historical
  eligibility criteria as current requirements.
- [HUD Fair Housing Enforcement Handbook 8024.01, chapter 3](https://www.hud.gov/sites/documents/80241c3-1fheh.pdf).
  Jurisdiction, dwelling coverage and exceptions require factual assessment.
  Owner-occupied or single-family dwelling exemptions do not automatically exempt
  discriminatory advertising.
- [24 CFR part 100, official 2025 edition](https://www.govinfo.gov/content/pkg/CFR-2025-title24-vol1/pdf/CFR-2025-title24-vol1-part100.pdf),
  sections 100.303–100.307: older-person housing exceptions and eligibility evidence.
  A `55+` claim alone is not proof. Qualification can affect familial-status
  restrictions, not exclusions based on unrelated protected categories.

The seven rule categories are `race`, `color`, `religion`, `sex`,
`national_origin`, `familial_status`, and `disability` (the regulation uses the
term handicap). Familial status includes households with children and pregnancy.
The sex screening vocabulary also includes selected sexual-orientation and
gender-identity expressions; the library is a screening policy, not an exhaustive
statement of evolving legal interpretations. State and local protections require
separate policy and legal review.

## Method and configuration

`scripts/compliance_patterns.py` defines immutable `ComplianceRule` objects and
library version 1.2. Each has a stable ID, category, regex, severity, explanation
and recommended action. `ComplianceChecker(rules=...)` accepts a replacement
collection; extend `default_rules()` to retain federal coverage. An empty
collection intentionally disables detection and should not be used as a production
policy. Invalid categories, severities, duplicate IDs and empty-matching patterns
are rejected. Configuration is trusted Python code, not advertiser input; arbitrary
regex can be expensive and must be reviewed before deployment.

Patterns combine protected-group vocabulary with restriction/preference grammar
and word boundaries. Isolated words such as white, ethnic, diverse, Christian,
or family are not automatically violations. Case-insensitive matching supports
whitespace and selected typographic punctuation. Single-character normalization
preserves original Python string offsets. Findings retain repeated matches and
are sorted by offsets and rule ID.

Local preceding negation and specific following policy denials suppress matches.
These are deliberately narrow rather than document-wide exceptions: an inclusive
sentence cannot erase an independent exclusion. Positive accessibility features
produce info; a negated accessibility description does not become a resident
exclusion. Ordinary property features such as white cabinets, French doors,
family rooms and proximity to a church produce no finding.

Senior-housing claims route familial-status exclusions to warning, never automatic
approval. Sex-specific roommate requests also route to review because the sharing
arrangement and applicable exception cannot be verified from a phrase. General
sex restrictions remain errors; reviewers must resolve other shared-living claims
rather than assuming that all roommate advertisements are exempt. Religious or
owner-occupied claims do not automatically suppress exclusions.

## Severity and API

| Severity | Policy | Example |
| --- | --- | --- |
| error | Apparent clear resident restriction; block submission | No children |
| warning | Ambiguous audience, context or exception; review required | Ideal for singles; 55+ community |
| info | Nonblocking factual guidance | Wheelchair accessible entrance |

These are application severity labels, not statutory legal classifications.
Warnings can include lawful language. Prefer objective descriptions of the home.

```python
from scripts.compliance_checker import ComplianceChecker
result = ComplianceChecker().check_listing('No children. Sunny patio.')
# result['status'] == 'blocked'
# result['can_publish'] == False
```

The JSON-compatible result contains `status` (`blocked`, `review_required`,
`ready`), `can_publish`, `requires_review`, `highest_severity` (also `none` when
there are no findings), and `findings`. Each finding contains `category`,
`rule_id`, `matched_text`, `start`, `end` (exclusive), `severity`, `explanation`,
and `recommended_action`. Multiple categories and severities can coexist; errors
always dominate the publication decision. Empty descriptions raise `ValueError`;
non-string descriptions raise `TypeError`, rather than silently permitting them.

## Submission workflow

```bash
python -m scripts.demo_week9_submission
```

`submit_listing(description)` is a pure example gate with no publication or
database side effects. Errors block, warnings remain in a review queue, and
none/info may proceed. The example has no approval override. A real publisher
should evaluate the exact final text on each submission/edit, present findings to
an authorized reviewer, and record review decisions against that text version
and rule configuration. Corrections must be checked again. For a justified
exception requiring manual approval, implement a separate authenticated, audited
review process; never trust a client-supplied approval flag. Do not publish when
checking fails. The repository's search and summary pipelines are not changed.

## Indirect-language revision (v1.1)

The original misses were:

- “Applicants raising little ones will be turned away.” Version 1.0 lacked both
  dependent-child paraphrases and passive rejection grammar.
- “Tenants must attend our church each Sunday.” Version 1.0 matched religious
  group preferences, but not religious practice imposed as a tenancy condition.

`scripts/compliance_context_patterns.py` now composes resident nouns, dependent
relationships, rejection verbs, obligation verbs, religious activities and
membership phrases. Rules require these elements in a bounded grammatical
sequence; they do not search arbitrarily across sentences for co-occurring words.
Explicit exclusion/obligation yields error. Discouragement or religious
encouragement/expectation yields warning. Optional activity, factual proximity,
property inspections and local negations remain unflagged. This is a limited
English grammar, not semantic understanding.

39 additional development examples exercise variations and benign counterexamples.
Original labels and descriptions remain unchanged. Original challenge tests were
strengthened to require error-level detection; assertions expecting exactly two
misses were replaced with assertions requiring zero misses and correct severity.
No existing expected-severity assertions were relaxed.

## Reproducible evaluation

Historical v1.1 commands below describe the prior run; do not use the current
v1.2 checkout to overwrite those reports. For current reproduction commands,
including the preserved v1.1 source snapshot, see
[the generalization report](week9_generalization.md).

```bash
python -m scripts.evaluate_week9 --output docs/week9_evaluation.json
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_development.json \
  --output docs/week9_development_evaluation.json
python -m scripts.evaluate_week9 --dataset data/evaluation/week9_holdout.json \
  --freeze docs/week9_rule_freeze.json --output docs/week9_holdout_evaluation.json
python -m pytest tests/test_week9_compliance.py -q
```

Dataset provenance and separation:

- **Original:** 62 AI-authored synthetic examples: 30 direct known violations,
  21 compliant examples, nine review cases, two indirect challenges. This remains
  development/regression data, including the two original misses. Its unchanged
  SHA-256 is recorded in both baseline and final reports.
- **Additional development:** 39 AI-authored examples used to develop and test
  the general grammar: 14 errors, four warnings and 21 none/info cases.
- **Held out:** 42 new AI-authored examples: seven direct violations, 12 indirect
  violations, seven warnings and 16 none/info cases. The checker, rule modules,
  submission gate and evaluator were hashed in `week9_rule_freeze.json` **before**
  this corpus was created. Labels and corpus hash were sealed in
  `week9_holdout_manifest.json` before scoring. No rule, label or evaluator changes
  followed scoring. `--freeze` refuses changed code before reading the dataset.
  The same agent authored the rules and holdout, so temporal separation is real,
  but independent authorship and human verification are **not** claimed. The data
  is now observed and must not be reused as an untouched test for future tuning.

All labels are screening judgments, not human legal determinations. Binary
positive means warning/error (review or blocking action expected); none/info are
negative. TP/FP/TN/FN use one decision per listing. Precision is TP/(TP+FP), recall
TP/(TP+FN), and severity accuracy is exact agreement on maximum severity over all
examples. Zero denominators are null. Reports include per-kind scores, every
prediction, FP/FN IDs, severity errors, dataset hash and executable source hashes.
Direct recall is the recall of `known_violation` examples; error-level direct
recall separately verifies that they actually block. Category and exact evidence
spans are tested on development fixtures, not summarized by these metrics.

| Dataset | TP | FP | TN | FN | Direct recall | Overall recall | Precision | Severity accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original baseline v1.0 (62) | 39 | 0 | 21 | 2 | 100% (30/30) | 95.12% | 100% | 96.77% |
| Original revised v1.1 (62) | 41 | 0 | 21 | 0 | 100% (30/30) | 100% | 100% | 100% |
| Additional development (39) | 18 | 0 | 21 | 0 | n/a | 100% | 100% | 100% |
| Held out (42) | 18 | 1 | 15 | 8 | 100% (7/7) | 69.23% | 94.74% | 78.57% |

All detected direct violations are errors. Error-labeled recall is 32/32 (100%)
on the original set and 13/19 (68.42%) on held-out data. Held-out indirect recall
is 6/12 (50%); borderline recall is 5/7 (71.43%). Do not pool development and
held-out results. Original precision is preserved; 100% precision does **not**
generalize to the holdout. The requested direct-set recall and >80% precision
thresholds are met in both measured sets, but broad discrimination detection
remains incomplete. `week9_evaluation_baseline.json` preserves the initial scores.

Held-out errors (unchanged after evaluation):

| ID suffix (`w9-held-`) | Expected / predicted | Cause |
| --- | --- | --- |
| 011 | error / none | Conditional second-person baby exclusion; grammar requires a resident noun. |
| 012 | error / none | Housing reserved for people without dependents; inverse qualification not covered. |
| 016 | error / none | Pastor-letter qualification; indirect religious evidence requirement not covered. |
| 017 | error / none | Practicing members of a faith; restriction vocabulary/grammar gap. |
| 018 | error / none | Mobility-aid exclusion; new indirect grammar currently covers family/religion only. |
| 019 | error / none | Birthplace exclusion; national-origin paraphrase not covered. |
| 030 | none / error | Explicitly abolished religious requirement; historical scope is not recognized. |
| 041 | warning / none | Finished-raising-children audience language is outside the discouragement grammar. |
| 042 | warning / none | Independent-living ability expectation is not recognized. |

There are no FP/FN on the original or added development corpus. Full descriptions
and label rationales for the above IDs are in the sealed held-out JSON. Do not
change those labels to improve scores. Future work should use these as development
cases and obtain a fresh independently authored, preferably human-reviewed test.

## Validation and submission gate

127 Week 9 tests passed (50 more than v1.0). Full offline discovery: **549 passed**,
with the same pre-existing pytest warning about
`scripts/evaluate_week3_test.py::test_manifest_path` returning a value. Both database
integration files remain excluded explicitly:

```bash
RUN_MYSQL_INTEGRATION=0 python -m pytest -q \
  --ignore=tests/test_setup.py --ignore=tests/test_week4_integration.py
```

Tests verify error blocks, warning requires review, info/none permits proceeding,
error precedence over combined warning/info, unverified senior exception review,
invalid-input rejection, exact original evidence spans, independent-clause
negation, metric calculations and refusal when frozen code changes. No approval
bypass or publication side effect was introduced. No dependency was added.
Week 1–8 file hashes were compared before/after the work; no changes were made.

## Limits and next evaluation work

Finite English regex misses unseen groups, indirect conditions, coded language,
misspellings, obfuscation, complex negation and multilingual content. It does not
analyze images, targeting, applicant treatment or other evidence. Simple context
rules may misread quotations, historical restrictions, amenity-only rules,
negated preferences or cross-clause relationships. A demographic neighborhood
statement may be factual yet receive a warning. Accurate no-elevator descriptions
are distinct from resident exclusions; accessibility claims are not verified.
Senior claims may downgrade familial-status errors to review even if misleading,
but cannot enable publication. No exception is established by a pattern match.

Before deployment, obtain independent compliance-reviewed representative labels,
freeze rules before evaluating them, measure category and subgroup errors, review
false negatives and false positives, and calibrate policy for the jurisdiction.
Preserve disagreements instead of treating synthetic labels as authoritative.
