"""ROUGE-L F1 for explicitly approved human references, with held-out gates.

No generated output is ever used as a reference fallback. Test scoring requires
all 30 approved references and a matching, explicitly created model freeze file.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/annotations/week8'
PREDICTIONS=ROOT/'data/processed/week8_summaries'
METHODS=('lead2','extractive','hybrid')
REQUIRED={'listing_id','reference_summary','reference_status'}
NORMALIZATION='Unicode NFKC + casefold; Unicode alphanumeric tokens excluding underscores; no stemming; document-level LCS; macro mean F1'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tokens(text):
    return re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',text).casefold(),flags=re.UNICODE)


def rouge_l_f1(prediction,reference):
    a,b=tokens(prediction),tokens(reference)
    if not a or not b:
        return 0.0
    previous=[0]*(len(b)+1)
    for token in a:
        current=[0]
        for j,other in enumerate(b,1):
            current.append(previous[j-1]+1 if token==other else max(previous[j],current[-1]))
        previous=current
    return 2*previous[-1]/(len(a)+len(b))


def read_references(path):
    path=Path(path)
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle)
            fields=reader.fieldnames or []
            rows=list(reader)
    elif path.suffix.lower()=='.xlsx':
        # Read the saved cell values, not Excel calculations or embedded code.
        with zipfile.ZipFile(path) as z:
            strings=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                strings=[''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
            workbook=ET.fromstring(z.read('xl/workbook.xml'))
            sheets=workbook.findall('s:sheets/s:sheet',NS)
            sheet=next((s for s in sheets if s.get('name')=='References'),None)
            if sheet is None:
                raise ValueError('Workbook must contain the source-only References sheet')
            rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
            target=next(r.get('Target') for r in rels if r.get('Id')==rid)
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            grid=[]
            for row in ET.fromstring(z.read(target)).findall('s:sheetData/s:row',NS):
                cells={}
                for cell in row.findall('s:c',NS):
                    col=re.match(r'[A-Z]+',cell.get('r')).group()
                    index=0
                    for letter in col: index=index*26+ord(letter)-64
                    if cell.find('s:f',NS) is not None:
                        raise ValueError('Reference worksheets must contain entered text, not formulas')
                    if cell.get('t')=='inlineStr':
                        value=''.join(cell.find('s:is',NS).itertext())
                    else:
                        value=cell.findtext('s:v','',NS)
                        if cell.get('t')=='s': value=strings[int(value)]
                    cells[index-1]=value
                grid.append([cells.get(i,'') for i in range(max(cells,default=-1)+1)])
            fields=grid[0] if grid else []
            rows=[{name:row[i] if i<len(row) else '' for i,name in enumerate(fields)} for row in grid[1:] if any(row)]
    else:
        raise ValueError('References must be a CSV or XLSX human annotation file, not prediction JSONL')
    if not REQUIRED <= set(fields) or len(fields)!=len(set(fields)):
        raise ValueError('Missing or duplicate human-reference columns')
    return rows


def approved(row):
    """The single annotator approves text with one status; metadata is optional."""
    if str(row.get('reference_status') or '').strip()!='human_verified': return False,'unreviewed'
    summary=row.get('reference_summary')
    if not isinstance(summary,str) or not summary.strip(): return False,'missing_reference'
    return True,'approved'


def validate_prediction_run(prediction_dir, data_dir):
    prediction_dir,data_dir=Path(prediction_dir),Path(data_dir)
    run=json.loads((prediction_dir/'run_manifest.json').read_text())
    for name,h in run['code_sha256'].items():
        if sha(ROOT/'scripts'/name)!=h: raise ValueError('Predictions are stale relative to implementation: '+name)
    if sha(ROOT/'data/processed/taxonomy.json')!=run['taxonomy_sha256']:
        raise ValueError('Prediction taxonomy has changed')
    for name in ('manifest.json','dev_listings.jsonl','test_listings.jsonl'):
        if sha(data_dir/name)!=run['input_hashes'][name]: raise ValueError('Frozen dataset changed: '+name)
    return run


def freeze(output, prediction_dir=PREDICTIONS, data_dir=DATA, confirmed=False):
    if not confirmed: raise ValueError('Explicit --confirm-models-frozen is required')
    output=Path(output)
    validate_prediction_run(prediction_dir,data_dir)
    payload={'models_frozen':True,'normalization':NORMALIZATION,
             'prediction_hashes':{s:sha(Path(prediction_dir)/f'{s}_summaries.jsonl') for s in ('dev','test')},
             'prediction_run_sha256':sha(Path(prediction_dir)/'run_manifest.json'),
             'dataset_manifest_sha256':sha(Path(data_dir)/'manifest.json'),
             'evaluator_sha256':sha(Path(__file__))}
    safe_write(output,payload)
    return payload


def safe_write(output,payload):
    output=Path(output)
    if output.suffix.lower()!='.json': raise ValueError('Output must be a new JSON file')
    annotations=(ROOT/'data/annotations').resolve()
    if output.resolve()==annotations or annotations in output.resolve().parents:
        raise ValueError('Evaluation outputs cannot be written into annotation storage')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as handle:
        json.dump(payload,handle,ensure_ascii=False,indent=2);handle.write('\n')


def evaluate(split,references,prediction_dir=PREDICTIONS,data_dir=DATA,freeze_file=None):
    if split not in ('dev','test'): raise ValueError('Choose dev or test explicitly')
    prediction_dir,data_dir=Path(prediction_dir),Path(data_dir)
    validate_prediction_run(prediction_dir,data_dir)
    manifest=json.loads((data_dir/'manifest.json').read_text())
    expected=manifest['splits'][split]['listing_ids']
    rows=read_references(references)
    ids=[r['listing_id'].strip() for r in rows]
    if len(ids)!=len(set(ids)) or any(i not in expected for i in ids):
        raise ValueError('Duplicate, unknown, or wrong-split reference IDs')
    ignored=Counter(); accepted=[]
    for row in rows:
        ok,reason=approved(row)
        if ok: accepted.append(row)
        else: ignored[reason]+=1
    if split=='test':
        if set(ids)!=set(expected) or len(accepted)!=len(expected) or len(expected)!=30:
            raise ValueError('Held-out evaluation requires all 30 nonempty, human-verified references')
        if freeze_file is None: raise ValueError('Held-out evaluation requires an explicit model freeze file')
        frozen=json.loads(Path(freeze_file).read_text())
        expected_freeze={'models_frozen':True,'normalization':NORMALIZATION,
                         'prediction_hashes':{s:sha(prediction_dir/f'{s}_summaries.jsonl') for s in ('dev','test')},
                         'prediction_run_sha256':sha(prediction_dir/'run_manifest.json'),
                         'dataset_manifest_sha256':sha(data_dir/'manifest.json'),
                         'evaluator_sha256':sha(Path(__file__))}
        if frozen!=expected_freeze: raise ValueError('Model freeze no longer matches predictions, dataset, or evaluator')
    # Do not load held-out prediction text until reference and freeze gates pass.
    predictions={}
    for line in (prediction_dir/f'{split}_summaries.jsonl').read_text().splitlines():
        row=json.loads(line)
        if row['listing_id'] in predictions or row.get('split')!=split or any(not isinstance(row.get(m),str) for m in METHODS):
            raise ValueError('Invalid or duplicate prediction record')
        predictions[row['listing_id']]=row
    if set(predictions)!=set(expected): raise ValueError('Prediction membership does not match frozen split')
    scores={method:[] for method in METHODS}
    for row in accepted:
        for method in METHODS:
            scores[method].append(rouge_l_f1(predictions[row['listing_id'].strip()][method],row['reference_summary']))
    return {'split':split,'evaluation_status':'scored' if accepted else 'no_approved_references',
            'metric':'ROUGE-L F1','normalization':NORMALIZATION,'split_size':len(expected),
            'reference_rows':len(rows),'approved_references':len(accepted),'ignored_references':dict(ignored),
            'not_in_annotation_file':len(set(expected)-set(ids)),
            'methods':{m:{'sample_count':len(scores[m]),'mean_rouge_l_f1':sum(scores[m])/len(scores[m]) if scores[m] else None} for m in METHODS},
            'reference_sha256':sha(references),'prediction_sha256':sha(prediction_dir/f'{split}_summaries.jsonl'),
            'freeze_sha256':sha(freeze_file) if split=='test' else None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze'); f.add_argument('--confirm-models-frozen',action='store_true'); f.add_argument('--output',type=Path,required=True)
    e=sub.add_parser('evaluate'); e.add_argument('--split',choices=['dev','test'],required=True)
    e.add_argument('--references',type=Path,required=True); e.add_argument('--freeze-file',type=Path); e.add_argument('--output',type=Path,required=True)
    for child in (e,f): child.add_argument('--prediction-dir',type=Path,default=PREDICTIONS)
    args=parser.parse_args()
    try:
        if args.action=='freeze': payload=freeze(args.output,args.prediction_dir,confirmed=args.confirm_models_frozen)
        else:
            if args.output.resolve()==args.references.resolve(): raise ValueError('Cannot overwrite references')
            payload=evaluate(args.split,args.references,args.prediction_dir,freeze_file=args.freeze_file)
            safe_write(args.output,payload)
        print(json.dumps(payload,indent=2))
    except (ValueError,FileExistsError) as exc: parser.exit(2,str(exc)+'\n')


if __name__=='__main__': main()
