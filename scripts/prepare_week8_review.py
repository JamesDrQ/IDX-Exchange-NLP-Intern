"""Prepare source-only reference packets and separate prediction rating forms."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

from scripts.entity_extractor import EntityExtractor, BEDROOM_RE, BATHROOM_RE
from scripts.signal_extractor import _boolean, _negated

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'data/annotations/week8'
OUTPUT = ROOT / 'data/annotations/week8_review'
PREDICTIONS = ROOT / 'data/processed/week8_summaries'
REFERENCE_COLUMNS = ['listing_id', 'reference_summary', 'reference_status',
                     'remarks', 'source_facts', 'features_evidence', 'missing_or_uncertain', 'notes',
                     'batch', 'priority_reason', 'source_fields_json']
RATING_COLUMNS = ['rating_id', 'listing_id', 'generated_summary', 'factual_accuracy',
                  'completeness', 'readability', 'conciseness', 'comments', 'remarks',
                  'source_facts', 'features_evidence', 'missing_or_uncertain', 'rater',
                  'rated_at', 'rating_status']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence(row, extractor):
    """Source facts and literal evidence spans; no generated output is consulted."""
    source, remarks = row['source_fields'], row['remarks']
    bed = list(dict.fromkeys(m.group() for m in BEDROOM_RE.finditer(remarks)))
    bath = list(dict.fromkeys(m.group() for m in BATHROOM_RE.finditer(remarks)))
    facts, uncertainties = [], []
    for key, label, quotes in [('L_Keyword2', 'Bedrooms', bed), ('LM_Dec_3', 'Bathrooms', bath)]:
        if source.get(key) is not None:
            facts.append(f'{label}: {source[key]} ({key})')
        elif quotes:
            facts.append(f'{label}, remarks only: ' + '; '.join('“'+q+'”' for q in quotes))
            uncertainties.append(label + ': no structured total; verify quoted counts and dwelling scope.')
        else:
            facts.append(label + ': not specified in the available structured fields or recognized count phrases.')
            uncertainties.append(label + ': not established; read full remarks.')
    for key, label in [('L_SystemPrice', 'Price (USD)'), ('L_City', 'City')]:
        value = source.get(key)
        facts.append(f'{label}: {value if value not in (None, "") else "not provided"} ({key})')
        if value in (None, '', 'Other'):
            uncertainties.append(label + ': missing or nonspecific.')
    features = []
    for key, label in [('GarageYN', 'Garage'), ('FireplaceYN', 'Fireplace'), ('PoolPrivateYN', 'Private pool')]:
        state = _boolean(source.get(key))
        if state is not None:
            features.append(f'{label}: {"yes" if state else "no"} ({key}={source[key]})')
    if source.get('PoolFeatures') not in (None, ''):
        features.append('PoolFeatures=' + str(source['PoolFeatures']))
    snippets = []
    for start, end, label in extractor.extract_spans(remarks):
        if label != 'AMENITY' or _negated(remarks, start, end):
            continue
        prefix = re.split(r'[.!?;]', remarks[:start])[-1]
        if re.search(r'\b(?:no|without|not|could|may|might|potential|proposed|planned|near|nearby|room for|space for|build|add)\b', prefix, re.I):
            continue
        quote = remarks[start:end]
        if quote.casefold() not in {s.casefold() for s in snippets}:
            snippets.append(quote)
    if snippets:
        features.append('Literal feature phrases to verify in remarks: ' + '; '.join('“'+s+'”' for s in snippets[:8]))
    multiple_counts = len({extractor._quantity_value(q) for q in bed}) > 1 or len({extractor._quantity_value(q) for q in bath}) > 1
    scope_warning = multiple_counts or bool(re.search(r'\b(?:guest (?:house|unit)|main residence|adu|duplex|half bath|homes range|bedroom homes|rear home|front home)\b', remarks, re.I))
    if scope_warning:
        uncertainties.append('Check dwelling scope, component counts, proposals, or advertised floor-plan ranges.')
    if not features:
        features.append('No supported feature has been preselected; inspect the original remarks.')
    uncertainties.append('Feature phrases are source excerpts, not verified amenity labels. Check negation, proposals, access and conflicts.')
    return {'source_facts': '\n'.join(facts), 'features_evidence': '\n'.join(features),
            'missing_or_uncertain': '\n'.join(uncertainties), 'has_counts': bool(bed and bath),
            'complex': scope_warning or len(uncertainties) > 3 or len(remarks) > 2200}


def choose_development(rows, info):
    remaining = {r['listing_id']: r for r in rows}
    chosen = []
    policies = [
        ('1. Clearer records', lambda r: (not info[r['listing_id']]['has_counts'], info[r['listing_id']]['complex'], len(r['remarks']), r['listing_id']), 'Begin with shorter records that state both counts where possible.'),
        ('2. Missing facts', lambda r: (info[r['listing_id']]['has_counts'], len(r['remarks']), r['listing_id']), 'Practice omitting unsupported or missing facts.'),
        ('3. Complex records', lambda r: (not info[r['listing_id']]['complex'], -len(r['remarks']), r['listing_id']), 'Resolve longer descriptions and dwelling-scope ambiguity.'),
    ]
    for batch, key, reason in policies:
        for row in sorted(remaining.values(), key=key)[:10]:
            chosen.append((row, batch, reason)); remaining.pop(row['listing_id'])
    return chosen


def write_csv(path, columns, rows):
    with path.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)


def prepare(input_dir=INPUT, output_dir=OUTPUT, predictions_dir=PREDICTIONS):
    input_dir, output_dir, predictions_dir = map(Path, (input_dir, output_dir, predictions_dir))
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite review work: {output_dir}')
    frozen = json.loads((input_dir/'manifest.json').read_text())
    before = {p.name: sha(p) for p in input_dir.iterdir() if p.is_file()}
    extractor = EntityExtractor()
    rows_by_split, metadata, original_annotations = {}, {}, {}
    info = {}
    for split in ('dev', 'test'):
        source = input_dir/f'{split}_listings.jsonl'
        if sha(source) != frozen['initial_artifact_sha256'][source.name]:
            raise ValueError('Frozen source hash mismatch')
        rows = [json.loads(line) for line in source.read_text().splitlines()]
        with (input_dir/f'{split}_reference_review.csv').open(newline='', encoding='utf-8-sig') as handle:
            original_annotations[split] = list(csv.DictReader(handle))
            old = {r['listing_id']: r for r in original_annotations[split]}
            if len(old) != len(original_annotations[split]):
                raise ValueError('Duplicate annotation IDs')
        if [r['listing_id'] for r in rows] != frozen['splits'][split]['listing_ids'] or set(old) != {r['listing_id'] for r in rows}:
            raise ValueError('Source or annotation IDs do not match frozen membership')
        info.update({r['listing_id']: evidence(r, extractor) for r in rows})
        selection = choose_development(rows, info) if split == 'dev' else [(r, 'Held-out test', 'All 30 test records; author independently of predictions.') for r in rows]
        packet = []
        for row, batch, reason in selection:
            prior = old[row['listing_id']]
            item = {key: prior.get(key, '') for key in REFERENCE_COLUMNS}
            item.update({k: info[row['listing_id']][k] for k in ('source_facts','features_evidence','missing_or_uncertain')})
            item.update(listing_id=row['listing_id'], remarks=row['remarks'], batch=batch, priority_reason=reason,
                        source_fields_json=json.dumps(row['source_fields'], ensure_ascii=False))
            # Do not infer authorship/independence or overwrite any existing reference.
            packet.append(item)
        rows_by_split[split] = packet
        metadata[split] = {'listing_ids': [r['listing_id'] for r in packet], 'count': len(packet)}
    # Prediction access is confined to the separate teammate-rating packet.
    predictions = [json.loads(line) for line in (predictions_dir/'dev_summaries.jsonl').read_text().splitlines()]
    sources = {r['listing_id']: r for r in map(json.loads, (input_dir/'dev_listings.jsonl').read_text().splitlines())}
    if len(predictions) != len(sources) or {r['listing_id'] for r in predictions} != set(sources):
        raise ValueError('Development predictions do not match source membership')
    ranked = sorted(predictions, key=lambda r: hashlib.sha256(('week8-ratings-42:'+r['listing_id']).encode()).hexdigest())[:20]
    ratings, key = [], []
    for i, pred in enumerate(ranked):
        method = ('lead2', 'extractive', 'hybrid')[i % 3]
        row, facts = sources[pred['listing_id']], info[pred['listing_id']]
        rating_id = f'R{i+1:02d}'
        ratings.append(dict.fromkeys(RATING_COLUMNS, '') | {
            'rating_id': rating_id, 'listing_id': row['listing_id'], 'generated_summary': pred[method],
            'remarks': row['remarks'], 'source_facts': facts['source_facts'],
            'features_evidence': facts['features_evidence'], 'missing_or_uncertain': facts['missing_or_uncertain'],
            'rating_status': 'pending',
        })
        key.append({'rating_id': rating_id, 'listing_id': row['listing_id'], 'method': method})
    output_dir.mkdir(parents=True)
    for split, packet in rows_by_split.items():
        write_csv(output_dir/f'{split}30_references.csv', REFERENCE_COLUMNS, packet)
    write_csv(output_dir/'teammate_ratings20.csv', RATING_COLUMNS, ratings)
    # Preserve old annotation columns in a complete sidecar, not in model-free cards.
    (output_dir/'original_annotations_snapshot.json').write_text(json.dumps(original_annotations, indent=2))
    (output_dir/'rating_method_key.json').write_text(json.dumps(key, indent=2)+'\n')
    manifest = {'input_hashes': before, 'selection': metadata, 'priority_policy': 'Three source-only development batches of 10; all 30 test records.',
                'ratings': {'count':20, 'split':'dev', 'method_counts':{'lead2':7,'extractive':7,'hybrid':6},
                            'prediction_sha256':sha(predictions_dir/'dev_summaries.jsonl')},
                'reference_policy':'Source-only evidence. No generated summaries, model scores or verified claims are inserted into references.'}
    (output_dir/'review_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Typed JSON intermediate for workbook authoring; reference arrays contain no predictions.
    (output_dir/'workbook_data.json').write_text(json.dumps({'reference_columns':REFERENCE_COLUMNS,'rating_columns':RATING_COLUMNS,
                                                           'dev':rows_by_split['dev'],'test':rows_by_split['test'],'ratings':ratings}, ensure_ascii=False,indent=2))
    if before != {p.name:sha(p) for p in input_dir.iterdir() if p.is_file()}:
        raise RuntimeError('Original inputs changed during preparation')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    args=parser.parse_args()
    print(json.dumps(prepare(output_dir=args.output_dir)['selection'],indent=2))
