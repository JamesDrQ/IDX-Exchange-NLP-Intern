"""Deterministic listing-level screening metrics (not legal verdict metrics)."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.compliance_checker import ComplianceChecker
from scripts.compliance_patterns import SEVERITIES, LIBRARY_VERSION

ROOT = Path(__file__).resolve().parents[1]
FROZEN_FILES = ('scripts/compliance_checker.py', 'scripts/compliance_patterns.py',
                'scripts/compliance_context_patterns.py', 'scripts/compliance_context.py', 'scripts/evaluate_week9.py',
                'scripts/demo_week9_submission.py')


def code_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FROZEN_FILES}


def verify_freeze(path):
    manifest = json.loads(Path(path).read_text())
    if manifest['code_sha256'] != code_hashes():
        raise ValueError('Frozen code has changed; held-out evaluation refused')
    return manifest


DEFAULT_DATASET = Path(__file__).resolve().parents[1] / 'data/evaluation/week9_compliance.json'


def score(expected, predicted):
    if len(expected) != len(predicted):
        raise ValueError('Expected and predicted lengths differ')
    if any(s not in SEVERITIES for s in [*expected, *predicted]):
        raise ValueError('Unknown severity label')
    counts = dict(TP=0, FP=0, TN=0, FN=0)
    for gold, pred in zip(expected, predicted):
        actual, detected = gold in {'warning', 'error'}, pred in {'warning', 'error'}
        counts['TP' if actual and detected else 'FN' if actual else 'FP' if detected else 'TN'] += 1
    def ratio(n, d):
        return n / d if d else None
    return {**counts, 'count':len(expected),
            'precision':ratio(counts['TP'], counts['TP']+counts['FP']),
            'recall':ratio(counts['TP'], counts['TP']+counts['FN']),
            'severity_accuracy':ratio(sum(a == b for a,b in zip(expected,predicted)),len(expected))}


def evaluate(path=DEFAULT_DATASET, checker=None, freeze=None):
    if freeze is not None:
        if checker is not None:
            raise ValueError("Frozen evaluation requires the default checker")
        verify_freeze(freeze)
    path = Path(path)
    raw = path.read_bytes()
    dataset = json.loads(raw)
    examples = dataset['examples']
    if not examples or len({e['id'] for e in examples}) != len(examples):
        raise ValueError('Dataset must be nonempty with unique IDs')
    checker = checker or ComplianceChecker()
    predictions = [dict(id=e['id'], kind=e['kind'], expected=e['expected_severity'],
                        predicted=checker.check_listing(e['text'])['highest_severity']) for e in examples]
    def metrics(rows):
        return score([r['expected'] for r in rows], [r['predicted'] for r in rows])
    known = [r for r in predictions if r['kind'] == 'known_violation']
    overall = metrics(predictions)
    known_metrics = metrics(known)
    return {'dataset_sha256':hashlib.sha256(raw).hexdigest(), 'library_version':LIBRARY_VERSION,
            'provenance':dataset['provenance'], 'overall':overall,
            'code_sha256':code_hashes(),
            'false_positives':[r['id'] for r in predictions if r['expected'] in {'none', 'info'} and r['predicted'] in {'warning', 'error'}],
            'false_negatives':[r['id'] for r in predictions if r['expected'] in {'warning', 'error'} and r['predicted'] in {'none', 'info'}],
            'severity_errors':[r for r in predictions if r['expected'] != r['predicted']],
            'error_label_recall':metrics([r for r in predictions if r['expected']=='error'])['recall'],
            'by_kind':{kind:metrics([r for r in predictions if r['kind']==kind]) for kind in sorted({r['kind'] for r in predictions})},
            'known_violation_recall':known_metrics['recall'],
            'known_violation_error_recall':sum(r['predicted']=='error' for r in known)/len(known) if known else None,
            'targets_met':known_metrics['recall']==1 and overall['precision'] is not None and overall['precision']>0.8,
            'predictions':predictions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--freeze', type=Path, help='Require an unchanged code snapshot before reading data')
    args = parser.parse_args()
    report = evaluate(args.dataset, freeze=args.freeze)
    rendered = json.dumps(report, indent=2)+'\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered)
