"""Source preservation may review a native bleed; it must not hide authored overflow."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_lint_all.py'

def api():
    spec = importlib.util.spec_from_file_location('decor_lint', SCRIPT)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert hasattr(m, 'review_source_decorations'), 'source-aware bleed review missing'
    return m

def fixture(tmp_path, element=None):
    element = element or '<shape id="circle" type="ellipse" topLeftX="-30" topLeftY="17" width="505" height="505"><border color="rgb(89,89,89)" width="1"/></shape>'
    source = tmp_path/'source.xml'; source.write_text('<slide><data>'+element+'</data></slide>')
    authored = tmp_path/'authored.xml'; authored.write_bytes(source.read_bytes())
    visual = tmp_path/'source.png'; visual.write_bytes(b'source visual evidence')
    decision = tmp_path/'decision.json'
    definition = {'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'element_ids':['circle'], 'reason':'Source screenshot confirms a decorative edge bleed', 'visual_evidence':['source.png']}
    decision.write_text(json.dumps(definition))
    issue = {'code':'shape_out_of_canvas','level':'error','elements':['circle'], 'canvas':{'width':960,'height':540},'bbox':{'x':-30,'y':17,'width':505,'height':505}}
    report = {'summary':{'error_count':1},'document':{'errors':[]},'slides':[{'errors':[issue]}]}
    return source, authored, decision, report

def review(tmp_path, **kwargs):
    s,a,d,r = fixture(tmp_path,kwargs.pop('element',None))
    return api().review_source_decorations(r,r,a,s,d), (s,a,d,r)

def test_native_unchanged_circle_is_reviewed_without_mutating_raw_report(tmp_path):
    s,a,d,r = fixture(tmp_path); before=copy.deepcopy(r)
    result=api().review_source_decorations(r,r,a,s,d)
    assert result['ok'] and result['remaining_error_count']==0
    assert result['reviewed'][0]['element_id']=='circle'
    assert result['reviewed'][0]['source_sha256']==hashlib.sha256(s.read_bytes()).hexdigest()
    assert r==before

def test_changed_geometry_or_paint_cannot_use_source_decision(tmp_path):
    s,a,d,r=fixture(tmp_path)
    for old,new in [('topLeftX="-30"','topLeftX="-40"'),('89,89,89','192,0,0')]:
        a.write_text(s.read_text().replace(old,new))
        result=api().review_source_decorations(r,r,a,s,d)
        assert not result['ok'] and result['remaining_error_count']==1

def test_visible_text_even_on_rect_is_never_decoration(tmp_path):
    result,_=review(tmp_path,element='<shape id="circle" type="rect" topLeftX="-30"><content><p>New title</p></content></shape>')
    assert not result['ok'] and result['remaining_error_count']==1

def test_dynamic_text_field_is_never_hidden_as_blank_decoration(tmp_path):
    result,_=review(tmp_path,element='<shape id="circle" type="rect"><content><p><field type="slidenum"/></p></content></shape>')
    assert not result['ok'] and result['remaining_error_count']==1

def test_source_canvas_and_issue_must_match_and_other_errors_stay_blocked(tmp_path):
    s,a,d,r=fixture(tmp_path); source_report=copy.deepcopy(r)
    source_report['slides'][0]['errors'][0]['canvas']['width']=720
    assert not api().review_source_decorations(r,source_report,a,s,d)['ok']
    other={'code':'text_overflows_container','elements':['title'],'level':'error'}
    r['slides'][0]['errors'].append(other);r['summary']['error_count']=2
    result=api().review_source_decorations(r,r,a,s,d)
    assert result['ok'] and result['remaining_error_count']==1

def test_incomplete_source_lint_cannot_authorize_bleed(tmp_path):
    s,a,d,r=fixture(tmp_path);original=copy.deepcopy(r);original.pop('summary')
    assert not api().review_source_decorations(r,original,a,s,d)['ok']

def test_stale_source_missing_evidence_and_duplicate_ids_fail_closed(tmp_path):
    s,a,d,r=fixture(tmp_path); original=json.loads(d.read_text())
    for change in [{'source_sha256':'0'*64},{'visual_evidence':['missing.png']},{'element_ids':['circle','circle']}]:
        d.write_text(json.dumps({**original,**change}))
        result=api().review_source_decorations(r,r,a,s,d)
        assert not result['ok'] and result['remaining_error_count']==1

def test_chart_or_table_cannot_be_declared_decoration(tmp_path):
    result,_=review(tmp_path,element='<chart id="circle" topLeftX="-30"/>')
    assert not result['ok']

def test_unchanged_image_requires_source_evidence_and_keeps_token(tmp_path):
    s,a,d,r=fixture(tmp_path,'<img id="circle" src="source-token" topLeftX="-30" width="505" height="505"/>')
    r['slides'][0]['errors'][0]['code']='img_out_of_canvas'
    assert api().review_source_decorations(r,r,a,s,d)['remaining_error_count']==0
    a.write_text(s.read_text().replace('source-token','new-token'))
    assert not api().review_source_decorations(r,r,a,s,d)['ok']
