"""Regression controls for real empty-cover, response and source-bleed failures."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from test_template_publish import module, invoke, Runner, READY, SUCCESS, XML, readback
from test_source_decoration_review import api, fixture

ACTUAL = XML.replace('<slide ', '<slide id="S1" ', 1)


def test_stderr_rejection_is_not_unknown_or_retried(tmp_path):
    failure = {'ok': False, 'error': {'code': 4000153, 'message': 'real rejection'}}
    runner = Runner(READY, subprocess.CompletedProcess([], 1, '', json.dumps(failure)))
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['status'] == 'write_rejected' and len(runner.calls) == 2
    assert not (tmp_path / 'published-pages.pending.json').exists()
    report = json.loads(Path(result['report_path']).read_text())
    assert report['write']['json_source'] == 'stderr'


@pytest.mark.parametrize('actual', ['<slide id="S1"><data/></slide>', ACTUAL.replace('真实正文', '旧内容')])
def test_existing_id_with_empty_or_old_content_never_recovers(tmp_path, actual):
    runner = Runner(READY, subprocess.TimeoutExpired('write', 120), readback(actual))
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['status'] == 'write_content_unconfirmed' and not result['ok']
    assert not (tmp_path / 'published-pages.json').exists()
    assert (tmp_path / 'published-pages.pending.json').exists()
    assert sum('+update-slide' in args for args, _ in runner.calls) == 1


def test_timeout_with_exact_actual_content_restores_real_registry(tmp_path):
    runner = Runner(READY, subprocess.TimeoutExpired('write', 120), readback(ACTUAL))
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['ok'] and result['status'] == 'published_recovered_requires_review'
    row = json.loads((tmp_path / 'published-pages.json').read_text())['pages'][0]
    assert row['slide_id'] == 'S1' and row['xml_sha256'] == hashlib.sha256(XML.encode()).hexdigest()
    assert 'content_readback' in row and not (tmp_path / 'published-pages.pending.json').exists()
    assert len(runner.calls) == 3


def test_later_read_only_recovery_never_resends_or_overwrites_old_report(tmp_path):
    initial = invoke(tmp_path, Runner(READY, subprocess.TimeoutExpired('write', 120), readback('<slide id="S1"/>')), slide_id='S1')
    original = Path(initial['report_path']).read_bytes()
    runner = Runner(readback(ACTUAL))
    result = invoke(tmp_path, runner, slide_id='S1', recover_write=True)
    assert result['ok'] and len(runner.calls) == 1
    assert runner.calls[0][0][2] == '+xml-get'
    assert Path(initial['report_path']).read_bytes() == original


def test_modified_pending_payload_cannot_be_recovered(tmp_path):
    invoke(tmp_path, Runner(READY, subprocess.TimeoutExpired('write', 120), readback('<slide id="S1"/>')), slide_id='S1')
    pending = json.loads((tmp_path / 'published-pages.pending.json').read_text())
    Path(pending['xml']).write_text(XML.replace('真实正文', '改过的内容'))
    runner = Runner()
    result = invoke(tmp_path, runner, slide_id='S1', recover_write=True)
    assert not result['ok'] and not runner.calls
    assert (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('change', ['width="10"', 'src="media-new"'])
def test_same_text_with_changed_geometry_or_media_does_not_match(change):
    expected = '<slide><data><img id="I" width="20" src="media-old"/></data></slide>'
    actual = expected.replace('width="20"', change) if change.startswith('width') else expected.replace('src="media-old"', change)
    assert not module()._payload_matches(expected, actual)


def test_server_id_remapping_keeps_reference_structure():
    expected = '<slide><data><shape id="A" width="20"/><shape id="B" width="30"/><line startShapeId="A" endShapeId="B"/></data></slide>'
    actual = expected.replace('"A"', '"X"').replace('"B"', '"Y"')
    assert module()._payload_matches(expected, actual)
    assert not module()._payload_matches(expected, actual.replace('endShapeId="Y"', 'endShapeId="X"'))


def test_source_visual_derives_ids_without_moving_geometry(tmp_path):
    s, a, _, strict = fixture(tmp_path)
    before = a.read_bytes()
    result = api().review_source_visual(strict, strict, a, s, [tmp_path / 'source.png'])
    assert result['ok'] and result['remaining_error_count'] == 0
    assert result['declaration']['element_ids'] == ['circle'] and a.read_bytes() == before


def test_source_visual_cannot_hide_text_new_overflow_or_missing_evidence(tmp_path):
    s, a, _, strict = fixture(tmp_path)
    a.write_text(a.read_text().replace('topLeftX="-30"', 'topLeftX="-40"'))
    result = api().review_source_visual(strict, strict, a, s, [tmp_path / 'source.png'])
    assert result['remaining_error_count'] == 1 and not result['reviewed']
    assert not api().review_source_visual(strict, strict, a, s, [tmp_path / 'missing.png'])['ok']


def rejection_and_preflight(tmp_path, extra=False):
    visual = tmp_path / 'source.png'; visual.write_bytes(b'reviewed source image')
    issue = {'code': 'shape_out_of_canvas', 'level': 'error', 'elements': ['circle'],
             'canvas': {'width': 960, 'height': 540}, 'bbox': {'x': -30, 'y': 0, 'width': 100, 'height': 100}}
    errors = [issue]
    if extra:
        errors.append({'code': 'text_overflows_container', 'level': 'error', 'elements': ['title']})
    report = {'summary': {'error_count': len(errors), 'warning_count': 0, 'info_count': 0,
                          'slide_count': 1, 'status': 'blocked'},
              'document': {'errors': [], 'warnings': [], 'infos': []},
              'slides': [{'slide_number': 1, 'errors': errors, 'warnings': [], 'infos': []}]}
    member = {'element_id': 'circle', 'code': issue['code'], 'canvas': issue['canvas'], 'bbox': issue['bbox'],
              'visual_evidence_sha256': {str(visual): hashlib.sha256(visual.read_bytes()).hexdigest()}}
    ready = {**READY, 'checks': {'source_decoration_review': {'ok': True, 'reviewed': [member]}}}
    failure = {'ok': False, 'error': {'code': 4000153, 'message': json.dumps(report)}}
    return ready, failure


def test_only_reviewed_bleed_gets_one_bound_retry_and_actual_readback(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path)
    runner = Runner(ready, subprocess.CompletedProcess([], 1, '', json.dumps(failure)), SUCCESS, readback(ACTUAL))
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['ok'] and result['xml_readback_complete']
    writes = [args for args, _ in runner.calls if '+update-slide' in args]
    assert len(writes) == 2 and '--no-lint' not in writes[0] and '--no-lint' in writes[1]
    report = json.loads(Path(result['report_path']).read_text())
    original = json.loads(Path(report['source_decoration_retry_of']).read_text())
    assert original['result']['status'] == 'write_rejected'
    assert original['write']['json_source'] == 'stderr'
    assert (tmp_path / 'published-pages.pending.json').exists() is False


def test_unrelated_server_error_does_not_get_decoration_exception(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path, extra=True)
    runner = Runner(ready, failure)
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['status'] == 'write_rejected' and len(runner.calls) == 2
    assert not any('--no-lint' in args for args, _ in runner.calls)


def test_second_rejection_is_terminal_no_third_write(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path)
    runner = Runner(ready, failure, failure)
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['status'] == 'write_rejected' and len(runner.calls) == 3


def test_ack_but_empty_exception_cover_remains_blocked(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path)
    runner = Runner(ready, failure, SUCCESS, readback('<slide id="S1"><data/></slide>'))
    result = invoke(tmp_path, runner, slide_id='S1')
    assert result['status'] == 'published_content_unconfirmed' and not result['ok']
    assert (tmp_path / 'published-pages.pending.json').exists()
    recover = invoke(tmp_path, Runner(readback(ACTUAL)), recover_readback=True)
    assert recover['ok'] and not (tmp_path / 'published-pages.pending.json').exists()


def test_general_recovery_flag_routes_ack_barrier_to_read_only_recovery(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path)
    invoke(tmp_path, Runner(ready, failure, SUCCESS, readback('<slide id="S1"><data/></slide>')), slide_id='S1')
    runner = Runner(readback(ACTUAL))
    result = invoke(tmp_path, runner, slide_id='S1', recover_write=True)
    assert result['ok'] and result['status'] == 'readback_recovered_requires_review'
    assert len(runner.calls) == 1 and runner.calls[0][0][2] == '+xml-get'
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_general_recovery_flag_keeps_ack_barrier_when_content_still_wrong(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path)
    invoke(tmp_path, Runner(ready, failure, SUCCESS, readback('<slide id="S1"><data/></slide>')), slide_id='S1')
    runner = Runner(readback('<slide id="S1"><data/></slide>'))
    result = invoke(tmp_path, runner, slide_id='S1', recover_write=True)
    assert result['status'] == 'readback_recovery_failed'
    assert len(runner.calls) == 1 and runner.calls[0][0][2] == '+xml-get'
    assert (tmp_path / 'published-pages.pending.json').exists()


def test_late_page_is_inserted_before_already_registered_ending(tmp_path):
    ending = {'ok': True, 'data': {'slide_id': 'ENDING', 'xml_presentation_id': 'D'}}
    assert invoke(tmp_path, Runner(READY, ending), page=10)['ok']
    body = {'ok': True, 'data': {'slide_id': 'BODY5', 'xml_presentation_id': 'D'}}
    runner = Runner(READY, body)
    assert invoke(tmp_path, runner, page=5)['ok']
    command = runner.calls[1][0]
    assert command[command.index('--before-slide-id') + 1] == 'ENDING'
    state = json.loads((tmp_path / 'published-pages.json').read_text())
    assert [(r['page'], r['slide_id']) for r in state['pages']] == [(5, 'BODY5'), (10, 'ENDING')]
