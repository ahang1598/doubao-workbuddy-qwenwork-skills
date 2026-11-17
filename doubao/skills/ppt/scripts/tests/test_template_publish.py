"""Only subprocess boundaries are simulated; files and registration logic are real."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_publish.py'
XML = '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data><shape type="text"><content><p>真实正文</p></content></shape></data></slide>'


def module():
    assert SCRIPT.exists(), 'single-page template publisher is missing'
    spec = importlib.util.spec_from_file_location('template_publish', SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Runner:
    """Legacy scripted writes/readbacks with a separate, empty initial deck lookup.

    Initial-blank integration tests use a stateful server and inspect every call.
    These older fixtures retain their scripted operation sequence in ``calls``;
    the new convenience queries are recorded explicitly in ``initial_reads``.
    """
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.initial_reads = []

    def __call__(self, args, **kwargs):
        if args[:3] == ['lark-cli', 'slides', '+xml-get'] and '--slide-id' not in args:
            self.initial_reads.append((args, kwargs))
            deck = args[args.index('--presentation') + 1]
            return subprocess.CompletedProcess(args, 0, json.dumps({'ok': True, 'data': {
                'xml_presentation_id': deck, 'xml_presentation': {'content': '<presentation id="' + deck + '"/>'}}}), '')
        self.calls.append((args, kwargs))
        response = self.responses.pop(0)
        if callable(response):
            response = response(args, kwargs)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, subprocess.CompletedProcess):
            return response
        return subprocess.CompletedProcess(args, 0, json.dumps(response), '')


READY = {'ok': True, 'status': 'ready_to_write'}
SUCCESS = {'ok': True, 'data': {'slide_id': 'S1', 'xml_presentation_id': 'D'}}


def test_independent_user_overrides_block_a_reference_card_that_omits_request(tmp_path):
    _,card=style_inputs(tmp_path,'rgb(62,74,46)')
    d=json.loads(card.read_text())
    d['roles']['main_title']['selected']['color']='#3E4A2E'
    d['roles']['main_title']['field_basis']['color']='reference_candidate'
    card.write_text(json.dumps(d))
    (card.parent/'style-overrides.json').write_text(json.dumps({
        'main_title':{'basis':'explicit_user','values':{'color':'#C49A3C'}}}))
    runner=Runner()
    result=invoke(tmp_path,runner,link='L9')
    assert result['status']=='style_card_blocked' and not runner.calls
    assert not (tmp_path/'published-pages.pending.json').exists()


def test_independent_user_overrides_are_verified_and_registered_with_hash(tmp_path):
    _,card=style_inputs(tmp_path)
    requested={'main_title':{'basis':'explicit_user','values':{'color':'#C49A3C'}}}
    d=json.loads(card.read_text());d['user_overrides']=requested;card.write_text(json.dumps(d))
    overrides=card.parent/'style-overrides.json';overrides.write_text(json.dumps(requested))
    result=invoke(tmp_path,Runner(READY,SUCCESS),link='L9')
    assert result['ok']
    row=json.loads((tmp_path/'published-pages.json').read_text())['pages'][0]
    import hashlib
    assert row['style_card']['user_overrides']==str(overrides)
    assert row['style_card']['user_overrides_sha256']==hashlib.sha256(overrides.read_bytes()).hexdigest()


def test_user_requirement_file_without_style_card_cannot_skip_l9_check(tmp_path):
    folder=tmp_path/'manifest';folder.mkdir()
    (folder/'style-overrides.json').write_text(json.dumps({
        'main_title':{'basis':'explicit_user','values':{'color':'#C49A3C'}}}))
    runner=Runner()
    result=invoke(tmp_path,runner,link='L9')
    assert result['status']=='style_card_blocked' and not runner.calls


def invoke(tmp_path, runner, **kwargs):
    """Legacy strict-policy regressions; default advisory uses a separate fixture."""
    xml = tmp_path / 'authoring' / 'slide-01.xml'
    xml.parent.mkdir(exist_ok=True)
    if not xml.exists():
        xml.write_text(XML)
    return module().publish(validation_policy=kwargs.pop('validation_policy', 'strict'),
                            presentation=kwargs.pop('presentation', 'D'), xml=xml,
                            page=kwargs.pop('page', 1), mode='component_reuse',
                            work_dir=tmp_path, runner=runner, **kwargs)


def test_exit_zero_business_failure_is_not_registered_and_full_report_retained(tmp_path):
    detail = {'slides': [{'errors': [{'message': 'x' * 15000}]}]}
    failure = {'ok': False, 'error': {'code': 4000153, 'message': json.dumps(detail)}}
    runner = Runner(READY, failure)
    out = invoke(tmp_path, runner)
    assert not out['ok'] and out['status'] == 'write_rejected'
    assert not (tmp_path / 'published-pages.json').exists()
    assert not (tmp_path / 'published-pages.pending.json').exists()
    report = json.loads(Path(out['report_path']).read_text())
    assert report['write']['json'] == failure
    assert report['write']['decoded_details']['error.message'] == detail
    assert '--no-lint' not in runner.calls[1][0]


def test_success_without_id_remains_unknown_and_cannot_be_resent(tmp_path):
    out = invoke(tmp_path, Runner(READY, {'ok': True, 'data': {}}))
    assert not out['ok'] and out['status'] == 'write_unknown'
    assert not (tmp_path / 'published-pages.json').exists()
    runner = Runner()
    retry = invoke(tmp_path, runner)
    assert retry['status'] == 'recovery_required' and not runner.calls
    assert '回读' in retry['error']


def test_success_registers_only_after_pending_and_preserves_stdin_and_sha(tmp_path):
    def written(args, kwargs):
        intent = json.loads((tmp_path / 'published-pages.pending.json').read_text())
        assert intent['page'] == 1 and intent['presentation'] == 'D'
        assert not (tmp_path / 'published-pages.json').exists()
        assert args == ['lark-cli', 'slides', '+add-slide', '--presentation', 'D', '--slide', '-', '--json']
        assert kwargs['input'] == XML and kwargs['cwd'] == str(tmp_path)
        return SUCCESS
    runner = Runner(READY, written)
    source = tmp_path / 'source.xml'; source.write_text(XML)
    out = invoke(tmp_path, runner, source=source)
    assert out['ok'] and out['slide_id'] == 'S1'
    record = json.loads((tmp_path / 'published-pages.json').read_text())
    assert record['presentation'] == 'D'
    import hashlib
    assert record['pages'] == [{'page': 1, 'mode': 'component_reuse', 'source': str(source),
                                'xml_sha256': hashlib.sha256(XML.encode()).hexdigest(),
                                'slide_id': 'S1', 'presentation': 'D', 'validation_policy': 'strict'}]
    lint = runner.calls[0][0]
    assert '--solo' in lint and '--page-role' in lint and '--source' in lint
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_same_page_updates_registered_id_instead_of_adding(tmp_path):
    assert invoke(tmp_path, Runner(READY, SUCCESS))['ok']
    runner = Runner(READY, SUCCESS)
    out = invoke(tmp_path, runner)
    assert out['ok']
    assert runner.calls[1][0] == ['lark-cli', 'slides', '+update-slide', '--presentation', 'D',
                                 '--slide-id', 'S1', '--content', '-', '--json']
    assert len(json.loads((tmp_path / 'published-pages.json').read_text())['pages']) == 1


def layout_inputs(tmp_path):
    import sys
    sys.path.insert(0, str(SCRIPT.parent))
    from scripts.template.template_layouts import inspect_template
    from scripts.template.template_layout_contract import build_layout_contract, generate_skeleton
    spec = importlib.util.spec_from_file_location('lf', Path(__file__).with_name('test_template_layouts.py'))
    lf=importlib.util.module_from_spec(spec);spec.loader.exec_module(lf)
    source=tmp_path/'input.pptx';lf.fixture(source)
    manifest=inspect_template(source)
    contract=build_layout_contract(manifest,'Inherited',instance_id='P1')
    folder=tmp_path/'manifest';folder.mkdir()
    (folder/'layouts.json').write_text(json.dumps(manifest))
    contracts=folder/'layout-contracts';contracts.mkdir()
    (contracts/'page-01.json').write_text(json.dumps(contract))
    xml=tmp_path/'authoring/slide-01.xml';xml.parent.mkdir()
    import xml.etree.ElementTree as ET
    skeleton=ET.fromstring(generate_skeleton(contract))
    title=next(n for n in skeleton.findall('{*}data/{*}shape') if n.get('id')==contract['slots'][0]['slot_id'])
    title.find('{*}content/{*}p').text='真实标题'
    xml.write_text(ET.tostring(skeleton,encoding='unicode'))
    return xml,contracts/'page-01.json'


def test_l3_source_slots_are_checked_before_lint_or_remote_write(tmp_path):
    xml,contract=layout_inputs(tmp_path)
    xml.write_text(xml.read_text().replace('topLeftX="20"','topLeftX="60"').replace('width="700"','width="840"'))
    runner=Runner()
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,link='L3',runner=runner)
    assert result['status']=='layout_contract_blocked' and not runner.calls
    report=json.loads(Path(result['report_path']).read_text())
    assert any(e['code']=='title_bbox_mismatch' for e in report['layout_contract']['errors'])
    assert not (tmp_path/'published-pages.pending.json').exists()


def test_l3_cannot_omit_contract_or_edit_source_slot_to_fit_authored_page(tmp_path):
    xml,contract=layout_inputs(tmp_path);definition=json.loads(contract.read_text())
    definition['slots'][0]['bbox']['x']=60;contract.write_text(json.dumps(definition))
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,runner=Runner())
    assert result['status']=='layout_contract_blocked'
    contract.unlink()
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,link='L3',runner=Runner())
    assert result['status']=='layout_contract_blocked'


def test_valid_l3_contract_is_recorded_with_acknowledged_write(tmp_path):
    xml,contract=layout_inputs(tmp_path);runner=Runner(READY,SUCCESS)
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,link='L3',runner=runner)
    assert result['ok'] and len(runner.calls)==2
    report=json.loads(Path(result['report_path']).read_text())
    assert report['layout_contract']['ok']
    row=json.loads((tmp_path/'published-pages.json').read_text())['pages'][0]
    assert row['layout_contract']['path']==str(contract)
    assert row['layout_contract']['layout']=='Inherited'


def test_explicit_non_l3_link_is_not_locked_by_unused_layout_manifest(tmp_path):
    xml,_=layout_inputs(tmp_path)
    xml.write_text(XML)
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,link='L4',runner=Runner(READY,SUCCESS))
    assert result['ok']


def style_inputs(tmp_path, color='rgb(196,154,60)', kind='title'):
    folder=tmp_path/'manifest';folder.mkdir(exist_ok=True)
    card=folder/'style-card.json'
    card.write_text(json.dumps({'schema_version':1,'card_type':'visual_style_card','roles':{
        'main_title':{'selected':{'fontFamily':'Noto Serif SC','fontSize':30,'color':'#C49A3C'},
                      'field_basis':{'color':'explicit_user'}}}}))
    xml=tmp_path/'authoring/slide-01.xml';xml.parent.mkdir(exist_ok=True)
    xml.write_text(f'<slide><data><shape id="main" type="text"><content textType="{kind}" fontFamily="Noto Serif SC" fontSize="30" color="{color}"><p>独立标题</p></content></shape>'
                   '<shape id="kicker" type="text"><content textType="caption" fontFamily="Noto Serif SC" fontSize="12" color="#C49A3C"><p>编号</p></content></shape></data></slide>')
    return xml,card


def test_l9_default_style_card_blocks_green_main_title_before_any_write(tmp_path):
    _,card=style_inputs(tmp_path,'rgb(62,74,46)');runner=Runner()
    result=invoke(tmp_path,runner,link='L9')
    assert result['status']=='style_card_blocked' and not runner.calls
    report=json.loads(Path(result['report_path']).read_text())
    assert any(e['code']=='role_color_mismatch' and e['element_id']=='main' for e in report['style_card']['errors'])
    assert report['style_card']['source']['path']==str(card)
    assert not (tmp_path/'published-pages.pending.json').exists()


def test_l9_gold_title_style_card_is_recorded_on_acknowledged_write(tmp_path):
    _,card=style_inputs(tmp_path);runner=Runner(READY,SUCCESS)
    result=invoke(tmp_path,runner,link='L9')
    assert result['ok'] and len(runner.calls)==2
    report=json.loads(Path(result['report_path']).read_text())
    assert report['style_card']['ok'] and report['style_card']['semantic_copy']=='not_assessed'
    row=json.loads((tmp_path/'published-pages.json').read_text())['pages'][0]
    import hashlib
    assert row['style_card']['path']==str(card)
    assert row['style_card']['sha256']==hashlib.sha256(card.read_bytes()).hexdigest()


def test_explicit_style_card_and_helper_role_bindings_are_used(tmp_path):
    _,card=style_inputs(tmp_path,kind='body');bindings=tmp_path/'bindings.json'
    bindings.write_text(json.dumps({'main_title':['main']}))
    result=invoke(tmp_path,Runner(READY,SUCCESS),link='L9',style_card=card,style_bindings=bindings)
    assert result['ok']
    report=json.loads(Path(result['report_path']).read_text())
    assert report['style_card']['source']['bindings']==str(bindings)


def test_no_card_l9_and_other_link_with_unused_default_card_preserve_existing_flow(tmp_path):
    no_card=tmp_path/'no-card';no_card.mkdir()
    assert invoke(no_card,Runner(READY,SUCCESS),link='L9')['ok']
    unrelated=tmp_path/'unrelated';unrelated.mkdir();style_inputs(unrelated,'rgb(62,74,46)')
    assert invoke(unrelated,Runner(READY,SUCCESS),link='L4')['ok']


def test_missing_explicit_style_card_is_blocked_without_subprocess(tmp_path):
    runner=Runner()
    result=invoke(tmp_path,runner,link='L9',style_card=tmp_path/'missing.json')
    assert result['status']=='style_card_blocked' and not runner.calls


def test_source_decorations_are_forwarded_to_strict_preflight(tmp_path):
    decision=tmp_path/'decorations.json';decision.write_text('{}')
    runner=Runner(READY,SUCCESS)
    assert invoke(tmp_path,runner,source_decorations=decision)['ok']
    assert '--source-decorations' in runner.calls[0][0]

def chart_inputs(tmp_path, role='data_page'):
    spec=importlib.util.spec_from_file_location('chart_fixture',Path(__file__).with_name('test_template_chart_contract.py'))
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    api=fixture.module();inventory=fixture.inventory()
    data={'category_name':'category','categories':['A','B','C'],'series':[{'name':'Current metric','values':[1,4,7]}]}
    built=api.build_chart(inventory,inventory['slides'][0]['charts'][0]['chart_id'],data,series_map=[0]) if role=='data_page' else api.make_page_contract(inventory,role=role)
    manifest=tmp_path/'manifest';manifest.mkdir()
    (manifest/'native-chart-inventory.json').write_text(json.dumps(inventory))
    folder=manifest/'chart-contracts';folder.mkdir()
    contract=built['contract'] if role=='data_page' else built
    (folder/'page-01.json').write_text(json.dumps(contract))
    (folder/'page-01.bindings.json').write_text(json.dumps(built['bindings'] if role=='data_page' else {}))
    xml=tmp_path/'authoring/slide-01.xml';xml.parent.mkdir()
    xml.write_text('<slide><data>'+built['xml']+'</data></slide>' if role=='data_page' else XML)
    return xml,folder/'page-01.json'

def test_l6_chart_source_palette_is_checked_before_lint_or_remote_write(tmp_path):
    xml,_=chart_inputs(tmp_path);xml.write_text(xml.read_text().replace('rgb(36,81,255)','rgb(211,9,50)'))
    runner=Runner();result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='component_reuse',work_dir=tmp_path,link='L6',runner=runner)
    assert result['status']=='chart_contract_blocked' and not runner.calls
    report=json.loads(Path(result['report_path']).read_text())
    assert any(e['code']=='source_palette_mismatch' for e in report['chart_contract']['errors'])

def test_declared_l6_data_page_cannot_substitute_shape_bars(tmp_path):
    xml,_=chart_inputs(tmp_path);xml.write_text(XML)
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='component_reuse',work_dir=tmp_path,link='L6',runner=Runner())
    assert result['status']=='chart_contract_blocked'

def test_valid_l6_source_chart_is_registered_with_contract_evidence(tmp_path):
    xml,contract=chart_inputs(tmp_path);runner=Runner(READY,SUCCESS)
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='component_reuse',work_dir=tmp_path,link='L6',runner=runner)
    assert result['ok'] and len(runner.calls)==2
    row=json.loads((tmp_path/'published-pages.json').read_text())['pages'][0]
    assert row['chart_contract']['path']==str(contract) and row['chart_contract']['role']=='data_page'

def test_l6_cover_can_have_no_chart_but_cannot_omit_its_source_contract(tmp_path):
    xml,contract=chart_inputs(tmp_path,'cover')
    assert module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,link='L6',runner=Runner(READY,SUCCESS))['ok']
    contract.unlink()
    result=module().publish(validation_policy='strict', presentation='D',xml=xml,page=1,mode='active_rebuild',work_dir=tmp_path,link='L6',runner=Runner())
    assert result['status']=='chart_contract_blocked'

def test_cli_requires_explicit_link_before_any_publication(tmp_path):
    import sys
    xml=tmp_path/'invalid.xml';xml.write_text('<not-slide/>')
    result=subprocess.run([sys.executable,str(SCRIPT),'--presentation','D','--xml',str(xml),'--page','1','--mode','component_reuse','--work-dir',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==2 and '--link' in result.stderr


def test_cross_deck_and_conflicting_explicit_id_are_blocked_before_cli(tmp_path):
    assert invoke(tmp_path, Runner(READY, SUCCESS))['ok']
    for args in [{'presentation': 'OTHER'}, {'slide_id': 'S2'}]:
        runner = Runner()
        out = invoke(tmp_path, runner, **args)
        assert not out['ok'] and not runner.calls
        assert Path(out['report_path']).is_file()


def test_timeout_and_invalid_json_leave_pending_blocking_even_another_page(tmp_path):
    for response in [subprocess.TimeoutExpired('lark-cli', 120),
                     subprocess.CompletedProcess([], 0, '{truncated', '')]:
        case = tmp_path / str(len(list(tmp_path.iterdir()))); case.mkdir()
        assert invoke(case, Runner(READY, response))['status'] == 'write_unknown'
        runner = Runner()
        assert invoke(case, runner, page=2)['status'] == 'recovery_required'
        assert not runner.calls


@pytest.mark.parametrize('preflight', [
    {'ok': True, 'status': 'blocked', 'block_reasons': ['overlap']},
    {'ok': True, 'status': 'preview'}, {'ok': True}, {'ok': False, 'status': 'ready_to_write'},
])
def test_preview_or_nonready_lint_cannot_reach_write(tmp_path, preflight):
    runner = Runner(preflight)
    out = invoke(tmp_path, runner)
    assert not out['ok'] and out['status'] == 'preflight_blocked'
    assert len(runner.calls) == 1
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_response_must_match_update_target_and_deck(tmp_path):
    for data in [{'slide_id': 'WRONG'}, {'slide_id': 'S1', 'xml_presentation_id': 'OTHER'}]:
        case = tmp_path / str(len(list(tmp_path.iterdir()))); case.mkdir()
        out = invoke(case, Runner(READY, {'ok': True, 'data': data}), slide_id='S1')
        assert out['status'] == 'write_unknown'
        assert not (case / 'published-pages.json').exists()


def test_single_page_and_unchanged_xml_required(tmp_path):
    xml = tmp_path / 'authoring' / 'slide-01.xml'; xml.parent.mkdir()
    xml.write_text('<presentation><slide/><slide/></presentation>')
    runner = Runner()
    assert not invoke(tmp_path, runner)['ok'] and not runner.calls
    xml.write_text(XML)
    def change(args, kwargs):
        xml.write_text(XML.replace('真实正文', 'Changed'))
        return READY
    runner = Runner(change)
    out = invoke(tmp_path, runner)
    assert out['status'] == 'input_changed' and len(runner.calls) == 1


def test_success_issues_are_preserved_and_require_readback(tmp_path):
    response = {'ok': True, 'data': {'slide_id': 'S1', 'issues': json.dumps({'warnings': ['check me']})}}
    out = invoke(tmp_path, Runner(READY, response))
    assert out['ok'] and out['requires_readback']
    assert json.loads(Path(out['report_path']).read_text())['write']['decoded_details']['data.issues']['warnings'] == ['check me']


def test_nonzero_process_exit_never_registers_even_with_ok_json(tmp_path):
    out = invoke(tmp_path, Runner(READY, subprocess.CompletedProcess([], 1, json.dumps(SUCCESS), 'broken pipe')))
    assert out['status'] == 'write_unknown'
    assert not (tmp_path / 'published-pages.json').exists()


def test_explicit_business_failure_is_known_even_when_cli_exits_nonzero(tmp_path):
    failure = {'ok': False, 'error': {'code': 4000153, 'message': 'blocked'}}
    out = invoke(tmp_path, Runner(READY, subprocess.CompletedProcess([], 1, json.dumps(failure), '')))
    assert out['status'] == 'write_rejected'
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_returned_id_already_registered_to_another_page_stays_unknown(tmp_path):
    assert invoke(tmp_path, Runner(READY, SUCCESS))['ok']
    out = invoke(tmp_path, Runner(READY, SUCCESS), page=2)
    assert out['status'] == 'write_unknown'
    assert len(json.loads((tmp_path / 'published-pages.json').read_text())['pages']) == 1


def test_concurrent_writer_does_not_enter_preflight_or_overwrite_state(tmp_path):
    import fcntl
    with (tmp_path / 'published-pages.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = Runner()
        out = invoke(tmp_path, runner)
        assert out['status'] == 'publish_in_progress' and not runner.calls


def test_malformed_registry_cannot_be_replaced_with_empty_registry(tmp_path):
    registry = tmp_path / 'published-pages.json'; registry.write_text('{incomplete')
    runner = Runner()
    out = invoke(tmp_path, runner)
    assert not out['ok'] and not runner.calls
    assert registry.read_text() == '{incomplete'


def test_registration_failure_after_ack_keeps_recovery_intent(tmp_path, monkeypatch):
    m = module(); atomic = m._atomic_json
    def disk_full(path, value):
        if path.name == 'published-pages.json':
            raise OSError('disk full')
        return atomic(path, value)
    monkeypatch.setattr(m, '_atomic_json', disk_full)
    xml = tmp_path / 'page.xml'; xml.write_text(XML)
    out = m.publish(validation_policy='strict', presentation='D', xml=xml, page=1, mode='active_rebuild',
                    work_dir=tmp_path, runner=Runner(READY, SUCCESS))
    assert out['status'] == 'write_unknown'
    assert (tmp_path / 'published-pages.pending.json').exists()
    assert json.loads(Path(out['report_path']).read_text())['write']['json'] == SUCCESS


def test_cli_rejects_unsupported_retry_flag(tmp_path, monkeypatch, capsys):
    m = module()
    argv = ['--presentation', 'D', '--xml', 'p.xml', '--page', '1', '--mode',
            'active_rebuild', '--work-dir', str(tmp_path), '--link', 'L4']
    for extra in ['--retry']:
        with pytest.raises(SystemExit):
            m.main(argv + [extra])
    def no_network(**kwargs):
        assert kwargs['page'] == 1 and kwargs['work_dir'] == str(tmp_path)
        return {'ok': True, 'report_path': str(tmp_path / 'report.json')}
    monkeypatch.setattr(m, 'publish', no_network)
    assert m.main(argv) == 0
    assert json.loads(capsys.readouterr().out)['ok']

def test_windows_lock_fallback_uses_same_byte_for_lock_and_unlock(tmp_path, monkeypatch):
    import types
    import sys
    pub = module()
    calls=[]
    fake=types.SimpleNamespace(LK_NBLCK=1,LK_UNLCK=2,locking=lambda fd,mode,n:calls.append((fd,mode,n)))
    monkeypatch.setattr(pub,'fcntl',None)
    monkeypatch.setitem(sys.modules,'msvcrt',fake)
    with (tmp_path/'lock').open('a+') as stream:
        pub._acquire_lock(stream)
        pub._release_lock(stream)
        assert calls==[(stream.fileno(),1,1),(stream.fileno(),2,1)]
        assert (tmp_path/'lock').stat().st_size==1

def test_windows_atomic_write_does_not_open_directory(tmp_path, monkeypatch):
    pub=module()
    original=pub.os.open
    def windows_open(path,*args,**kwargs):
        if Path(path).is_dir():raise PermissionError('Windows directory handle requires a native API')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(pub.sys,'platform','win32')
    monkeypatch.setattr(pub.os,'open',windows_open)
    pub._atomic_json(tmp_path/'state.json',{'safe':True})
    assert json.loads((tmp_path/'state.json').read_text())=={'safe':True}


def exception_fixture(tmp_path, *, code=4000153):
    """Produce a real wrapper rejection artifact using a simulated CLI response."""
    import base64
    rejected = invoke(tmp_path, Runner(READY, {'ok': False, 'error': {'code': code, 'message': 'layout blocked'}}))
    visual = tmp_path / 'preview.png'
    visual.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII='))
    definition = {'rejection_report': rejected['report_path'],
                  'reason': '逐条检查重叠报告及本页预览，蓝色节点与基线相交为设计所需。',
                  'visual_evidence': str(visual)}
    path = tmp_path / 'exception.json'; path.write_text(json.dumps(definition))
    return path, definition


def invoke_exception(tmp_path, runner, exception, **kwargs):
    import inspect
    assert 'exception_file' in inspect.signature(module().publish).parameters, 'bound single-page exception interface is missing'
    return invoke(tmp_path, runner, exception_file=exception, **kwargs)


def test_exception_missing_report_is_rejected_before_cli(tmp_path):
    exception, definition = exception_fixture(tmp_path)
    definition['rejection_report'] = str(tmp_path / 'absent.json')
    exception.write_text(json.dumps(definition))
    runner = Runner()
    out = invoke_exception(tmp_path, runner, exception)
    assert not out['ok'] and not runner.calls
    assert '例外' in out['error'] and Path(out['report_path']).exists()


def test_exception_cannot_follow_changed_xml(tmp_path):
    exception, _ = exception_fixture(tmp_path)
    xml = tmp_path / 'authoring' / 'slide-01.xml'
    xml.write_text(XML.replace('真实正文', '实际修改'))
    runner = Runner()
    out = invoke_exception(tmp_path, runner, exception)
    assert not out['ok'] and not runner.calls
    assert 'XML' in out['error']


@pytest.mark.parametrize('kwargs', [{'page': 2}, {'presentation': 'OTHER'}, {'slide_id': 'S2'}])
def test_exception_cannot_cross_page_deck_or_write_target(tmp_path, kwargs):
    exception, _ = exception_fixture(tmp_path)
    runner = Runner()
    out = invoke_exception(tmp_path, runner, exception, **kwargs)
    assert not out['ok'] and not runner.calls


def test_legal_exception_is_bound_logged_registered_and_single_use(tmp_path):
    exception, definition = exception_fixture(tmp_path)
    runner = Runner(READY, SUCCESS, readback(XML.replace('<slide ', '<slide id="S1" ', 1)))
    out = invoke_exception(tmp_path, runner, exception)
    assert out['ok'] and out['requires_readback']
    assert '--no-lint' in runner.calls[1][0] and '--no-lint' not in runner.calls[0][0]
    report = json.loads(Path(out['report_path']).read_text())
    decision = report['exception']
    assert decision['reason'] == definition['reason']
    assert decision['rejection_report'] == definition['rejection_report']
    assert decision['visual_evidence'] == [definition['visual_evidence']]
    assert report['intent']['exception'] == decision
    assert json.loads((tmp_path / 'published-pages.json').read_text())['pages'][0]['exception'] == decision
    retry = Runner()
    assert not invoke_exception(tmp_path, retry, exception)['ok'] and not retry.calls


@pytest.mark.parametrize('change', ['wrong_code', 'prior_no_lint', 'missing_preflight', 'missing_intent',
                                    'missing_visual', 'bad_visual_type', 'empty_reason', 'missing_payload'])
def test_exception_requires_real_rejection_preflight_and_visual_evidence(tmp_path, change):
    exception, definition = exception_fixture(tmp_path)
    old = Path(definition['rejection_report']); report = json.loads(old.read_text())
    if change == 'wrong_code':
        report['write']['json']['error']['code'] = 500
    elif change == 'prior_no_lint':
        report['write']['command'].append('--no-lint')
    elif change == 'missing_preflight':
        del report['preflight']
    elif change == 'missing_intent':
        del report['intent']
    elif change == 'missing_visual':
        Path(definition['visual_evidence']).unlink()
    elif change == 'bad_visual_type':
        visual = tmp_path / 'text.txt'; visual.write_text('not visual')
        definition['visual_evidence'] = str(visual)
    elif change == 'empty_reason':
        definition['reason'] = '  '
    elif change == 'missing_payload':
        Path(report['intent']['xml']).unlink()
    old.write_text(json.dumps(report)); exception.write_text(json.dumps(definition))
    runner = Runner()
    out = invoke_exception(tmp_path, runner, exception)
    assert not out['ok'] and not runner.calls


def test_exception_still_requires_local_ready_preflight(tmp_path):
    exception, _ = exception_fixture(tmp_path)
    runner = Runner({'ok': True, 'status': 'blocked'})
    out = invoke_exception(tmp_path, runner, exception)
    assert out['status'] == 'preflight_blocked' and len(runner.calls) == 1
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_exception_unknown_result_keeps_pending_and_stops_all_resends(tmp_path):
    exception, _ = exception_fixture(tmp_path)
    out = invoke_exception(tmp_path, Runner(READY, subprocess.TimeoutExpired('lark-cli', 120)), exception)
    assert out['status'] == 'write_unknown'
    runner = Runner()
    assert invoke_exception(tmp_path, runner, exception)['status'] == 'recovery_required'
    assert not runner.calls


def test_cli_passes_exception_file_without_exposing_global_no_lint(tmp_path, monkeypatch, capsys):
    m = module()
    def no_network(**kwargs):
        assert kwargs['exception_file'] == 'exception.json'
        return {'ok': True}
    monkeypatch.setattr(m, 'publish', no_network)
    assert m.main(['--presentation', 'D', '--xml', 'p.xml', '--page', '1', '--mode', 'active_rebuild',
                   '--work-dir', str(tmp_path), '--link', 'L4', '--exception-file', 'exception.json']) == 0


def test_rejected_exception_attempt_also_consumes_prior_rejection(tmp_path):
    exception, _ = exception_fixture(tmp_path)
    rejected = {'ok': False, 'error': {'code': 4000153, 'message': 'still blocked'}}
    out = invoke_exception(tmp_path, Runner(READY, rejected), exception)
    assert out['status'] == 'write_rejected'
    runner = Runner()
    retry = invoke_exception(tmp_path, runner, exception)
    assert not retry['ok'] and not runner.calls
    assert '已用于一次' in retry['error']


def test_exception_does_not_become_a_default_for_later_updates(tmp_path):
    exception, _ = exception_fixture(tmp_path)
    assert invoke_exception(tmp_path, Runner(READY, SUCCESS, readback(XML.replace('<slide ', '<slide id="S1" ', 1))), exception)['ok']
    runner = Runner(READY, SUCCESS)
    assert invoke(tmp_path, runner)['ok']
    assert '--no-lint' not in runner.calls[1][0]
    assert 'exception' not in json.loads((tmp_path / 'published-pages.json').read_text())['pages'][0]


def test_exception_accepts_relative_evidence_paths_and_bound_update(tmp_path):
    assert invoke(tmp_path, Runner(READY, SUCCESS))['ok']
    exception, definition = exception_fixture(tmp_path)
    definition['rejection_report'] = str(Path(definition['rejection_report']).relative_to(tmp_path))
    definition['visual_evidence'] = ['preview.png']
    exception.write_text(json.dumps(definition))
    runner = Runner(READY, SUCCESS, readback(XML.replace('<slide ', '<slide id="S1" ', 1)))
    assert invoke_exception(tmp_path, runner, exception)['ok']
    assert '+update-slide' in runner.calls[1][0] and '--no-lint' in runner.calls[1][0]

# The optional optimistic guard compares actual remote pages, never authored drafts.
ACTUAL = ('<slide id="S1"><style fontFamily="Noto Serif SC" fontSize="30"/>'
          '<note>Speaker notes</note><data><shape id="T1" type="text" topLeftX="20" width="400">'
          '<content><p>' + 'long text ' * 20 + 'end</p></content></shape>'
          '<img id="I1" token="media-old"/><chart id="C1" chartType="bar">'
          '<series name="Revenue"><value>10</value></series></chart>'
          '<table id="B1"><row><cell>42</cell></row></table></data></slide>')


def cache_envelope(xml=ACTUAL, *, deck='D', sid='S1'):
    return {'ok': True, 'data': {'xml_presentation_id': deck, 'scope': 'slide',
                               'slide_id': sid, 'slide': {'slide_id': sid, 'content': xml}}}


def cas_cache(tmp_path, content=None):
    path = tmp_path / 'actual-cache.xml'
    path.write_text(json.dumps(cache_envelope()) if content is None else content)
    return path


def readback(xml=ACTUAL, *, deck='D', sid='S1', file_envelope=False):
    def fetch(args, kwargs):
        assert args[:3] == ['lark-cli', 'slides', '+xml-get']
        assert args[args.index('--presentation') + 1] == 'D'
        assert args[args.index('--slide-id') + 1] == 'S1'
        assert '--no-lint' not in args and '--revision-id' not in args
        output = args[args.index('--output') + 1]
        assert not Path(output).is_absolute() and '..' not in Path(output).parts
        target = Path(kwargs['cwd']) / output
        target.write_text(json.dumps(cache_envelope(xml, deck=deck, sid=sid)) if file_envelope else xml)
        return {'ok': True, 'data': {'xml_presentation_id': deck, 'slide_id': sid,
                                   'scope': 'slide', 'content_saved': True, 'revision_id': 7}}
    return fetch


@pytest.mark.parametrize('live', [
    ACTUAL.replace('end</p>', 'changed after character 60</p>'),
    ACTUAL.replace('Speaker notes', 'Different notes'),
    ACTUAL.replace('Noto Serif SC', 'Arial'),
    ACTUAL.replace('fontSize="30"', 'fontSize="31"'),
    ACTUAL.replace('topLeftX="20"', 'topLeftX="21"'),
    ACTUAL.replace('media-old', 'media-new'),
    ACTUAL.replace('<value>10</value>', '<value>11</value>'),
    ACTUAL.replace('<cell>42</cell>', '<cell>43</cell>'),
])
def test_local_cache_conflicts_compare_full_text_notes_styles_geometry_media_chart_and_table(tmp_path, live):
    cache = cas_cache(tmp_path)
    runner = Runner(READY, readback(live))
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
    assert out['status'] == 'cas_conflict' and not out['ok']
    assert len(runner.calls) == 2 and not any('+update-slide' in args or '+add-slide' in args for args, _ in runner.calls)
    assert not (tmp_path / 'published-pages.pending.json').exists()
    assert not (tmp_path / 'published-pages.json').exists()
    assert json.loads(cache.read_text()) == cache_envelope(live)
    report = json.loads(Path(out['report_path']).read_text())
    assert 'write' not in report and Path(report['cas_pre_readback']['xml_path']).exists()


def test_local_cache_wrapper_revision_and_attribute_order_do_not_conflict(tmp_path):
    cached = '<presentation id="D" revision_id="1">' + ACTUAL + '</presentation>'
    latest = '<presentation revision_id="9" id="D">' + ACTUAL.replace('id="S1"', 'id="S1"') + '</presentation>'
    cache = cas_cache(tmp_path, cached)
    runner = Runner(READY, readback(latest, file_envelope=True), SUCCESS, readback(ACTUAL.replace('end</p>', 'published</p>')))
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
    assert out['ok'] and out['cache_refreshed'] and out['xml_readback_complete']
    assert len(runner.calls) == 4
    write = runner.calls[2][0]
    assert '+update-slide' in write and '--no-lint' not in write and '--revision-id' not in write
    report = json.loads(Path(out['report_path']).read_text())
    assert report['cas']['atomic'] is False
    assert report['cas_pre_readback']['json']['data']['revision_id'] == 7
    assert Path(report['cas_post_readback']['xml_path']).exists()
    assert 'published' in cache.read_text()
    assert not (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('content', [
    json.dumps(cache_envelope(deck='OTHER')),
    json.dumps(cache_envelope(sid='S2')),
    ACTUAL.replace('id="S1"', 'id="S2"', 1),
    ACTUAL.replace(' id="S1"', '', 1),
    '<presentation id="D">' + ACTUAL + '<slide id="S2"/></presentation>',
    '<!DOCTYPE slide [<!ENTITY x "bad">]>' + ACTUAL,
    json.dumps({'unexpected': {'xml': ACTUAL}}),
])
def test_local_cache_wrong_identity_ambiguous_pages_and_unsafe_payload_are_invalid_without_write(tmp_path, content):
    cache = cas_cache(tmp_path, content)
    runner = Runner()
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
    assert out['status'] == 'invalid_input' and not runner.calls
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_local_cache_never_falls_back_to_add_without_an_existing_target_id(tmp_path):
    cache = cas_cache(tmp_path)
    runner = Runner()
    out = invoke(tmp_path, runner, local_cache=cache)
    assert out['status'] == 'invalid_input' and not runner.calls
    assert not (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('get_result', [
    {'ok': False, 'error': {'code': 404}},
    {'ok': True, 'data': {'xml_presentation_id': 'D', 'slide_id': 'S1', 'content_saved': True}},
    readback(deck='OTHER'), readback(sid='S2'), readback('<slide id="S2"/>'),
    subprocess.TimeoutExpired('lark-cli', 180),
])
def test_local_cache_failed_prewrite_readback_does_not_write_or_create_pending(tmp_path, get_result):
    cache = cas_cache(tmp_path)
    before = cache.read_bytes()
    runner = Runner(READY, get_result)
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
    assert out['status'] == 'cas_readback_failed'
    assert len(runner.calls) == 2 and cache.read_bytes() == before
    assert not (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('write_result,status,pending', [
    ({'ok': False, 'error': {'code': 4000153}}, 'write_rejected', False),
    ({'ok': True, 'data': {}}, 'write_content_unconfirmed', True),
    (subprocess.TimeoutExpired('lark-cli', 120), 'write_content_unconfirmed', True),
])
def test_local_cache_write_failure_or_unknown_preserves_once_only_ack_semantics(tmp_path, write_result, status, pending):
    cache = cas_cache(tmp_path)
    before = cache.read_bytes()
    runner = Runner(READY, readback(), write_result, *([readback()] if pending else []))
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
    assert out['status'] == status and len(runner.calls) == (4 if pending else 3)
    assert sum('+update-slide' in args for args, _ in runner.calls) == 1
    assert not any('+add-slide' in args for args, _ in runner.calls)
    assert cache.read_bytes() == before
    assert (tmp_path / 'published-pages.pending.json').exists() is pending
    if pending:
        retry = Runner()
        assert invoke(tmp_path, retry, slide_id='S1', local_cache=cache)['status'] == 'recovery_required'
        assert not retry.calls


def test_local_cache_postwrite_readback_failure_retains_ack_and_blocks_rewrite(tmp_path):
    cache = cas_cache(tmp_path)
    before = cache.read_bytes()
    runner = Runner(READY, readback(), SUCCESS, {'ok': False, 'error': {'code': 503}})
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
    assert out['status'] == 'published_readback_failed' and out['write_acknowledged']
    assert out['requires_readback'] and not out['ok']
    assert cache.read_bytes() == before and len(runner.calls) == 4
    assert json.loads((tmp_path / 'published-pages.json').read_text())['pages'][0]['slide_id'] == 'S1'
    pending = json.loads((tmp_path / 'published-pages.pending.json').read_text())
    assert pending['status'] == 'acknowledged_readback_required'
    retry = Runner()
    recovered = invoke(tmp_path, retry, slide_id='S1', local_cache=cache)
    assert recovered['status'] == 'recovery_required' and recovered['write_acknowledged']
    assert 'ACK' in recovered['error'] and not retry.calls


def test_local_cache_registered_id_and_preflight_are_preserved(tmp_path):
    assert invoke(tmp_path, Runner(READY, SUCCESS))['ok']
    cache = cas_cache(tmp_path, ACTUAL)
    runner = Runner({'ok': True, 'status': 'blocked'})
    out = invoke(tmp_path, runner, local_cache=cache)
    assert out['status'] == 'preflight_blocked' and len(runner.calls) == 1
    runner = Runner(READY, readback(), SUCCESS, readback())
    assert invoke(tmp_path, runner, local_cache=cache)['ok']
    assert runner.calls[2][0][runner.calls[2][0].index('--slide-id') + 1] == 'S1'


def test_cli_passes_optional_local_cache_to_existing_publisher(tmp_path, monkeypatch, capsys):
    m = module()
    def no_network(**kwargs):
        assert kwargs['local_cache'] == 'actual.xml'
        return {'ok': True}
    monkeypatch.setattr(m, 'publish', no_network)
    assert m.main(['--presentation', 'D', '--xml', 'p.xml', '--page', '1', '--mode', 'active_rebuild',
                   '--work-dir', str(tmp_path), '--link', 'L4', '--slide-id', 'S1', '--local-cache', 'actual.xml']) == 0


@pytest.mark.parametrize('change', [
    lambda xml: xml.replace('width="960"', 'width="1000"'),
    lambda xml: xml.replace('background="white"', 'background="black"'),
])
def test_local_cache_presentation_geometry_and_global_styles_remain_in_comparison(tmp_path, change):
    original = '<presentation id="D" width="960"><style background="white"/>' + ACTUAL + '</presentation>'
    cache = cas_cache(tmp_path, original)
    runner = Runner(READY, readback(change(original)))
    assert invoke(tmp_path, runner, slide_id='S1', local_cache=cache)['status'] == 'cas_conflict'
    assert len(runner.calls) == 2 and not (tmp_path / 'published-pages.pending.json').exists()


def test_local_cache_sml_namespace_serialization_and_attribute_order_can_match(tmp_path):
    cache = cas_cache(tmp_path, ACTUAL)
    namespaced = ACTUAL.replace('<slide id="S1">', '<slide xmlns="https://www.larkoffice.com/sml/2.0" id="S1">')
    namespaced = namespaced.replace('id="T1" type="text"', 'type="text" id="T1"')
    runner = Runner(READY, readback(namespaced), SUCCESS, readback(namespaced))
    assert invoke(tmp_path, runner, slide_id='S1', local_cache=cache)['ok']


def test_local_cache_cannot_be_the_authored_payload(tmp_path):
    authored = tmp_path / 'authoring/slide-01.xml'; authored.parent.mkdir()
    authored.write_text(ACTUAL)
    runner = Runner()
    out = invoke(tmp_path, runner, slide_id='S1', local_cache=authored)
    assert out['status'] == 'invalid_input' and not runner.calls
    assert authored.read_text() == ACTUAL


def test_local_cache_cache_disk_failure_after_readback_retains_ack_barrier(tmp_path, monkeypatch):
    cache = cas_cache(tmp_path)
    pub = module(); atomic = pub._atomic_json
    def fail_cache(path, value):
        if path == cache:
            raise OSError('cache disk full')
        atomic(path, value)
    monkeypatch.setattr(pub, '_atomic_json', fail_cache)
    authored = tmp_path / 'authored.xml'; authored.write_text(XML)
    runner = Runner(READY, readback(), SUCCESS, readback())
    out = pub.publish(validation_policy='strict', presentation='D', xml=authored, page=1, mode='component_reuse',
                      work_dir=tmp_path, slide_id='S1', local_cache=cache, runner=runner)
    assert out['status'] == 'published_readback_failed' and out['write_acknowledged']
    assert json.loads((tmp_path / 'published-pages.pending.json').read_text())['status'] == 'acknowledged_readback_required'
    assert Path(json.loads(Path(out['report_path']).read_text())['cas_post_readback']['xml_path']).exists()
    assert sum('+update-slide' in args for args, _ in runner.calls) == 1


def test_local_cache_guard_obeys_existing_workdir_lock(tmp_path):
    import fcntl
    cache = cas_cache(tmp_path)
    with (tmp_path / 'published-pages.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = Runner()
        out = invoke(tmp_path, runner, slide_id='S1', local_cache=cache)
        assert out['status'] == 'publish_in_progress' and not runner.calls


def test_malformed_pending_still_blocks_network_and_retries(tmp_path):
    (tmp_path / 'published-pages.pending.json').write_text('[]')
    runner = Runner()
    assert invoke(tmp_path, runner)['status'] == 'recovery_required'
    assert not runner.calls


def acknowledged_readback_pending(tmp_path):
    cache = cas_cache(tmp_path)
    out = invoke(tmp_path, Runner(READY, readback(), SUCCESS, {'ok': False, 'error': {'code': 503}}),
                 slide_id='S1', local_cache=cache)
    assert out['status'] == 'published_readback_failed'
    return cache, Path(out['report_path'])


def test_recover_readback_fetches_actual_cache_and_clears_only_ack_barrier(tmp_path):
    cache, original_path = acknowledged_readback_pending(tmp_path)
    original_bytes = original_path.read_bytes()
    registry_bytes = (tmp_path / 'published-pages.json').read_bytes()
    actual = ACTUAL.replace('end</p>', 'changed remotely after ACK</p>')
    runner = Runner(readback(actual))
    out = invoke(tmp_path, runner, recover_readback=True)
    assert out['status'] == 'readback_recovered_requires_review'
    assert out['ok'] and out['published'] is False
    assert out['write_acknowledged'] and out['requires_review'] and out['cache_refreshed']
    assert len(runner.calls) == 1 and '+xml-get' in runner.calls[0][0]
    assert not (tmp_path / 'published-pages.pending.json').exists()
    assert json.loads(cache.read_text()) == cache_envelope(actual)
    assert original_path.read_bytes() == original_bytes
    assert (tmp_path / 'published-pages.json').read_bytes() == registry_bytes
    report = json.loads(Path(out['report_path']).read_text())
    assert report['recovery']['original_report_path'] == str(original_path)
    assert report['recovery']['pending']['status'] == 'acknowledged_readback_required'
    assert report['recovery']['original_write']['json'] == SUCCESS
    assert Path(report['cas_recovery_readback']['xml_path']).exists()
    assert 'write' not in report
    retry = Runner()
    again = invoke(tmp_path, retry, recover_readback=True)
    assert again['status'] == 'readback_recovery_refused' and not retry.calls


@pytest.mark.parametrize('failure', [
    {'ok': False, 'error': {'code': 503}}, readback(deck='OTHER'), readback(sid='S2'),
    readback('<slide id="WRONG"/>'), subprocess.TimeoutExpired('lark-cli', 180),
])
def test_recover_readback_failure_or_wrong_remote_identity_keeps_original_barrier(tmp_path, failure):
    cache, _ = acknowledged_readback_pending(tmp_path)
    before_cache = cache.read_bytes()
    before_pending = (tmp_path / 'published-pages.pending.json').read_bytes()
    runner = Runner(failure)
    out = invoke(tmp_path, runner, recover_readback=True)
    assert out['status'] == 'readback_recovery_failed' and out['write_acknowledged']
    assert len(runner.calls) == 1 and '+xml-get' in runner.calls[0][0]
    assert cache.read_bytes() == before_cache
    assert (tmp_path / 'published-pages.pending.json').read_bytes() == before_pending


@pytest.mark.parametrize('kwargs', [
    {'presentation': 'OTHER'}, {'page': 2}, {'slide_id': 'WRONG'}, {'local_cache': 'other-cache.xml'},
])
def test_recover_readback_wrong_caller_identity_never_contacts_service_or_clears_pending(tmp_path, kwargs):
    acknowledged_readback_pending(tmp_path)
    runner = Runner()
    out = invoke(tmp_path, runner, recover_readback=True, **kwargs)
    assert out['status'] == 'readback_recovery_refused' and not runner.calls
    assert (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('change', ['unknown_status', 'tampered_report_ack', 'tampered_payload',
                                    'wrong_registry_id', 'mismatched_pending', 'wrong_payload_path'])
def test_recover_readback_requires_script_ack_original_intent_payload_and_registration(tmp_path, change):
    _, old_path = acknowledged_readback_pending(tmp_path)
    pending_path = tmp_path / 'published-pages.pending.json'
    pending = json.loads(pending_path.read_text())
    if change == 'unknown_status':
        pending['status'] = 'pending'
    elif change == 'tampered_report_ack':
        old = json.loads(old_path.read_text()); old['write']['json']['data']['slide_id'] = 'WRONG'
        old_path.write_text(json.dumps(old))
    elif change == 'tampered_payload':
        Path(pending['xml']).write_text('<slide id="S1"/>')
    elif change == 'wrong_registry_id':
        registry_path = tmp_path / 'published-pages.json'
        registry = json.loads(registry_path.read_text()); registry['pages'][0]['slide_id'] = 'WRONG'
        registry_path.write_text(json.dumps(registry))
    elif change == 'mismatched_pending':
        pending['xml_sha256'] = 'fake'
    elif change == 'wrong_payload_path':
        pending['xml'] = str(tmp_path / 'unrelated.xml')
    pending_path.write_text(json.dumps(pending))
    runner = Runner()
    out = invoke(tmp_path, runner, recover_readback=True)
    assert out['status'] == 'readback_recovery_refused' and not runner.calls
    assert pending_path.exists()


def test_recover_readback_unknown_write_pending_cannot_be_read_or_cleared(tmp_path):
    cache = cas_cache(tmp_path)
    unknown = invoke(tmp_path, Runner(READY, readback(), {'ok': True, 'data': {}}, readback()),
                     slide_id='S1', local_cache=cache)
    assert unknown['status'] == 'write_content_unconfirmed'
    runner = Runner()
    out = invoke(tmp_path, runner, recover_readback=True)
    assert out['status'] == 'readback_recovery_refused' and not runner.calls
    assert (tmp_path / 'published-pages.pending.json').exists()


def test_recover_readback_rejects_different_original_xml_request(tmp_path):
    _, old_path = acknowledged_readback_pending(tmp_path)
    unrelated = tmp_path / 'another.xml'; unrelated.write_text(XML)
    runner = Runner()
    out = module().publish(validation_policy='strict', presentation='D', xml=unrelated, page=1, mode='component_reuse',
                           work_dir=tmp_path, recover_readback=True, runner=runner)
    assert out['status'] == 'readback_recovery_refused' and not runner.calls
    original = json.loads(old_path.read_text())
    out = module().publish(validation_policy='strict', presentation='D', xml=original['intent']['xml'], page=1, mode='component_reuse',
                           work_dir=tmp_path, recover_readback=True, runner=Runner(readback()))
    assert out['status'] == 'readback_recovered_requires_review'


def test_cli_passes_readonly_recover_readback_flag(tmp_path, monkeypatch):
    pub = module()
    def no_network(**kwargs):
        assert kwargs['recover_readback'] is True
        return {'ok': True, 'status': 'readback_recovered_requires_review',
                'requires_review': True, 'published': False}
    monkeypatch.setattr(pub, 'publish', no_network)
    assert pub.main(['--presentation', 'D', '--xml', 'p.xml', '--page', '1', '--mode', 'component_reuse',
                     '--work-dir', str(tmp_path), '--link', 'L4', '--recover-readback', '--strict']) == 0


def test_recover_readback_persists_ack_and_new_read_evidence_before_removing_barrier(tmp_path, monkeypatch):
    _, original_path = acknowledged_readback_pending(tmp_path)
    pending_path = tmp_path / 'published-pages.pending.json'
    pub = module(); unlink = pub.Path.unlink
    def check_evidence_before_unlink(path, *args, **kwargs):
        if path == pending_path:
            recovery_reports = [json.loads(p.read_text()) for p in (tmp_path / 'publish-reports').glob('*.json')
                                if p != original_path and 'recovery' in json.loads(p.read_text())]
            assert len(recovery_reports) == 1
            report = recovery_reports[0]
            assert report['result']['status'] == 'readback_recovered_requires_review'
            assert report['recovery']['original_write']['json'] == SUCCESS
            assert Path(report['cas_recovery_readback']['xml_path']).exists()
        return unlink(path, *args, **kwargs)
    monkeypatch.setattr(pub.Path, 'unlink', check_evidence_before_unlink)
    out = pub.publish(validation_policy='strict', presentation='D', xml=tmp_path / 'authoring/slide-01.xml', page=1,
                      mode='component_reuse', work_dir=tmp_path, recover_readback=True, runner=Runner(readback()))
    assert out['status'] == 'readback_recovered_requires_review' and not pending_path.exists()


def test_recover_readback_cache_write_failure_preserves_ack_pending(tmp_path, monkeypatch):
    cache, _ = acknowledged_readback_pending(tmp_path)
    pub = module(); atomic = pub._atomic_json
    def disk_failure(path, value):
        if path == cache:
            raise OSError('cache disk full')
        return atomic(path, value)
    monkeypatch.setattr(pub, '_atomic_json', disk_failure)
    runner = Runner(readback())
    out = pub.publish(validation_policy='strict', presentation='D', xml=tmp_path / 'authoring/slide-01.xml', page=1,
                      mode='component_reuse', work_dir=tmp_path, recover_readback=True, runner=runner)
    assert out['status'] == 'readback_recovery_failed' and out['write_acknowledged']
    assert (tmp_path / 'published-pages.pending.json').exists()
    assert len(runner.calls) == 1 and '+xml-get' in runner.calls[0][0]


def test_recover_readback_wrong_mode_preserves_pending_without_network(tmp_path):
    acknowledged_readback_pending(tmp_path)
    runner = Runner()
    out = module().publish(validation_policy='strict', presentation='D', xml=tmp_path / 'authoring/slide-01.xml', page=1,
                           mode='active_rebuild', work_dir=tmp_path, recover_readback=True, runner=runner)
    assert out['status'] == 'readback_recovery_refused' and not runner.calls
    assert (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('case', ['get_failure', 'wrong_identity', 'unknown_write'])
def test_cli_recovery_failures_remain_nonzero_and_keep_barrier(tmp_path, monkeypatch, capsys, case):
    if case == 'unknown_write':
        cache = cas_cache(tmp_path)
        out = invoke(tmp_path, Runner(READY, readback(), {'ok': True, 'data': {}}, readback()),
                     slide_id='S1', local_cache=cache)
        assert out['status'] == 'write_content_unconfirmed'
    else:
        acknowledged_readback_pending(tmp_path)
    pub = module()
    runner = Runner({'ok': False, 'error': {'code': 503}}) if case == 'get_failure' else Runner()
    monkeypatch.setattr(pub.subprocess, 'run', runner)
    argv = ['--presentation', 'D', '--xml', str(tmp_path / 'authoring/slide-01.xml'),
            '--page', '1', '--mode', 'component_reuse', '--work-dir', str(tmp_path),
            '--link', 'L4', '--recover-readback', '--strict']
    if case == 'wrong_identity':
        argv += ['--slide-id', 'WRONG']
    assert pub.main(argv) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['ok'] is False
    assert result['status'] == ('readback_recovery_failed' if case == 'get_failure' else 'readback_recovery_refused')
    assert (tmp_path / 'published-pages.pending.json').exists()
    assert all('+xml-get' in args for args, _ in runner.calls)
