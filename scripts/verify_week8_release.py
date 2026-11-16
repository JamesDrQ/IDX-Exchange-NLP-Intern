"""Read-only verification of the private frozen release; no prediction generation."""
import json
from pathlib import Path

if __package__:
    from .evaluate_week8_rouge import NORMALIZATION, sha, validate_prediction_run
else:
    from evaluate_week8_rouge import NORMALIZATION, sha, validate_prediction_run

ROOT = Path(__file__).resolve().parents[1]


def verify():
    data = ROOT / 'data/annotations/week8'
    pred = ROOT / 'data/processed/week8_summaries_frozen'
    reports = ROOT / 'data/processed/week8_eval'
    run = validate_prediction_run(pred, data)
    freeze_path = reports / 'model_freeze.json'
    frozen = json.loads(freeze_path.read_text())
    expected = {
        'models_frozen': True, 'normalization': NORMALIZATION,
        'prediction_hashes': {s: sha(pred/f'{s}_summaries.jsonl') for s in ('dev', 'test')},
        'prediction_run_sha256': sha(pred/'run_manifest.json'),
        'dataset_manifest_sha256': sha(data/'manifest.json'),
        'evaluator_sha256': sha(ROOT/'scripts/evaluate_week8_rouge.py'),
    }
    if frozen != expected:
        raise ValueError('Frozen release integrity failure')
    manifest = json.loads((data/'manifest.json').read_text())
    dev = set(manifest['splits']['dev']['listing_ids'])
    test = set(manifest['splits']['test']['listing_ids'])
    if len(dev) != 70 or len(test) != 30 or dev & test:
        raise ValueError('Split integrity failure')
    results = {}
    for split, name in [('dev', 'dev_freeze_verification.json'), ('test', 'test_rouge_frozen.json')]:
        report = json.loads((reports/name).read_text())
        reference = ROOT/f'data/annotations/week8_review/{split}30_references.csv'
        if report['reference_sha256'] != sha(reference) or report['prediction_sha256'] != expected['prediction_hashes'][split]:
            raise ValueError('Saved evaluation inputs changed: '+split)
        if report.get('freeze_sha256') and report['freeze_sha256'] != sha(freeze_path):
            raise ValueError('Saved evaluation freeze changed: '+split)
        results[split] = report['methods']
    return {'freeze_valid': True, 'split_sizes': {'dev':70,'test':30},
            'freeze_sha256': sha(freeze_path), 'artifact_hashes': expected,
            'code_sha256': run['code_sha256'], 'saved_results': results,
            'evaluation_rerun': False, 'predictions_regenerated': False}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
