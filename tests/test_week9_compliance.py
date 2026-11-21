import json
from dataclasses import replace
import pytest
from scripts.compliance_checker import ComplianceChecker
from scripts.compliance_patterns import CATEGORIES, default_rules
from scripts.demo_week9_submission import submit_listing
from scripts.evaluate_week9 import DEFAULT_DATASET, evaluate, score

DATA = json.loads(DEFAULT_DATASET.read_text())['examples']


@pytest.mark.parametrize('example', DATA, ids=lambda e:e['id'])
def test_labeled_examples(example):
    result = ComplianceChecker().check_listing(example['text'])
    assert result['highest_severity'] == example['expected_severity']
    for category in example['categories']:
        assert category in {f['category'] for f in result['findings']}
    assert json.loads(json.dumps(result)) == result
    for finding in result['findings']:
        assert example['text'][finding['start']:finding['end']] == finding['matched_text']
        assert finding['explanation'] and finding['recommended_action']


@pytest.mark.parametrize('text', ['No children. No Muslims.',
    'Not adults only, but no Muslims.', 'Wheelchair accessible; no disabled tenants.',
    '55+ community. No Black tenants.', 'No children allowed is not our policy, but Christians only.'])
def test_context_does_not_hide_independent_errors(text):
    assert not submit_listing(text)['publication_allowed']
    assert submit_listing(text)['decision'] == 'blocked'


@pytest.mark.parametrize('text', ['NO\nCHILDREN', 'Adults‑only', 'We don’t rent to foreigners.'])
def test_case_spacing_unicode(text):
    assert ComplianceChecker().check_listing(text)['highest_severity']=='error'


def test_workflow():
    assert submit_listing('Sunny patio.')['publication_allowed']
    assert submit_listing('Step-free entry.')['publication_allowed']
    assert submit_listing('Ideal for singles.')['decision']=='review_required'
    assert not submit_listing('Ideal for singles.')['publication_allowed']
    assert submit_listing('No children.')['decision']=='blocked'


def test_configuration_is_isolated_and_validated():
    assert {r.category for r in default_rules()} == CATEGORIES
    rule = replace(default_rules()[0], pattern=r'\breview me\b', severity='warning')
    assert ComplianceChecker([rule]).check_listing('Review me')['highest_severity']=='warning'
    assert ComplianceChecker().check_listing('Review me')['highest_severity']=='none'
    for rules in [[rule, rule], [replace(rule, category='invalid')],
                  [replace(rule, severity='critical')], [replace(rule, pattern='')]]:
        with pytest.raises(ValueError): ComplianceChecker(rules)
    with pytest.raises(TypeError): ComplianceChecker([{}])


@pytest.mark.parametrize('text', [None, 123, [], '', '  '])
def test_invalid_input_cannot_publish(text):
    with pytest.raises((TypeError, ValueError)): submit_listing(text)


def test_metrics_independent_oracle():
    result = score(['error','warning','none','info'], ['error','none','warning','info'])
    assert {k:result[k] for k in ['TP','FP','TN','FN']} == dict(TP=1,FP=1,TN=1,FN=1)
    assert result['precision']==result['recall']==result['severity_accuracy']==0.5
    assert score([],[])['precision'] is None
    with pytest.raises(ValueError): score(['none'],[])
    with pytest.raises(ValueError): score(['invalid'],['none'])


def test_reproducible_evaluation_and_honest_challenges():
    report = evaluate()
    assert report == evaluate()
    assert report['known_violation_error_recall']==1
    assert report['overall']['precision']>0.8
    assert report['by_kind']['challenge']['FN']==0
    assert report['by_kind']['challenge']['severity_accuracy']==1
    assert report['overall']['recall']==1


DEVELOPMENT = json.loads((DEFAULT_DATASET.parent / 'week9_development.json').read_text())['examples']


@pytest.mark.parametrize('example', DEVELOPMENT, ids=lambda e:e['id'])
def test_context_development_examples(example):
    test_labeled_examples(example)


@pytest.mark.parametrize(('text', 'severity', 'decision', 'allowed', 'review'), [
    ('Tenants must attend worship services. Step-free entry.', 'error', 'blocked', False, False),
    ('Tenants encouraged to attend church. Step-free entry.', 'warning', 'review_required', False, True),
    ('Step-free entry with wide doors.', 'info', 'ready', True, False),
    ('Sunny patio.', 'none', 'ready', True, False),
    ('Households with infants are rejected. Ideal for singles. Step-free entry.', 'error', 'blocked', False, True),
    ('55+ housing. Households with infants are rejected.', 'warning', 'review_required', False, True),
])
def test_gate_severity_precedence(text, severity, decision, allowed, review):
    result = submit_listing(text)
    assert result['decision'] == decision
    assert result['publication_allowed'] is allowed
    assert result['compliance']['highest_severity'] == severity
    assert result['compliance']['requires_review'] is review


def test_negation_does_not_cross_independent_clauses():
    text = 'We never reject families with kids, but tenants must attend church.'
    result = submit_listing(text)
    assert result['decision'] == 'blocked'
    assert {f['category'] for f in result['compliance']['findings']} == {'religion'}


def test_freeze_rejects_modified_code_before_reading_data(tmp_path):
    from scripts.evaluate_week9 import code_hashes
    freeze = tmp_path / 'freeze.json'
    hashes = code_hashes()
    freeze.write_text(json.dumps({'code_sha256': hashes}))
    assert evaluate(freeze=freeze) == evaluate()
    hashes['scripts/compliance_checker.py'] = 'tampered'
    freeze.write_text(json.dumps({'code_sha256': hashes}))
    with pytest.raises(ValueError, match='Frozen code has changed'):
        evaluate(tmp_path / 'nonexistent-data.json', freeze=freeze)


def test_metrics_diagnostics_expose_misses(tmp_path):
    dataset = tmp_path / 'evaluation.json'
    dataset.write_text(json.dumps({'provenance': 'metric fixture', 'examples': [
        {'id':'miss', 'kind':'challenge', 'text':'Sunny patio.', 'expected_severity':'error'},
        {'id':'false_alarm', 'kind':'compliant', 'text':'No children.', 'expected_severity':'none'},
        {'id':'severity', 'kind':'borderline', 'text':'No men.', 'expected_severity':'warning'},
    ]}))
    report = evaluate(dataset)
    assert report['false_negatives'] == ['miss']
    assert report['false_positives'] == ['false_alarm']
    assert len(report['severity_errors']) == 3
    assert report['overall']['TP'] == 1


# The formerly held-out corpus is now explicitly diagnostic regression data.
DIAGNOSTIC = json.loads((DEFAULT_DATASET.parent / 'week9_holdout.json').read_text())['examples']
V12_DEVELOPMENT = json.loads((DEFAULT_DATASET.parent / 'week9_v12_development.json').read_text())['examples']


@pytest.mark.parametrize('example', DIAGNOSTIC + V12_DEVELOPMENT, ids=lambda e:e['id'])
def test_generalized_diagnostic_and_development(example):
    test_labeled_examples(example)


@pytest.mark.parametrize(('text', 'decision'), [
    ('Residents should be self-sufficient. Wheelchair accessible entrance.', 'review_required'),
    ('Residents must be self-sufficient. Wheelchair accessible entrance.', 'blocked'),
    ('The rule that tenants must attend church was revoked. Step-free entry.', 'ready'),
])
def test_generalized_severity_gate(text, decision):
    assert submit_listing(text)['decision'] == decision
