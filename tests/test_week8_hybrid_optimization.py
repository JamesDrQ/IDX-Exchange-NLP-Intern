"""Hybrid regression cases use synthetic sources, never human references."""
import json
from pathlib import Path
import pytest
from scripts.listing_summarizer import ListingSummarizer
from scripts.generate_week8_summaries import generate

@pytest.fixture(scope='module')
def s():
    return ListingSummarizer()

@pytest.mark.parametrize('text,beds,baths', [
    ('This home features three bedrooms and two bathrooms.',3,2),
    ('This 4-bedroom, 3.5-bath home has a patio. A half bath serves the living room.',4,3.5),
    ('The home offers five bedrooms (one downstairs) and three full bathrooms.',5,3),
    ('This 3-bedroom, 2.5-bath residence is on a hill.',3,2.5),
    ('The home has 4 pristine and roomy bedrooms.',4,None),
    ('This is the larger 1 bedroom floorplan with a useful alcove.',1,None),
])
def test_supported_counts(s,text,beds,baths):
    fields=s.hybrid_evidence(text,{})['fields']
    assert fields['bedrooms']['value']==beds
    if baths is not None: assert fields['bathrooms']['value']==baths


def test_singular_grammar(s):
    result=s.hybrid_summary('One bedroom and one bathroom. Covered patio.',{'BedroomsTotal':1,'BathroomsTotalDecimal':1})
    assert '1 bedroom' in result and '1 bathroom' in result
    assert '1 bedrooms' not in result and '1 bathrooms' not in result

@pytest.mark.parametrize('text', [
    'Space for a future pool. Solar panels are installed.',
    'There is room to add a pool. Solar panels are installed.',
    'A pool could be installed. Solar panels are installed.',
    'A garage with ADU potential. Solar panels are installed.',
    'New-construction plans describe a 5,000 square foot design. Solar panels are installed.',
    'Choose homes ranging from 900 to 1,900 sq ft. Solar panels are installed.',
])
def test_hypothetical_features_not_promoted(s,text):
    result=s.hybrid_summary(text,{'City':'Austin','PoolPrivateYN':1})
    assert 'ADU' not in result and '5,000' not in result and '1,900' not in result
    if 'pool' in text.lower(): assert 'pool' not in result.lower()


def test_unbuilt_counts_not_existing(s):
    result=s.hybrid_summary('The proposed home has 4 bedrooms. The residence has not yet been constructed. Renderings are illustrative.',{'BedroomsTotal':4,'City':'Austin'})
    assert 'proposed construction' in result and 'not a completed residence' in result
    assert 'with 4 bedrooms' not in result

@pytest.mark.parametrize(('text','expected'),[
    ('The home is stripped to the studs and awaiting restoration. French doors open to a terrace.','awaiting restoration'),
    ('The property needs a little TLC and is being sold "AS/IS".','offered as-is'),
    ('This fixer-upper needs renovation.','in need of renovation'),
    ('This home is under construction.','under construction'),
    ('This is vacant land.','vacant land'),
])
def test_condition(s,text,expected):
    assert expected in s.hybrid_summary(text,{'City':'Austin'})


def test_negated_condition(s):
    result=s.hybrid_summary('This home does not need renovation. Covered patio.',{'City':'Austin'})
    assert 'in need of renovation' not in result

@pytest.mark.parametrize('text',[
    'No solar panels or private pool. Covered patio.',
    'There is no private pool. A private pool is included. Covered patio.',
    'The fireplace is not available. Covered patio.',
])
def test_negative_features(s,text):
    result=s.hybrid_summary(text,{'City':'Austin'})
    assert 'solar' not in result.lower() and 'pool' not in result.lower() and 'fireplace' not in result.lower()


def test_pool_scope(s):
    assert s.hybrid_evidence('The community offers a pool.',{'PoolPrivateYN':0})['features'][0]['value']=='community pool'
    result=s.hybrid_summary('This condo has access to a pool.',{})
    assert 'private pool' not in result and 'community pool' not in result


def test_priority_and_no_fabrication(s):
    text='Must see! A living room and dining room. Owned solar panels and a renovated kitchen. A covered patio.'
    result=s.hybrid_summary(text,{'City':'Austin'})
    assert 'owned solar panels' in result and 'renovated kitchen' in result
    assert 'Must see' not in result and 'pool' not in result
    assert '$' not in result and 'bedroom' not in result and 'bathroom' not in result
    assert result==s.hybrid_summary(text,{'City':'Austin'})


def test_no_component_or_conflicting_counts(s):
    for text in ('Each unit has 2 bedrooms.','There are 2 bedrooms upstairs.','This home has 2 bedrooms. This home has 3 bedrooms.'):
        assert 'bedrooms' not in s.hybrid_evidence(text,{})['fields']
    assert 'bedrooms' not in s.hybrid_evidence('This home has 3 bedrooms.',{'BedroomsTotal':3,'L_Keyword2':4})['fields']


def test_dev_only_generation_never_reads_references_or_test_text(tmp_path,monkeypatch):
    original_text=Path.read_text
    original_bytes=Path.read_bytes
    def guard_text(path,*args,**kwargs):
        assert path.name!='test_listings.jsonl'
        assert not ('reference' in path.name and path.suffix=='.csv')
        return original_text(path,*args,**kwargs)
    def guard_bytes(path,*args,**kwargs):
        assert not ('reference' in path.name and path.suffix=='.csv')
        return original_bytes(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',guard_text)
    monkeypatch.setattr(Path,'read_bytes',guard_bytes)
    a,b=tmp_path/'a',tmp_path/'b'
    assert generate(output_dir=a,dev_only=True)['counts']=={'dev':70}
    generate(output_dir=b,dev_only=True)
    assert not (a/'test_summaries.jsonl').exists()
    for p in a.iterdir(): assert p.read_bytes()==(b/p.name).read_bytes()
    assert len([json.loads(x) for x in (a/'dev_summaries.jsonl').read_text().splitlines()])==70


def test_short_source_cannot_override_structured_denial(s):
    assert 'private pool' not in s.hybrid_summary('A private pool is included.',{'PoolPrivateYN':0})
    assert 'garage' not in s.hybrid_summary('A garage is included.',{'GarageYN':0})
