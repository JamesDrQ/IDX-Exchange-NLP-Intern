"""Generate Week 8 predictions independently of human reference annotations."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import os

from scripts.listing_summarizer import ListingSummarizer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / 'data/annotations/week8'
DEFAULT_OUTPUT = ROOT / 'data/processed/week8_summaries'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(input_dir=DEFAULT_INPUT, output_dir=DEFAULT_OUTPUT, sample_size=12, dev_only=False):
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    if not 10 <= sample_size <= 15:
        raise ValueError('Development sample size must be between 10 and 15')
    # Even a caller-provided output path must never point into annotation storage.
    annotation_root = (ROOT / 'data/annotations').resolve()
    resolved = output_dir.resolve()
    if resolved == input_dir.resolve() or input_dir.resolve() in resolved.parents or resolved == annotation_root or annotation_root in resolved.parents:
        raise ValueError('Generated summaries must be outside annotation storage')
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite generated outputs: {output_dir}')
    manifest = json.loads((input_dir / 'manifest.json').read_text())
    tracked = [input_dir/name for name in ('manifest.json', 'dev_listings.jsonl', 'test_listings.jsonl')]
    before = {p.name: sha(p) for p in tracked}
    splits = {}
    for split in (('dev',) if dev_only else ('dev', 'test')):
        path = input_dir / f'{split}_listings.jsonl'
        expected = manifest['initial_artifact_sha256'][path.name]
        if sha(path) != expected:
            raise ValueError(f'Frozen source hash mismatch: {path.name}')
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if [r['listing_id'] for r in rows] != manifest['splits'][split]['listing_ids'] or any(r['split'] != split for r in rows):
            raise ValueError(f'Split membership mismatch: {split}')
        splits[split] = rows
    for field in ('listing_id', 'remarks_sha256'):
        if not dev_only and {r[field] for r in splits['dev']} & {r[field] for r in splits['test']}:
            raise ValueError(f'Split overlap: {field}')
    summarizer = ListingSummarizer()
    results = {}
    for split, rows in splits.items():
        results[split] = []
        for row in rows:
            remarks = row['remarks']
            # Week 6 suggestions inform extractive ranking but are checked against text.
            hints = row.get('candidate_signals', {}).get('entities', {})
            results[split].append({
                'listing_id': row['listing_id'], 'split': split,
                'lead2': summarizer.lead2_summary(remarks),
                'extractive': summarizer.extractive_summary(remarks, hints),
                'hybrid': summarizer.hybrid_summary(remarks, row),
                'supported_evidence': summarizer.supported_evidence(remarks, row),
                'hybrid_evidence': summarizer.hybrid_evidence(remarks, row),
                'output_status': 'machine_generated_not_human_reference',
            })
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    # Build in a temporary sibling so errors cannot leave a partial published run.
    with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix='.week8-') as temporary:
        stage = Path(temporary) / 'outputs'; stage.mkdir()
        for split, records in results.items():
            (stage / f'{split}_summaries.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
        sample = ['# Week 8 development examples', '',
                  'Machine-generated outputs; not human reference summaries. Evidence is automatically source-supported, not human-verified.', '']
        for row, result in zip(splits['dev'][:sample_size], results['dev'][:sample_size]):
            sample += [f"## Listing {row['listing_id']}", '', '**Original remarks**', '', row['remarks'], '']
            for key, title in [('lead2', 'Lead-2'), ('extractive', 'Extractive'), ('hybrid', 'Hybrid')]:
                sample += [f'**{title}**', '', result[key] or '(No supported summary)', '']
            sample += ['**Available source-supported evidence (not human-verified)**', '', '```json',
                       json.dumps(result['supported_evidence'], indent=2, ensure_ascii=False), '```', '']
        (stage / 'dev_examples.md').write_text('\n'.join(sample), encoding='utf-8')
        import nltk
        with nltk.data.find('tokenizers/punkt/english.pickle').open() as resource:
            tokenizer_hash = hashlib.sha256(resource.read()).hexdigest()
        metadata = {
            'input_hashes': before, 'counts': {s: len(r) for s, r in results.items()},
            'num_sentences': 2, 'development_examples': sample_size, 'nltk_version': nltk.__version__,
            'tokenizer': 'NLTK pretrained English Punkt plus real estate abbreviation list',
            'tokenizer_resource_sha256': tokenizer_hash,
            'code_sha256': {name: sha(ROOT / 'scripts' / name) for name in
                            ('listing_summarizer.py', 'generate_week8_summaries.py', 'entity_extractor.py', 'signal_extractor.py')},
            'taxonomy_sha256': sha(ROOT / 'data/processed/taxonomy.json'),
            'reference_policy': 'Reference files are never read; source dataset hashes track preservation.',
            'rouge': 'not_computed_by_generator',
        }
        (stage / 'run_manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        after = {p.name: sha(p) for p in tracked}
        if before != after:
            raise RuntimeError('Input artifacts changed during generation')
        os.rename(stage, output_dir)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--dev-only', action='store_true', help='Generate development only; never load test records or annotations')
    parser.add_argument('--sample-size', type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(generate(args.input_dir, args.output_dir, args.sample_size, args.dev_only)['counts']))


if __name__ == '__main__':
    main()
