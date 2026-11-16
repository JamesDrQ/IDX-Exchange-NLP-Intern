"""Synthetic-reference tests only; no real held-out evaluation is performed."""
import csv
import json
from pathlib import Path
import shutil

import pytest

from scripts.prepare_week8_review import prepare, INPUT, OUTPUT, REFERENCE_COLUMNS
from scripts.evaluate_week8_rouge import (
    ROOT, REQUIRED, METHODS, approved, evaluate, freeze, read_references, rouge_l_f1, safe_write, sha, tokens,
)


def write_refs(path, rows):
    with path.open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=sorted(REQUIRED));writer.writeheader();writer.writerows(rows)


def human(identifier,text='a b c'):
    return dict(listing_id=identifier,reference_summary=text,reference_status='human_verified')


@pytest.fixture
def fake_run(tmp_path):
    data=tmp_path/'data';data.mkdir();pred=tmp_path/'pred';pred.mkdir()
    ids={'dev':['d0','d1'],'test':[f't{i}' for i in range(30)]}
    manifest={'splits':{s:{'listing_ids':v} for s,v in ids.items()}}
    (data/'manifest.json').write_text(json.dumps(manifest))
    for s in ids:
        (data/f'{s}_listings.jsonl').write_text(''.join(json.dumps({'listing_id':i,'split':s})+'\n' for i in ids[s]))
        (pred/f'{s}_summaries.jsonl').write_text(''.join(json.dumps({'listing_id':i,'split':s,'lead2':'a b c','extractive':'a c','hybrid':'x'})+'\n' for i in ids[s]))
    (pred/'run_manifest.json').write_text(json.dumps({'code_sha256':{'listing_summarizer.py':sha(ROOT/'scripts/listing_summarizer.py')},
        'taxonomy_sha256':sha(ROOT/'data/processed/taxonomy.json'),
        'input_hashes':{p.name:sha(p) for p in data.iterdir()}}))
    return data,pred,ids


@pytest.mark.parametrize(('pred','ref','expected'),[
    ('a b c','a b c',1),('a c','a b c',.8),('a b','b a',.5),
    ('a a b','a b b',2/3),('','a',0),('x','a',0),('','',0),
])
def test_metric_known_lcs(pred,ref,expected):
    assert rouge_l_f1(pred,ref)==pytest.approx(expected)


def test_normalization():
    assert tokens('CAFÉ, Ａ 2.5_BATH!')==['café','a','2','5','bath']


@pytest.mark.parametrize(('field','value'),[
    ('reference_status','pending_human_authoring'),('reference_summary',''),
    ('reference_summary','  \n  '),('reference_summary',None),
    ('reference_status','human_authored'),('reference_status',''),('reference_status',None),
])
def test_approval_requires_every_prerequisite(field,value):
    row=human('x');row[field]=value
    assert not approved(row)[0]


def test_dev_ignores_unreviewed_and_reports_same_denominator(fake_run,tmp_path):
    data,pred,_=fake_run
    a=human('d0');b=human('d1');b['reference_status']='human_authored'
    refs=tmp_path/'human.csv';write_refs(refs,[a,b]);before=sha(refs)
    report=evaluate('dev',refs,pred,data)
    assert report['approved_references']==1
    assert report['ignored_references']=={'unreviewed':1}
    assert report['methods']['lead2']=={'sample_count':1,'mean_rouge_l_f1':1}
    assert report['methods']['extractive']['mean_rouge_l_f1']==pytest.approx(.8)
    assert report['methods']['hybrid']['mean_rouge_l_f1']==0
    assert sha(refs)==before


def test_no_approved_references_has_null_not_zero(fake_run,tmp_path):
    data,pred,_=fake_run;row=human('d0');row['reference_summary']=''
    refs=tmp_path/'human.csv';write_refs(refs,[row])
    report=evaluate('dev',refs,pred,data)
    assert report['evaluation_status']=='no_approved_references'
    assert all(report['methods'][m]['mean_rouge_l_f1'] is None for m in METHODS)


def test_test_requires_all_30_and_matching_freeze(fake_run,tmp_path):
    data,pred,ids=fake_run;refs=tmp_path/'human.csv'
    write_refs(refs,[human(i) for i in ids['test'][:29]])
    with pytest.raises(ValueError,match='all 30'): evaluate('test',refs,pred,data)
    write_refs(refs,[human(i) for i in ids['test']])
    with pytest.raises(ValueError,match='freeze file'): evaluate('test',refs,pred,data)
    lock=tmp_path/'freeze.json'
    with pytest.raises(ValueError,match='confirm'): freeze(lock,pred,data)
    freeze(lock,pred,data,confirmed=True)
    # This scores synthetic strings in a temporary fixture, never real test data.
    assert evaluate('test',refs,pred,data,lock)['approved_references']==30
    path=pred/'test_summaries.jsonl';path.write_text(path.read_text().replace('a b c','z'))
    with pytest.raises(ValueError,match='freeze no longer'): evaluate('test',refs,pred,data,lock)


def test_duplicate_wrong_split_and_missing_predictions_rejected(fake_run,tmp_path):
    data,pred,_=fake_run;refs=tmp_path/'human.csv'
    for rows in ([human('d0'),human('d0')],[human('t0')]):
        write_refs(refs,rows)
        with pytest.raises(ValueError,match='reference IDs'): evaluate('dev',refs,pred,data)
    write_refs(refs,[human('d0')]);(pred/'dev_summaries.jsonl').write_text('')
    with pytest.raises(ValueError,match='Prediction membership'): evaluate('dev',refs,pred,data)


def test_predictions_cannot_be_read_as_references(fake_run,tmp_path):
    _,pred,_=fake_run
    with pytest.raises(ValueError,match='human annotation'): read_references(pred/'dev_summaries.jsonl')
    path=tmp_path/'pretend.csv';path.write_text('listing_id,summary\nd0,a b c\n')
    with pytest.raises(ValueError,match='human-reference columns'): read_references(path)


def test_output_guards(tmp_path):
    path=tmp_path/'report.json';safe_write(path,{'x':1})
    with pytest.raises(FileExistsError):safe_write(path,{'x':2})
    with pytest.raises(ValueError):safe_write(INPUT/'new_report.json',{})
    with pytest.raises(ValueError):safe_write(tmp_path/'human.csv',{})
    assert json.loads(path.read_text())=={'x':1}


def test_review_preparation_preserves_inputs_and_excludes_predictions(tmp_path):
    before={p.name:sha(p) for p in INPUT.iterdir() if p.is_file()}
    target=tmp_path/'packet';manifest=prepare(output_dir=target)
    assert manifest['selection']['dev']['count']==manifest['selection']['test']['count']==30
    for split in ('dev','test'):
        rows=read_references(target/f'{split}30_references.csv')
        assert all(not r['reference_summary'] for r in rows)
        assert not {'lead2','extractive','hybrid','generated_summary'} & set(rows[0])
        assert all(r['remarks'] and r['source_facts'] for r in rows)
    with (target/'teammate_ratings20.csv').open(encoding='utf-8-sig') as f: ratings=list(csv.DictReader(f))
    assert len({r['listing_id'] for r in ratings})==20
    assert all(all(r[k]=='' for k in ['factual_accuracy','completeness','readability','conciseness','comments']) for r in ratings)
    with pytest.raises(FileExistsError):prepare(output_dir=target)
    assert before=={p.name:sha(p) for p in INPUT.iterdir() if p.is_file()}


def test_existing_human_content_is_preserved(tmp_path):
    source=tmp_path/'original';shutil.copytree(INPUT,source)
    path=source/'dev_reference_review.csv'
    with path.open() as f: reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    target_id='1190591392'
    row=next(r for r in rows if r['listing_id']==target_id)
    row.update(reference_summary='Existing human text.',notes='Do not replace.',reviewer='Existing reviewer')
    with path.open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    prepare(input_dir=source,output_dir=tmp_path/'packet')
    saved=next(r for r in read_references(tmp_path/'packet/dev30_references.csv') if r['listing_id']==target_id)
    assert saved['reference_summary']=='Existing human text.' and saved['notes']=='Do not replace.'
    assert 'reference_origin' not in saved
    snapshot=json.loads((tmp_path/'packet/original_annotations_snapshot.json').read_text())
    preserved=next(r for r in snapshot['dev'] if r['listing_id']==target_id)
    assert preserved['reviewer']=='Existing reviewer'


def test_delivered_xlsx_source_columns_match_csv():
    for split in ('dev','test'):
        workbook=ROOT/f'outputs/week8_step4a/{split}30_references.xlsx'
        if not workbook.exists():pytest.skip('Workbook delivery not present')
        rows=read_references(workbook)
        originals=read_references(OUTPUT/f'{split}30_references.csv')
        assert len(rows)==30
        original_by_id={r['listing_id']:r for r in originals}
        for row in rows:
            # Human-editable cells are intentionally allowed to change later.
            for key in ('remarks','source_facts','features_evidence','missing_or_uncertain'):
                normalize=lambda x:x.replace('\r\n','\n').replace('\r','\n')
                assert normalize(row[key])==normalize(original_by_id[row['listing_id']][key])


def test_approval_ignores_optional_legacy_metadata():
    row=human('x')
    assert approved(row)==(True,'approved')
    row.update(reviewer='',reviewed_at='not a date',reference_origin='',independence_confirmed='')
    assert approved(row)==(True,'approved')


def test_test_gate_prevents_loading_prediction_text(fake_run,tmp_path,monkeypatch):
    data,pred,ids=fake_run
    refs=tmp_path/'human.csv';write_refs(refs,[human(i) for i in ids['test']])
    original=Path.read_text
    def guarded(path,*args,**kwargs):
        assert path != pred/'test_summaries.jsonl', 'Test predictions read before gates passed'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',guarded)
    with pytest.raises(ValueError,match='freeze file'):evaluate('test',refs,pred,data)
    pending=[human(i) for i in ids['test']];pending[0]['reference_status']='pending_human_authoring'
    write_refs(refs,pending)
    with pytest.raises(ValueError,match='all 30'):evaluate('test',refs,pred,data)
