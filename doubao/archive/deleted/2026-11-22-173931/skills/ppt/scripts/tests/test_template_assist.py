"""Optional template assistance never exports while its current writers still own pages."""
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import multiagent_sync as ms


def _put(path, text, at):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    os.utime(path, (at, at))
    return path


def _assist(tmp_path, monkeypatch, *, age=20):
    calls = []
    monkeypatch.setattr(ms, '_export_pptx', lambda *args: calls.append(args) or
                        {'ok': True, 'pptx': str(tmp_path/'deck.pptx')})
    ms.dispatch(tmp_path, 'template', template_assist=True)
    path = tmp_path/'.lark-slides/template-assist-dispatch.json'
    rec = json.loads(path.read_text())
    rec.update(template_assist=True, t=time.time()-age)
    path.write_text(json.dumps(rec))
    work = tmp_path/'.lark-slides/template/deck1'
    work.mkdir(parents=True)
    return work, rec['t'], calls


def _summary(work, at):
    return _put(work/'.lark-slides/organizer/return-summary.md', 'All assigned writers stopped; returned.', at)


def _assignment(work, at, name='p3'):
    return _put(work/f'.lark-slides/organizer/assignments/{name}.json',
                json.dumps({'deck_xml_presentation_id':'D', 'pages':[{'page':3,'slide_id':'s3'}]}), at)


@pytest.mark.parametrize('who', ['main', 'solo', 'lead'])
def test_assist_missing_summary_cannot_export_even_first_draft_or_role_override(tmp_path, monkeypatch, who):
    work, _, calls = _assist(tmp_path, monkeypatch)
    out = ms.export('D', work, who=who)
    assert out['ok'] is False
    assert out['code'] == 'template_assist_pending'
    assert not calls
    assert not (work/'.lark-slides/closing.json').exists()


def test_assist_never_treats_elapsed_window_or_old_dispatch_as_return(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch, age=ms.TEMPLATE_GATE_MAX_AGE+100)
    _put(work/'.lark-slides/closing.json', json.dumps({'t':stamp,'to':['organizer'],'minutes':3}), stamp)
    out = ms.export('D', tmp_path, who='main')
    assert out['ok'] is False and out['code'] == 'template_assist_pending'
    assert not calls


def test_assist_current_nonempty_summary_allows_final_export(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _assignment(work, stamp+3)
    summary = _summary(work, stamp+6)
    out = ms.export('D', work, who='main')
    assert out['ok'] and out['organizer_returned']
    assert out['return_summary'] == str(summary.resolve())
    assert len(calls) == 1 and 'draft' not in out and 'organizer_timed_out' not in out


def test_assist_stale_or_empty_summary_cannot_release_writers(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    summary = _summary(work, stamp-1)
    assert ms.export('D', work, who='main')['ok'] is False
    _put(summary, '', stamp+5)
    assert ms.export('D', work, who='main')['ok'] is False
    assert not calls


def test_assist_new_assignment_invalidates_previous_summary_until_return(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _assignment(work, stamp+1)
    summary = _summary(work, stamp+3)
    _assignment(work, stamp+8, name='p5')
    out = ms.export('D', tmp_path, who='main')
    assert out['ok'] is False and not calls
    _put(summary, 'p3 and p5 writers stopped and returned.', stamp+9)
    assert ms.export('D', tmp_path, who='main')['ok'] is True
    assert len(calls) == 1


def test_assist_unrelated_workdir_summary_does_not_complete_assigned_work(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _assignment(work, stamp+2)
    other = tmp_path/'.lark-slides/template/another-deck'
    _summary(other, stamp+5)
    assert ms.export('D', tmp_path, who='main')['ok'] is False
    assert not calls


def test_no_dispatch_single_main_and_normal_strategy_export_still_work(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ms, '_export_pptx', lambda *args: calls.append(args) or
                        {'ok': True, 'pptx': str(tmp_path/'deck.pptx')})
    assert ms.export('D', tmp_path, who='main')['ok']
    result = ms.dispatch(tmp_path, 'strategy')
    assert Path(result['sync']).is_dir()
    assert ms.export('D', tmp_path, who='main')['ok']
    assert len(calls) == 2


def test_assist_dispatch_cli_registers_scope_without_retiring_strategy(tmp_path, capsys):
    strategy = ms.dispatch(tmp_path, 'strategy')
    sync = Path(strategy['sync'])
    status_before = (sync/'status.json').read_bytes()
    rc = ms.main(['dispatch','--cwd',str(tmp_path),'--flow','template','--template-assist'])
    assert rc == 0
    record = json.loads((tmp_path/'.lark-slides/template-assist-dispatch.json').read_text())
    assert record['template_assist'] is True and 'sync' not in record
    assert (sync/'status.json').read_bytes() == status_before
    assert not (sync/'abandoned').exists()
    role = ms.role(tmp_path, marker='template')
    assert role['role'] == 'organizer' and role['template_assist'] is True
    assert role['scope'] == 'assigned_pages' and 'sync' not in role
    document = Path(role['doc'])
    assert document.is_file()
    assert document == ms._SKILL_ROOT / 'SKILL.md'
    assert 'doc_section' not in role


def test_assist_flag_is_invalid_for_strategy_without_any_mutation(tmp_path):
    with pytest.raises(SystemExit):
        ms.main(['dispatch','--cwd',str(tmp_path),'--flow','strategy','--template-assist'])
    assert not (tmp_path/'.lark-slides/dispatch.json').exists()


def test_unscoped_legacy_role_does_not_create_lead_or_retire_other_tasks(tmp_path):
    sync = tmp_path / '.lark-slides/strategy/existing/sync'
    status = sync / 'status.json'
    status.parent.mkdir(parents=True)
    status.write_text(json.dumps({'task_flow': 'strategy', 'phase': 'pages_in_progress'}))
    before = status.read_bytes()
    result = ms.role(tmp_path)
    assert result['role'] == 'lead'  # compatibility label, not a new workflow
    assert Path(result['doc']) == ms._SKILL_ROOT / 'SKILL.md'
    assert Path(result['doc']).is_file()
    assert result['legacy_role'] is True
    assert result['sync_by_flow'] == {}
    assert status.read_bytes() == before
    assert not (tmp_path / '.lark-slides/lead.json').exists()
    assert list((tmp_path / '.lark-slides/strategy').iterdir()) == [sync.parent]


def test_legacy_lead_metadata_is_read_without_refresh_or_new_task(tmp_path):
    record = tmp_path / '.lark-slides/lead.json'
    record.parent.mkdir(parents=True)
    previous = {'t': 0, 'sync': {'strategy': str(tmp_path / 'previous/sync')}}
    record.write_text(json.dumps(previous))
    before = record.read_bytes()
    assert ms.lead_syncs(tmp_path) == previous['sync']
    assert record.read_bytes() == before
    assert not (tmp_path / '.lark-slides/strategy').exists()
    assert not (tmp_path/'.lark-slides/strategy').exists()


def test_assist_cannot_close_dispatch_to_bypass_missing_return(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _assignment(work, stamp+1)
    out = ms.dispatch(tmp_path, 'template', close=True, template_assist=True)
    assert out['ok'] is False
    record = json.loads((tmp_path/'.lark-slides/template-assist-dispatch.json').read_text())
    assert not record.get('closed')
    assert ms.export('D', work, who='main')['ok'] is False and not calls
    _summary(work, stamp+4)
    assert ms.dispatch(tmp_path, 'template', close=True, template_assist=True)['ok'] is True


def test_assist_old_open_dispatch_retains_assigned_scope_instead_of_becoming_lead(tmp_path, monkeypatch):
    _, _, _ = _assist(tmp_path, monkeypatch, age=ms.DISPATCH_FRESH+100)
    role = ms.role(tmp_path, marker='template')
    assert role['role'] == 'organizer' and role['scope'] == 'assigned_pages'
    assert 'sync' not in role


def test_assist_for_explicit_deck_d_does_not_hold_unrelated_deck_e(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _assignment(work, stamp+1)
    out = ms.export('E', tmp_path, who='main')
    assert out['ok'] is True and len(calls) == 1
    assert ms.export('D', work, who='main')['ok'] is False
    assert len(calls) == 1


def test_assist_request_without_trustworthy_deck_identity_stays_fail_closed(tmp_path, monkeypatch):
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _put(work/'.lark-slides/organizer/assignments/p3.json', '{invalid', stamp+1)
    assert ms.export('E', tmp_path, who='main')['ok'] is False and not calls


def test_strategy_role_keeps_original_sync_when_template_assist_starts(tmp_path):
    strategy = ms.dispatch(tmp_path, 'strategy')
    ms.dispatch(tmp_path, 'template', template_assist=True)
    role = ms.role(tmp_path, marker='strategy')
    assert role['role'] == 'organizer' and role['flow'] == 'strategy'
    assert role['sync'] == strategy['sync']
    template_role = ms.role(tmp_path, marker='template')
    assert template_role['role'] == 'organizer' and template_role['scope'] == 'assigned_pages'
    assert 'sync' not in template_role


def test_closing_assist_keeps_strategy_dispatch_and_sync_open(tmp_path, monkeypatch):
    strategy = ms.dispatch(tmp_path, 'strategy')
    global_path = tmp_path/'.lark-slides/dispatch.json'
    record_before = global_path.read_bytes()
    sync = Path(strategy['sync'])
    status_before = (sync/'status.json').read_bytes()
    work, stamp, _ = _assist(tmp_path, monkeypatch)
    assert global_path.read_bytes() == record_before
    _assignment(work, stamp+1)
    _summary(work, stamp+4)
    assert ms.dispatch(tmp_path, 'template', close=True, template_assist=True)['ok'] is True
    assert global_path.read_bytes() == record_before
    assert (sync/'status.json').read_bytes() == status_before
    closed_role = ms.role(tmp_path, marker='template')
    assert closed_role['ok'] is False and closed_role['code'] == 'template_assist_closed'
    assert (sync/'status.json').read_bytes() == status_before
    role = ms.role(tmp_path, marker='strategy')
    assert role['role'] == 'organizer' and role['flow'] == 'strategy' and role['sync'] == strategy['sync']


def test_legacy_close_only_closes_global_dispatch_not_open_assist(tmp_path, monkeypatch):
    ms.dispatch(tmp_path, 'strategy')
    work, stamp, calls = _assist(tmp_path, monkeypatch)
    _assignment(work, stamp+1)
    assert ms.dispatch(tmp_path, None, close=True)['ok'] is True
    assist = json.loads((tmp_path/'.lark-slides/template-assist-dispatch.json').read_text())
    assert not assist.get('closed')
    assert ms.export('D', work, who='main')['ok'] is False and not calls
