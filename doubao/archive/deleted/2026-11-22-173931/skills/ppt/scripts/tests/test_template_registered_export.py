import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
import multiagent_sync as ms

def setup(tmp_path,monkeypatch,ids=('a','b')):
    work=tmp_path/'.lark-slides/template/test';(work/'manifest').mkdir(parents=True)
    (work/'manifest/template-index.json').write_text(json.dumps({'lark':{'deck':{'xml_presentation_id':'D'}}}))
    rows=[{'page':i,'mode':'component_reuse','source':'s.xml','xml_sha256':'a'*64,'slide_id':sid,'presentation':'D'} for i,sid in enumerate(('a','b'),1)]
    (work/'published-pages.json').write_text(json.dumps({'version':1,'presentation':'D','pages':rows}))
    (work/'page-plan.md').write_text('| P1 | content |\n| P2 | content |\n')
    calls=[]
    def cli(args,cwd):
        calls.append(args)
        return {'ok':True,'data':{'xml_presentation_id':'D','xml_presentation':{'content':'<presentation>'+''.join(f'<slide id="{x}"/>' for x in ids)+'</presentation>'}}}
    monkeypatch.setattr(ms,'_cli',cli)
    return work,calls

def test_gate_accepts_exact_registered_order(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    assert ms._template_registry_gate(tmp_path,'D') is None

def test_gate_reads_official_sml_namespace_prefix(tmp_path,monkeypatch):
    setup(tmp_path,monkeypatch)
    monkeypatch.setattr(ms,'_cli',lambda *args:{'ok':True,'data':{'xml_presentation_id':'D',
        'xml_presentation':{'content':'<s:presentation xmlns:s="https://www.larkoffice.com/sml/2.0">'
            '<s:slide id="a"><s:data/></s:slide><s:slide id="b"><s:data/></s:slide></s:presentation>'}}})
    assert ms._template_registry_gate(tmp_path,'D') is None

def test_export_refuses_unregistered_remote_page_before_export(tmp_path,monkeypatch):
    _,calls=setup(tmp_path,monkeypatch,('a','b','stranger'))
    result=ms.export('D',tmp_path,who='solo',strict=True)
    assert not result['ok'] and result['code']=='template_registry_mismatch'
    assert all('+export' not in c for c in calls)

def test_gate_refuses_pending_and_missing_registration(tmp_path,monkeypatch):
    work,calls=setup(tmp_path,monkeypatch)
    (work/'published-pages.pending.json').write_text(json.dumps({'presentation':'D'}))
    assert ms._template_registry_gate(tmp_path,'D')['code']=='template_publish_pending'
    assert calls==[]
    (work/'published-pages.pending.json').unlink();(work/'published-pages.json').unlink()
    assert ms._template_registry_gate(tmp_path,'D')['code']=='unregistered_pages'

def test_gate_refuses_wrong_order_and_incomplete_plan(tmp_path,monkeypatch):
    work,_=setup(tmp_path,monkeypatch,('b','a'))
    assert ms._template_registry_gate(tmp_path,'D')['code']=='template_registry_mismatch'
    (work/'page-plan.md').write_text('| P1 | content |\n| P2 | content |\n| P3 | content |\n')
    assert ms._template_registry_gate(tmp_path,'D')['code']=='template_plan_incomplete'

def test_unrelated_export_not_gated(tmp_path,monkeypatch):
    _,calls=setup(tmp_path,monkeypatch)
    assert ms._template_registry_gate(tmp_path,'OTHER') is None
    assert calls==[]

def test_corrupt_ledger_without_template_index_cannot_bypass(tmp_path,monkeypatch):
    work=tmp_path/'.lark-slides/template/vi';work.mkdir(parents=True)
    (work/'page-plan.md').write_text('LINK: L1\n| P1 | content |\n')
    (work/'published-pages.json').write_text('{corrupt')
    calls=[];monkeypatch.setattr(ms,'_cli',lambda *args:calls.append(args))
    result=ms._template_registry_gate(tmp_path,'D')
    assert result and result['code']=='template_registry_invalid'
    assert calls==[]
